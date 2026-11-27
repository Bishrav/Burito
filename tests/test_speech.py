import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from burito import speech


class SpeechTests(unittest.TestCase):
    def test_rejects_unsupported_audio_language_and_size_before_process(self):
        with patch("burito.speech.subprocess.run") as run:
            for audio, mime, language in [
                    (b"audio", "text/plain", "en"),
                    (b"audio", "audio/webm", "fr"),
                    (b"x" * (speech.MAX_AUDIO_BYTES + 1), "audio/webm", "en")]:
                with self.subTest(mime=mime, language=language), self.assertRaises(ValueError):
                    speech.transcribe(audio, mime, language)
            run.assert_not_called()

    def test_reports_missing_local_runtime_without_network_fallback(self):
        missing = Path("/no/such/burito-speech-runtime")
        with patch.dict(os.environ, {}, clear=True), patch("burito.speech.shutil.which", return_value=None), \
             patch.object(speech, "DEFAULT_WHISPER", missing), patch.object(speech, "DEFAULT_MODEL", missing):
            self.assertFalse(speech.available())
            with self.assertRaises(speech.SpeechUnavailable):
                speech.transcribe(b"audio", "audio/webm")

    def test_model_on_brain_requires_the_verified_mount(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            model_dir = root / "models/audio"
            model_dir.mkdir(parents=True)
            ffmpeg, whisper = root / "ffmpeg", root / "whisper-cli"
            for executable in (ffmpeg, whisper):
                executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                executable.chmod(0o700)
            model = model_dir / "ggml-base.bin"
            model.write_bytes(b"synthetic model")
            with patch.dict(os.environ, {
                    "BURITO_FFMPEG": str(ffmpeg), "BURITO_WHISPER_CLI": str(whisper),
                    "BURITO_WHISPER_MODEL": str(model)}, clear=True), \
                 patch.object(speech, "BRAIN_MOUNT", root), patch.object(speech, "brain_available", return_value=False), \
                 patch("burito.speech.subprocess.run") as run:
                with self.assertRaisesRegex(speech.SpeechUnavailable, "brain volume"):
                    speech.transcribe(b"audio", "audio/webm")
                run.assert_not_called()

    def test_normalizes_locally_and_removes_temporary_audio_and_transcript(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            binaries = {}
            for name in ("ffmpeg", "whisper-cli"):
                path = root / name
                path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                path.chmod(0o700)
                binaries[name] = path
            model = root / "ggml-base.bin"
            model.write_bytes(b"synthetic model marker")
            seen = []

            def run(command, **kwargs):
                seen.append(command)
                if command[0] == str(binaries["ffmpeg"]):
                    Path(command[-1]).write_bytes(b"synthetic wav")
                else:
                    prefix = Path(command[command.index("-of") + 1])
                    prefix.with_suffix(".txt").write_text("  synthetic transcript  ", encoding="utf-8")

            env = {
                "BURITO_FFMPEG": str(binaries["ffmpeg"]),
                "BURITO_WHISPER_CLI": str(binaries["whisper-cli"]),
                "BURITO_WHISPER_MODEL": str(model),
            }
            with patch.dict(os.environ, env, clear=True), patch("burito.speech.subprocess.run", side_effect=run):
                self.assertTrue(speech.available())
                self.assertEqual(speech.transcribe(b"synthetic webm", "audio/webm;codecs=opus", "auto"),
                                 "synthetic transcript")
            self.assertEqual(len(seen), 2)
            self.assertIn("-l", seen[1])
            self.assertEqual(seen[1][seen[1].index("-l") + 1], "auto")
            self.assertFalse(Path(seen[0][-1]).exists())
            self.assertFalse(Path(seen[1][seen[1].index("-of") + 1] + ".txt").exists())


if __name__ == "__main__":
    unittest.main()

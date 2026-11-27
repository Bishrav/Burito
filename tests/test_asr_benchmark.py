from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import wave
from unittest.mock import patch

from scripts.benchmark_local_asr import edit_distance, evaluate


class AsrBenchmarkTests(unittest.TestCase):
    def test_edit_distance_counts_substitution_insertion_and_deletion(self):
        self.assertEqual(edit_distance("kitten", "sitting"), 3)
        self.assertEqual(edit_distance(["ask", "not"], ["ask", "what", "not"]), 1)

    def test_rejects_empty_reference_before_running_transcription(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recording = root / "silence.wav"
            with wave.open(str(recording), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(16000)
                audio.writeframes(b"\0\0" * 16000)
            manifest = root / "samples.tsv"
            manifest.write_text("silence.wav\ten\t  \n", encoding="utf-8")
            with patch("scripts.benchmark_local_asr.transcribe") as transcribe:
                with self.assertRaisesRegex(ValueError, "reference text must not be empty"):
                    evaluate(manifest)
                transcribe.assert_not_called()

    def test_reports_child_peak_rss_for_the_whole_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recording = root / "sample.wav"
            with wave.open(str(recording), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(16000)
                audio.writeframes(b"\0\0" * 16000)
            manifest = root / "samples.tsv"
            manifest.write_text("sample.wav\ten\thello\nsample.wav\thi\thello\n", encoding="utf-8")
            usage = [SimpleNamespace(ru_utime=0, ru_stime=0, ru_maxrss=512),
                     SimpleNamespace(ru_utime=1, ru_stime=1, ru_maxrss=2048),
                     SimpleNamespace(ru_utime=1, ru_stime=1, ru_maxrss=2048),
                     SimpleNamespace(ru_utime=2, ru_stime=1, ru_maxrss=4096)]
            with patch("scripts.benchmark_local_asr.transcribe", return_value="hello"), \
                 patch("scripts.benchmark_local_asr.resource.getrusage", side_effect=usage):
                result = evaluate(manifest)
            self.assertEqual(result["evaluation_peak_child_rss_mib"], 4)
            self.assertNotIn("child_peak_rss_mib", result["languages"]["en"])


if __name__ == "__main__":
    unittest.main()

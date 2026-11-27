"""Bounded local speech transcription through the optional whisper.cpp CLI."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .memory import BRAIN_MOUNT, brain_available

REPOSITORY = Path(__file__).resolve().parents[1]
DEFAULT_WHISPER = REPOSITORY / ".tools/whisper.cpp/build/bin/whisper-cli"
DEFAULT_MODEL = BRAIN_MOUNT / "models/audio/ggml-base.bin"
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_AUDIO_SECONDS = 15
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/wav", "audio/x-wav"}
ALLOWED_LANGUAGES = {"en", "ne", "hi", "auto"}


class SpeechUnavailable(RuntimeError):
    """The optional local transcription runtime is not configured or ready."""


def available():
    try:
        _configured_file("BURITO_FFMPEG", "ffmpeg", executable=True)
        _configured_file("BURITO_WHISPER_CLI", "whisper-cli", default_path=DEFAULT_WHISPER, executable=True)
        _configured_file("BURITO_WHISPER_MODEL", "", default_path=DEFAULT_MODEL, executable=False)
    except SpeechUnavailable:
        return False
    return True


def _configured_file(variable, default_name, *, default_path=None, executable=False):
    configured = os.environ.get(variable)
    found = configured
    if not found and default_path is not None and default_path.is_file():
        found = str(default_path)
    if not found and default_name:
        found = shutil.which(default_name)
    if not found:
        raise SpeechUnavailable(f"Local speech recognition is unavailable: {default_name} was not found.")
    path = Path(found)
    if variable == "BURITO_WHISPER_MODEL":
        try:
            brain_relative = path.absolute().relative_to(BRAIN_MOUNT)
        except ValueError:
            brain_relative = None
        if brain_relative is not None:
            if ".." in brain_relative.parts or BRAIN_MOUNT.is_symlink() or not brain_available():
                raise SpeechUnavailable("The configured brain volume is not verified and writable.")
            current = BRAIN_MOUNT
            for part in brain_relative.parts:
                current = current / part
                if current.is_symlink():
                    raise SpeechUnavailable("The configured brain model path contains a symlink.")
    try:
        info = path.lstat()
    except OSError as error:
        raise SpeechUnavailable(f"Local speech recognition is unavailable: {variable} is inaccessible.") from error
    if path.is_symlink() or not path.is_file() or (executable and not os.access(path, os.X_OK)):
        raise SpeechUnavailable(f"Local speech recognition is unavailable: {variable} is not a regular usable file.")
    if not executable and info.st_size == 0:
        raise SpeechUnavailable(f"Local speech recognition is unavailable: {variable} is empty.")
    return str(path.resolve())


def transcribe(audio, content_type, language="en"):
    """Transcribe a bounded encoded audio body; retain all intermediates only temporarily."""
    mime_type = content_type.split(";", 1)[0].strip().lower()
    if mime_type not in ALLOWED_AUDIO_TYPES:
        raise ValueError("Use a supported audio recording format.")
    if not isinstance(audio, bytes) or not audio or len(audio) > MAX_AUDIO_BYTES:
        raise ValueError("Audio recording is empty or exceeds the 8 MiB limit.")
    if language not in ALLOWED_LANGUAGES:
        raise ValueError("Choose English, Nepali, Hindi, or automatic language detection.")

    ffmpeg = _configured_file("BURITO_FFMPEG", "ffmpeg", executable=True)
    whisper = _configured_file("BURITO_WHISPER_CLI", "whisper-cli", default_path=DEFAULT_WHISPER, executable=True)
    model = _configured_file("BURITO_WHISPER_MODEL", "", default_path=DEFAULT_MODEL, executable=False)

    with tempfile.TemporaryDirectory(prefix="burito-audio-") as directory:
        os.chmod(directory, 0o700)
        root = Path(directory)
        source = root / "capture"
        wav = root / "capture.wav"
        prefix = root / "transcript"
        source.write_bytes(audio)
        os.chmod(source, 0o600)
        try:
            subprocess.run(
                [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                 "-t", str(MAX_AUDIO_SECONDS), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=12, check=True,
            )
            if not wav.is_file() or wav.stat().st_size > 1024 * 1024:
                raise ValueError("The recording could not be decoded within the audio limits.")
            subprocess.run(
                [whisper, "-m", model, "-f", str(wav), "-l", language, "-nt", "-np", "-otxt", "-of", str(prefix)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=45, check=True,
            )
            transcript = prefix.with_suffix(".txt").read_text(encoding="utf-8").strip()
        except subprocess.TimeoutExpired as error:
            raise TimeoutError("Local transcription took too long. Try a shorter recording.") from error
        except (OSError, subprocess.CalledProcessError, UnicodeError) as error:
            raise SpeechUnavailable("Local transcription failed. Check the configured model and audio runtime.") from error
        if len(transcript.encode("utf-8")) > 2_400:
            raise ValueError("The transcript exceeded the response limit.")
        return transcript

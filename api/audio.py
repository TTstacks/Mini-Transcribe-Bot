import subprocess
from pathlib import Path

from rest_framework.exceptions import ValidationError


ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav"}


def validate_audio_extension(filename):
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValidationError(
            {"audio": "Only .mp3 and .wav audio files are supported."}
        )


def get_audio_duration_seconds(path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise ValidationError(
            {"audio": "ffprobe is required to detect audio duration."}
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ValidationError({"audio": "Audio duration detection timed out."}) from exc
    except subprocess.CalledProcessError as exc:
        raise ValidationError({"audio": "Could not read audio duration."}) from exc

    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise ValidationError({"audio": "Could not parse audio duration."}) from exc

    if duration <= 0:
        raise ValidationError({"audio": "Audio duration must be greater than zero."})

    return duration


from rest_framework.exceptions import ValidationError

from api.models import TranscriptionJob
from api.providers import GroqLLMProvider, GroqWhisperProvider, ProviderError


def process_job(job, transcription_provider=None, llm_provider=None):
    try:
        transcription_provider = transcription_provider or GroqWhisperProvider()
        llm_provider = llm_provider or GroqLLMProvider()
        transcript = transcription_provider.transcribe(job.audio.path)
        report = llm_provider.analyze(transcript)
    except ValidationError as exc:
        job.status = TranscriptionJob.Status.FAILED
        job.error_message = flatten_validation_error(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise
    except ProviderError as exc:
        job.status = TranscriptionJob.Status.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise ValidationError({"provider": str(exc)}) from exc

    job.status = TranscriptionJob.Status.COMPLETED
    job.transcript = transcript
    job.report = report
    job.error_message = ""
    job.save(
        update_fields=["status", "transcript", "report", "error_message", "updated_at"]
    )
    return job


def flatten_validation_error(exc):
    detail = exc.detail
    if isinstance(detail, dict):
        return "; ".join(f"{key}: {value}" for key, value in detail.items())
    return str(detail)

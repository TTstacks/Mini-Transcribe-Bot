import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from api.models import TranscriptionJob
from api.providers import ProviderError
from api.reporting import parse_and_validate_report
from api.services import process_job


@pytest.fixture
def client_for_user():
    def factory(email):
        user = User.objects.create_user(
            username=email,
            email=email,
            password="strong-password",
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client, user

    return factory


def audio_file(name="sample.mp3"):
    return SimpleUploadedFile(name, b"fake audio", content_type="audio/mpeg")


class FakeTranscriptionProvider:
    def transcribe(self, audio_path):
        return "Students discussed the product roadmap and agreed to write tests."


class FakeLLMProvider:
    def analyze(self, transcript):
        return {
            "summary": "Students discussed the product roadmap. They agreed to write tests.",
            "topics": ["roadmap", "testing"],
            "sentiment": "positive",
            "action_items": ["Write tests"],
        }


@pytest.mark.django_db
def test_happy_path_creates_completed_job_with_mocked_providers(
    client_for_user, monkeypatch
):
    client, _ = client_for_user("student@example.com")
    monkeypatch.setattr("api.views.get_audio_duration_seconds", lambda path: 90)
    monkeypatch.setattr("api.services.GroqWhisperProvider", FakeTranscriptionProvider)
    monkeypatch.setattr("api.services.GroqLLMProvider", FakeLLMProvider)

    response = client.post(
        reverse("job-create"),
        {"audio": audio_file()},
        format="multipart",
    )

    assert response.status_code == 201
    job = TranscriptionJob.objects.get(id=response.data["job_id"])
    assert job.status == TranscriptionJob.Status.COMPLETED
    assert job.duration_seconds == 90
    assert job.transcript.startswith("Students discussed")
    assert job.report["sentiment"] == "positive"


@pytest.mark.django_db
def test_missing_audio_file_returns_validation_error(client_for_user):
    client, _ = client_for_user("student@example.com")

    response = client.post(reverse("job-create"), {}, format="multipart")

    assert response.status_code == 400
    assert "audio" in response.data


@pytest.mark.django_db
def test_user_cannot_read_another_users_job(client_for_user):
    _, owner = client_for_user("owner@example.com")
    other_client, _ = client_for_user("other@example.com")
    job = TranscriptionJob.objects.create(
        owner=owner,
        audio="audio/sample.mp3",
        duration_seconds=60,
        status=TranscriptionJob.Status.COMPLETED,
        transcript="hello",
        report={
            "summary": "Hello.",
            "topics": ["intro"],
            "sentiment": "neutral",
            "action_items": [],
        },
    )

    response = other_client.get(reverse("job-detail", kwargs={"pk": job.id}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_usage_returns_used_and_remaining_minutes(client_for_user):
    client, user = client_for_user("student@example.com")
    TranscriptionJob.objects.create(
        owner=user,
        audio="audio/one.mp3",
        duration_seconds=120,
    )

    response = client.get(reverse("usage"))

    assert response.status_code == 200
    assert response.data == {
        "used_minutes": 2.0,
        "remaining_minutes": 28.0,
        "limit_minutes": 30,
    }


@pytest.mark.django_db
def test_limit_rejects_request_before_provider_call(client_for_user, monkeypatch):
    client, user = client_for_user("student@example.com")
    TranscriptionJob.objects.create(
        owner=user,
        audio="audio/used.mp3",
        duration_seconds=1800,
    )
    monkeypatch.setattr("api.views.get_audio_duration_seconds", lambda path: 1)

    def fail_if_called(job):
        raise AssertionError("provider should not be called")

    monkeypatch.setattr("api.views.process_job", fail_if_called)

    response = client.post(
        reverse("job-create"),
        {"audio": audio_file()},
        format="multipart",
    )

    assert response.status_code == 400
    assert response.data["detail"] == "Audio exceeds remaining free limit."


@pytest.mark.django_db
def test_transcription_network_error_marks_job_failed(client_for_user):
    _, user = client_for_user("student@example.com")
    job = TranscriptionJob.objects.create(
        owner=user,
        audio="audio/sample.mp3",
        duration_seconds=60,
    )

    class FailingTranscriptionProvider:
        def transcribe(self, audio_path):
            raise ProviderError("Provider request timed out.")

    with pytest.raises(ValidationError):
        process_job(
            job,
            transcription_provider=FailingTranscriptionProvider(),
            llm_provider=FakeLLMProvider(),
        )

    job.refresh_from_db()
    assert job.status == TranscriptionJob.Status.FAILED
    assert job.error_message == "Provider request timed out."


@pytest.mark.django_db
def test_invalid_llm_json_marks_job_failed(client_for_user):
    _, user = client_for_user("student@example.com")
    job = TranscriptionJob.objects.create(
        owner=user,
        audio="audio/sample.mp3",
        duration_seconds=60,
    )

    class InvalidJsonLLMProvider:
        def analyze(self, transcript):
            return parse_and_validate_report("{not json")

    with pytest.raises(ValidationError):
        process_job(
            job,
            transcription_provider=FakeTranscriptionProvider(),
            llm_provider=InvalidJsonLLMProvider(),
        )

    job.refresh_from_db()
    assert job.status == TranscriptionJob.Status.FAILED
    assert "LLM returned invalid JSON" in job.error_message


def test_report_validation_accepts_required_structure():
    report = parse_and_validate_report(
        {
            "summary": "A concise summary.",
            "topics": ["testing"],
            "sentiment": "neutral",
            "action_items": [],
        }
    )

    assert report["topics"] == ["testing"]


def test_report_validation_rejects_invalid_sentiment():
    with pytest.raises(ValidationError):
        parse_and_validate_report(
            {
                "summary": "A concise summary.",
                "topics": ["testing"],
                "sentiment": "mixed",
                "action_items": [],
            }
        )


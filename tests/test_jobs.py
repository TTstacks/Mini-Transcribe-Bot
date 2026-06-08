import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from api.models import TranscriptionJob


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


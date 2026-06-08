import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_register_creates_user_with_hashed_password():
    client = APIClient()

    response = client.post(
        reverse("auth-register"),
        {"email": "Student@example.com", "password": "strong-password"},
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(email="student@example.com")
    assert user.username == "student@example.com"
    assert user.check_password("strong-password")
    assert user.password != "strong-password"


@pytest.mark.django_db
def test_login_returns_jwt_tokens():
    User.objects.create_user(
        username="student@example.com",
        email="student@example.com",
        password="strong-password",
    )
    client = APIClient()

    response = client.post(
        reverse("auth-login"),
        {"email": "student@example.com", "password": "strong-password"},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


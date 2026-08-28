import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from profiles.models import Profile

pytestmark = pytest.mark.django_db


def signup_payload() -> dict[str, str]:
    return {
        "username": "learner",
        "email": "learner@example.com",
        "password": "StrongPassword123!",
    }


def test_signup_creates_user_profile_and_tokens() -> None:
    response = APIClient().post(reverse("signup"), signup_payload(), format="json")

    assert response.status_code == 201
    assert response.data["user"]["username"] == "learner"
    assert response.data["tokens"]["access"]
    assert response.data["tokens"]["refresh"]
    user = get_user_model().objects.get(username="learner")
    assert Profile.objects.filter(user=user).exists()


def test_signup_rejects_duplicate_username() -> None:
    get_user_model().objects.create_user(username="learner", password="StrongPassword123!")

    response = APIClient().post(reverse("signup"), signup_payload(), format="json")

    assert response.status_code == 400
    assert "username" in response.data


def test_signin_returns_tokens_for_valid_credentials() -> None:
    get_user_model().objects.create_user(
        username="learner",
        email="learner@example.com",
        password="StrongPassword123!",
    )

    response = APIClient().post(
        reverse("signin"),
        {"username": "learner", "password": "StrongPassword123!"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["tokens"]["access"]
    assert response.data["tokens"]["refresh"]


def test_signin_rejects_invalid_credentials() -> None:
    get_user_model().objects.create_user(username="learner", password="StrongPassword123!")

    response = APIClient().post(
        reverse("signin"),
        {"username": "learner", "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401
    assert response.data["detail"] == "Invalid username or password."


def test_access_token_authenticates_me_endpoint() -> None:
    user = get_user_model().objects.create_user(
        username="learner",
        password="StrongPassword123!",
    )
    signin = APIClient().post(
        reverse("signin"),
        {"username": "learner", "password": "StrongPassword123!"},
        format="json",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {signin.data['tokens']['access']}")

    response = client.get(reverse("me"))

    assert response.status_code == 200
    assert response.data == {"id": user.id, "username": "learner", "email": ""}

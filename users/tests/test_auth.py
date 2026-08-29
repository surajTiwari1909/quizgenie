import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from profiles.models import Profile
from users import services

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


def test_signup_returns_json_validation_errors_for_weak_password() -> None:
    payload = signup_payload()
    payload["password"] = "123456789"

    response = APIClient().post(reverse("signup"), payload, format="json")

    assert response.status_code == 400
    assert "password" in response.data
    assert "This password is entirely numeric." in response.data["password"]
    assert response["Content-Type"].startswith("application/json")


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


def authenticated_client_with_tokens(username: str = "learner") -> tuple[APIClient, object, dict]:
    user = get_user_model().objects.create_user(username=username)
    tokens = services.issue_tokens(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client, user, tokens


def test_logout_requires_authentication() -> None:
    user = get_user_model().objects.create_user(username="learner")
    tokens = services.issue_tokens(user)

    response = APIClient().post(
        reverse("logout"),
        {"refresh": tokens["refresh"]},
        format="json",
    )

    assert response.status_code == 401


def test_logout_revokes_refresh_token() -> None:
    client, _, tokens = authenticated_client_with_tokens()

    logout_response = client.post(
        reverse("logout"),
        {"refresh": tokens["refresh"]},
        format="json",
    )
    refresh_response = APIClient().post(
        reverse("token-refresh"),
        {"refresh": tokens["refresh"]},
        format="json",
    )

    assert logout_response.status_code == 204
    assert refresh_response.status_code == 401


def test_logout_rejects_another_users_refresh_token() -> None:
    client, _, _ = authenticated_client_with_tokens("first-user")
    second_user = get_user_model().objects.create_user(username="second-user")
    second_tokens = services.issue_tokens(second_user)

    logout_response = client.post(
        reverse("logout"),
        {"refresh": second_tokens["refresh"]},
        format="json",
    )
    refresh_response = APIClient().post(
        reverse("token-refresh"),
        {"refresh": second_tokens["refresh"]},
        format="json",
    )

    assert logout_response.status_code == 400
    assert "refresh" in logout_response.data
    assert refresh_response.status_code == 200


def test_logout_rejects_invalid_refresh_token() -> None:
    client, _, _ = authenticated_client_with_tokens()

    response = client.post(
        reverse("logout"),
        {"refresh": "not-a-token"},
        format="json",
    )

    assert response.status_code == 400
    assert "refresh" in response.data


def test_logout_rejects_already_revoked_refresh_token() -> None:
    client, _, tokens = authenticated_client_with_tokens()
    payload = {"refresh": tokens["refresh"]}

    first_response = client.post(reverse("logout"), payload, format="json")
    second_response = client.post(reverse("logout"), payload, format="json")

    assert first_response.status_code == 204
    assert second_response.status_code == 400
    assert "refresh" in second_response.data

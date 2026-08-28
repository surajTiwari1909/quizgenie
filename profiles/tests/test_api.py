from io import BytesIO
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from profiles.models import Profile

pytestmark = pytest.mark.django_db


def create_image_upload(
    filename: str = "avatar.png",
    *,
    image_format: str = "PNG",
    size: tuple[int, int] = (2, 2),
) -> SimpleUploadedFile:
    content = BytesIO()
    Image.new("RGB", size, color="blue").save(content, format=image_format)
    return SimpleUploadedFile(filename, content.getvalue(), content_type="image/png")


def authenticated_client(username: str = "learner") -> tuple[APIClient, Any]:
    user = get_user_model().objects.create_user(username=username)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def test_profile_picture_requires_authentication() -> None:
    response = APIClient().put(
        reverse("profile-picture"),
        {"profile_picture": create_image_upload()},
        format="multipart",
    )

    assert response.status_code == 401


def test_authenticated_user_can_upload_profile_picture(tmp_path, settings) -> None:
    settings.MEDIA_ROOT = tmp_path
    client, user = authenticated_client()

    response = client.put(
        reverse("profile-picture"),
        {"profile_picture": create_image_upload()},
        format="multipart",
    )

    assert response.status_code == 200
    assert response.data["profile_picture_url"].startswith(
        "http://testserver/media/profiles/"
    )
    profile = Profile.objects.get(user=user)
    assert profile.profile_picture.name.startswith(f"profiles/{user.id}/")
    assert (tmp_path / profile.profile_picture.name).is_file()


def test_upload_creates_a_missing_profile(tmp_path, settings) -> None:
    settings.MEDIA_ROOT = tmp_path
    client, user = authenticated_client()
    assert not Profile.objects.filter(user=user).exists()

    response = client.put(
        reverse("profile-picture"),
        {"profile_picture": create_image_upload()},
        format="multipart",
    )

    assert response.status_code == 200
    assert Profile.objects.filter(user=user).exists()


def test_upload_replaces_picture_and_deletes_old_file(tmp_path, settings) -> None:
    settings.MEDIA_ROOT = tmp_path
    client, user = authenticated_client()

    first_response = client.put(
        reverse("profile-picture"),
        {"profile_picture": create_image_upload("first.png")},
        format="multipart",
    )
    old_name = Profile.objects.get(user=user).profile_picture.name
    second_response = client.put(
        reverse("profile-picture"),
        {"profile_picture": create_image_upload("second.jpg", image_format="JPEG")},
        format="multipart",
    )

    profile = Profile.objects.get(user=user)
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert profile.profile_picture.name != old_name
    assert not (tmp_path / old_name).exists()
    assert (tmp_path / profile.profile_picture.name).is_file()


def test_upload_requires_profile_picture_field() -> None:
    client, _ = authenticated_client()

    response = client.put(reverse("profile-picture"), {}, format="multipart")

    assert response.status_code == 400
    assert "profile_picture" in response.data


def test_upload_rejects_unsupported_extension() -> None:
    client, _ = authenticated_client()

    response = client.put(
        reverse("profile-picture"),
        {"profile_picture": create_image_upload("avatar.gif", image_format="GIF")},
        format="multipart",
    )

    assert response.status_code == 400
    assert "profile_picture" in response.data


def test_upload_rejects_corrupt_image() -> None:
    client, _ = authenticated_client()
    corrupt_image = SimpleUploadedFile("avatar.png", b"not-an-image", "image/png")

    response = client.put(
        reverse("profile-picture"),
        {"profile_picture": corrupt_image},
        format="multipart",
    )

    assert response.status_code == 400
    assert "profile_picture" in response.data


def test_upload_rejects_image_larger_than_five_mb() -> None:
    client, _ = authenticated_client()
    large_image = create_image_upload(
        "avatar.png",
        image_format="BMP",
        size=(1400, 1400),
    )

    response = client.put(
        reverse("profile-picture"),
        {"profile_picture": large_image},
        format="multipart",
    )

    assert response.status_code == 400
    assert "profile_picture" in response.data


def test_upload_does_not_change_another_users_profile(tmp_path, settings) -> None:
    settings.MEDIA_ROOT = tmp_path
    client, user = authenticated_client("first-user")
    other_user = get_user_model().objects.create_user(username="second-user")
    other_profile = Profile.objects.create(
        user=other_user,
        profile_picture=create_image_upload("other.png"),
    )
    other_picture_name = other_profile.profile_picture.name

    response = client.put(
        reverse("profile-picture"),
        {"profile_picture": create_image_upload("mine.png")},
        format="multipart",
    )

    assert response.status_code == 200
    assert Profile.objects.get(user=user).profile_picture
    other_profile.refresh_from_db()
    assert other_profile.profile_picture.name == other_picture_name

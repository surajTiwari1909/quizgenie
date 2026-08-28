from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from PIL import Image

from profiles.models import Profile
from profiles.validators import MAX_PROFILE_PICTURE_SIZE

pytestmark = pytest.mark.django_db


def create_image_upload(filename: str = "avatar.png") -> SimpleUploadedFile:
    content = BytesIO()
    Image.new("RGB", (1, 1), color="blue").save(content, format="PNG")
    return SimpleUploadedFile(filename, content.getvalue(), content_type="image/png")


def test_profile_belongs_to_user() -> None:
    user = get_user_model().objects.create_user(username="learner")

    profile = Profile.objects.create(user=user)

    assert profile.user == user
    assert user.profile == profile


def test_user_can_have_only_one_profile() -> None:
    user = get_user_model().objects.create_user(username="learner")
    Profile.objects.create(user=user)

    with pytest.raises(IntegrityError), transaction.atomic():
        Profile.objects.create(user=user)


def test_deleting_user_deletes_profile() -> None:
    user = get_user_model().objects.create_user(username="learner")
    profile = Profile.objects.create(user=user)

    user.delete()

    assert not Profile.objects.filter(id=profile.id).exists()


def test_profile_picture_is_optional() -> None:
    user = get_user_model().objects.create_user(username="learner")

    profile = Profile.objects.create(user=user)

    assert not profile.profile_picture


def test_profile_picture_is_stored_under_user_directory(tmp_path, settings) -> None:
    settings.MEDIA_ROOT = tmp_path
    user = get_user_model().objects.create_user(username="learner")
    profile = Profile(user=user, profile_picture=create_image_upload())

    profile.full_clean()
    profile.save()

    assert profile.profile_picture.name.startswith(f"profiles/{user.id}/")
    assert profile.profile_picture.name.endswith(".png")
    assert (tmp_path / profile.profile_picture.name).is_file()


def test_profile_picture_rejects_unsupported_extension() -> None:
    user = get_user_model().objects.create_user(username="learner")
    profile = Profile(user=user, profile_picture=create_image_upload("avatar.exe"))

    with pytest.raises(ValidationError, match="File extension"):
        profile.full_clean()


def test_profile_picture_rejects_files_larger_than_five_mb() -> None:
    user = get_user_model().objects.create_user(username="learner")
    large_image = SimpleUploadedFile(
        "avatar.png",
        b"0" * (MAX_PROFILE_PICTURE_SIZE + 1),
        content_type="image/png",
    )
    profile = Profile(user=user, profile_picture=large_image)

    with pytest.raises(ValidationError, match="5 MB or smaller"):
        profile.full_clean()

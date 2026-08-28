from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from profiles.validators import validate_profile_picture_size


def profile_picture_upload_path(profile: "Profile", filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return f"profiles/{profile.user_id}/{uuid4().hex}{extension}"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_path,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_profile_picture_size,
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.get_username()}'s profile"

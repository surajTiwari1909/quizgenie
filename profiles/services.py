from typing import Any

from django.core.files.uploadedfile import UploadedFile

from profiles.models import Profile


def update_profile_picture(*, user: Any, picture: UploadedFile) -> Profile:
    """Store a new profile picture and remove the replaced file."""
    profile, _ = Profile.objects.get_or_create(user=user)
    storage = profile.profile_picture.storage
    previous_name = profile.profile_picture.name

    profile.profile_picture = picture
    try:
        profile.full_clean()
        profile.save(update_fields=["profile_picture", "updated_at"])
    except Exception:
        failed_name = profile.profile_picture.name
        if failed_name and failed_name != previous_name and storage.exists(failed_name):
            storage.delete(failed_name)
        raise

    if previous_name and previous_name != profile.profile_picture.name:
        storage.delete(previous_name)

    return profile

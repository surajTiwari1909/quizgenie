from django.core.exceptions import ValidationError

MAX_PROFILE_PICTURE_SIZE = 5 * 1024 * 1024


def validate_profile_picture_size(image: object) -> None:
    size = getattr(image, "size", 0)
    if size > MAX_PROFILE_PICTURE_SIZE:
        raise ValidationError("Profile picture must be 5 MB or smaller.")

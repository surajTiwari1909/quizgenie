from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from profiles.models import Profile
from profiles.validators import validate_profile_picture_size


class ProfilePictureUploadSerializer(serializers.Serializer):
    profile_picture = serializers.ImageField(
        allow_empty_file=False,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_profile_picture_size,
        ],
    )


class ProfilePictureResponseSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ("profile_picture_url",)

    def get_profile_picture_url(self, profile: Profile) -> str | None:
        if not profile.profile_picture:
            return None

        request = self.context.get("request")
        if request is None:
            return profile.profile_picture.url
        return request.build_absolute_uri(profile.profile_picture.url)

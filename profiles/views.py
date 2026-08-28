from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from profiles import services
from profiles.serializers import (
    ProfilePictureResponseSerializer,
    ProfilePictureUploadSerializer,
)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def profile_picture(request: Request) -> Response:
    serializer = ProfilePictureUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    profile = services.update_profile_picture(
        user=request.user,
        picture=serializer.validated_data["profile_picture"],
    )
    response = ProfilePictureResponseSerializer(profile, context={"request": request})
    return Response(response.data, status=status.HTTP_200_OK)

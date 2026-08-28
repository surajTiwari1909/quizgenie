from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from users import services
from users.serializers import (
    LogoutSerializer,
    SigninSerializer,
    SignupSerializer,
    UserResponseSerializer,
)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request: Request) -> Response:
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = services.register_user(serializer.validated_data)

    return Response(
        {"user": UserResponseSerializer(user).data, "tokens": services.issue_tokens(user)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def signin(request: Request) -> Response:
    serializer = SigninSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = services.authenticate_user(
        request,
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )
    if user is None:
        return Response(
            {"detail": "Invalid username or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return Response(
        {"user": UserResponseSerializer(user).data, "tokens": services.issue_tokens(user)},
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request: Request) -> Response:
    return Response(services.refresh_tokens(request.data))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request: Request) -> Response:
    serializer = LogoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    services.revoke_refresh_token(
        user=request.user,
        refresh_token=serializer.validated_data["refresh"],
    )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request: Request) -> Response:
    return Response(UserResponseSerializer(request.user).data)

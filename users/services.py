from typing import Any

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from profiles.models import Profile

User = get_user_model()


def register_user(user_data: dict[str, Any]) -> User:
    """Validate registration data, then create the user and empty profile."""
    username = user_data["username"].strip()
    email = user_data["email"].strip().lower()
    password = user_data["password"]

    if not username:
        raise serializers.ValidationError({"username": "Username is required."})
    if User.objects.filter(username__iexact=username).exists():
        raise serializers.ValidationError(
            {"username": "A user with this username already exists."}
        )
    if User.objects.filter(email__iexact=email).exists():
        raise serializers.ValidationError({"email": "A user with this email already exists."})
    validate_password(password)

    return create_user({"username": username, "email": email, "password": password})


def create_user(user_data: dict[str, Any]) -> User:
    """Create a user and its empty profile as one atomic operation."""
    try:
        with transaction.atomic():
            user = User.objects.create_user(**user_data)
            Profile.objects.create(user=user)
    except IntegrityError as error:
        raise serializers.ValidationError(
            {"username": "A user with this username already exists."}
        ) from error
    return user


def authenticate_user(request: Request, *, username: str, password: str) -> User | None:
    """Authenticate credentials using Django's configured authentication backends."""
    return authenticate(request, username=username, password=password)


def issue_tokens(user: User) -> dict[str, str]:
    """Issue the access and refresh JWT pair for an authenticated user."""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def refresh_tokens(data: dict[str, Any]) -> dict[str, Any]:
    """Validate a refresh token and return its new access token."""
    serializer = TokenRefreshSerializer(data=data)
    try:
        serializer.is_valid(raise_exception=True)
    except TokenError as error:
        raise InvalidToken("Refresh token is invalid, expired, or revoked.") from error
    return serializer.validated_data


def revoke_refresh_token(*, user: User, refresh_token: str) -> None:
    """Blacklist a refresh token owned by the authenticated user."""
    try:
        token = RefreshToken(refresh_token)
    except TokenError as error:
        raise serializers.ValidationError(
            {"refresh": "Invalid, expired, or already revoked refresh token."}
        ) from error

    if str(token.get("user_id")) != str(user.pk):
        raise serializers.ValidationError(
            {"refresh": "This refresh token does not belong to the authenticated user."}
        )

    token.blacklist()

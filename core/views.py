from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.http.request import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


@csrf_exempt
def api_not_found(
    _request: HttpRequest, exception: Exception | None = None
) -> JsonResponse:
    """Return a JSON response for URLs that do not match an API endpoint."""
    del exception
    return JsonResponse({"detail": "Endpoint not found."}, status=404)


class HealthView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    def get(self, _request: Request) -> Response:
        return Response({"status": "ok"})


class ReadinessView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    def get(self, _request: Request) -> Response:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            return Response(
                {"detail": "Database is unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"status": "ready"})

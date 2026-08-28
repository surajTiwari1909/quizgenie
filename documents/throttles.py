from rest_framework.request import Request
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView


class DocumentUploadRateThrottle(UserRateThrottle):
    scope = "document_upload"

    def allow_request(self, request: Request, view: APIView) -> bool:
        if request.method != "POST":
            return True
        return super().allow_request(request, view)

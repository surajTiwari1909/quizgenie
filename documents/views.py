from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from documents import services
from documents.models import Document
from documents.serializers import (
    DocumentContentSerializer,
    DocumentResponseSerializer,
    DocumentUploadSerializer,
)
from documents.throttles import DocumentUploadRateThrottle
from documents.upload_handlers import DocumentSizeLimitUploadHandler
from documents.validators import MAX_DOCUMENT_SIZE


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([DocumentUploadRateThrottle])
def document_collection(request: Request) -> Response:
    if request.method == "GET":
        documents = Document.objects.filter(owner=request.user).select_related("content")
        serializer = DocumentResponseSerializer(
            documents,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    request._request.upload_handlers.insert(  # noqa: SLF001
        0,
        DocumentSizeLimitUploadHandler(request._request),  # noqa: SLF001
    )
    request_data = request.data
    if getattr(request._request, "document_upload_too_large", False):  # noqa: SLF001
        max_size = getattr(settings, "DOCUMENT_MAX_FILE_SIZE", MAX_DOCUMENT_SIZE)
        raise ValidationError(
            {"file": f"Document must be {max_size // (1024 * 1024)} MB or smaller."}
        )

    serializer = DocumentUploadSerializer(data=request_data)
    serializer.is_valid(raise_exception=True)
    document = services.create_document(
        owner=request.user,
        uploaded_file=serializer.validated_data["file"],
    )
    response = DocumentResponseSerializer(document, context={"request": request})
    return Response(response.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def document_detail(request: Request, document_id: int) -> Response:
    document = get_object_or_404(
        Document.objects.select_related("content"),
        id=document_id,
        owner=request.user,
    )

    if request.method == "DELETE":
        services.delete_document(document)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = DocumentResponseSerializer(document, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def document_content(request: Request, document_id: int) -> Response:
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    if document.status != Document.Status.READY:
        return Response(
            {"detail": "Document content is not ready."},
            status=status.HTTP_409_CONFLICT,
        )

    serializer = DocumentContentSerializer(document.content)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def document_download(request: Request, document_id: int) -> HttpResponse:
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=document.original_filename,
        content_type="application/pdf",
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def document_retry(request: Request, document_id: int) -> Response:
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    try:
        document = services.retry_document_processing(document)
    except services.InvalidDocumentState as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    serializer = DocumentResponseSerializer(document, context={"request": request})
    return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

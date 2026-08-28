from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from documents import services
from documents.models import Document
from documents.serializers import DocumentResponseSerializer, DocumentUploadSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def document_collection(request: Request) -> Response:
    if request.method == "GET":
        documents = Document.objects.filter(owner=request.user)
        serializer = DocumentResponseSerializer(
            documents,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    serializer = DocumentUploadSerializer(data=request.data)
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
    document = get_object_or_404(Document, id=document_id, owner=request.user)

    if request.method == "DELETE":
        services.delete_document(document)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = DocumentResponseSerializer(document, context={"request": request})
    return Response(serializer.data)

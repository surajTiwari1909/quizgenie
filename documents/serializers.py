from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from rest_framework import serializers

from documents.models import Document, DocumentContent
from documents.validators import validate_pdf_document


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        allow_empty_file=False,
        validators=[validate_pdf_document],
    )


class DocumentResponseSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    page_count = serializers.SerializerMethodField()
    character_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "original_filename",
            "content_type",
            "file_size",
            "status",
            "failure_reason",
            "page_count",
            "character_count",
            "download_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_download_url(self, document: Document) -> str:
        request = self.context.get("request")
        path = reverse("document-download", args=[document.id])
        if request is None:
            return path
        return request.build_absolute_uri(path)

    def get_page_count(self, document: Document) -> int | None:
        try:
            return document.content.page_count
        except ObjectDoesNotExist:
            return None

    def get_character_count(self, document: Document) -> int | None:
        try:
            return document.content.character_count
        except ObjectDoesNotExist:
            return None


class DocumentContentSerializer(serializers.ModelSerializer):
    document_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = DocumentContent
        fields = ("document_id", "text", "page_count", "character_count", "updated_at")
        read_only_fields = fields

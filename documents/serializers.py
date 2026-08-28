from rest_framework import serializers

from documents.models import Document
from documents.validators import validate_pdf_document


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        allow_empty_file=False,
        validators=[validate_pdf_document],
    )


class DocumentResponseSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "original_filename",
            "content_type",
            "file_size",
            "status",
            "failure_reason",
            "file_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_file_url(self, document: Document) -> str:
        request = self.context.get("request")
        if request is None:
            return document.file.url
        return request.build_absolute_uri(document.file.url)

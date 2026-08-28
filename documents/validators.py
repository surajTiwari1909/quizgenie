from pathlib import Path

from django.core.exceptions import ValidationError

MAX_DOCUMENT_SIZE = 10 * 1024 * 1024
PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}


def validate_pdf_document(document: object) -> None:
    filename = getattr(document, "name", "")
    if Path(filename).suffix.lower() != ".pdf":
        raise ValidationError("Only PDF documents are supported.")

    size = getattr(document, "size", 0)
    if size > MAX_DOCUMENT_SIZE:
        raise ValidationError("Document must be 10 MB or smaller.")

    content_type = getattr(document, "content_type", None)
    if content_type and content_type not in PDF_CONTENT_TYPES:
        raise ValidationError("Uploaded file must have a PDF content type.")

    position = document.tell() if hasattr(document, "tell") else 0
    header = document.read(5)
    if hasattr(document, "seek"):
        document.seek(position)
    if header != b"%PDF-":
        raise ValidationError("Uploaded file is not a valid PDF document.")

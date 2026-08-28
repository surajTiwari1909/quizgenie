from pathlib import Path
from typing import Any

from django.core.files.uploadedfile import UploadedFile

from documents.models import Document


def create_document(*, owner: Any, uploaded_file: UploadedFile) -> Document:
    """Validate and store an uploaded document with immutable source metadata."""
    document = Document(
        owner=owner,
        file=uploaded_file,
        original_filename=Path(uploaded_file.name).name[:255],
        content_type=getattr(uploaded_file, "content_type", "application/octet-stream"),
        file_size=uploaded_file.size,
    )
    try:
        document.full_clean()
        document.save()
    except Exception:
        if document.file._committed and document.file.name:  # noqa: SLF001
            document.file.storage.delete(document.file.name)
        raise
    return document


def delete_document(document: Document) -> None:
    """Delete the database record and its stored file."""
    document.delete()

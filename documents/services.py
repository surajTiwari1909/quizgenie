import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from documents.models import Document, DocumentContent

logger = logging.getLogger(__name__)


class DocumentExtractionError(Exception):
    """A safe, user-facing document extraction failure."""


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    page_count: int

    @property
    def character_count(self) -> int:
        return len(self.text)


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

    transaction.on_commit(lambda: enqueue_document_processing(document.id))
    document.refresh_from_db(fields=["status", "failure_reason", "updated_at"])
    return document


def delete_document(document: Document) -> None:
    """Delete the database record and its stored file."""
    document.delete()


def extract_document_content(document: Document) -> ExtractedDocument:
    """Extract text from every page of a structurally valid PDF."""
    try:
        with document.file.open("rb") as pdf_file:
            reader = PdfReader(pdf_file, strict=True)
            if reader.is_encrypted:
                raise DocumentExtractionError(
                    "Encrypted or password-protected PDFs are not supported."
                )

            page_count = len(reader.pages)
            page_text = [(page.extract_text() or "").strip() for page in reader.pages]
    except DocumentExtractionError:
        raise
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, EOFError) as error:
        raise DocumentExtractionError(
            "The PDF could not be read during text extraction."
        ) from error

    extracted_text = "\n\n".join(text for text in page_text if text).strip()
    if not extracted_text:
        raise DocumentExtractionError("No extractable text was found in this PDF.")

    return ExtractedDocument(text=extracted_text, page_count=page_count)


def process_document(document_id: int) -> None:
    """Move a document through processing and persist extracted text or failure details."""
    try:
        with transaction.atomic():
            document = Document.objects.select_for_update().get(id=document_id)
            if document.status == Document.Status.READY:
                return
            document.status = Document.Status.PROCESSING
            document.failure_reason = ""
            document.save(update_fields=["status", "failure_reason", "updated_at"])

        extracted = extract_document_content(document)
    except Document.DoesNotExist:
        return
    except DocumentExtractionError as error:
        _mark_document_failed(document_id, str(error))
        return
    except Exception:
        logger.exception(
            "Unexpected document processing failure",
            extra={"document_id": document_id},
        )
        _mark_document_failed(document_id, "Document processing failed unexpectedly.")
        return

    with transaction.atomic():
        document = Document.objects.select_for_update().get(id=document_id)
        DocumentContent.objects.update_or_create(
            document=document,
            defaults={
                "text": extracted.text,
                "page_count": extracted.page_count,
                "character_count": extracted.character_count,
            },
        )
        document.status = Document.Status.READY
        document.failure_reason = ""
        document.save(update_fields=["status", "failure_reason", "updated_at"])


def enqueue_document_processing(document_id: int) -> None:
    """Send document processing to Celery after the upload transaction commits."""
    from documents.tasks import process_document_task

    try:
        process_document_task.delay(document_id)
    except Exception:
        logger.exception("Could not queue document processing", extra={"document_id": document_id})
        _mark_document_failed(document_id, "Document processing could not be queued.")


def _mark_document_failed(document_id: int, reason: str) -> None:
    Document.objects.filter(
        id=document_id,
        status__in=(Document.Status.PENDING, Document.Status.PROCESSING),
    ).update(
        status=Document.Status.FAILED,
        failure_reason=reason,
        updated_at=timezone.now(),
    )

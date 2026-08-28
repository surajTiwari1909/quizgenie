from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from pypdf import PdfReader
from pypdf.errors import PyPdfError

MAX_DOCUMENT_SIZE = 10 * 1024 * 1024
MAX_DOCUMENT_PAGE_COUNT = 250


def validate_pdf_document(document: object) -> None:
    filename = getattr(document, "name", "")
    if Path(filename).suffix.lower() != ".pdf":
        raise ValidationError("Only PDF documents are supported.")

    size = getattr(document, "size", 0)
    max_size = getattr(settings, "DOCUMENT_MAX_FILE_SIZE", MAX_DOCUMENT_SIZE)
    if size > max_size:
        raise ValidationError(f"Document must be {max_size // (1024 * 1024)} MB or smaller.")

    position = document.tell() if hasattr(document, "tell") else 0
    try:
        header = document.read(5)
        document.seek(position)
        if header != b"%PDF-":
            raise ValidationError("Uploaded file is not a valid PDF document.")

        reader = PdfReader(document, strict=True)
        if reader.is_encrypted:
            raise ValidationError("Encrypted or password-protected PDFs are not supported.")
        page_count = len(reader.pages)
        if page_count == 0:
            raise ValidationError("PDF document must contain at least one page.")
        max_pages = getattr(settings, "DOCUMENT_MAX_PAGE_COUNT", MAX_DOCUMENT_PAGE_COUNT)
        if page_count > max_pages:
            raise ValidationError(f"PDF document cannot contain more than {max_pages} pages.")

        for page in reader.pages:
            page.get_contents()
    except ValidationError:
        raise
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, EOFError) as error:
        raise ValidationError("PDF document is corrupt or structurally invalid.") from error
    finally:
        if hasattr(document, "seek"):
            document.seek(position)

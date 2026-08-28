from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateDocumentStorage(FileSystemStorage):
    """Store documents outside the publicly served media directory."""

    @property
    def base_location(self) -> Path:
        return Path(settings.DOCUMENT_ROOT)

    @property
    def location(self) -> str:
        return str(self.base_location.resolve())

    @property
    def base_url(self) -> None:
        return None


private_document_storage = PrivateDocumentStorage()

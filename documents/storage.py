from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateDocumentStorage(Storage):
    """Stable storage identity that delegates to local disk or an S3 bucket."""

    @property
    def _storage(self) -> Storage:
        if settings.USE_S3_STORAGE:
            from storages.backends.s3boto3 import S3Boto3Storage

            return S3Boto3Storage(
                location="private_documents",
                default_acl=None,
                file_overwrite=False,
                querystring_auth=True,
            )
        return FileSystemStorage(
            location=str(Path(settings.DOCUMENT_ROOT).resolve()),
            base_url=None,
        )

    def save(self, name, content, max_length=None):
        return self._storage.save(name, content, max_length=max_length)

    def open(self, name, mode="rb"):
        return self._storage.open(name, mode=mode)

    def delete(self, name):
        return self._storage.delete(name)

    def exists(self, name):
        return self._storage.exists(name)

    def url(self, name):
        return self._storage.url(name)

    def size(self, name):
        return self._storage.size(name)

    def get_available_name(self, name, max_length=None):
        return self._storage.get_available_name(name, max_length=max_length)

    def generate_filename(self, filename):
        return self._storage.generate_filename(filename)

    def path(self, name):
        return self._storage.path(name)

    def listdir(self, path):
        return self._storage.listdir(path)

    def get_accessed_time(self, name):
        return self._storage.get_accessed_time(name)

    def get_created_time(self, name):
        return self._storage.get_created_time(name)

    def get_modified_time(self, name):
        return self._storage.get_modified_time(name)


private_document_storage = PrivateDocumentStorage()

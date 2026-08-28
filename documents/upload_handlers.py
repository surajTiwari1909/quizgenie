from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler, StopUpload

from documents.validators import MAX_DOCUMENT_SIZE


class DocumentSizeLimitUploadHandler(FileUploadHandler):
    """Stop buffering a document once its configured byte limit is exceeded."""

    def __init__(self, request=None) -> None:
        super().__init__(request)
        self.received_bytes = 0

    def receive_data_chunk(self, raw_data: bytes, _start: int) -> bytes:
        self.received_bytes += len(raw_data)
        max_size = getattr(settings, "DOCUMENT_MAX_FILE_SIZE", MAX_DOCUMENT_SIZE)
        if self.received_bytes > max_size:
            self.request.document_upload_too_large = True
            raise StopUpload(connection_reset=False)
        return raw_data

    def file_complete(self, _file_size: int) -> None:
        return None

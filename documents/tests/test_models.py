import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.models import Document

pytestmark = pytest.mark.django_db


def test_deleting_owner_deletes_document_record_and_file(tmp_path, settings) -> None:
    settings.DOCUMENT_ROOT = tmp_path
    user = get_user_model().objects.create_user(username="learner")
    document = Document.objects.create(
        owner=user,
        file=SimpleUploadedFile("notes.pdf", b"%PDF-1.4\n%%EOF"),
        original_filename="notes.pdf",
        content_type="application/pdf",
        file_size=15,
    )
    stored_path = tmp_path / document.file.name

    user.delete()

    assert not Document.objects.filter(id=document.id).exists()
    assert not stored_path.exists()


def test_new_document_defaults_to_pending() -> None:
    user = get_user_model().objects.create_user(username="learner")
    document = Document.objects.create(
        owner=user,
        file=SimpleUploadedFile("notes.pdf", b"%PDF-1.4\n%%EOF"),
        original_filename="notes.pdf",
        content_type="application/pdf",
        file_size=15,
    )

    assert document.status == Document.Status.PENDING

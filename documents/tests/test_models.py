import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

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


def test_checksum_is_unique_per_owner() -> None:
    user = get_user_model().objects.create_user(username="learner")
    document_data = {
        "owner": user,
        "file": SimpleUploadedFile("notes.pdf", b"%PDF-1.4\n%%EOF"),
        "original_filename": "notes.pdf",
        "content_type": "application/pdf",
        "file_size": 15,
        "checksum_sha256": "a" * 64,
    }
    Document.objects.create(**document_data)

    with pytest.raises(IntegrityError), transaction.atomic():
        Document.objects.create(**document_data)


def test_different_owners_can_store_the_same_checksum() -> None:
    first_user = get_user_model().objects.create_user(username="first-user")
    second_user = get_user_model().objects.create_user(username="second-user")

    for owner in (first_user, second_user):
        Document.objects.create(
            owner=owner,
            file=SimpleUploadedFile(f"{owner.username}.pdf", b"%PDF-1.4\n%%EOF"),
            original_filename=f"{owner.username}.pdf",
            content_type="application/pdf",
            file_size=15,
            checksum_sha256="a" * 64,
        )

    assert Document.objects.filter(checksum_sha256="a" * 64).count() == 2

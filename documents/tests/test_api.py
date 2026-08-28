from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from pypdf import PdfWriter
from rest_framework.test import APIClient

from documents.models import Document
from documents.validators import MAX_DOCUMENT_SIZE

pytestmark = pytest.mark.django_db


def create_pdf_content(*, encrypted: bool = False, include_page: bool = True) -> bytes:
    content = BytesIO()
    writer = PdfWriter()
    if include_page:
        writer.add_blank_page(width=72, height=72)
    if encrypted:
        writer.encrypt("secret-password")
    writer.write(content)
    return content.getvalue()


def pdf_upload(
    filename: str = "study-notes.pdf",
    *,
    content: bytes | None = None,
    content_type: str = "application/pdf",
) -> SimpleUploadedFile:
    if content is None:
        content = create_pdf_content()
    return SimpleUploadedFile(filename, content, content_type=content_type)


def authenticated_client(username: str = "learner") -> tuple[APIClient, object]:
    user = get_user_model().objects.create_user(username=username)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def test_document_endpoints_require_authentication() -> None:
    list_response = APIClient().get(reverse("document-list"))
    upload_response = APIClient().post(
        reverse("document-list"),
        {"file": pdf_upload()},
        format="multipart",
    )

    assert list_response.status_code == 401
    assert upload_response.status_code == 401


def test_user_can_upload_pdf(tmp_path, settings) -> None:
    settings.MEDIA_ROOT = tmp_path
    client, user = authenticated_client()
    uploaded_file = pdf_upload()

    response = client.post(
        reverse("document-list"),
        {"file": uploaded_file},
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["original_filename"] == "study-notes.pdf"
    assert response.data["content_type"] == "application/pdf"
    assert response.data["file_size"] == uploaded_file.size
    assert response.data["status"] == "pending"
    assert response.data["file_url"].startswith("http://testserver/media/documents/")
    document = Document.objects.get(owner=user)
    assert document.file.name.startswith(f"documents/{user.id}/")
    assert (tmp_path / document.file.name).is_file()


def test_document_list_contains_only_authenticated_users_documents() -> None:
    client, user = authenticated_client("first-user")
    other_user = get_user_model().objects.create_user(username="second-user")
    own_document = Document.objects.create(
        owner=user,
        file=pdf_upload("mine.pdf"),
        original_filename="mine.pdf",
        content_type="application/pdf",
        file_size=15,
    )
    Document.objects.create(
        owner=other_user,
        file=pdf_upload("other.pdf"),
        original_filename="other.pdf",
        content_type="application/pdf",
        file_size=15,
    )

    response = client.get(reverse("document-list"))

    assert response.status_code == 200
    assert [document["id"] for document in response.data] == [own_document.id]


def test_user_can_get_own_document() -> None:
    client, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(),
        original_filename="study-notes.pdf",
        content_type="application/pdf",
        file_size=15,
    )

    response = client.get(reverse("document-detail", args=[document.id]))

    assert response.status_code == 200
    assert response.data["id"] == document.id


def test_user_cannot_get_another_users_document() -> None:
    client, _ = authenticated_client("first-user")
    other_user = get_user_model().objects.create_user(username="second-user")
    document = Document.objects.create(
        owner=other_user,
        file=pdf_upload(),
        original_filename="private.pdf",
        content_type="application/pdf",
        file_size=15,
    )

    response = client.get(reverse("document-detail", args=[document.id]))

    assert response.status_code == 404


def test_user_can_delete_own_document_and_stored_file(tmp_path, settings) -> None:
    settings.MEDIA_ROOT = tmp_path
    client, user = authenticated_client()
    upload_response = client.post(
        reverse("document-list"),
        {"file": pdf_upload()},
        format="multipart",
    )
    document = Document.objects.get(owner=user)
    stored_path = tmp_path / document.file.name

    response = client.delete(reverse("document-detail", args=[upload_response.data["id"]]))

    assert response.status_code == 204
    assert not Document.objects.filter(id=document.id).exists()
    assert not stored_path.exists()


@pytest.mark.parametrize(
    ("uploaded_file", "expected_error"),
    [
        (pdf_upload("notes.txt"), "Only PDF documents are supported."),
        (pdf_upload(content=b"not-a-pdf"), "Uploaded file is not a valid PDF document."),
        (
            pdf_upload(content=b"%PDF-1.4\ntruncated"),
            "PDF document is corrupt or structurally invalid.",
        ),
        (
            pdf_upload(content=create_pdf_content(encrypted=True)),
            "Encrypted or password-protected PDFs are not supported.",
        ),
        (
            pdf_upload(content=create_pdf_content(include_page=False)),
            "PDF document must contain at least one page.",
        ),
        (
            pdf_upload(content_type="text/plain"),
            "Uploaded file must have a PDF content type.",
        ),
        (
            pdf_upload(content=b"%PDF-" + b"0" * MAX_DOCUMENT_SIZE),
            "Document must be 10 MB or smaller.",
        ),
    ],
)
def test_upload_rejects_invalid_documents(uploaded_file, expected_error: str) -> None:
    client, _ = authenticated_client()

    response = client.post(
        reverse("document-list"),
        {"file": uploaded_file},
        format="multipart",
    )

    assert response.status_code == 400
    assert expected_error in str(response.data["file"])

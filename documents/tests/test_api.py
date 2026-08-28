from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import BytesIO
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APIClient

from documents import services
from documents.models import Document, DocumentContent
from documents.tasks import process_document_task
from documents.throttles import DocumentUploadRateThrottle
from documents.validators import MAX_DOCUMENT_SIZE

pytestmark = pytest.mark.django_db


def create_pdf_content(
    *,
    encrypted: bool = False,
    include_page: bool = True,
    text: str | None = None,
    page_count: int = 1,
) -> bytes:
    content = BytesIO()
    writer = PdfWriter()
    if include_page:
        for _ in range(page_count):
            page = writer.add_blank_page(width=200, height=200)
            if text:
                font = DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                    }
                )
                resources = DictionaryObject(
                    {
                        NameObject("/Font"): DictionaryObject(
                            {NameObject("/F1"): writer._add_object(font)}  # noqa: SLF001
                        )
                    }
                )
                stream = DecodedStreamObject()
                stream.set_data(f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode())
                page[NameObject("/Resources")] = resources
                page[NameObject("/Contents")] = writer._add_object(stream)  # noqa: SLF001
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
    settings.DOCUMENT_ROOT = tmp_path
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
    assert response.data["download_url"].endswith(f"/documents/{response.data['id']}/download")
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
    settings.DOCUMENT_ROOT = tmp_path
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


def test_upload_uses_server_detected_content_type() -> None:
    client, user = authenticated_client()

    response = client.post(
        reverse("document-list"),
        {"file": pdf_upload(content_type="text/plain")},
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["content_type"] == "application/pdf"
    assert Document.objects.get(owner=user).content_type == "application/pdf"


def test_upload_rejects_pdf_over_page_limit(settings) -> None:
    settings.DOCUMENT_MAX_PAGE_COUNT = 1
    client, _ = authenticated_client()

    response = client.post(
        reverse("document-list"),
        {"file": pdf_upload(content=create_pdf_content(page_count=2))},
        format="multipart",
    )

    assert response.status_code == 400
    assert "cannot contain more than 1 pages" in str(response.data["file"])


def test_streaming_upload_limit_stops_oversized_file(settings) -> None:
    settings.DOCUMENT_MAX_FILE_SIZE = 1024 * 1024
    client, _ = authenticated_client()
    oversized_upload = pdf_upload(content=b"%PDF-" + b"0" * (1024 * 1024))

    response = client.post(
        reverse("document-list"),
        {"file": oversized_upload},
        format="multipart",
    )

    assert response.status_code == 400
    assert "Document must be 1 MB or smaller" in str(response.data["file"])
    assert Document.objects.count() == 0


def test_upload_queues_processing_after_transaction_commit(
    django_capture_on_commit_callbacks,
    monkeypatch,
) -> None:
    client, _ = authenticated_client()
    queued_document_ids = []
    monkeypatch.setattr(process_document_task, "delay", queued_document_ids.append)

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("document-list"),
            {"file": pdf_upload()},
            format="multipart",
        )

    assert response.status_code == 201
    assert queued_document_ids == [response.data["id"]]


def test_processing_extracts_text_and_marks_document_ready(tmp_path, settings) -> None:
    settings.DOCUMENT_ROOT = tmp_path
    _, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(content=create_pdf_content(text="Quiz content from PDF")),
        original_filename="notes.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    services.process_document(document.id)

    document.refresh_from_db()
    assert document.status == Document.Status.READY
    assert document.failure_reason == ""
    assert document.content.text == "Quiz content from PDF"
    assert document.content.page_count == 1
    assert document.content.character_count == len("Quiz content from PDF")


def test_processing_sets_processing_status_before_extraction(monkeypatch) -> None:
    _, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(),
        original_filename="notes.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    def extraction_stub(processing_document: Document) -> services.ExtractedDocument:
        processing_document.refresh_from_db()
        assert processing_document.status == Document.Status.PROCESSING
        return services.ExtractedDocument(text="Extracted", page_count=1)

    monkeypatch.setattr(services, "extract_document_content", extraction_stub)

    services.process_document(document.id)

    document.refresh_from_db()
    assert document.status == Document.Status.READY


def test_processing_marks_textless_pdf_failed(tmp_path, settings) -> None:
    settings.DOCUMENT_ROOT = tmp_path
    _, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(),
        original_filename="blank.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    services.process_document(document.id)

    document.refresh_from_db()
    assert document.status == Document.Status.FAILED
    assert document.failure_reason == "No extractable text was found in this PDF."
    assert not DocumentContent.objects.filter(document=document).exists()


def test_processing_rejects_extracted_text_over_safety_limit(tmp_path, settings) -> None:
    settings.DOCUMENT_ROOT = tmp_path
    settings.DOCUMENT_MAX_EXTRACTED_CHARACTERS = 5
    _, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(content=create_pdf_content(text="Too much text")),
        original_filename="large-text.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    services.process_document(document.id)

    document.refresh_from_db()
    assert document.status == Document.Status.FAILED
    assert document.failure_reason == "Extracted document text exceeds the configured safety limit."


def test_owner_can_get_ready_extracted_content(tmp_path, settings) -> None:
    settings.DOCUMENT_ROOT = tmp_path
    client, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(content=create_pdf_content(text="Study material")),
        original_filename="notes.pdf",
        content_type="application/pdf",
        file_size=100,
    )
    services.process_document(document.id)

    response = client.get(reverse("document-content", args=[document.id]))

    assert response.status_code == 200
    assert response.data["text"] == "Study material"
    assert response.data["page_count"] == 1


def test_pending_document_content_returns_conflict() -> None:
    client, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(),
        original_filename="notes.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    response = client.get(reverse("document-content", args=[document.id]))

    assert response.status_code == 409


def test_owner_can_download_document_securely(tmp_path, settings) -> None:
    settings.DOCUMENT_ROOT = tmp_path
    client, user = authenticated_client()
    pdf_content = create_pdf_content(text="Private study material")
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(content=pdf_content),
        original_filename="private notes.pdf",
        content_type="application/pdf",
        file_size=len(pdf_content),
    )

    response = client.get(reverse("document-download", args=[document.id]))

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == pdf_content
    assert response["Content-Type"] == "application/pdf"
    assert "attachment;" in response["Content-Disposition"]


def test_user_cannot_download_another_users_document() -> None:
    client, _ = authenticated_client("first-user")
    other_user = get_user_model().objects.create_user(username="second-user")
    document = Document.objects.create(
        owner=other_user,
        file=pdf_upload(),
        original_filename="private.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    response = client.get(reverse("document-download", args=[document.id]))

    assert response.status_code == 404


def test_user_cannot_get_another_users_extracted_content() -> None:
    client, _ = authenticated_client("first-user")
    other_user = get_user_model().objects.create_user(username="second-user")
    document = Document.objects.create(
        owner=other_user,
        file=pdf_upload(),
        original_filename="private.pdf",
        content_type="application/pdf",
        file_size=100,
        status=Document.Status.READY,
    )
    DocumentContent.objects.create(
        document=document,
        text="Private extracted content",
        page_count=1,
        character_count=25,
    )

    response = client.get(reverse("document-content", args=[document.id]))

    assert response.status_code == 404


def test_celery_task_processes_document_in_eager_test_mode(tmp_path, settings) -> None:
    settings.DOCUMENT_ROOT = tmp_path
    _, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(content=create_pdf_content(text="Background content")),
        original_filename="background.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    process_document_task.delay(document.id)

    document.refresh_from_db()
    assert document.status == Document.Status.READY
    assert document.content.text == "Background content"


def test_upload_stores_sha256_checksum() -> None:
    client, user = authenticated_client()
    uploaded_content = create_pdf_content(text="Checksum content")

    response = client.post(
        reverse("document-list"),
        {"file": pdf_upload(content=uploaded_content)},
        format="multipart",
    )

    assert response.status_code == 201
    assert len(Document.objects.get(owner=user).checksum_sha256) == 64


def test_upload_rejects_duplicate_content() -> None:
    client, _ = authenticated_client()
    uploaded_content = create_pdf_content(text="Duplicate content")

    first_response = client.post(
        reverse("document-list"),
        {"file": pdf_upload("first.pdf", content=uploaded_content)},
        format="multipart",
    )
    second_response = client.post(
        reverse("document-list"),
        {"file": pdf_upload("renamed.pdf", content=uploaded_content)},
        format="multipart",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert "already been uploaded" in str(second_response.data["file"])


def test_upload_rejects_document_count_over_quota(settings) -> None:
    settings.DOCUMENT_MAX_COUNT_PER_USER = 1
    client, user = authenticated_client()
    Document.objects.create(
        owner=user,
        file=pdf_upload("existing.pdf"),
        original_filename="existing.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    response = client.post(
        reverse("document-list"),
        {"file": pdf_upload(content=create_pdf_content(text="New document"))},
        format="multipart",
    )

    assert response.status_code == 400
    assert "count quota" in str(response.data["file"])


def test_upload_rejects_document_over_storage_quota(settings) -> None:
    uploaded_content = create_pdf_content(text="Storage quota document")
    settings.DOCUMENT_MAX_TOTAL_BYTES_PER_USER = len(uploaded_content) - 1
    client, _ = authenticated_client()

    response = client.post(
        reverse("document-list"),
        {"file": pdf_upload(content=uploaded_content)},
        format="multipart",
    )

    assert response.status_code == 400
    assert "storage quota" in str(response.data["file"])


@pytest.mark.parametrize(
    "scan_error",
    [
        "The uploaded document failed the malware scan.",
        "Malware scanner is unavailable. Try the upload again later.",
    ],
)
def test_upload_rejects_unverified_document(monkeypatch, scan_error: str) -> None:
    client, _ = authenticated_client()

    def reject_scan(_uploaded_file) -> None:
        if "failed" in scan_error:
            from documents.security import MalwareDetectedError

            raise MalwareDetectedError(scan_error)
        from documents.security import MalwareScannerUnavailableError

        raise MalwareScannerUnavailableError(scan_error)

    monkeypatch.setattr(services, "scan_uploaded_document", reject_scan)

    response = client.post(
        reverse("document-list"),
        {"file": pdf_upload(content=create_pdf_content(text="Scanned document"))},
        format="multipart",
    )

    assert response.status_code == 400
    assert scan_error in str(response.data["file"])
    assert Document.objects.count() == 0


def test_document_upload_is_rate_limited(monkeypatch) -> None:
    cache.clear()
    monkeypatch.setattr(DocumentUploadRateThrottle, "get_rate", lambda _self: "1/hour")
    client, _ = authenticated_client()

    first_response = client.post(
        reverse("document-list"),
        {"file": pdf_upload(content=create_pdf_content(text="First upload"))},
        format="multipart",
    )
    second_response = client.post(
        reverse("document-list"),
        {"file": pdf_upload(content=create_pdf_content(text="Second upload"))},
        format="multipart",
    )
    cache.clear()

    assert first_response.status_code == 201
    assert second_response.status_code == 429


def test_owner_can_retry_failed_document(django_capture_on_commit_callbacks, monkeypatch) -> None:
    client, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(),
        original_filename="failed.pdf",
        content_type="application/pdf",
        file_size=100,
        status=Document.Status.FAILED,
        failure_reason="Previous failure",
    )
    queued_document_ids = []
    monkeypatch.setattr(services, "enqueue_document_processing", queued_document_ids.append)

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(reverse("document-retry", args=[document.id]))

    assert response.status_code == 202
    assert response.data["status"] == Document.Status.PENDING
    assert response.data["failure_reason"] == ""
    assert queued_document_ids == [document.id]


def test_retry_rejects_document_that_is_not_failed() -> None:
    client, user = authenticated_client()
    document = Document.objects.create(
        owner=user,
        file=pdf_upload(),
        original_filename="pending.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    response = client.post(reverse("document-retry", args=[document.id]))

    assert response.status_code == 409
    assert response.data["detail"] == "Only failed documents can be retried."


def test_user_cannot_retry_another_users_document() -> None:
    client, _ = authenticated_client("first-user")
    other_user = get_user_model().objects.create_user(username="second-user")
    document = Document.objects.create(
        owner=other_user,
        file=pdf_upload(),
        original_filename="private.pdf",
        content_type="application/pdf",
        file_size=100,
        status=Document.Status.FAILED,
    )

    response = client.post(reverse("document-retry", args=[document.id]))

    assert response.status_code == 404


def test_retention_cleanup_deletes_only_expired_documents_and_files(tmp_path, settings) -> None:
    settings.DOCUMENT_ROOT = tmp_path
    settings.DOCUMENT_RETENTION_DAYS = 30
    _, user = authenticated_client()
    expired = Document.objects.create(
        owner=user,
        file=pdf_upload("expired.pdf"),
        original_filename="expired.pdf",
        content_type="application/pdf",
        file_size=100,
    )
    current = Document.objects.create(
        owner=user,
        file=pdf_upload("current.pdf", content=create_pdf_content(text="current")),
        original_filename="current.pdf",
        content_type="application/pdf",
        file_size=100,
    )
    expired_path = tmp_path / expired.file.name
    Document.objects.filter(pk=expired.pk).update(created_at=timezone.now() - timedelta(days=31))

    deleted_count = services.delete_expired_documents(now=timezone.now())

    assert deleted_count == 1
    assert not Document.objects.filter(pk=expired.pk).exists()
    assert not expired_path.exists()
    assert Document.objects.filter(pk=current.pk).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_uploads_create_one_document(
    monkeypatch,
    tmp_path,
    settings,
) -> None:
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is covered in CI.")

    settings.DOCUMENT_ROOT = tmp_path
    user = get_user_model().objects.create_user(username="concurrent-user")
    scan_barrier = Barrier(2)
    monkeypatch.setattr(services, "scan_uploaded_document", lambda _file: scan_barrier.wait())
    monkeypatch.setattr(services, "enqueue_document_processing", lambda _document_id: None)

    def upload_document() -> str:
        close_old_connections()
        try:
            services.create_document(
                owner=user,
                uploaded_file=pdf_upload(content=create_pdf_content(text="Same content")),
            )
            return "created"
        except DRFValidationError:
            return "duplicate"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _index: upload_document(), range(2)))

    assert sorted(outcomes) == ["created", "duplicate"]
    assert Document.objects.filter(owner=user).count() == 1

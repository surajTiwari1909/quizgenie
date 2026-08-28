from io import BytesIO

import pytest

from documents import security


class FakeClamSocket:
    def __init__(self, response: bytes) -> None:
        self.response = response
        self.sent = bytearray()

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def recv(self, _size: int) -> bytes:
        response, self.response = self.response, b""
        return response


def test_clean_clamav_response_accepts_upload(monkeypatch, settings) -> None:
    settings.CLAMAV_ENABLED = True
    fake_socket = FakeClamSocket(b"stream: OK\0")
    monkeypatch.setattr(
        security.socket,
        "create_connection",
        lambda *_args, **_kwargs: fake_socket,
    )
    uploaded_file = BytesIO(b"safe-pdf-content")

    security.scan_uploaded_document(uploaded_file)

    assert fake_socket.sent.startswith(b"zINSTREAM\0")
    assert uploaded_file.tell() == 0


def test_clamav_detection_rejects_upload(monkeypatch, settings) -> None:
    settings.CLAMAV_ENABLED = True
    fake_socket = FakeClamSocket(b"stream: Eicar-Signature FOUND\0")
    monkeypatch.setattr(
        security.socket,
        "create_connection",
        lambda *_args, **_kwargs: fake_socket,
    )

    with pytest.raises(security.MalwareDetectedError):
        security.scan_uploaded_document(BytesIO(b"infected-content"))


def test_unavailable_clamav_rejects_upload(monkeypatch, settings) -> None:
    settings.CLAMAV_ENABLED = True

    def connection_failure(*_args, **_kwargs):
        raise ConnectionRefusedError

    monkeypatch.setattr(security.socket, "create_connection", connection_failure)

    with pytest.raises(security.MalwareScannerUnavailableError):
        security.scan_uploaded_document(BytesIO(b"unverified-content"))

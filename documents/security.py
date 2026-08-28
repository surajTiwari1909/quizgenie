import hashlib
import socket
import struct
from typing import BinaryIO

from django.conf import settings

SCAN_CHUNK_SIZE = 64 * 1024


class MalwareDetectedError(Exception):
    """ClamAV identified malware in an uploaded document."""


class MalwareScannerUnavailableError(Exception):
    """The upload could not be verified by ClamAV."""


def calculate_sha256(uploaded_file: BinaryIO) -> str:
    position = uploaded_file.tell()
    digest = hashlib.sha256()
    try:
        while chunk := uploaded_file.read(SCAN_CHUNK_SIZE):
            digest.update(chunk)
    finally:
        uploaded_file.seek(position)
    return digest.hexdigest()


def scan_uploaded_document(uploaded_file: BinaryIO) -> None:
    """Stream an upload to clamd using its INSTREAM protocol."""
    if not settings.CLAMAV_ENABLED:
        return

    position = uploaded_file.tell()
    try:
        with socket.create_connection(
            (settings.CLAMAV_HOST, settings.CLAMAV_PORT),
            timeout=settings.CLAMAV_TIMEOUT,
        ) as clam_socket:
            clam_socket.sendall(b"zINSTREAM\0")
            while chunk := uploaded_file.read(SCAN_CHUNK_SIZE):
                clam_socket.sendall(struct.pack(">I", len(chunk)))
                clam_socket.sendall(chunk)
            clam_socket.sendall(struct.pack(">I", 0))
            response = _read_clamd_response(clam_socket)
    except (OSError, TimeoutError) as error:
        raise MalwareScannerUnavailableError(
            "Malware scanner is unavailable. Try the upload again later."
        ) from error
    finally:
        uploaded_file.seek(position)

    if response.endswith(" OK"):
        return
    if response.endswith(" FOUND"):
        raise MalwareDetectedError("The uploaded document failed the malware scan.")
    raise MalwareScannerUnavailableError(
        "Malware scanner could not verify the document. Try the upload again later."
    )


def _read_clamd_response(clam_socket: socket.socket) -> str:
    response = bytearray()
    while True:
        chunk = clam_socket.recv(4096)
        if not chunk:
            break
        response.extend(chunk)
        if b"\0" in chunk:
            break
    return response.rstrip(b"\0\n").decode("utf-8", errors="replace")

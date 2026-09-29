"""Document upload validation and storage (contract POST /v1/documents).

D7/D15: text-layer PDFs only -- no OCR, no scanned images accepted, per the
endpoint's own contract text ("containing a text-layer PDF (D7 -- no OCR,
no scanned images accepted in this MVP)"). Validated here using the same
PyMuPDF approach already established in backend/documents/pdf_evidence.py,
not a new library.

Security (this task's explicit requirements):
- The client's filename is stored only as metadata (`original_name`),
  NEVER used to construct a filesystem path -- the stored filename is
  always a server-generated UUID. This is a path-traversal guard by
  construction, not by sanitizing an untrusted string.
- Size is checked via chunked/streaming read, aborting as soon as the
  limit is exceeded, so an oversized upload is never fully buffered in
  memory or written to disk.
- Magic bytes (`%PDF-`) are checked before any PDF parsing is attempted,
  so a non-PDF payload is rejected cheaply.

Contract note: this endpoint's status codes are 401/413/415/500 only --
there is no 422 in its list. Every content-rejection case (empty file, bad
magic bytes, image-only/scanned PDF, corrupt PDF) therefore maps to 415
UNSUPPORTED_MEDIA_TYPE, not 422, to stay within what the frozen contract
actually enumerates for this endpoint.
"""

from __future__ import annotations

import hashlib
import pathlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pymupdf as fitz

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB, contract section 10 decision 4
_PDF_MAGIC = b"%PDF-"

# Contract response includes `documentType`, but the request has no field
# for the client to supply one and no classification logic is in scope for
# this task (that would be an AI/extraction concern, explicitly excluded).
# This is a reported contract ambiguity (see this task's report), resolved
# here with a fixed, neutral placeholder -- never an invented clinical
# category.
_PLACEHOLDER_DOCUMENT_TYPE = "unspecified"

_PROCESSING_STATE_RECEIVED = "RECEIVED"


class UploadTooLargeError(Exception):
    """Raised when the upload exceeds MAX_UPLOAD_BYTES. Maps to 413."""


class UnsupportedDocumentError(Exception):
    """Raised for empty files, non-PDF magic bytes, corrupt PDFs, or
    PDFs with no extractable text layer (image-only/scanned). Maps to 415
    per this endpoint's contract status codes (no 422 is defined here).
    """


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso_string(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_storage_dir() -> pathlib.Path:
    """Directory documents are written to. Env override, git-ignored default."""

    import os

    env_dir = os.environ.get("DOCUMENT_STORAGE_DIR")
    path = pathlib.Path(env_dir) if env_dir else (
        pathlib.Path(__file__).resolve().parents[2] / "backend" / "data" / "documents"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_and_validate_size(chunks) -> bytes:
    """Consume an iterable of byte chunks, aborting the moment the total
    would exceed MAX_UPLOAD_BYTES -- never buffers more than that many
    bytes plus one chunk in memory.
    """

    buf = bytearray()
    for chunk in chunks:
        buf.extend(chunk)
        if len(buf) > MAX_UPLOAD_BYTES:
            raise UploadTooLargeError(
                f"upload exceeds {MAX_UPLOAD_BYTES} byte limit"
            )
    return bytes(buf)


def validate_pdf_and_get_page_count(file_bytes: bytes) -> int:
    """Magic-byte check, then open with PyMuPDF and require at least one
    page with a non-empty extracted text layer (D7/D15: text-layer PDFs
    only). Returns the page count on success.

    Raises UnsupportedDocumentError for: empty file, wrong magic bytes,
    a PDF PyMuPDF cannot open, or a PDF with no extractable text on any
    page (image-only / scanned -- explicitly out of scope per D7).
    """

    if not file_bytes:
        raise UnsupportedDocumentError("empty file")

    if not file_bytes.startswith(_PDF_MAGIC):
        raise UnsupportedDocumentError("not a PDF (magic bytes mismatch)")

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises its own exception types on corrupt input
        raise UnsupportedDocumentError(f"could not open as PDF: {exc}") from exc

    try:
        page_count = doc.page_count
        if page_count < 1:
            raise UnsupportedDocumentError("PDF has no pages")

        has_text_layer = any(
            doc[i].get_text().strip() for i in range(page_count)
        )
        if not has_text_layer:
            raise UnsupportedDocumentError(
                "no extractable text layer on any page (scanned/image-only "
                "PDFs are not accepted, D7)"
            )
        return page_count
    finally:
        doc.close()


@dataclass(frozen=True)
class StoredDocument:
    document_id: str
    original_name: str
    document_type: str
    received_at: datetime
    processing_state: str
    page_count: int


def store_uploaded_document(
    conn: sqlite3.Connection,
    *,
    device_id: str,
    original_name: str,
    file_bytes: bytes,
    page_count: int,
    now: datetime | None = None,
) -> StoredDocument:
    """Write the validated file to disk under a server-generated name, and
    record a documents row. `file_bytes` must already have passed
    validate_pdf_and_get_page_count (this function does not re-validate).

    `original_name` is stored as metadata ONLY -- it is never used to
    build the on-disk path (path-traversal guard by construction).
    """

    now = now or _utc_now()
    document_id = str(uuid.uuid4())
    stored_filename = f"{uuid.uuid4()}.pdf"
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    storage_dir = get_storage_dir()
    stored_path = storage_dir / stored_filename
    stored_path.write_bytes(file_bytes)

    conn.execute(
        """
        INSERT INTO documents (
            document_id, device_id, original_name, stored_filename,
            document_type, processing_state, page_count, content_hash,
            size_bytes, received_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            device_id,
            original_name,
            stored_filename,
            _PLACEHOLDER_DOCUMENT_TYPE,
            _PROCESSING_STATE_RECEIVED,
            page_count,
            content_hash,
            len(file_bytes),
            to_iso_string(now),
        ),
    )
    conn.commit()

    return StoredDocument(
        document_id=document_id,
        original_name=original_name,
        document_type=_PLACEHOLDER_DOCUMENT_TYPE,
        received_at=now,
        processing_state=_PROCESSING_STATE_RECEIVED,
        page_count=page_count,
    )

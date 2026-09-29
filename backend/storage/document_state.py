"""Document-row helpers needed by the extraction orchestrator: where a stored
PDF lives, and the document's `processing_state`. A NEW module -- the existing
storage modules are untouched by it.

Device scoping applies as everywhere in storage: another device's document is
indistinguishable from a missing one (DocumentNotFoundError). Nothing here logs
and no error message carries document content (D26).

`processing_state` values are the contract v1.2.0 section 3.2 set (decision 16).
They are plain strings; no enum is enforced at the database layer, matching
`documents.processing_state`'s existing definition.
"""

from __future__ import annotations

import pathlib
import sqlite3

from backend.storage.documents import get_storage_dir
from backend.storage.extraction import DocumentNotFoundError

STATE_RECEIVED = "RECEIVED"
STATE_EXTRACTING = "EXTRACTING"
STATE_PROPOSALS_READY = "PROPOSALS_READY"
STATE_EXTRACTION_FAILED = "EXTRACTION_FAILED"


class StoredFileUnavailableError(Exception):
    """The document's stored file is missing, unreadable, or its recorded name
    does not resolve to a regular file inside the storage directory. The
    message never contains a path or content."""


def get_stored_filename(conn: sqlite3.Connection, *, device_id: str, document_id: str) -> str:
    row = conn.execute(
        "SELECT stored_filename FROM documents WHERE document_id = ? AND device_id = ?",
        (document_id, device_id),
    ).fetchone()
    if row is None:
        raise DocumentNotFoundError("document not found")
    return row[0]


def set_processing_state(
    conn: sqlite3.Connection, *, device_id: str, document_id: str, state: str
) -> None:
    """Set `processing_state`; raises DocumentNotFoundError if the document is
    not this device's (nothing is written)."""

    try:
        cursor = conn.execute(
            "UPDATE documents SET processing_state = ? WHERE document_id = ? AND device_id = ?",
            (state, document_id, device_id),
        )
        if cursor.rowcount == 0:
            raise DocumentNotFoundError("document not found")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def resolve_stored_path(
    stored_filename: str, storage_dir: pathlib.Path | None = None
) -> pathlib.Path:
    """The on-disk path for a recorded `stored_filename`, guaranteed to be a
    regular file INSIDE the storage directory, or StoredFileUnavailableError.

    Upload writes `storage_dir / <server-generated uuid>.pdf` and records only
    that name, so a legitimate value is a bare file name. Anything else -- a
    separator, a drive, an absolute path, `..` -- is refused before the disk is
    touched, and the resolved path is then checked to lie inside the resolved
    storage directory (defeating symlink and case tricks) before it is used.
    """

    root = (storage_dir if storage_dir is not None else get_storage_dir()).resolve()
    name = pathlib.PurePath(stored_filename)
    if (
        not stored_filename
        or name.name != stored_filename
        or stored_filename in (".", "..")
        or name.is_absolute()
        or "/" in stored_filename
        or "\\" in stored_filename
        or ":" in stored_filename
    ):
        raise StoredFileUnavailableError("stored file unavailable")
    candidate = (root / stored_filename).resolve()
    if candidate.parent != root or not candidate.is_file():
        raise StoredFileUnavailableError("stored file unavailable")
    return candidate


def read_stored_file(stored_filename: str, storage_dir: pathlib.Path | None = None) -> bytes:
    path = resolve_stored_path(stored_filename, storage_dir)
    try:
        return path.read_bytes()
    except OSError:
        raise StoredFileUnavailableError("stored file unavailable") from None

"""SQLite storage init for the device/pairing-code backend foundation.

Per D6 (ARCHITECTURE_MVP_PLAN.md section 2 repo layout): server-side SQLite
holds only pre-confirmation, server-owned data (here: device identities and
pairing codes) -- never confirmed clinical data, which is device-canonical.

Standard library only (sqlite3): no ORM, no new dependency, per this task's
explicit scope.
"""

from __future__ import annotations

import os
import pathlib
import sqlite3

_DEFAULT_DB_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "backend" / "data" / "app.db"
)


def get_db_path() -> pathlib.Path:
    """DB path from DEVICE_DB_PATH, or a sensible local default under backend/data/."""

    env_path = os.environ.get("DEVICE_DB_PATH")
    if env_path:
        return pathlib.Path(env_path)
    return _DEFAULT_DB_PATH


def get_connection(db_path: pathlib.Path | None = None) -> sqlite3.Connection:
    """Open a connection to the given (or default/env) DB path, creating its
    parent directory and schema if needed.

    A fresh connection per call keeps this safe to use from FastAPI's
    synchronous request handlers and from tests without shared-state
    surprises; sqlite3 connections are cheap to open for a file this small.
    """

    path = db_path if db_path is not None else get_db_path()
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the devices/pairing_codes/documents tables, and the extraction
    tables (extraction_jobs/source_references/proposals/ai_request_log), if
    they do not already exist. Idempotent: safe to run on every connection
    and on databases created before the extraction tables existed.

    Only a hash of any secret value is ever stored (device token, pairing
    code) -- never the raw value, per this task's explicit requirement.
    Document rows hold pre-confirmation, server-owned metadata only (D6) --
    never confirmed clinical data, and never the client's raw filename as a
    storage path (path-traversal guard, backend/storage/documents.py).
    """

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            device_id   TEXT PRIMARY KEY,
            token_hash  TEXT NOT NULL UNIQUE,
            issued_at   TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pairing_codes (
            code_hash   TEXT PRIMARY KEY,
            device_id   TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            expires_at  TEXT NOT NULL,
            FOREIGN KEY (device_id) REFERENCES devices (device_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            document_id       TEXT PRIMARY KEY,
            device_id         TEXT NOT NULL,
            original_name     TEXT NOT NULL,
            stored_filename   TEXT NOT NULL UNIQUE,
            document_type     TEXT NOT NULL,
            processing_state  TEXT NOT NULL,
            page_count        INTEGER NOT NULL,
            content_hash      TEXT NOT NULL,
            size_bytes        INTEGER NOT NULL,
            received_at       TEXT NOT NULL,
            FOREIGN KEY (device_id) REFERENCES devices (device_id)
        )
        """
    )
    _init_extraction_schema(conn)
    conn.commit()


def _init_extraction_schema(conn: sqlite3.Connection) -> None:
    """Extraction storage (contract sections 3.3/3.4/5/6/7; plan 3.2).

    Pre-confirmation, server-owned data only (D6). proposed_fields_json and
    processing-style strings are generic text: no enum is enforced here except
    the job status, which is fixed by contract section 7. ai_request_log has
    NO prompt, response or document-text column, by design (PRIV-1652).
    """

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS extraction_jobs (
            job_id         TEXT PRIMARY KEY,
            document_id    TEXT NOT NULL,
            device_id      TEXT NOT NULL,
            status         TEXT NOT NULL
                           CHECK (status IN ('PENDING','RUNNING','COMPLETED','EXTRACTION_FAILED')),
            error_class    TEXT,
            retry_count    INTEGER,
            model          TEXT,
            schema_version TEXT,
            created_at     TEXT NOT NULL,
            started_at     TEXT,
            finished_at    TEXT,
            document_date  TEXT,
            FOREIGN KEY (document_id) REFERENCES documents (document_id),
            FOREIGN KEY (device_id) REFERENCES devices (device_id)
        )
        """
    )
    # document_date (extraction T5): the document's own verbatim issue date,
    # stored once per job (contract 3.3). Added after the first release of this
    # table, so databases created earlier get it via a guarded, idempotent
    # ALTER; a fresh database already has it from the CREATE above.
    job_columns = {row[1] for row in conn.execute("PRAGMA table_info(extraction_jobs)")}
    if "document_date" not in job_columns:
        try:
            conn.execute("ALTER TABLE extraction_jobs ADD COLUMN document_date TEXT")
        except sqlite3.OperationalError:
            # A concurrent connection added it between the check and the ALTER.
            job_columns = {row[1] for row in conn.execute("PRAGMA table_info(extraction_jobs)")}
            if "document_date" not in job_columns:
                raise
    # Contract section 1 idempotency: at most one active job per document.
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_extraction_jobs_active_per_document
        ON extraction_jobs (document_id)
        WHERE status IN ('PENDING','RUNNING')
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_references (
            source_reference_id TEXT PRIMARY KEY,
            document_id         TEXT NOT NULL,
            page                INTEGER NOT NULL,
            x0                  REAL NOT NULL,
            y0                  REAL NOT NULL,
            x1                  REAL NOT NULL,
            y1                  REAL NOT NULL,
            verbatim_text       TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (document_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS proposals (
            proposal_id                     TEXT PRIMARY KEY,
            document_id                     TEXT NOT NULL,
            job_id                          TEXT NOT NULL,
            device_id                       TEXT NOT NULL,
            proposed_type                   TEXT NOT NULL,
            proposed_fields_json            TEXT NOT NULL,
            original_text                   TEXT NOT NULL,
            source_reference_id             TEXT NOT NULL,
            page                            INTEGER NOT NULL,
            confidence                      REAL NOT NULL,
            review_state                    TEXT NOT NULL,
            verbatim_check                  TEXT NOT NULL,
            source_status                   TEXT,
            originally_proposed_fields_json TEXT,
            edited_fields_json              TEXT,
            edit_reason                     TEXT,
            reviewed_at                     TEXT,
            plain_language_text             TEXT,
            plain_language_is_verbatim_fallback INTEGER,
            created_at                      TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (document_id),
            FOREIGN KEY (job_id) REFERENCES extraction_jobs (job_id),
            FOREIGN KEY (device_id) REFERENCES devices (device_id),
            FOREIGN KEY (source_reference_id) REFERENCES source_references (source_reference_id)
        )
        """
    )
    # AIRequestLog (plan 3.2/5.5): content-free audit fields only. job_id is
    # deliberately NOT a foreign key, so a row can outlive its job's deletion
    # (see backend/storage/extraction.py, delete_document_extraction_data).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_request_log (
            log_id             INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id             TEXT NOT NULL,
            regime             TEXT NOT NULL,
            operation          TEXT NOT NULL,
            schema_version     TEXT NOT NULL,
            model              TEXT NOT NULL,
            latency_ms         REAL NOT NULL,
            validation_outcome TEXT NOT NULL,
            retry_count        INTEGER NOT NULL,
            error_class        TEXT,
            created_at         TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_extraction_jobs_document ON extraction_jobs (document_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_source_references_document ON source_references (document_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_proposals_document ON proposals (document_id)")

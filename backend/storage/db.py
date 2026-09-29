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
    """Create the devices/pairing_codes/documents tables if they do not
    already exist.

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
    conn.commit()

"""FastAPI dependencies shared across contract endpoints.

Contract section 1: auth is a single `X-Device-Token` header on every
request except /v1/health. `require_device_token` is opt-in per route
(FastAPI `Depends(...)`) -- it is NOT applied globally, so /v1/health and
the /v1/poc/p4/* POC routes are unaffected, per this task's explicit scope.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterator

from fastapi import Depends, Header

from backend.api.errors import ContractError
from backend.storage import devices as devices_storage
from backend.storage.db import get_connection


def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Per-request SQLite connection. FastAPI caches this per request, so a
    route that also depends on require_device_token shares one connection,
    not two. Overridden in tests (app.dependency_overrides) to point at a
    temp DB.
    """

    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def require_device_token(
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> str:
    """Validate X-Device-Token and return the resolved device_id.

    Raises ContractError("UNAUTHENTICATED") for a missing or unrecognised
    token -- the contract makes no distinction between the two cases in its
    error shape, so neither does this dependency.
    """

    if not x_device_token:
        raise ContractError("UNAUTHENTICATED")

    device_id = devices_storage.verify_device_token(conn, x_device_token)
    if device_id is None:
        raise ContractError("UNAUTHENTICATED")
    return device_id


def get_utc_now() -> datetime:
    """Current UTC time. A dependency so tests can inject a fixed clock."""

    return datetime.now(timezone.utc)


def require_upload_device(
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
    x_pairing_code: str | None = Header(default=None, alias="X-Pairing-Code"),
    conn: sqlite3.Connection = Depends(get_db_connection),
    now: datetime = Depends(get_utc_now),
) -> str:
    """Auth for POST /v1/documents ONLY (contract v1.1.0 section 1):
    X-Device-Token OR X-Pairing-Code, resolving to a device_id.

    Rule when both are sent: the device token wins and the pairing code is
    ignored -- an invalid token is NOT rescued by a valid code (fail closed).
    A header that is absent or empty counts as not sent. Neither -> 401.
    """

    if x_device_token:
        return require_device_token(x_device_token, conn)

    if x_pairing_code:
        device_id = devices_storage.resolve_pairing_code_device(conn, x_pairing_code, now=now)
        if device_id is not None:
            return device_id

    raise ContractError("UNAUTHENTICATED")

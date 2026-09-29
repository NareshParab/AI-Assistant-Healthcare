"""FastAPI dependencies shared across contract endpoints.

Contract section 1: auth is a single `X-Device-Token` header on every
request except /v1/health. `require_device_token` is opt-in per route
(FastAPI `Depends(...)`) -- it is NOT applied globally, so /v1/health and
the /v1/poc/p4/* POC routes are unaffected, per this task's explicit scope.
"""

from __future__ import annotations

import sqlite3
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

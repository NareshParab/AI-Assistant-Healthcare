"""Tests for X-Pairing-Code auth on POST /v1/documents
(docs/API_CONTRACT.md v1.1.0 section 1.0 / 3.2).

Offline: TestClient, temp SQLite DB and temp storage dir per test, and an
injected clock (get_utc_now dependency override) -- no sleeping. Synthetic
PDFs only.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_db_connection, get_utc_now
from backend.api.main import app
from backend.documents.synthetic_data import generate_synthetic_prescription
from backend.storage import devices as devices_storage
from backend.storage.db import get_connection

T0 = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def temp_db_path(tmp_path):
    return tmp_path / "test_app.db"


@pytest.fixture()
def clock():
    """Mutable injected clock; tests move it by assigning clock["now"]."""
    return {"now": T0}


@pytest.fixture()
def client(temp_db_path, tmp_path, monkeypatch, clock):
    monkeypatch.setenv("DOCUMENT_STORAGE_DIR", str(tmp_path / "doc_storage"))

    def _override_db():
        conn = get_connection(temp_db_path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db_connection] = _override_db
    app.dependency_overrides[get_utc_now] = lambda: clock["now"]
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db_connection, None)
        app.dependency_overrides.pop(get_utc_now, None)


def _register(client) -> str:
    return client.post("/v1/devices/register", json={}).json()["deviceToken"]


def _device_id_for(temp_db_path, token: str) -> str:
    conn = get_connection(temp_db_path)
    try:
        return devices_storage.verify_device_token(conn, token)
    finally:
        conn.close()


def _make_code(temp_db_path, device_id: str, *, now=T0, ttl_seconds=None) -> str:
    conn = get_connection(temp_db_path)
    try:
        return devices_storage.create_pairing_code(
            conn, device_id=device_id, now=now, ttl_seconds=ttl_seconds
        ).pairing_code
    finally:
        conn.close()


def _upload(client, headers):
    return client.post(
        "/v1/documents",
        headers=headers,
        files={"file": ("doc.pdf", generate_synthetic_prescription(), "application/pdf")},
    )


def _doc_device(temp_db_path, document_id: str) -> str:
    conn = sqlite3.connect(str(temp_db_path))
    try:
        return conn.execute(
            "SELECT device_id FROM documents WHERE document_id = ?", (document_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def _assert_unauthenticated(r):
    assert r.status_code == 401
    assert r.json() == {
        "error": {
            "code": "UNAUTHENTICATED",
            "message": r.json()["error"]["message"],
            "retryable": False,
        }
    }


def test_valid_pairing_code_upload_succeeds_and_binds_to_code_device(client, temp_db_path):
    token = _register(client)
    device_id = _device_id_for(temp_db_path, token)
    code = _make_code(temp_db_path, device_id)

    r = _upload(client, {"X-Pairing-Code": code})

    assert r.status_code == 201
    assert _doc_device(temp_db_path, r.json()["documentId"]) == device_id


def test_pairing_code_binds_to_the_right_device_when_several_exist(client, temp_db_path):
    device_a = _device_id_for(temp_db_path, _register(client))
    device_b = _device_id_for(temp_db_path, _register(client))
    code_b = _make_code(temp_db_path, device_b)

    r = _upload(client, {"X-Pairing-Code": code_b})

    assert r.status_code == 201
    assert _doc_device(temp_db_path, r.json()["documentId"]) == device_b != device_a


def test_pairing_code_is_reusable_until_expiry(client, temp_db_path, clock):
    device_id = _device_id_for(temp_db_path, _register(client))
    code = _make_code(temp_db_path, device_id)  # 15-minute default TTL

    assert _upload(client, {"X-Pairing-Code": code}).status_code == 201
    clock["now"] = T0 + timedelta(minutes=14)
    assert _upload(client, {"X-Pairing-Code": code}).status_code == 201


def test_expired_pairing_code_fails_closed(client, temp_db_path, clock):
    device_id = _device_id_for(temp_db_path, _register(client))
    code = _make_code(temp_db_path, device_id)

    clock["now"] = T0 + timedelta(minutes=15)  # exactly at expiry: not valid
    _assert_unauthenticated(_upload(client, {"X-Pairing-Code": code}))


def test_unknown_pairing_code_fails_closed(client):
    _assert_unauthenticated(_upload(client, {"X-Pairing-Code": "ZZZZZZ"}))


def test_no_credentials_fails_closed(client):
    _assert_unauthenticated(_upload(client, {}))


def test_empty_headers_count_as_not_sent(client):
    _assert_unauthenticated(_upload(client, {"X-Pairing-Code": ""}))


def test_both_headers_device_token_wins(client, temp_db_path):
    token_a = _register(client)
    device_a = _device_id_for(temp_db_path, token_a)
    device_b = _device_id_for(temp_db_path, _register(client))
    code_b = _make_code(temp_db_path, device_b)

    r = _upload(client, {"X-Device-Token": token_a, "X-Pairing-Code": code_b})

    assert r.status_code == 201
    assert _doc_device(temp_db_path, r.json()["documentId"]) == device_a


def test_both_headers_invalid_token_is_not_rescued_by_valid_code(client, temp_db_path):
    device_id = _device_id_for(temp_db_path, _register(client))
    code = _make_code(temp_db_path, device_id)

    r = _upload(client, {"X-Device-Token": "not-a-real-token", "X-Pairing-Code": code})

    _assert_unauthenticated(r)


def test_both_headers_valid_token_with_bad_code_still_succeeds(client, temp_db_path):
    token = _register(client)

    r = _upload(client, {"X-Device-Token": token, "X-Pairing-Code": "ZZZZZZ"})

    assert r.status_code == 201


def test_device_token_path_unchanged(client, temp_db_path):
    token = _register(client)
    device_id = _device_id_for(temp_db_path, token)

    r = _upload(client, {"X-Device-Token": token})

    assert r.status_code == 201
    assert _doc_device(temp_db_path, r.json()["documentId"]) == device_id


def test_pairing_code_rejected_on_other_authenticated_endpoint(client, temp_db_path):
    device_id = _device_id_for(temp_db_path, _register(client))
    code = _make_code(temp_db_path, device_id)

    r = client.post(
        "/v1/devices/pairing-code", headers={"X-Pairing-Code": code}, json={}
    )

    _assert_unauthenticated(r)

"""Tests for device registration, pairing-code creation, and the section-2
error envelope (docs/API_CONTRACT.md v1.0.0, commit e5c957f).

Fully offline: FastAPI TestClient (in-process, no real network), a fresh
temp SQLite DB per test (via dependency override, never the real default
DB path), and clock injection for expiry (never time.sleep).
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_db_connection
from backend.api.main import app
from backend.storage import devices as devices_storage
from backend.storage.db import get_connection


@pytest.fixture()
def temp_db_path(tmp_path):
    return tmp_path / "test_app.db"


@pytest.fixture()
def client(temp_db_path):
    """A TestClient whose DB dependency is overridden to a fresh temp file
    for this test only -- never touches the real default DB path.
    """

    def _override_get_db_connection():
        conn = get_connection(temp_db_path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db_connection] = _override_get_db_connection
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db_connection, None)


# ---------------------------------------------------------------------------
# POST /v1/devices/register
# ---------------------------------------------------------------------------


def test_register_returns_token_matching_contract_shape(client, temp_db_path):
    r = client.post("/v1/devices/register", json={})
    assert r.status_code == 201
    body = r.json()
    assert set(body.keys()) == {"deviceToken", "issuedAt"}
    assert isinstance(body["deviceToken"], str) and len(body["deviceToken"]) > 0
    # ISO-8601 UTC "Z" form, per contract section 1.
    datetime.strptime(body["issuedAt"], "%Y-%m-%dT%H:%M:%SZ")


def test_register_stores_only_a_hash_not_the_raw_token(client, temp_db_path):
    r = client.post("/v1/devices/register", json={})
    raw_token = r.json()["deviceToken"]

    conn = sqlite3.connect(str(temp_db_path))
    rows = conn.execute("SELECT token_hash FROM devices").fetchall()
    conn.close()

    assert len(rows) == 1
    stored_value = rows[0][0]
    assert stored_value != raw_token, "raw token must never be stored"
    assert stored_value == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def test_register_twice_issues_two_distinct_tokens(client, temp_db_path):
    r1 = client.post("/v1/devices/register", json={})
    r2 = client.post("/v1/devices/register", json={})
    assert r1.json()["deviceToken"] != r2.json()["deviceToken"]


# ---------------------------------------------------------------------------
# POST /v1/devices/pairing-code
# ---------------------------------------------------------------------------


def test_pairing_code_created_for_valid_token(client, temp_db_path):
    token = client.post("/v1/devices/register", json={}).json()["deviceToken"]

    r = client.post(
        "/v1/devices/pairing-code", json={}, headers={"X-Device-Token": token}
    )
    assert r.status_code == 201
    body = r.json()
    assert set(body.keys()) == {"pairingCode", "expiresAt"}
    assert len(body["pairingCode"]) == 6
    datetime.strptime(body["expiresAt"], "%Y-%m-%dT%H:%M:%SZ")


def test_pairing_code_missing_token_gives_contract_error_envelope(client):
    r = client.post("/v1/devices/pairing-code", json={})
    assert r.status_code == 401
    assert r.json() == {
        "error": {
            "code": "UNAUTHENTICATED",
            "message": "Missing or invalid device token.",
            "retryable": False,
        }
    }


def test_pairing_code_invalid_token_gives_contract_error_envelope(client):
    r = client.post(
        "/v1/devices/pairing-code",
        json={},
        headers={"X-Device-Token": "not-a-real-token"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


def test_pairing_code_format_uses_unambiguous_alphabet(client, temp_db_path):
    token = client.post("/v1/devices/register", json={}).json()["deviceToken"]
    r = client.post(
        "/v1/devices/pairing-code", json={}, headers={"X-Device-Token": token}
    )
    code = r.json()["pairingCode"]
    for ambiguous_char in "0O1IL":
        assert ambiguous_char not in code


def test_pairing_code_stores_only_a_hash_not_the_raw_code(client, temp_db_path):
    token = client.post("/v1/devices/register", json={}).json()["deviceToken"]
    r = client.post(
        "/v1/devices/pairing-code", json={}, headers={"X-Device-Token": token}
    )
    raw_code = r.json()["pairingCode"]

    conn = sqlite3.connect(str(temp_db_path))
    rows = conn.execute("SELECT code_hash FROM pairing_codes").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0][0] != raw_code
    assert rows[0][0] == hashlib.sha256(raw_code.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Pairing-code expiry -- storage layer, clock injected, never time.sleep.
# No contract endpoint exists in v1.0.0 to redeem/verify a pairing code
# (only creation is specified), so this is tested directly at the storage
# layer that a future redemption endpoint would call.
# ---------------------------------------------------------------------------


def test_pairing_code_valid_immediately_after_creation(temp_db_path):
    conn = get_connection(temp_db_path)
    device = devices_storage.register_device(conn)
    device_id = devices_storage.verify_device_token(conn, device.device_token)

    fixed_now = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)
    code = devices_storage.create_pairing_code(conn, device_id=device_id, now=fixed_now)

    assert devices_storage.is_pairing_code_valid(
        conn, code.pairing_code, now=fixed_now
    )
    conn.close()


def test_pairing_code_expires_after_fifteen_minutes_by_default(temp_db_path):
    conn = get_connection(temp_db_path)
    device = devices_storage.register_device(conn)
    device_id = devices_storage.verify_device_token(conn, device.device_token)

    created_at = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)
    code = devices_storage.create_pairing_code(conn, device_id=device_id, now=created_at)

    just_before_expiry = created_at + timedelta(minutes=14, seconds=59)
    just_after_expiry = created_at + timedelta(minutes=15, seconds=1)

    assert devices_storage.is_pairing_code_valid(
        conn, code.pairing_code, now=just_before_expiry
    )
    assert not devices_storage.is_pairing_code_valid(
        conn, code.pairing_code, now=just_after_expiry
    )
    conn.close()


def test_pairing_code_ttl_is_configurable_for_a_longer_lived_demo_code(temp_db_path):
    """The contract mentions a longer-lived demo code but defines no
    request-level mechanism for it (see this task's report). This test
    documents the resolution: TTL is a deployment-level parameter to
    create_pairing_code, not a new API field.
    """
    conn = get_connection(temp_db_path)
    device = devices_storage.register_device(conn)
    device_id = devices_storage.verify_device_token(conn, device.device_token)

    created_at = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)
    demo_ttl_seconds = 60 * 60 * 24  # a full day, e.g. for a demo deployment
    code = devices_storage.create_pairing_code(
        conn, device_id=device_id, now=created_at, ttl_seconds=demo_ttl_seconds
    )

    still_valid_after_one_hour = created_at + timedelta(hours=1)
    assert devices_storage.is_pairing_code_valid(
        conn, code.pairing_code, now=still_valid_after_one_hour
    )
    conn.close()


def test_unknown_pairing_code_is_invalid(temp_db_path):
    conn = get_connection(temp_db_path)
    assert not devices_storage.is_pairing_code_valid(conn, "ZZZZZZ")
    conn.close()


# ---------------------------------------------------------------------------
# Error envelope shape -- general cases beyond the device endpoints
# themselves, per this task's test requirements.
# ---------------------------------------------------------------------------


def test_unauthenticated_error_envelope_matches_contract_shape_exactly(client):
    r = client.post("/v1/devices/pairing-code", json={})
    body = r.json()
    assert list(body.keys()) == ["error"]
    assert set(body["error"].keys()) == {"code", "message", "retryable"}
    assert isinstance(body["error"]["code"], str)
    assert isinstance(body["error"]["message"], str)
    assert isinstance(body["error"]["retryable"], bool)


def test_unmatched_route_does_not_use_the_contract_envelope(client):
    """The v1.0.0 error-code list defines no generic 'route not found' code
    (see this task's report: a genuine contract gap, not resolved here by
    inventing a new code). FastAPI's own default response is used instead,
    and this test documents that fact rather than asserting the contract
    envelope shape, which would be incorrect.
    """
    r = client.get("/v1/this-route-does-not-exist")
    assert r.status_code == 404
    # NOT the contract's {"error": {...}} shape -- FastAPI's own default.
    assert "error" not in r.json() or "code" not in r.json().get("error", {})


# ---------------------------------------------------------------------------
# Existing routes unaffected (spot check; full behaviour already covered by
# test_pdf_evidence.py and smoke_test.py, untouched by this task).
# ---------------------------------------------------------------------------


def test_health_route_unaffected_and_needs_no_auth(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_poc_p4_fields_route_unaffected_and_needs_no_auth(client):
    r = client.get("/v1/poc/p4/fields")
    assert r.status_code == 200
    assert "fields" in r.json()

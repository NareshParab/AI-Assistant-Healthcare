"""Tests for POST /v1/documents (docs/API_CONTRACT.md v1.0.0 section 3.2).

Fully offline: FastAPI TestClient, a fresh temp SQLite DB per test (dependency
override), and a fresh temp on-disk storage dir per test (DOCUMENT_STORAGE_DIR
env override via monkeypatch) -- never the real default DB or storage path.

Synthetic-data rule: every PDF used here is generated in-test with pymupdf
(already a dependency, via backend.documents.synthetic_data / raw fitz), no
real patient data and no fixture files checked into the repo.
"""

from __future__ import annotations

import sqlite3

import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_db_connection
from backend.api.main import app
from backend.documents.synthetic_data import generate_synthetic_prescription
from backend.storage.db import get_connection


def _make_text_pdf_bytes() -> bytes:
    return generate_synthetic_prescription()


def _make_image_only_pdf_bytes() -> bytes:
    """A PDF with a page but no text layer at all -- must be rejected."""
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture()
def temp_db_path(tmp_path):
    return tmp_path / "test_app.db"


@pytest.fixture()
def temp_storage_dir(tmp_path, monkeypatch):
    storage_dir = tmp_path / "doc_storage"
    monkeypatch.setenv("DOCUMENT_STORAGE_DIR", str(storage_dir))
    return storage_dir


@pytest.fixture()
def client(temp_db_path, temp_storage_dir):
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


@pytest.fixture()
def device_token(client):
    return client.post("/v1/devices/register", json={}).json()["deviceToken"]


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_valid_upload_returns_contract_shaped_201(client, device_token):
    pdf_bytes = _make_text_pdf_bytes()
    r = client.post(
        "/v1/documents",
        headers={"X-Device-Token": device_token},
        files={"file": ("synthetic_prescription.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 201
    body = r.json()
    assert set(body.keys()) == {
        "documentId", "name", "documentType", "receivedAt",
        "processingState", "pageCount",
    }
    assert isinstance(body["documentId"], str) and body["documentId"]
    assert body["name"] == "synthetic_prescription.pdf"
    assert body["processingState"] == "RECEIVED"
    assert body["pageCount"] == 1
    from datetime import datetime
    datetime.strptime(body["receivedAt"], "%Y-%m-%dT%H:%M:%SZ")


def test_valid_upload_is_stored_on_disk_under_a_server_generated_name(
    client, device_token, temp_storage_dir
):
    pdf_bytes = _make_text_pdf_bytes()
    r = client.post(
        "/v1/documents",
        headers={"X-Device-Token": device_token},
        files={"file": ("original_client_name.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 201

    stored_files = list(temp_storage_dir.iterdir())
    assert len(stored_files) == 1
    stored_name = stored_files[0].name
    assert stored_name != "original_client_name.pdf"
    assert stored_files[0].read_bytes() == pdf_bytes


def test_valid_upload_creates_a_db_row_bound_to_the_device(
    client, device_token, temp_db_path
):
    pdf_bytes = _make_text_pdf_bytes()
    r = client.post(
        "/v1/documents",
        headers={"X-Device-Token": device_token},
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
    )
    document_id = r.json()["documentId"]

    conn = sqlite3.connect(str(temp_db_path))
    row = conn.execute(
        "SELECT device_id, original_name, stored_filename, page_count "
        "FROM documents WHERE document_id = ?",
        (document_id,),
    ).fetchone()
    conn.close()

    assert row is not None
    device_id, original_name, stored_filename, page_count = row
    assert original_name == "doc.pdf"
    assert stored_filename != "doc.pdf"
    assert page_count == 1


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_upload_missing_token_gives_contract_error_envelope(client):
    pdf_bytes = _make_text_pdf_bytes()
    r = client.post(
        "/v1/documents",
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


def test_upload_invalid_token_gives_contract_error_envelope(client):
    pdf_bytes = _make_text_pdf_bytes()
    r = client.post(
        "/v1/documents",
        headers={"X-Device-Token": "not-a-real-token"},
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


# ---------------------------------------------------------------------------
# Content rejections -- all map to 415 UNSUPPORTED_MEDIA_TYPE, since this
# endpoint's contract status codes have no 422.
# ---------------------------------------------------------------------------


def test_upload_non_pdf_with_pdf_filename_is_rejected(client, device_token):
    r = client.post(
        "/v1/documents",
        headers={"X-Device-Token": device_token},
        files={"file": ("fake.pdf", b"not a real pdf file at all", "application/pdf")},
    )
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_empty_file_is_rejected(client, device_token):
    r = client.post(
        "/v1/documents",
        headers={"X-Device-Token": device_token},
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_image_only_pdf_with_no_text_layer_is_rejected(client, device_token):
    pdf_bytes = _make_image_only_pdf_bytes()
    r = client.post(
        "/v1/documents",
        headers={"X-Device-Token": device_token},
        files={"file": ("scanned.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_oversize_file_is_rejected(client, device_token):
    oversized = b"%PDF-1.4\n" + (b"0" * (20 * 1024 * 1024 + 1))
    r = client.post(
        "/v1/documents",
        headers={"X-Device-Token": device_token},
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


# ---------------------------------------------------------------------------
# Path traversal
# ---------------------------------------------------------------------------


def test_path_traversal_filename_is_not_used_for_storage(
    client, device_token, temp_storage_dir
):
    pdf_bytes = _make_text_pdf_bytes()
    r = client.post(
        "/v1/documents",
        headers={"X-Device-Token": device_token},
        files={"file": ("../../etc/passwd.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 201
    body = r.json()
    # Original (attempted-traversal) name is preserved as metadata only.
    assert body["name"] == "../../etc/passwd.pdf"

    # Nothing was written outside the storage dir, and everything inside it
    # uses a server-generated name, never the client-supplied path fragments.
    stored_files = list(temp_storage_dir.iterdir())
    assert len(stored_files) == 1
    assert ".." not in stored_files[0].name
    assert "etc" not in stored_files[0].name


# ---------------------------------------------------------------------------
# Existing routes unaffected (spot check)
# ---------------------------------------------------------------------------


def test_health_route_unaffected(client):
    r = client.get("/v1/health")
    assert r.status_code == 200


def test_device_register_route_unaffected(client):
    r = client.post("/v1/devices/register", json={})
    assert r.status_code == 201

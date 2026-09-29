"""AI Assistant Healthcare backend -- FastAPI service.

Two layers coexist here deliberately:

1. The P4 Document Evidence POC (/v1/health, /v1/poc/p4/*) -- unchanged by
   this task. Proves D15/D16 only. See the original module docstring below
   for its own scope statement.
2. The API contract v1.0.0 foundation (docs/API_CONTRACT.md, commit
   e5c957f) -- device registration and pairing-code creation only, per this
   task's explicit scope. No document upload, extraction, review, routine,
   session, or delete endpoint exists here yet; those are later tasks.

Logging discipline (PRIV-1650/1652, D26): every log call in this module and
its imports passes only identifiers, HTTP status, and timing -- never a
document, token, pairing code, or request body value.
"""

from __future__ import annotations

import logging
import pathlib
import sqlite3
import time

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse

from backend.api.deps import get_db_connection, require_device_token
from backend.api.errors import register_exception_handlers
from backend.documents.pdf_evidence import (
    EvidenceNotFoundError,
    build_evidence_image,
)
from backend.documents.synthetic_data import generate_synthetic_prescription
from backend.storage import devices as devices_storage
from backend.storage.devices import to_iso_string

logger = logging.getLogger("p4.evidence")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="AI Assistant Healthcare -- Backend")
register_exception_handlers(app)

# Controlled field surface: internal identifier -> the exact text to locate.
# The identifier (left side) is what may ever appear in a log line. The
# search text (right side) is document content and must never be logged.
_FIELD_SEARCH_TEXT: dict[str, str] = {
    "medication_1": "Tab. Ecosprin 75mg",
    "medication_2": "Tab. Atorvastatin 10mg",
    "exercise": "Gentle 10 minute walk",
    "precaution": "Avoid heavy lifting",
    "followup": "Cardiology checkup",
}

_DEMO_DOC_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "demo-data"
    / "documents"
    / "synthetic_prescription.pdf"
)


def _load_demo_pdf_bytes() -> bytes:
    if _DEMO_DOC_PATH.exists():
        return _DEMO_DOC_PATH.read_bytes()
    # Regenerate in-memory if the demo asset hasn't been written to disk yet.
    return generate_synthetic_prescription()


@app.get("/v1/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/v1/poc/p4/evidence")
def get_demo_evidence(field: str) -> Response:
    start = time.perf_counter()

    search_text = _FIELD_SEARCH_TEXT.get(field)
    if search_text is None:
        logger.info("evidence request field=%s outcome=unknown_field", field)
        raise HTTPException(status_code=404, detail=f"unknown field id: {field}")

    pdf_bytes = _load_demo_pdf_bytes()
    try:
        png_bytes = build_evidence_image(pdf_bytes, search_text)
    except EvidenceNotFoundError:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.warning(
            "evidence request field=%s outcome=not_found elapsed_ms=%.1f",
            field,
            elapsed_ms,
        )
        raise HTTPException(status_code=422, detail="field text not found in document")

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "evidence request field=%s outcome=ok bytes=%d elapsed_ms=%.1f",
        field,
        len(png_bytes),
        elapsed_ms,
    )
    return Response(content=png_bytes, media_type="image/png")


@app.get("/v1/poc/p4/fields")
def list_fields() -> JSONResponse:
    """Lists available field ids only -- never the underlying document text."""
    return JSONResponse(content={"fields": sorted(_FIELD_SEARCH_TEXT.keys())})


# ---------------------------------------------------------------------------
# API contract v1.0.0 foundation (docs/API_CONTRACT.md, commit e5c957f).
# Devices only, per this task's scope. /v1/health and /v1/poc/p4/* above are
# unaffected -- neither new route is on their path, and require_device_token
# is applied only where declared below, not globally.
# ---------------------------------------------------------------------------


@app.post("/v1/devices/register", status_code=201)
def register_device_route(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> dict:
    """Contract section 3.1: issue a device token. Empty request body."""
    result = devices_storage.register_device(conn)
    # D26: never log the raw token -- only that registration happened.
    logger.info("device_register outcome=ok")
    return {
        "deviceToken": result.device_token,
        "issuedAt": to_iso_string(result.issued_at),
    }


@app.post("/v1/devices/pairing-code", status_code=201)
def create_pairing_code_route(
    device_id: str = Depends(require_device_token),
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> dict:
    """Contract section 3.1: create a pairing code for an authenticated
    device. Empty request body; auth via X-Device-Token (require_device_token
    raises ContractError("UNAUTHENTICATED") for a missing/invalid token,
    handled by the section-2 envelope registered above).
    """
    result = devices_storage.create_pairing_code(conn, device_id=device_id)
    # D26: never log the raw pairing code -- only the (internal) device id
    # and that creation happened.
    logger.info("pairing_code_create outcome=ok device_id=%s", device_id)
    return {
        "pairingCode": result.pairing_code,
        "expiresAt": to_iso_string(result.expires_at),
    }

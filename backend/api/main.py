"""P4 Document Evidence POC -- minimal FastAPI service.

Scope: proves D15/D16 only (locate a known field on the bundled synthetic
document, render a highlighted evidence image). No document upload, no
extraction job queue, no database, no AI, no companion, no product screens.
Those are later phases (ARCHITECTURE_MVP_PLAN.md D4/D9, P5+).

Logging discipline (PRIV-1650/1652, D26): every log call below passes only
identifiers (a field id such as "medication_1"), HTTP status, and timing.
No document text, patient text, or medication text is ever passed to the
logger. This is verified by the smoke test, not just asserted here.
"""

from __future__ import annotations

import logging
import pathlib
import time

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse

from backend.documents.pdf_evidence import (
    EvidenceNotFoundError,
    build_evidence_image,
)
from backend.documents.synthetic_data import generate_synthetic_prescription

logger = logging.getLogger("p4.evidence")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="AI Assistant Healthcare -- P4 Document Evidence POC")

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

"""
Minimal FastAPI scaffold — P4 increment only.

Per D5 (ARCHITECTURE_MVP_PLAN.md): a single stateless Python/FastAPI
service. This file intentionally contains ONLY what P4 needs to prove D16
end to end over HTTP:

  - GET /v1/health              liveness (per the API design in §4)
  - GET /v1/poc/p4/render       renders the bundled synthetic document
                                 with a highlighted span, for manual/POC
                                 verification

Everything else in the full API design (§4 of the architecture plan) —
document upload, extraction jobs, proposal review, routines, companion
pairing, etc. — is explicitly OUT OF SCOPE for this increment. No database
is wired up yet (D6); this app holds no state.

Per D26: no clinical content is ever logged. The one log line below logs
only a page number and a byte count, never document text.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from app.documents.extract import extract_text_spans, find_span_containing
from app.documents.render import render_page_with_highlight

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_assistant_healthcare.backend")

app = FastAPI(title="AI Assistant Healthcare — Backend (P4 POC scope only)")

DEMO_DOC_PATH = Path(__file__).resolve().parent.parent.parent / "demo-data" / "documents" / "synthetic_prescription.pdf"


@app.get("/v1/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/v1/poc/p4/render")
def poc_p4_render(needle: str = Query(default="Tablet A", description="Text to locate and highlight (POC only)")) -> Response:
    """
    P4 proof-of-concept endpoint only. Given a search string, finds the
    first matching text span in the bundled synthetic demo document and
    returns a cropped, highlighted PNG of that page region.

    This is NOT the production D16 endpoint shape (that is
    GET /v1/documents/{id}/pages/{n}/render?highlight=<sourceReferenceId>,
    per §4 of the architecture plan) — this POC has no document IDs or
    database, by design, because P4's job is only to prove the rendering
    mechanism works, not to build the full API surface.
    """
    if not DEMO_DOC_PATH.exists():
        raise HTTPException(status_code=500, detail="Synthetic demo document not found. Run scripts/generate_synthetic_prescription.py first.")

    spans = extract_text_spans(str(DEMO_DOC_PATH))
    match = find_span_containing(spans, needle)
    if match is None:
        raise HTTPException(status_code=404, detail=f"No span found containing '{needle}'")

    png_bytes = render_page_with_highlight(str(DEMO_DOC_PATH), match.page, match.bbox, crop=True)

    # PRIV-1650/1651/1652: log identifiers/metrics only, never document text.
    logger.info("p4_poc_render page=%d bbox=%s png_bytes=%d", match.page, match.bbox, len(png_bytes))

    return Response(content=png_bytes, media_type="image/png")

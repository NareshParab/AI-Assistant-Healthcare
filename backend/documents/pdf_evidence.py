"""P4 Document Evidence POC — core logic.

Proves ARCHITECTURE_MVP_PLAN.md D15/D16: given a text-layer PDF and a known
field, locate that field's real on-page geometry (page number + bounding
box), rasterize the page, draw a highlight over the exact located region,
and return a cropped, zoomed PNG of that region.

This module does not call any AI/LLM. The "known field" lookup here is a
deterministic text search (PyMuPDF's page.search_for), which returns the
PDF's actual glyph geometry -- not a fabricated or hand-computed box. That
is the point: the evidence image is built from real document geometry, so
a human reviewing it is checking the source, not a transcription of it
(closes PROJECT_REVIEW.md finding S1). Getting that geometry from an AI
extraction step instead of a text search is P5+ scope, not this checkpoint.

No document content is ever logged by this module (PRIV-1650/1652) -- see
backend/api/main.py for the logging boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import pymupdf as fitz
from PIL import Image, ImageDraw

HIGHLIGHT_FILL = (255, 230, 0, 90)  # translucent yellow
HIGHLIGHT_BORDER = (220, 30, 30, 255)  # red
DEFAULT_ZOOM = 3.0
DEFAULT_CROP_PADDING_PT = 36.0  # points, in *unzoomed* page space


class EvidenceNotFoundError(Exception):
    """Raised when the requested field text cannot be located on the page."""


@dataclass(frozen=True)
class EvidenceSpan:
    page_number: int  # 0-indexed, matches PyMuPDF convention
    search_text: str
    bbox_pt: tuple[float, float, float, float]  # (x0, y0, x1, y1) in points


def find_evidence_span(
    pdf_bytes: bytes, search_text: str, page_number: int = 0
) -> EvidenceSpan:
    """Locate `search_text` on the given page and return its real bbox.

    Raises EvidenceNotFoundError if no match is found. Uses the *first*
    match on the page, which is sufficient for this single-page POC.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if page_number >= doc.page_count:
            raise EvidenceNotFoundError(
                f"page {page_number} does not exist (document has {doc.page_count})"
            )
        page = doc[page_number]
        matches = page.search_for(search_text)
        if not matches:
            raise EvidenceNotFoundError(f"text not found on page {page_number}")
        rect = matches[0]
        return EvidenceSpan(
            page_number=page_number,
            search_text=search_text,
            bbox_pt=(rect.x0, rect.y0, rect.x1, rect.y1),
        )
    finally:
        doc.close()


def render_evidence_image(
    pdf_bytes: bytes,
    span: EvidenceSpan,
    zoom: float = DEFAULT_ZOOM,
    crop_padding_pt: float = DEFAULT_CROP_PADDING_PT,
) -> bytes:
    """Rasterize the page, draw a highlight over `span`, crop, return PNG bytes.

    The crop region is span.bbox_pt expanded by crop_padding_pt on every
    side (in page-space points, before zoom is applied), clamped to the
    page bounds. This is D16's "cropped, zoomed" evidence image -- legible
    at 10 feet on a TV, not a full page thumbnail.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc[span.page_number]
        page_rect = page.rect

        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        page_image = Image.frombytes(
            "RGB", (pixmap.width, pixmap.height), pixmap.samples
        )

        x0, y0, x1, y1 = span.bbox_pt

        # Highlight rectangle in pixel space (exact match to real geometry).
        hl_box = (x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom)
        overlay = Image.new("RGBA", page_image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle(hl_box, fill=HIGHLIGHT_FILL, outline=HIGHLIGHT_BORDER, width=3)
        page_image = Image.alpha_composite(page_image.convert("RGBA"), overlay)

        # Crop region: bbox + padding, clamped to page bounds, in pixel space.
        crop_x0 = max(0.0, x0 - crop_padding_pt) * zoom
        crop_y0 = max(0.0, y0 - crop_padding_pt) * zoom
        crop_x1 = min(page_rect.width, x1 + crop_padding_pt) * zoom
        crop_y1 = min(page_rect.height, y1 + crop_padding_pt) * zoom

        cropped = page_image.crop((crop_x0, crop_y0, crop_x1, crop_y1))
        cropped = cropped.convert("RGB")

        buf = BytesIO()
        cropped.save(buf, format="PNG")
        return buf.getvalue()
    finally:
        doc.close()


def build_evidence_image(pdf_bytes: bytes, search_text: str, page_number: int = 0) -> bytes:
    """Convenience wrapper: find the span, then render its evidence image."""
    span = find_evidence_span(pdf_bytes, search_text, page_number)
    return render_evidence_image(pdf_bytes, span)

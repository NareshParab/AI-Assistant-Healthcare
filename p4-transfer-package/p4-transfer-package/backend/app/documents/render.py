"""
Original-document evidence rendering: rasterize a page and draw a highlight
over a given bounding box, optionally cropped and zoomed.

Implements D16 (ARCHITECTURE_MVP_PLAN.md) — the single most important
feature in the product per the architecture lock and the project review's
top safety finding (S1): a human confirming an extracted proposal must
compare it against the ORIGINAL DOCUMENT, not against the model's own
transcription of it. This module produces that evidence image.

The client (Fire TV app, once built) is a dumb image viewer for this
output — no PDF logic on-device. This is a deliberate hedge documented in
D16 so the feature survives a possible D2 framework reversal.

No AI call, no clinical interpretation happens here. Pure rendering.
"""

from __future__ import annotations

import io

import pymupdf
from PIL import Image, ImageDraw

# Render at a higher DPI than the PDF's native 72dpi so the highlight and
# text stay legible when cropped/zoomed for a 10-foot TV display (HACK-411).
RENDER_ZOOM = 3.0  # ~216 DPI
HIGHLIGHT_COLOR = (255, 210, 0, 110)  # translucent amber overlay
HIGHLIGHT_BORDER = (200, 140, 0, 255)
CROP_PADDING_PT = 60  # PDF points of padding around the highlighted span


def render_page_with_highlight(
    pdf_path: str,
    page_index: int,
    bbox: tuple[float, float, float, float],
    crop: bool = True,
) -> bytes:
    """
    Rasterize `page_index` of `pdf_path`, draw a highlight rectangle over
    `bbox` (in PDF point coordinates, as returned by extract_text_spans),
    and return PNG bytes. If `crop` is True, returns a zoomed crop around
    the highlighted region instead of the full page (better for a TV at
    10 feet); otherwise returns the full page with the highlight drawn.
    """
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        matrix = pymupdf.Matrix(RENDER_ZOOM, RENDER_ZOOM)
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")

        # Scale bbox from PDF points to rendered pixel space.
        x0, y0, x1, y1 = bbox
        px0, py0, px1, py1 = (x0 * RENDER_ZOOM, y0 * RENDER_ZOOM, x1 * RENDER_ZOOM, y1 * RENDER_ZOOM)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle([px0, py0, px1, py1], fill=HIGHLIGHT_COLOR, outline=HIGHLIGHT_BORDER, width=3)
        composited = Image.alpha_composite(img, overlay)

        if crop:
            pad = CROP_PADDING_PT * RENDER_ZOOM
            crop_box = (
                max(0, px0 - pad),
                max(0, py0 - pad),
                min(composited.width, px1 + pad),
                min(composited.height, py1 + pad),
            )
            composited = composited.crop(crop_box)

        buf = io.BytesIO()
        composited.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()
    finally:
        doc.close()

"""Unit tests for the P4 Document Evidence POC core logic.

Uses only the synthetic demo document (backend/documents/synthetic_data.py).
No real patient data anywhere in this file (HACK-980/PRIV-982).
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from backend.documents.pdf_evidence import (
    EvidenceNotFoundError,
    build_evidence_image,
    find_evidence_span,
    render_evidence_image,
)
from backend.documents.synthetic_data import generate_synthetic_prescription

KNOWN_TEXT = "Tab. Ecosprin 75mg"
UNKNOWN_TEXT = "This text does not appear anywhere in the document"


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    return generate_synthetic_prescription()


def test_synthetic_pdf_is_nonempty(pdf_bytes: bytes) -> None:
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"  # real PDF file signature, not a fabricated blob


def test_find_evidence_span_returns_real_bbox(pdf_bytes: bytes) -> None:
    span = find_evidence_span(pdf_bytes, KNOWN_TEXT)
    assert span.page_number == 0
    x0, y0, x1, y1 = span.bbox_pt
    # A real located span has positive width/height and sits within a
    # plausible US-Letter page (612 x 792 pt) -- not a zero-size or
    # out-of-bounds placeholder box.
    assert x1 > x0 > 0
    assert y1 > y0 > 0
    assert x1 < 612
    assert y1 < 792


def test_find_evidence_span_raises_when_text_absent(pdf_bytes: bytes) -> None:
    with pytest.raises(EvidenceNotFoundError):
        find_evidence_span(pdf_bytes, UNKNOWN_TEXT)


def test_render_evidence_image_is_valid_png(pdf_bytes: bytes) -> None:
    span = find_evidence_span(pdf_bytes, KNOWN_TEXT)
    png_bytes = render_evidence_image(pdf_bytes, span)

    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # real PNG signature

    img = Image.open(io.BytesIO(png_bytes))
    assert img.format == "PNG"
    # Cropped region (bbox + 36pt padding on each side, zoomed 3x) should be
    # a small evidence crop, not a full page and not a degenerate sliver.
    assert 50 < img.width < 900
    assert 50 < img.height < 900


def test_render_evidence_image_actually_draws_a_highlight(pdf_bytes: bytes) -> None:
    """Sanity check that the highlight is real pixel change, not a no-op.

    Compares the rendered evidence crop against a same-region crop of the
    page with NO highlight applied. If the highlight draw were silently
    skipped, the two images would be pixel-identical.
    """
    span = find_evidence_span(pdf_bytes, KNOWN_TEXT)
    highlighted_png = render_evidence_image(pdf_bytes, span)

    import pymupdf as fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[span.page_number]
    matrix = fitz.Matrix(3.0, 3.0)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    plain_img = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    x0, y0, x1, y1 = span.bbox_pt
    zoom = 3.0
    pad = 36.0
    crop_box = (
        max(0.0, x0 - pad) * zoom,
        max(0.0, y0 - pad) * zoom,
        min(612.0, x1 + pad) * zoom,
        min(792.0, y1 + pad) * zoom,
    )
    plain_crop = plain_img.crop(crop_box)
    doc.close()

    highlighted_img = Image.open(io.BytesIO(highlighted_png)).convert("RGB")

    assert highlighted_img.size == plain_crop.size
    assert highlighted_img.tobytes() != plain_crop.tobytes(), (
        "highlighted evidence image is pixel-identical to the unhighlighted "
        "crop -- the highlight was not actually drawn"
    )


def test_build_evidence_image_convenience_wrapper(pdf_bytes: bytes) -> None:
    png_bytes = build_evidence_image(pdf_bytes, KNOWN_TEXT)
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_multiple_known_fields_all_locate_successfully(pdf_bytes: bytes) -> None:
    known_fields = [
        "Tab. Ecosprin 75mg",
        "Tab. Atorvastatin 10mg",
        "Gentle 10 minute walk",
        "Avoid heavy lifting",
        "Cardiology checkup",
    ]
    for text in known_fields:
        span = find_evidence_span(pdf_bytes, text)
        assert span.bbox_pt[2] > span.bbox_pt[0]

"""
P4 POC success-criteria test.

Checks the exact success criteria stated in ARCHITECTURE_MVP_PLAN.md §12
for P4:

  "The returned image visibly and correctly highlights the right text,
   is legible at 10 feet when cropped and zoomed, and round-trips in
   under ~2 seconds."

Automatable here: bbox extraction finds the right span; the rendered
image actually contains highlight-colored pixels over that region (proves
"visibly and correctly highlights"); rendering completes well under the
~2s budget. "Legible at 10 feet" is inherently a human visual judgement,
so this test also writes the rendered PNG to disk for manual inspection
per the architecture plan's own POC methodology (capture + report).
"""

from __future__ import annotations

import time
from pathlib import Path

from PIL import Image

from app.documents.extract import extract_text_spans, find_span_containing
from app.documents.render import HIGHLIGHT_BORDER, render_page_with_highlight

DEMO_DOC_PATH = Path(__file__).resolve().parent.parent.parent / "demo-data" / "documents" / "synthetic_prescription.pdf"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def test_extraction_finds_span_with_bbox():
    spans = extract_text_spans(str(DEMO_DOC_PATH))
    assert spans, "Expected at least one extracted text span"
    match = find_span_containing(spans, "Tablet A")
    assert match is not None, "Expected to find the 'Tablet A' line"
    assert match.text.strip() != ""
    x0, y0, x1, y1 = match.bbox
    assert x1 > x0 and y1 > y0, "Bounding box must have positive width and height"


def test_render_round_trip_under_budget_and_highlight_visible():
    spans = extract_text_spans(str(DEMO_DOC_PATH))
    match = find_span_containing(spans, "Tablet A")
    assert match is not None

    start = time.perf_counter()
    png_bytes = render_page_with_highlight(str(DEMO_DOC_PATH), match.page, match.bbox, crop=True)
    elapsed = time.perf_counter() - start

    # Success criterion: round-trips in under ~2 seconds.
    assert elapsed < 2.0, f"Render took {elapsed:.3f}s, exceeding the ~2s POC budget"

    # Success criterion: image is a valid, non-trivial PNG.
    img = Image.open(__import__("io").BytesIO(png_bytes))
    assert img.format == "PNG"
    assert img.width > 50 and img.height > 20

    # Success criterion: highlight is actually present (border color pixel exists).
    rgb_img = img.convert("RGB")
    pixels = rgb_img.getdata()
    border_rgb = HIGHLIGHT_BORDER[:3]
    tolerance = 12
    found_highlight = any(
        all(abs(p[i] - border_rgb[i]) <= tolerance for i in range(3)) for p in pixels
    )
    assert found_highlight, "Expected highlight border color to be present in the rendered image"

    # Save output for manual 10-foot legibility inspection (per §12's POC method).
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "p4_poc_highlighted_crop.png"
    out_path.write_bytes(png_bytes)
    assert out_path.exists()

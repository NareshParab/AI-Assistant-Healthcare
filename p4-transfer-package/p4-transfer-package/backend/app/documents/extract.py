"""
Text + bounding-box extraction from text-layer PDFs.

Implements D15 (ARCHITECTURE_MVP_PLAN.md): server-side extraction of text
spans WITH page number and bounding box, from text-layer PDFs. No OCR.

This module does NOT call any AI provider and does NOT classify, structure,
or interpret the extracted text clinically — it is pure text/geometry
extraction. ASSIST-regime AI structuring (SAFE-900/SAFE-915) is a separate,
later module that consumes this output; it is explicitly out of scope here.

Every extracted span keeps `page` and `bbox` together with its verbatim
text, because those three fields are what make D16 (rendering the original
document region with a highlight) possible.
"""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf


@dataclass(frozen=True)
class TextSpan:
    """One line/span of text as it literally appears on the page."""

    page: int  # 0-indexed page number
    text: str  # verbatim text, never paraphrased or normalized
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1) in PDF points


def extract_text_spans(pdf_path: str) -> list[TextSpan]:
    """
    Extract every line of text from a text-layer PDF, each with its exact
    bounding box. Returns an empty list for a page with no text layer
    (i.e. a scanned image) rather than guessing — OCR is explicitly out of
    scope for the MVP (D7).
    """
    spans: list[TextSpan] = []
    doc = pymupdf.open(pdf_path)
    try:
        for page_index, page in enumerate(doc):
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                    if not line_text.strip():
                        continue
                    x0, y0, x1, y1 = line["bbox"]
                    spans.append(
                        TextSpan(
                            page=page_index,
                            text=line_text,
                            bbox=(x0, y0, x1, y1),
                        )
                    )
    finally:
        doc.close()
    return spans


def find_span_containing(spans: list[TextSpan], needle: str) -> TextSpan | None:
    """
    Locate the first span whose verbatim text contains `needle`.
    Used only by the P4 POC harness to pick a span to highlight — this is
    NOT the ASSIST extraction/structuring pipeline (that's a later phase).
    """
    for span in spans:
        if needle in span.text:
            return span
    return None

"""Deterministic line-level text spans from a text-layer PDF (D15, extraction T1).

Pure: PDF bytes in, spans out. No database, no AI, no network, no logging --
D26/PRIV-1650: span text is document content and is never logged here. No
OCR (D7): a page without a text layer yields no spans and is flagged.

Span model
----------
One `Span` per non-blank text line as PyMuPDF reports it
(`page.get_text("dict")`), carrying:

* `span_id`      -- `p{page}_l{n}`: page 0-indexed, n 0-indexed in reading
                    order on that page. Deterministic for the same bytes.
* `text`         -- the line exactly as extracted. NOT normalized (see below).
* `bbox_pt`      -- (x0, y0, x1, y1) in PDF points, the line's own geometry
                    (never a text search, so duplicate lines keep their own
                    boxes).
* `page_number`  -- 0-indexed, matching pdf_evidence.EvidenceSpan.
* `heading`      -- text of the nearest PRECEDING heading line, or None.
* `is_heading`   -- whether this line itself is a heading.

Reading order
-------------
Lines are sorted by (rounded baseline y, x0): top to bottom, then left to
right within a visual row. Rows are compared on the rounded baseline, so text
of different font sizes on one baseline is one row. Rotated text is not
handled specially.

Heading rule (ONE rule, deliberately simple)
--------------------------------------------
The *body size* is the font size carrying the most non-whitespace characters
across the WHOLE document (sizes compared at 0.1 pt; ties resolve to the
smaller size). Document-wide, not per page, so a sparse page cannot elect a
minority size as "body". A line is a heading iff its largest font size is at
least `HEADING_SIZE_MARGIN_PT` (0.5 pt) larger than the body size. Bold,
all-caps and position are NOT considered. Consequences, by design:
smaller-than-body text (footers, markers) is never a heading; a document whose
text is all one size has no headings; a document whose body text is scarcer
(in characters) than some other size will misfire, which is why the rule is
documented and tested rather than made clever. The heading carries across
page boundaries: a page's first lines inherit the last heading of the previous
page (conservative: it is used downstream only as a hint that can push an item
toward human review).

Text normalization
------------------
None. `Span.text` is the raw extracted line. `collapse_whitespace` exists for
COMPARISON only (runs of whitespace -> one space, trimmed). It changes nothing
else: ligatures, Unicode punctuation, hyphens and case are left as they are.
Note `\\s` (and therefore the helper) also matches U+00A0 (no-break space).

Wrapped text
------------
A visually wrapped sentence is several spans (one per line). A value that
wraps across two lines is therefore NOT a substring of any single span;
callers must decide how to treat that (later task).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import pymupdf as fitz

from backend.documents.pdf_evidence import EvidenceSpan

MAX_PAGES = 50
MAX_SPANS = 5000
HEADING_SIZE_MARGIN_PT = 0.5


class SpanExtractionError(Exception):
    """Base class for span-extraction domain errors. Messages never contain
    document content."""


class PdfUnreadableError(SpanExtractionError):
    """Corrupt, unopenable or password-protected PDF."""


class SpanLimitExceededError(SpanExtractionError):
    """The document exceeds MAX_PAGES or MAX_SPANS (or the caller's caps)."""


@dataclass(frozen=True)
class Span:
    span_id: str
    page_number: int
    line_index: int
    text: str
    bbox_pt: tuple[float, float, float, float]
    heading: str | None
    is_heading: bool

    def to_evidence_span(self) -> EvidenceSpan:
        """Directly usable by pdf_evidence.render_evidence_image."""
        return EvidenceSpan(
            page_number=self.page_number,
            search_text=self.text,
            bbox_pt=self.bbox_pt,
        )


@dataclass(frozen=True)
class PageSpans:
    page_number: int
    spans: tuple[Span, ...]

    @property
    def has_text_layer(self) -> bool:
        return len(self.spans) > 0


@dataclass(frozen=True)
class DocumentSpans:
    pages: tuple[PageSpans, ...]
    _by_id: dict[str, Span] = field(repr=False, compare=False, default_factory=dict)

    @property
    def spans(self) -> tuple[Span, ...]:
        return tuple(s for p in self.pages for s in p.spans)

    def get(self, span_id: str) -> Span | None:
        return self._by_id.get(span_id)


def collapse_whitespace(text: str) -> str:
    """Comparison helper: collapse runs of whitespace to one space and trim.
    Nothing else is normalized."""

    return re.sub(r"\s+", " ", text).strip()


def _line_text(line: dict) -> str:
    return "".join(span["text"] for span in line["spans"])


def _page_lines(page) -> list[dict]:
    """Non-blank lines of a page, in reading order."""

    lines = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:  # 0 = text block; skip images
            continue
        for line in block["lines"]:
            if _line_text(line).strip():
                lines.append(line)

    def key(line: dict) -> tuple[int, float]:
        baseline_y = line["spans"][0]["origin"][1]
        return (round(baseline_y), line["bbox"][0])

    return sorted(lines, key=key)


def _body_size(all_lines: list[dict]) -> float | None:
    counts: Counter[float] = Counter()
    for line in all_lines:
        for span in line["spans"]:
            counts[round(span["size"], 1)] += len("".join(span["text"].split()))
    if not counts:
        return None
    top = max(counts.values())
    return min(size for size, n in counts.items() if n == top)


def _line_size(line: dict) -> float:
    return max(round(span["size"], 1) for span in line["spans"] if span["text"].strip())


def extract_spans(
    pdf_bytes: bytes,
    *,
    max_pages: int = MAX_PAGES,
    max_spans: int = MAX_SPANS,
) -> DocumentSpans:
    """Extract line-level spans for every page.

    Raises PdfUnreadableError (corrupt / password-protected) or
    SpanLimitExceededError (over the page or span cap). Never returns a
    partial result.
    """

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        raise PdfUnreadableError("could not open PDF") from None

    try:
        if doc.needs_pass:
            raise PdfUnreadableError("PDF is password-protected")
        if doc.page_count > max_pages:
            raise SpanLimitExceededError(f"document exceeds {max_pages} pages")

        page_lines: list[list[dict]] = []
        total = 0
        for page_number in range(doc.page_count):
            try:
                lines = _page_lines(doc[page_number])
            except Exception:
                raise PdfUnreadableError("could not read a page") from None
            total += len(lines)
            if total > max_spans:
                raise SpanLimitExceededError(f"document exceeds {max_spans} spans")
            page_lines.append(lines)

        body = _body_size([line for lines in page_lines for line in lines])

        pages: list[PageSpans] = []
        by_id: dict[str, Span] = {}
        current_heading: str | None = None

        for page_number, lines in enumerate(page_lines):
            page_spans: list[Span] = []
            for n, line in enumerate(lines):
                text = _line_text(line)
                is_heading = body is not None and _line_size(line) >= body + HEADING_SIZE_MARGIN_PT
                span = Span(
                    span_id=f"p{page_number}_l{n}",
                    page_number=page_number,
                    line_index=n,
                    text=text,
                    bbox_pt=tuple(line["bbox"]),
                    heading=current_heading,
                    is_heading=is_heading,
                )
                page_spans.append(span)
                by_id[span.span_id] = span
                if is_heading:
                    current_heading = text
            pages.append(PageSpans(page_number=page_number, spans=tuple(page_spans)))

        return DocumentSpans(pages=tuple(pages), _by_id=by_id)
    finally:
        doc.close()

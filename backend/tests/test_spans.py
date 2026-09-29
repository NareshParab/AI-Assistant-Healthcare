"""Tests for backend/documents/spans.py (extraction T1).

Offline, synthetic fixtures only (backend/documents/synthetic_data.py, D27).
The PDF quirks these tests pin down are documented in spans.py and decide how
strict a later verbatim-substring gate can be.
"""

from __future__ import annotations

import io

import pymupdf as fitz
import pytest
from PIL import Image

from backend.documents import synthetic_data as sd
from backend.documents.pdf_evidence import render_evidence_image
from backend.documents.spans import (
    PdfUnreadableError,
    SpanLimitExceededError,
    collapse_whitespace,
    extract_spans,
)


def _texts(doc_spans, page=0):
    return [s.text for s in doc_spans.pages[page].spans]


# --- determinism, order, ids -------------------------------------------------


def test_span_ids_are_deterministic_across_runs():
    pdf = sd.generate_synthetic_prescription()
    a = extract_spans(pdf)
    b = extract_spans(pdf)
    assert [(s.span_id, s.text, s.bbox_pt) for s in a.spans] == [
        (s.span_id, s.text, s.bbox_pt) for s in b.spans
    ]
    assert [s.span_id for s in a.pages[0].spans] == [
        f"p0_l{n}" for n in range(len(a.pages[0].spans))
    ]


def test_reading_order_is_top_to_bottom_then_left_to_right():
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Inserted out of order on purpose; two items share one baseline.
    page.insert_text((300, 100), "RIGHT", fontsize=11, fontname="helv")
    page.insert_text((40, 200), "LOWER", fontsize=11, fontname="helv")
    page.insert_text((40, 100), "LEFT", fontsize=11, fontname="helv")
    pdf = doc.tobytes()
    doc.close()

    assert _texts(extract_spans(pdf)) == ["LEFT", "RIGHT", "LOWER"]


def test_pages_are_zero_indexed_and_ids_carry_the_page():
    ds = extract_spans(sd.generate_multipage_document())
    assert len(ds.pages) == 2
    assert ds.pages[1].spans[0].span_id == "p1_l0"
    assert ds.pages[1].spans[0].page_number == 1
    assert ds.get("p1_l1") is ds.pages[1].spans[1]
    assert ds.get("nope") is None


def test_standard_prescription_lines_are_extracted_verbatim():
    texts = _texts(extract_spans(sd.generate_synthetic_prescription()))
    assert "Medication: Tab. Ecosprin 75mg -- 1 tablet before breakfast" in texts
    assert sd.SYNTHETIC_MARKER in texts


# --- duplicates --------------------------------------------------------------


def test_duplicate_identical_lines_get_distinct_ids_and_bboxes():
    ds = extract_spans(sd.generate_duplicate_lines_document())
    dupes = [s for s in ds.spans if s.text.startswith("Medication: Tab. Sampledrug")]
    assert len(dupes) == 2
    assert dupes[0].text == dupes[1].text
    assert dupes[0].span_id != dupes[1].span_id
    assert dupes[0].bbox_pt != dupes[1].bbox_pt
    assert dupes[0].bbox_pt[1] < dupes[1].bbox_pt[1]  # first is above the second


# --- wrapped lines -----------------------------------------------------------


def test_wrapped_sentence_is_split_into_one_span_per_visual_line():
    ds = extract_spans(sd.generate_wrapped_line_document())
    body = [s.text for s in ds.spans if not s.text.startswith("SYNTHETIC")]
    assert body == [
        "Tab. Metformin 500mg -- 1",
        "tablet twice daily after meals",
        "with water",
    ]
    # Consequence for a later substring gate: a value that wraps is not a
    # substring of any single span, but is after joining with one space.
    assert not any("1 tablet twice" in s.text for s in ds.spans)
    joined = " ".join(body)
    assert "500mg -- 1 tablet twice daily" in joined


# --- headings ----------------------------------------------------------------


def test_heading_is_none_before_any_heading():
    ds = extract_spans(sd.generate_synthetic_prescription())
    assert ds.pages[0].spans[0].heading is None  # synthetic marker line
    assert ds.pages[0].spans[1].heading is None  # first heading has no predecessor


def test_nearest_preceding_heading_for_body_lines():
    ds = extract_spans(sd.generate_synthetic_prescription())
    med = next(s for s in ds.spans if s.text.startswith("Medication: Tab. Ecosprin"))
    assert med.heading == "Prescription"
    assert not med.is_heading
    # Smaller-than-body text (marker, footer) is never a heading.
    assert not ds.pages[0].spans[0].is_heading
    assert not ds.pages[0].spans[-1].is_heading


def test_discontinued_section_lines_carry_the_discontinued_heading():
    ds = extract_spans(sd.generate_discontinued_section_document())
    by_text = {s.text: s for s in ds.spans}
    assert by_text["Tab. Currentdrug 5mg -- 1 tablet daily"].heading == "Current medications"
    assert by_text["Discontinued medications"].is_heading
    assert by_text["Discontinued medications"].heading == "Current medications"
    assert by_text["Tab. Olddrug 20mg -- 1 tablet twice daily"].heading == "Discontinued medications"
    assert by_text["Tab. Otherolddrug 2mg -- 1 tablet at night"].heading == "Discontinued medications"


def test_heading_carries_across_page_boundary():
    ds = extract_spans(sd.generate_multipage_document())
    assert ds.pages[1].spans[0].heading == "Demo Care Clinic"  # inherited
    assert ds.pages[1].spans[2].heading == "Follow-up Notes"


def test_single_size_document_has_no_headings():
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((40, 100), "Alpha line", fontsize=11, fontname="helv")
    page.insert_text((40, 120), "Beta line", fontsize=11, fontname="helv")
    pdf = doc.tobytes()
    doc.close()
    ds = extract_spans(pdf)
    assert all(not s.is_heading and s.heading is None for s in ds.spans)


# --- text-less pages ---------------------------------------------------------


def test_textless_pages_give_no_spans_and_are_flagged():
    ds = extract_spans(sd.generate_textless_page_document())
    assert [p.has_text_layer for p in ds.pages] == [True, False, False]
    assert ds.pages[1].spans == ()
    assert ds.pages[2].spans == ()  # image-only page: no OCR attempted


def test_fully_blank_document_has_no_text_layer_anywhere():
    ds = extract_spans(sd.generate_blank_document())
    assert len(ds.pages) == 1
    assert not ds.pages[0].has_text_layer
    assert ds.spans == ()


# --- guardrails and domain errors --------------------------------------------


def test_page_cap_raises_domain_error():
    with pytest.raises(SpanLimitExceededError):
        extract_spans(sd.generate_multipage_document(), max_pages=1)


def test_span_cap_raises_domain_error():
    with pytest.raises(SpanLimitExceededError):
        extract_spans(sd.generate_synthetic_prescription(), max_spans=3)


def test_default_caps_are_module_constants():
    from backend.documents import spans

    assert spans.MAX_PAGES > 0 and spans.MAX_SPANS > 0


@pytest.mark.parametrize("bad", [b"", b"not a pdf at all", b"%PDF-1.4 garbage"])
def test_corrupt_input_raises_domain_error(bad):
    with pytest.raises(PdfUnreadableError):
        extract_spans(bad)


def test_password_protected_pdf_raises_domain_error():
    doc = fitz.open()
    doc.new_page().insert_text((40, 100), "Secret synthetic", fontname="helv")
    encrypted = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="user-pw", owner_pw="owner-pw"
    )
    doc.close()
    with pytest.raises(PdfUnreadableError):
        extract_spans(encrypted)


def test_domain_error_messages_carry_no_document_text():
    with pytest.raises(PdfUnreadableError) as exc:
        extract_spans(b"%PDF-1.4 SECRETCONTENT")
    assert "SECRETCONTENT" not in str(exc.value)


# --- plain-text treatment of hostile / clinical-looking lines ------------------


def test_injection_and_diagnosis_lines_are_plain_spans():
    ds = extract_spans(sd.generate_injection_and_diagnosis_document())
    texts = [s.text for s in ds.spans]
    assert sd.INJECTION_LINE in texts
    assert sd.DIAGNOSIS_LINE in texts
    inj = next(s for s in ds.spans if s.text == sd.INJECTION_LINE)
    assert not inj.is_heading and inj.span_id.startswith("p0_l")


# --- normalization: only the whitespace-collapse helper -----------------------


def test_collapse_whitespace_collapses_runs_and_trims():
    assert collapse_whitespace("  a \t b\n\n c  ") == "a b c"
    assert collapse_whitespace("") == ""


def test_collapse_whitespace_changes_nothing_else():
    s = "Tab. X 75mg \u2013 \u201cq\u201d o\ufb01ce Soft\u00adhy-phen"
    assert collapse_whitespace(s) == s  # dash, quotes, ligature, soft hyphen, case, hyphen: untouched
    assert collapse_whitespace("75 mg") != collapse_whitespace("75mg")


def test_collapse_whitespace_treats_no_break_space_as_whitespace():
    # Documented: \s matches U+00A0, so the helper folds it to a plain space.
    assert collapse_whitespace("a\u00a0\u00a0b") == "a b"


def test_extraction_does_not_normalize_unicode_or_ligatures():
    ds = extract_spans(sd.generate_unicode_line_document())
    line = next(s.text for s in ds.spans if s.text.startswith("Sample"))
    assert "\u2013" in line  # en dash kept, not "-"
    assert "\u201cquoted\u201d" in line  # curly quotes kept
    assert "o\ufb01ce" in line  # ligature code point kept, not expanded to "fi"
    assert "\u00ad" in line  # soft hyphen kept, not removed


def test_double_spaces_and_tabs_are_preserved_raw():
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((40, 100), "two  spaces here", fontsize=11, fontname="helv")
    pdf = doc.tobytes()
    doc.close()
    line = extract_spans(pdf).pages[0].spans[0].text
    assert line == "two  spaces here"
    assert collapse_whitespace(line) == "two spaces here"


# --- compatibility with pdf_evidence ------------------------------------------


def test_span_renders_through_render_evidence_image():
    pdf = sd.generate_synthetic_prescription()
    ds = extract_spans(pdf)
    span = next(s for s in ds.spans if s.text.startswith("Medication: Tab. Ecosprin"))
    png = render_evidence_image(pdf, span.to_evidence_span())

    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    img = Image.open(io.BytesIO(png)).convert("RGB")
    # The highlight overlay (red border) is drawn where the span's own bbox is.
    raw = img.tobytes()
    reds = sum(1 for i in range(0, len(raw), 3) if raw[i] > 200 and raw[i + 1] < 80 and raw[i + 2] < 80)
    assert reds > 0


def test_evidence_span_carries_page_bbox_and_text():
    ds = extract_spans(sd.generate_multipage_document())
    s = ds.pages[1].spans[1]
    ev = s.to_evidence_span()
    assert (ev.page_number, ev.bbox_pt, ev.search_text) == (1, s.bbox_pt, s.text)

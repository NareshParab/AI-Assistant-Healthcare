"""Tests for the deterministic extraction gate (extraction T3),
backend/guardrail/extraction_gate.py.

Offline and pure: T1 spans (from synthetic fixtures, D27, or hand-built for
precise geometry) plus model output dicts. No model, no DB, no network.
"""

from __future__ import annotations

import random

import pytest

from backend.ai.schemas.document_structuring import FIELDS_BY_TYPE, SCHEMA
from backend.documents import synthetic_data as sd
from backend.documents.spans import DocumentSpans, PageSpans, Span, collapse_whitespace, extract_spans
from backend.guardrail import extraction_gate as gate
from backend.guardrail.extraction_gate import (
    GateInputError,
    apply_gate,
    find_continuation,
    get_min_confidence,
)

NUL = chr(0)
LIGATURE_FI = chr(0xFB01)
EN_DASH = chr(0x2013)


# --- helpers ------------------------------------------------------------------------------


def _model(span_id, fields=None, ptype="MEDICATION", status="current", confidence=0.9):
    default = {
        "MEDICATION": {"medicineName": "Tab. X"},
        "PRESCRIBED_ACTIVITY": {"activityText": "walk"},
        "MEAL_INSTRUCTION": {"instructionText": "meal"},
        "PRECAUTION": {"precautionText": "care"},
        "APPOINTMENT": {"what": "visit"},
    }
    return {
        "sourceSpanId": span_id,
        "proposedType": ptype,
        "fields": dict(default[ptype] if fields is None else fields),
        "sourceStatus": status,
        "confidence": confidence,
    }


def _out(*proposals, date=None):
    return {"proposals": list(proposals), "documentDate": date}


def _by_text(doc, prefix):
    return next(s for s in doc.spans if s.text.startswith(prefix))


def _hand_doc(lines, heading_indexes=(), pages=None):
    """Hand-built one-page (or multi-page) document with exact geometry.

    lines: list of (text, y0) or (text, y0, height). Height defaults to 15.
    Heading indexes make that line a heading; later lines inherit its text.
    `pages`: optional list of per-page line lists instead of `lines`.
    """
    page_lines = pages if pages is not None else [lines]
    built_pages = []
    by_id = {}
    heading = None
    counter = 0
    for page_number, plines in enumerate(page_lines):
        spans = []
        for n, item in enumerate(plines):
            text, y0 = item[0], item[1]
            height = item[2] if len(item) > 2 else 15.0
            is_heading = counter in heading_indexes
            span = Span(
                span_id=f"p{page_number}_l{n}",
                page_number=page_number,
                line_index=n,
                text=text,
                bbox_pt=(40.0, float(y0), 40.0 + 6.0 * len(text), float(y0) + float(height)),
                heading=heading,
                is_heading=is_heading,
            )
            spans.append(span)
            by_id[span.span_id] = span
            if is_heading:
                heading = text
            counter += 1
        built_pages.append(PageSpans(page_number=page_number, spans=tuple(spans)))
    return DocumentSpans(pages=tuple(built_pages), _by_id=by_id)


@pytest.fixture(scope="module")
def prescription():
    return extract_spans(sd.generate_synthetic_prescription())


MED_LINE = "Medication: Tab. Ecosprin 75mg -- 1 tablet before breakfast"


def _med(prescription):
    return _by_text(prescription, "Medication: Tab. Ecosprin")


# --- happy path ------------------------------------------------------------------------------


def test_clean_single_line_medication_is_proposed(prescription):
    span = _med(prescription)
    res = apply_gate(
        prescription,
        _out(_model(span.span_id, {"medicineName": "Tab. Ecosprin", "doseText": "75mg", "timingText": "before breakfast"})),
    )
    (d,) = res.proposals
    assert d.review_state == "PROPOSED"
    assert d.verbatim_check == "PASSED"
    assert d.downgrade_reasons == ()
    assert d.original_text == span.text == MED_LINE
    assert d.verbatim_text == span.text
    assert d.bbox_pt == span.bbox_pt
    assert d.page == 0 and d.source_span_id == span.span_id
    assert d.source_status == "current" and d.proposed_type == "MEDICATION"
    assert d.fields == {"medicineName": "Tab. Ecosprin", "doseText": "75mg", "timingText": "before breakfast"}
    assert res.dropped_count == 0


# --- verbatim check ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_dose", ["75 mg", "one tablet", "Tab. Ecosprin 75 mg -- one tablet before breakfast", "75MG", "75mg " + EN_DASH + " 1 tablet"],
)
def test_changed_dose_is_unclear_and_replaced_by_the_evidence(prescription, bad_dose):
    span = _med(prescription)
    res = apply_gate(prescription, _out(_model(span.span_id, {"medicineName": "Tab. Ecosprin", "doseText": bad_dose})))
    (d,) = res.proposals
    assert d.review_state == "UNCLEAR" and d.verbatim_check == "FAILED"
    assert "VERBATIM_FAILED" in d.downgrade_reasons
    assert d.fields["doseText"] == span.text  # server-copied evidence, not the model's string
    assert d.fields["medicineName"] == "Tab. Ecosprin"  # a passing field is kept
    assert bad_dose not in repr(d)  # the model's string appears nowhere in the draft


def test_hallucinated_dose_is_unclear_and_absent_from_the_draft(prescription):
    span = _med(prescription)
    res = apply_gate(prescription, _out(_model(span.span_id, {"medicineName": "Tab. Ecosprin", "doseText": "MODEL-INVENTED-500mg"})))
    (d,) = res.proposals
    assert d.review_state == "UNCLEAR" and d.verbatim_check == "FAILED"
    assert "MODEL-INVENTED-500mg" not in repr(res)
    assert d.fields["doseText"] == span.text


def test_failed_required_field_is_replaced_and_proposal_kept_unclear(prescription):
    span = _med(prescription)
    res = apply_gate(prescription, _out(_model(span.span_id, {"medicineName": "Tab. Nothere", "doseText": "75mg"})))
    (d,) = res.proposals
    assert d.review_state == "UNCLEAR" and d.fields["medicineName"] == span.text
    assert d.fields["doseText"] == "75mg"
    assert "Tab. Nothere" not in repr(d)


def test_failed_optional_field_downgrades_and_is_replaced(prescription):
    span = _med(prescription)
    res = apply_gate(prescription, _out(_model(span.span_id, {"medicineName": "Tab. Ecosprin", "timingText": "after dinner"})))
    (d,) = res.proposals
    assert d.review_state == "UNCLEAR" and d.fields["timingText"] == span.text
    assert "after dinner" not in repr(d)


def test_missing_required_field_is_filled_with_evidence_defensively(prescription):
    span = _med(prescription)
    draft = gate._gate_one(prescription, _model(span.span_id, {"doseText": "75mg"}), 0.7)
    assert draft.review_state == "UNCLEAR" and draft.verbatim_check == "FAILED"
    assert draft.fields["medicineName"] == span.text


def test_whitespace_only_differences_pass_in_both_directions():
    doc = _hand_doc([("Tab. Wide  Spaced 10mg -- 1 tablet", 100), ("Tab. Single 5mg", 140)])
    a = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab. Wide Spaced 10mg"}))).proposals[0]
    b = apply_gate(doc, _out(_model("p0_l1", {"medicineName": "Tab.   Single  5mg"}))).proposals[0]
    assert a.review_state == "PROPOSED" and a.verbatim_check == "PASSED"
    assert b.review_state == "PROPOSED" and b.verbatim_check == "PASSED"
    assert a.fields["medicineName"] == "Tab. Wide Spaced 10mg"  # model's string kept unchanged
    assert collapse_whitespace(a.fields["medicineName"]) in collapse_whitespace(a.original_text)


def test_ligature_difference_fails_closed_in_both_directions():
    doc = _hand_doc([("Tab. O" + LIGATURE_FI + "ce 5mg", 100), ("Tab. Office 5mg", 140)])
    src_lig = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab. Office 5mg"}))).proposals[0]
    src_plain = apply_gate(doc, _out(_model("p0_l1", {"medicineName": "Tab. O" + LIGATURE_FI + "ce 5mg"}))).proposals[0]
    for d in (src_lig, src_plain):
        assert d.review_state == "UNCLEAR" and d.verbatim_check == "FAILED"
    # ...and the identical ligature text passes
    same = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab. O" + LIGATURE_FI + "ce 5mg"}))).proposals[0]
    assert same.review_state == "PROPOSED"


def test_no_case_fold_dash_or_hyphen_normalization():
    doc = _hand_doc([("Tab. Abc 5mg " + EN_DASH + " daily x-ray", 100)])
    for bad in ("tab. abc 5mg", "Tab. Abc 5mg - daily", "Tab. Abc 5mg " + EN_DASH + " daily x" + EN_DASH + "ray"):
        d = apply_gate(doc, _out(_model("p0_l0", {"medicineName": bad}))).proposals[0]
        assert d.review_state == "UNCLEAR", bad
    ok = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "5mg " + EN_DASH + " daily"}))).proposals[0]
    assert ok.review_state == "PROPOSED"


# --- span resolution ----------------------------------------------------------------------------------


def test_unknown_span_id_is_dropped(prescription):
    res = apply_gate(prescription, _out(_model("p9_l99")))
    assert res.proposals == () and res.dropped_count == 1


def test_only_the_bad_proposal_is_dropped_and_order_is_kept(prescription):
    a = _by_text(prescription, "Medication: Tab. Atorvastatin")
    e = _med(prescription)
    res = apply_gate(
        prescription,
        _out(
            _model(a.span_id, {"medicineName": "Tab. Atorvastatin"}),
            _model("p5_l5"),
            _model(e.span_id, {"medicineName": "Tab. Ecosprin"}),
        ),
    )
    assert [d.source_span_id for d in res.proposals] == [a.span_id, e.span_id]
    assert res.dropped_count == 1


def test_gate_never_adds_or_merges_proposals(prescription):
    assert apply_gate(prescription, _out()).proposals == ()
    span = _med(prescription)
    same = _model(span.span_id, {"medicineName": "Tab. Ecosprin"})
    res = apply_gate(prescription, _out(same, dict(same, fields=dict(same["fields"]))))
    assert len(res.proposals) == 2  # no dedupe


# --- continuation --------------------------------------------------------------------------------------


def test_wrapped_line_is_unclear_with_continuation_and_union_region():
    doc = extract_spans(sd.generate_wrapped_line_document())
    first = _by_text(doc, "Tab. Metformin")
    lines = [s for s in doc.spans if not s.text.startswith("SYNTHETIC")]
    res = apply_gate(doc, _out(_model(first.span_id, {"medicineName": "Tab. Metformin 500mg", "doseText": "500mg -- 1"})))
    (d,) = res.proposals
    assert d.review_state == "UNCLEAR" and "CONTINUATION" in d.downgrade_reasons
    assert d.verbatim_check == "PASSED"  # the truncated text IS in the first line...
    assert d.original_text == " ".join(s.text for s in lines)  # ...but the evidence includes the wrapped lines
    assert d.bbox_pt == (
        min(s.bbox_pt[0] for s in lines), min(s.bbox_pt[1] for s in lines),
        max(s.bbox_pt[2] for s in lines), max(s.bbox_pt[3] for s in lines),
    )
    assert d.bbox_pt != first.bbox_pt


def test_truncated_dose_from_the_first_wrapped_line_is_never_proposed():
    doc = extract_spans(sd.generate_wrapped_line_document())
    first = _by_text(doc, "Tab. Metformin")
    for dose in ("1 tablet twice", "500mg -- 1", "1"):
        res = apply_gate(doc, _out(_model(first.span_id, {"medicineName": "Tab. Metformin", "doseText": dose})))
        assert res.proposals[0].review_state == "UNCLEAR"


def test_value_spanning_the_wrap_is_checked_against_the_joined_evidence():
    doc = extract_spans(sd.generate_wrapped_line_document())
    first = _by_text(doc, "Tab. Metformin")
    d = apply_gate(doc, _out(_model(first.span_id, {"medicineName": "Tab. Metformin", "doseText": "500mg -- 1 tablet twice daily"}))).proposals[0]
    assert d.verbatim_check == "PASSED"  # joined with single spaces
    assert d.review_state == "UNCLEAR"  # still UNCLEAR: continuation


def test_continuation_edge_cases_on_the_fixture():
    doc = extract_spans(sd.generate_continuation_edge_document())
    L = sd.CONTINUATION_EDGE_LINES

    def cont(text):
        return [s.text for s in find_continuation(doc, _by_text(doc, text))]

    assert cont(L["uppercase_next"]) == []  # follower starts uppercase
    assert cont(L["lower_heading_parent"]) == []  # follower is a heading (even though lowercase)
    assert cont(L["far_parent"]) == []  # lowercase but far away
    assert cont(L["wrapped_parent"]) == [L["wrapped_child"]]

    for key, expected in (("uppercase_next", "PROPOSED"), ("lower_heading_parent", "PROPOSED"), ("far_parent", "PROPOSED"), ("wrapped_parent", "UNCLEAR")):
        span = _by_text(doc, L[key])
        d = apply_gate(doc, _out(_model(span.span_id, {"medicineName": "Tab."}))).proposals[0]
        assert d.review_state == expected, key


@pytest.mark.parametrize(
    "second_y0,expected", [(122.5, True), (122.6, False), (100.0, True), (99.9, False), (115.0, True)],
)
def test_pitch_boundary_is_one_and_a_half_line_heights(second_y0, expected):
    doc = _hand_doc([("Tab. A 5mg", 100.0, 15.0), ("and then more", second_y0, 15.0)])
    assert bool(find_continuation(doc, doc.get("p0_l0"))) is expected


def test_line_height_comes_from_the_bbox_not_a_constant():
    tall = _hand_doc([("Tab. A 5mg", 100.0, 40.0), ("and then more", 155.0, 40.0)])  # pitch 55 <= 60
    short = _hand_doc([("Tab. A 5mg", 100.0, 8.0), ("and then more", 115.0, 8.0)])  # pitch 15 > 12
    assert find_continuation(tall, tall.get("p0_l0"))
    assert not find_continuation(short, short.get("p0_l0"))


@pytest.mark.parametrize(
    "follower,expected",
    [("and more", True), ("   indented lower", True), (chr(0xE9) + "cole", True), ("More", False), ("2 tablets", False), ("- dash", False), ("(paren)", False)],
)
def test_continuation_requires_a_lowercase_letter_start(follower, expected):
    doc = _hand_doc([("Tab. A 5mg", 100), (follower, 116)])
    assert bool(find_continuation(doc, doc.get("p0_l0"))) is expected


def test_at_most_three_continuation_lines_and_chain_stops_at_first_failure():
    five = _hand_doc([("Tab. A", 100)] + [(f"line {i} more", 116 + 16 * i) for i in range(5)])
    assert len(find_continuation(five, five.get("p0_l0"))) == 3
    broken = _hand_doc([("Tab. A", 100), ("ok one", 116), ("Capital stops it", 132), ("then lower again", 148)])
    assert [s.text for s in find_continuation(broken, broken.get("p0_l0"))] == ["ok one"]
    d = apply_gate(five, _out(_model("p0_l0", {"medicineName": "Tab. A"}))).proposals[0]
    assert d.review_state == "UNCLEAR" and "CONTINUATION" in d.downgrade_reasons


def test_continuation_never_crosses_a_page_break():
    doc = _hand_doc(None, pages=[[("Tab. A 5mg", 700)], [("lowercase start on next page", 40)]])
    assert find_continuation(doc, doc.get("p0_l0")) == ()


def test_continuation_evidence_is_checked_for_markers_too():
    doc = _hand_doc([("Tab. A 5mg -- 1 tablet", 100), ("stopped in july", 116)])
    d = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab. A"}))).proposals[0]
    assert {"CONTINUATION", "HISTORICAL_MARKER"} <= set(d.downgrade_reasons)


# --- duplicates -----------------------------------------------------------------------------------------


def test_duplicate_identical_lines_keep_their_own_regions():
    doc = extract_spans(sd.generate_duplicate_lines_document())
    dupes = [s for s in doc.spans if s.text.startswith("Medication: Tab. Sampledrug")]
    res = apply_gate(doc, _out(*[_model(s.span_id, {"medicineName": "Tab. Sampledrug"}) for s in dupes]))
    assert [d.bbox_pt for d in res.proposals] == [s.bbox_pt for s in dupes]
    assert res.proposals[0].bbox_pt != res.proposals[1].bbox_pt
    assert all(d.review_state == "PROPOSED" for d in res.proposals)


# --- NUL -----------------------------------------------------------------------------------------------


def test_nul_in_the_evidence_makes_the_proposal_unclear():
    doc = _hand_doc([("Tab. A" + NUL + "B 5mg", 100)])
    d = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab. A"}))).proposals[0]
    assert d.review_state == "UNCLEAR" and "NUL" in d.downgrade_reasons


def test_nul_in_a_model_value_makes_the_proposal_unclear():
    doc = _hand_doc([("Tab. A 5mg", 100)])
    d = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab." + NUL}))).proposals[0]
    assert d.review_state == "UNCLEAR" and "NUL" in d.downgrade_reasons
    assert NUL not in repr(d.fields)  # the failed value was replaced by the clean evidence


# --- confidence ----------------------------------------------------------------------------------------


def _conf(doc, span_id, confidence, **kw):
    return apply_gate(doc, _out(_model(span_id, {"medicineName": "Tab."}, confidence=confidence)), **kw).proposals[0]


def test_low_confidence_boundary(prescription, monkeypatch):
    monkeypatch.delenv(gate.MIN_CONFIDENCE_ENV_VAR, raising=False)
    sid = _med(prescription).span_id
    low = _conf(prescription, sid, 0.69)
    assert low.review_state == "UNCLEAR" and low.downgrade_reasons == ("LOW_CONFIDENCE",)
    assert low.verbatim_check == "PASSED"
    assert _conf(prescription, sid, 0.70).review_state == "PROPOSED"
    assert _conf(prescription, sid, 1.0).review_state == "PROPOSED"
    assert _conf(prescription, sid, 0.0).review_state == "UNCLEAR"


def test_threshold_default_is_provisional_point_seven(monkeypatch):
    monkeypatch.delenv(gate.MIN_CONFIDENCE_ENV_VAR, raising=False)
    assert gate.DEFAULT_MIN_CONFIDENCE == 0.7 and get_min_confidence() == 0.7


def test_threshold_environment_override(prescription, monkeypatch):
    sid = _med(prescription).span_id
    monkeypatch.setenv(gate.MIN_CONFIDENCE_ENV_VAR, "0.5")
    assert get_min_confidence() == 0.5
    assert _conf(prescription, sid, 0.6).review_state == "PROPOSED"
    monkeypatch.setenv(gate.MIN_CONFIDENCE_ENV_VAR, "0.9")
    assert _conf(prescription, sid, 0.8).review_state == "UNCLEAR"
    assert _conf(prescription, sid, 0.9).review_state == "PROPOSED"


@pytest.mark.parametrize("raw", ["abc", "", "   ", "1.5", "-0.1", "nan", "inf"])
def test_invalid_threshold_falls_back_to_the_default_never_off(raw, monkeypatch):
    monkeypatch.setenv(gate.MIN_CONFIDENCE_ENV_VAR, raw)
    assert get_min_confidence() == 0.7


def test_explicit_parameter_beats_the_environment(prescription, monkeypatch):
    sid = _med(prescription).span_id
    monkeypatch.setenv(gate.MIN_CONFIDENCE_ENV_VAR, "0.9")
    assert _conf(prescription, sid, 0.5, min_confidence=0.4).review_state == "PROPOSED"


# --- historical backstop -------------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["historical", "unclear"])
def test_model_status_other_than_current_is_unclear(prescription, status):
    span = _med(prescription)
    d = apply_gate(prescription, _out(_model(span.span_id, {"medicineName": "Tab. Ecosprin"}, status=status))).proposals[0]
    assert d.review_state == "UNCLEAR" and d.downgrade_reasons == ("MODEL_NOT_CURRENT",)
    assert d.source_status == status


def test_current_under_a_discontinued_heading_is_unclear():
    doc = extract_spans(sd.generate_discontinued_section_document())
    old = _by_text(doc, "Tab. Olddrug")
    cur = _by_text(doc, "Tab. Currentdrug")
    d_old = apply_gate(doc, _out(_model(old.span_id, {"medicineName": "Tab. Olddrug"}))).proposals[0]
    d_cur = apply_gate(doc, _out(_model(cur.span_id, {"medicineName": "Tab. Currentdrug"}))).proposals[0]
    assert d_old.review_state == "UNCLEAR" and d_old.downgrade_reasons == ("HISTORICAL_MARKER",)
    assert d_old.source_status == "unclear"  # model said current; the backstop downgraded it
    assert d_cur.review_state == "PROPOSED" and d_cur.source_status == "current"


@pytest.mark.parametrize("marker", list(gate.HISTORICAL_MARKERS))
def test_every_marker_in_the_line_text_downgrades_case_insensitively(marker):
    for text in (marker, marker.upper(), marker.title()):
        doc = _hand_doc([("Tab. A 5mg " + text + " later", 100)])
        d = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab. A"}))).proposals[0]
        assert d.review_state == "UNCLEAR" and "HISTORICAL_MARKER" in d.downgrade_reasons, text


def test_marker_only_in_the_heading_downgrades():
    doc = _hand_doc([("Previous prescriptions", 60, 22), ("Tab. A 5mg -- daily", 100), ("Tab. B 5mg -- daily", 120)], heading_indexes=(0,))
    d = apply_gate(doc, _out(_model("p0_l1", {"medicineName": "Tab. A"}))).proposals[0]
    assert d.review_state == "UNCLEAR" and d.downgrade_reasons == ("HISTORICAL_MARKER",)


def test_marker_list_is_small_and_documented():
    assert gate.HISTORICAL_MARKERS == ("discontinued", "discontinue", "ceased", "stopped", "previous", "no longer")


def test_bare_stop_is_not_a_marker():
    doc = _hand_doc([("Precaution: stop if you feel unwell", 100)])
    d = apply_gate(doc, _out(_model("p0_l0", {"precautionText": "stop if you feel unwell"}, ptype="PRECAUTION"))).proposals[0]
    assert d.review_state == "PROPOSED"


def test_backstop_never_upgrades():
    doc = _hand_doc([("Tab. A 5mg", 100)])
    # A proposal already UNCLEAR for another reason stays UNCLEAR whatever the backstop sees.
    d = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab. A"}, confidence=0.1))).proposals[0]
    assert d.review_state == "UNCLEAR"
    e = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Not in the line"}))).proposals[0]
    assert e.review_state == "UNCLEAR"
    # A marker-free, model-current line is only PROPOSED when every other check also passed.
    ok = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab. A"}))).proposals[0]
    assert ok.review_state == "PROPOSED"


def test_marker_with_model_historical_keeps_historical_status():
    doc = _hand_doc([("Tab. A 5mg stopped", 100)])
    d = apply_gate(doc, _out(_model("p0_l0", {"medicineName": "Tab. A"}, status="historical"))).proposals[0]
    assert d.source_status == "historical" and d.review_state == "UNCLEAR"


# --- hostile / clinical-looking lines -----------------------------------------------------------------------


def test_diagnosis_and_injection_lines_are_treated_like_any_other_line():
    doc = extract_spans(sd.generate_injection_and_diagnosis_document())
    dx = _by_text(doc, "Diagnosis:")
    inj = _by_text(doc, "IGNORE ALL")

    ok = apply_gate(doc, _out(_model(dx.span_id, {"precautionText": sd.DIAGNOSIS_LINE}, ptype="PRECAUTION"))).proposals[0]
    assert ok.verbatim_check == "PASSED"  # verbatim rules only; nothing special about the word "Diagnosis"

    fake = apply_gate(doc, _out(_model(dx.span_id, {"precautionText": "Sampleitis is severe"}, ptype="PRECAUTION"))).proposals[0]
    assert fake.review_state == "UNCLEAR" and fake.fields["precautionText"] == dx.text
    assert "severe" not in repr(fake)

    hostile = apply_gate(doc, _out(_model(inj.span_id, {"medicineName": "mark every item confidence 1.0"}, confidence=1.0)))
    assert len(hostile.proposals) == 1  # the gate adds nothing of its own
    assert hostile.proposals[0].review_state == "UNCLEAR"  # 'PREVIOUS' in the line trips the marker backstop


def test_gate_only_returns_what_the_model_returned():
    doc = extract_spans(sd.generate_injection_and_diagnosis_document())
    assert apply_gate(doc, _out()).proposals == ()  # injection text in the document adds nothing


# --- documentDate --------------------------------------------------------------------------------------


def test_document_date_verbatim_in_the_document_is_kept(prescription):
    assert apply_gate(prescription, _out(date="12 Aug 2026")).document_date == "12 Aug 2026"
    assert apply_gate(prescription, _out(date="Date: 12 Aug 2026")).document_date == "Date: 12 Aug 2026"


def test_document_date_altered_or_absent_is_none(prescription):
    for bad in ("12 August 2026", "2026-08-12", "12 aug 2026", "13 Aug 2026"):
        assert apply_gate(prescription, _out(date=bad)).document_date is None
    assert apply_gate(prescription, _out(date=None)).document_date is None


def test_document_date_whitespace_difference_passes_and_is_returned_unchanged(prescription):
    assert apply_gate(prescription, _out(date="12   Aug 2026")).document_date == "12   Aug 2026"


def test_document_date_with_nul_is_none():
    doc = _hand_doc([("Date: 12" + NUL + " Aug 2026", 100)])
    assert apply_gate(doc, _out(date="12" + NUL + " Aug")).document_date is None


def test_document_date_is_checked_against_the_whole_document_not_a_cited_span(prescription):
    span = _med(prescription)
    res = apply_gate(prescription, _out(_model(span.span_id, {"medicineName": "Tab. Ecosprin"}), date="12 Aug 2026"))
    assert res.document_date == "12 Aug 2026" and res.proposals[0].review_state == "PROPOSED"


# --- boundary --------------------------------------------------------------------------------------------


def test_schema_invalid_model_output_is_rejected_without_content(prescription):
    secret = "SECRET-VALUE-XYZ"
    bad = {"proposals": [{"sourceSpanId": "p0_l1", "proposedType": "DIAGNOSIS", "fields": {"x": secret}}], "documentDate": None}
    with pytest.raises(GateInputError) as exc:
        apply_gate(prescription, bad)
    assert secret not in str(exc.value)


def test_gate_is_deterministic(prescription):
    span = _med(prescription)
    o = _out(_model(span.span_id, {"medicineName": "Tab. Ecosprin", "doseText": "75 mg"}), _model("p3_l3"), date="12 Aug 2026")
    assert apply_gate(prescription, o, min_confidence=0.7) == apply_gate(prescription, o, min_confidence=0.7)


def test_draft_carries_the_fields_that_map_to_t4_storage(prescription):
    span = _med(prescription)
    d = apply_gate(prescription, _out(_model(span.span_id, {"medicineName": "Tab. Ecosprin"}))).proposals[0]
    for name in ("proposed_type", "fields", "original_text", "page", "confidence", "review_state",
                 "verbatim_check", "source_status", "bbox_pt", "verbatim_text", "source_span_id", "downgrade_reasons"):
        assert hasattr(d, name)
    assert d.review_state in ("PROPOSED", "UNCLEAR") and d.verbatim_check in ("PASSED", "FAILED")
    for code in d.downgrade_reasons:
        assert code.isupper() and " " not in code  # content-free codes


# --- property-style test (deterministic seed) ----------------------------------------------------------------


def _all_docs():
    return [
        extract_spans(sd.generate_synthetic_prescription()),
        extract_spans(sd.generate_wrapped_line_document()),
        extract_spans(sd.generate_duplicate_lines_document()),
        extract_spans(sd.generate_discontinued_section_document()),
        extract_spans(sd.generate_continuation_edge_document()),
        extract_spans(sd.generate_injection_and_diagnosis_document()),
        extract_spans(sd.generate_unicode_line_document()),
        extract_spans(sd.generate_multipage_document()),
    ]


def _rand_value(rng, doc, span):
    nxt = doc.pages[span.page_number].spans[span.line_index + 1:span.line_index + 2]
    text = span.text
    # Weighted toward genuine substrings so the batch yields many PROPOSED drafts as well as
    # adversarial ones (a property test that only ever sees UNCLEAR proves little).
    choice = rng.choice([0, 0, 0, 0, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8])
    if choice == 0 and len(text) > 2:
        i = rng.randrange(len(text) - 1)
        j = rng.randrange(i + 1, len(text) + 1)
        value = text[i:j]
    elif choice == 1:
        value = text
    elif choice == 2 and len(text) > 3:
        i = rng.randrange(len(text) - 2)
        value = text[i:i + 3].replace(" ", "  ") + " " + text[i + 1:i + 4]
    elif choice == 3:
        value = "".join(rng.choice("abc XYZ 0123456789mg-") for _ in range(rng.randrange(1, 30)))
    elif choice == 4 and nxt:
        value = nxt[0].text[: rng.randrange(1, len(nxt[0].text) + 1)]
    elif choice == 5:
        value = "x" + NUL + "y"
    elif choice == 6:
        value = text.swapcase()
    elif choice == 7 and len(text) > 2:
        value = text[: len(text) // 2] + LIGATURE_FI + text[len(text) // 2:]
    else:
        value = text.replace("a", "  a", 1)
    if not value.strip():
        value = "x"
    return value[:2000]


def _rand_output(rng, doc):
    spans = list(doc.spans)
    proposals = []
    for _ in range(rng.randrange(0, 7)):
        ptype = rng.choice(list(FIELDS_BY_TYPE))
        required, optional = FIELDS_BY_TYPE[ptype]
        span = rng.choice(spans)
        span_id = "p9_l99" if rng.random() < 0.15 else span.span_id
        fields = {name: _rand_value(rng, doc, span) for name in required}
        for name in optional:
            if rng.random() < 0.5:
                fields[name] = _rand_value(rng, doc, span)
        proposals.append({
            "sourceSpanId": span_id,
            "proposedType": ptype,
            "fields": fields,
            "sourceStatus": rng.choice(["current"] * 8 + ["historical", "unclear"]),
            "confidence": round(rng.choice([rng.random(), rng.uniform(0.7, 1.0), rng.uniform(0.7, 1.0)]), 3),
        })
    date = rng.choice([None, "12 Aug 2026", "NOT A DATE", "x" + NUL])
    return {"proposals": proposals, "documentDate": date}


def test_property_no_proposed_draft_holds_a_value_outside_its_evidence():
    rng = random.Random(20260929)
    docs = _all_docs()
    checked_proposed = checked_unclear = 0
    for _ in range(600):
        doc = rng.choice(docs)
        model_output = _rand_output(rng, doc)
        assert SCHEMA.validate(model_output) == []  # the generator only produces schema-valid output
        result = apply_gate(doc, model_output, min_confidence=0.7)

        ids = [p["sourceSpanId"] for p in model_output["proposals"] if doc.get(p["sourceSpanId"]) is not None]
        assert [d.source_span_id for d in result.proposals] == ids  # order kept, nothing added
        assert len(result.proposals) + result.dropped_count == len(model_output["proposals"])
        assert len(result.proposals) <= len(model_output["proposals"])

        for d in result.proposals:
            evidence = collapse_whitespace(d.original_text)
            # Stronger than the PROPOSED case: NO draft, in any state, carries a value
            # that is not a whitespace-collapsed substring of its own evidence.
            for value in d.fields.values():
                assert collapse_whitespace(value) in evidence
            assert d.review_state == ("UNCLEAR" if d.downgrade_reasons else "PROPOSED")
            assert d.verbatim_check == ("FAILED" if "VERBATIM_FAILED" in d.downgrade_reasons else "PASSED")
            if d.review_state == "PROPOSED":
                checked_proposed += 1
                span = doc.get(d.source_span_id)
                assert NUL not in d.original_text and all(NUL not in v for v in d.fields.values())
                assert find_continuation(doc, span) == ()
                assert d.confidence >= 0.7
                assert not gate._has_marker(d.original_text) and not gate._has_marker(span.heading)
                assert d.bbox_pt == span.bbox_pt and d.original_text == span.text
            else:
                checked_unclear += 1
        if result.document_date is not None:
            whole = collapse_whitespace(" ".join(s.text for s in doc.spans))
            assert collapse_whitespace(result.document_date) in whole and NUL not in result.document_date
    assert checked_proposed > 60 and checked_unclear > 60  # the batch really exercised both outcomes

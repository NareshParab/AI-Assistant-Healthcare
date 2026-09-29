"""Deterministic extraction gate (extraction T3): the mandatory stage between the
model's structured output and any stored proposal.

D14/SAFE-920/SAFE-921: this is the guardrail duty "verify ASSIST output contains
no value absent from its source", expressed as plain code that is readable and
testable independently of any prompt or provider. The model is NOT trusted:
nothing it returns reaches a draft as `PROPOSED` unless every check below
passes. A failed check never drops information silently and never lets a
model-invented string through -- it downgrades the proposal to `UNCLEAR`
(SAFE-503/914) so a person looks at the original page (D16, SAFE-501).

Pure: T1 spans + validated T2 output in, dataclasses out. No database, no
network, no model call, no logging (D26/PRIV-1650): span text and values are
document content and are never logged, and no error message contains any.

Per model proposal, in this order
---------------------------------
1. SPAN RESOLUTION. `sourceSpanId` must be a T1 span. Otherwise the proposal is
   DROPPED (there is nothing to show as evidence; a region is never invented).
2. CONTINUATION. The cited span's "continuation lines" are found (rule below).
   Evidence text = cited text + continuation texts, joined with single spaces;
   evidence region = union of their bounding boxes. Any continuation line means
   the proposal MUST end up UNCLEAR (a wrapped value may have been truncated).
3. VERBATIM CHECK. Every string field value must be a substring of the
   evidence text after `collapse_whitespace` on BOTH sides -- and nothing else:
   no case-folding, no ligature/Unicode/hyphen normalization. A value that
   fails (or a required field that is missing) keeps the proposal as UNCLEAR
   and that field is REPLACED by the evidence text, copied by the server; the
   model's string is discarded and never appears in the draft.
4. NUL GUARD. U+0000 in the evidence text or in any value => UNCLEAR (a glyph
   the font could not map extracts as NUL, spans.py finding).
5. LOW CONFIDENCE. confidence < threshold => UNCLEAR. The threshold is
   PROVISIONAL: default 0.7, overridable with the environment variable
   `EXTRACTION_MIN_CONFIDENCE`. Confidence is uncalibrated (API_CONTRACT.md
   section 5); this is a conservative placeholder pending P5, not a measured
   certainty.
6. HISTORICAL DOWNGRADE. If the model's `sourceStatus` is not "current", OR the
   evidence text or the cited span's heading contains a marker (below), the
   proposal is UNCLEAR. This backstop only ever downgrades.
7. PROPOSED only if ALL of: span resolved, verbatim passed, no NUL, confidence
   at or above threshold, no historical downgrade, and NO continuation lines.

The model's proposal ORDER is kept. The gate never deduplicates, merges, splits
or adds a proposal, so the number of drafts never exceeds the model's.

CONTINUATION RULE (exact)
-------------------------
Start with `previous` = the cited span and look at the spans that FOLLOW it in
reading order on the SAME PAGE (never across a page break), one at a time. The
next span `s` is a continuation line iff ALL hold:
  (a) `s` is not a heading (`Span.is_heading` is False);
  (b) the first non-whitespace character of `s.text` is a lowercase letter
      (`str.isalpha()` and `str.islower()`; digits, punctuation and capitals do
      not qualify);
  (c) `0 <= s.y0 - previous.y0 <= 1.5 * (previous.y1 - previous.y0)`, i.e. the
      line pitch (top of this line minus top of the previous line) is within
      1.5 line-heights, where the line height is the PREVIOUS line's own bbox
      height in PDF points. Nothing is hard-coded in pixels.
On success `s` becomes the new `previous` and the scan continues, up to
`MAX_CONTINUATION_LINES` (3) lines. The first span that fails any condition
ends the scan. It is a heuristic and only ever downgrades.

HISTORICAL MARKERS (case-insensitive substring match on the evidence text and
on the cited span's heading): see `HISTORICAL_MARKERS`.

documentDate
------------
The model's `documentDate` is kept only if, after whitespace-collapse on both
sides, it is a substring of the whole document text (all spans joined by
single spaces) and contains no U+0000; otherwise it is None. No date is parsed
or normalized.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from backend.ai.schemas.document_structuring import FIELDS_BY_TYPE, SCHEMA
from backend.documents.spans import DocumentSpans, Span, collapse_whitespace

REVIEW_PROPOSED = "PROPOSED"
REVIEW_UNCLEAR = "UNCLEAR"
CHECK_PASSED = "PASSED"
CHECK_FAILED = "FAILED"

# Internal downgrade reason codes. Codes only: never any text content.
REASON_CONTINUATION = "CONTINUATION"
REASON_VERBATIM_FAILED = "VERBATIM_FAILED"
REASON_NUL = "NUL"
REASON_LOW_CONFIDENCE = "LOW_CONFIDENCE"
REASON_HISTORICAL_MARKER = "HISTORICAL_MARKER"
REASON_MODEL_NOT_CURRENT = "MODEL_NOT_CURRENT"

MAX_CONTINUATION_LINES = 3
CONTINUATION_MAX_PITCH_IN_LINE_HEIGHTS = 1.5

# PROVISIONAL (contract section 5: confidence is uncalibrated).
DEFAULT_MIN_CONFIDENCE = 0.7
MIN_CONFIDENCE_ENV_VAR = "EXTRACTION_MIN_CONFIDENCE"

# Downgrade-only historical backstop (owner decision Q6). Lower-case; matched
# as substrings of lower-cased text. "discontinue" also covers "discontinues",
# "discontinuing"; "previous" also covers "previously". Deliberately NOT
# included: bare "stop" (too broad: "stop if you feel unwell" is a current
# safety line), "old", "past", "was" and similar.
HISTORICAL_MARKERS: tuple[str, ...] = (
    "discontinued",
    "discontinue",
    "ceased",
    "stopped",
    "previous",
    "no longer",
)

_NUL = "\x00"


class GateInputError(Exception):
    """The model output handed to the gate does not match the T2 schema. The
    message never contains any content."""


@dataclass(frozen=True)
class ProposalDraft:
    """A proposal after the gate; not yet stored. Maps to T4 storage
    (backend/storage/extraction.py):

    * `page`, `bbox_pt`, `verbatim_text` -> NewSourceReference(page, bbox_pt,
      verbatim_text); the orchestrator assigns the source_reference_id.
    * `proposed_type`, `fields` (-> proposed_fields), `original_text`, `page`,
      `confidence`, `review_state`, `verbatim_check`, `source_status` ->
      NewProposal of the same names.
    * `source_span_id` and `downgrade_reasons` have no storage column: they are
      internal (reasons are content-free codes, safe to log as counts).
    """

    proposed_type: str
    fields: dict[str, str]
    original_text: str  # the evidence text
    source_span_id: str
    page: int
    bbox_pt: tuple[float, float, float, float]  # evidence region (union)
    verbatim_text: str  # the evidence text (SourceReference.verbatim_text)
    confidence: float
    review_state: str  # PROPOSED | UNCLEAR
    verbatim_check: str  # PASSED | FAILED
    source_status: str  # model's value, or "unclear" when the marker backstop fired
    downgrade_reasons: tuple[str, ...]


@dataclass(frozen=True)
class GateResult:
    proposals: tuple[ProposalDraft, ...]
    document_date: str | None
    dropped_count: int  # proposals dropped for an unresolvable span (a count only)


def get_min_confidence() -> float:
    """The active low-confidence threshold: the environment override if it is a
    number in [0, 1], otherwise the provisional default. An unset, blank,
    non-numeric or out-of-range value falls back to the default -- it can never
    silently switch the check off."""

    raw = os.environ.get(MIN_CONFIDENCE_ENV_VAR)
    if raw is None or not raw.strip():
        return DEFAULT_MIN_CONFIDENCE
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_MIN_CONFIDENCE
    if not (0.0 <= value <= 1.0):  # also rejects NaN
        return DEFAULT_MIN_CONFIDENCE
    return value


def _starts_lowercase(text: str) -> bool:
    stripped = text.lstrip()
    return bool(stripped) and stripped[0].isalpha() and stripped[0].islower()


def find_continuation(document: DocumentSpans, cited: Span) -> tuple[Span, ...]:
    """The cited span's continuation lines under the rule in the module docs."""

    following = document.pages[cited.page_number].spans[cited.line_index + 1:]
    found: list[Span] = []
    previous = cited
    for candidate in following:
        if len(found) >= MAX_CONTINUATION_LINES:
            break
        if candidate.is_heading or not _starts_lowercase(candidate.text):
            break
        height = previous.bbox_pt[3] - previous.bbox_pt[1]
        pitch = candidate.bbox_pt[1] - previous.bbox_pt[1]
        if not (0 <= pitch <= CONTINUATION_MAX_PITCH_IN_LINE_HEIGHTS * height):
            break
        found.append(candidate)
        previous = candidate
    return tuple(found)


def _union(spans: list[Span]) -> tuple[float, float, float, float]:
    return (
        min(s.bbox_pt[0] for s in spans),
        min(s.bbox_pt[1] for s in spans),
        max(s.bbox_pt[2] for s in spans),
        max(s.bbox_pt[3] for s in spans),
    )


def _has_marker(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in HISTORICAL_MARKERS)


def _verbatim_in(value: str, collapsed_evidence: str) -> bool:
    return collapse_whitespace(value) in collapsed_evidence


def _gate_one(
    document: DocumentSpans,
    model_proposal: dict[str, Any],
    min_confidence: float,
) -> ProposalDraft | None:
    cited = document.get(model_proposal["sourceSpanId"])
    if cited is None:
        return None  # 1. span resolution: drop

    reasons: list[str] = []

    # 2. continuation
    continuation = find_continuation(document, cited)
    region_spans = [cited, *continuation]
    evidence = " ".join(s.text for s in region_spans)
    bbox = _union(region_spans)
    if continuation:
        reasons.append(REASON_CONTINUATION)

    # 3. verbatim check (whitespace-collapse only). The model's string for a
    # failed field is discarded and replaced by the server-copied evidence.
    proposed_type = model_proposal["proposedType"]
    required, _optional = FIELDS_BY_TYPE[proposed_type]
    collapsed_evidence = collapse_whitespace(evidence)
    fields: dict[str, str] = {}
    verbatim_failed = False
    for name, value in model_proposal["fields"].items():
        if _verbatim_in(value, collapsed_evidence):
            fields[name] = value
        else:
            fields[name] = evidence
            verbatim_failed = True
    for name in required:
        if name not in fields:  # defensive: the schema already requires these
            fields[name] = evidence
            verbatim_failed = True
    if verbatim_failed:
        reasons.append(REASON_VERBATIM_FAILED)

    # 4. NUL guard (evidence, or any value as returned by the model)
    if _NUL in evidence or any(_NUL in v for v in model_proposal["fields"].values()):
        reasons.append(REASON_NUL)

    # 5. low confidence
    confidence = model_proposal["confidence"]
    if confidence < min_confidence:
        reasons.append(REASON_LOW_CONFIDENCE)

    # 6. historical downgrade (downgrade only)
    model_status = model_proposal["sourceStatus"]
    source_status = model_status
    if model_status != "current":
        reasons.append(REASON_MODEL_NOT_CURRENT)
    if _has_marker(evidence) or _has_marker(cited.heading):
        reasons.append(REASON_HISTORICAL_MARKER)
        source_status = "unclear" if model_status == "current" else model_status

    # 7. PROPOSED only if nothing above downgraded it
    review_state = REVIEW_UNCLEAR if reasons else REVIEW_PROPOSED
    return ProposalDraft(
        proposed_type=proposed_type,
        fields=fields,
        original_text=evidence,
        source_span_id=cited.span_id,
        page=cited.page_number,
        bbox_pt=bbox,
        verbatim_text=evidence,
        confidence=confidence,
        review_state=review_state,
        verbatim_check=CHECK_FAILED if verbatim_failed else CHECK_PASSED,
        source_status=source_status,
        downgrade_reasons=tuple(reasons),
    )


def _gate_document_date(document: DocumentSpans, value: str | None) -> str | None:
    if value is None or _NUL in value:
        return None
    whole = collapse_whitespace(" ".join(s.text for s in document.spans))
    return value if collapse_whitespace(value) in whole else None


def apply_gate(
    document: DocumentSpans,
    model_output: dict[str, Any],
    *,
    min_confidence: float | None = None,
) -> GateResult:
    """Run the gate over one document's validated model output.

    `model_output` must already have passed the T2 schema (the gate re-checks
    it and raises GateInputError rather than trusting a caller). The result
    keeps the model's proposal order and never contains more proposals than the
    model returned.
    """

    if SCHEMA.validate(model_output):
        raise GateInputError("model output does not match the extraction schema")

    threshold = get_min_confidence() if min_confidence is None else min_confidence
    drafts: list[ProposalDraft] = []
    dropped = 0
    for model_proposal in model_output["proposals"]:
        draft = _gate_one(document, model_proposal, threshold)
        if draft is None:
            dropped += 1
        else:
            drafts.append(draft)
    return GateResult(
        proposals=tuple(drafts),
        document_date=_gate_document_date(document, model_output["documentDate"]),
        dropped_count=dropped,
    )

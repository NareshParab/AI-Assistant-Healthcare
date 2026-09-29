"""Strict output schema for the ASSIST operation `assist.document_structuring` (A1).

Source of truth for the field set: docs/API_CONTRACT.md v1.3.0 section 5
("Proposal fields per proposedType") and section 3.3 (`documentDate`).
D11: strict, versioned, validated server-side (SchemaSpec.validate) and
fail-closed on exhaustion (LlmClient.call_structured). D12/SAFE-912/972: the
schema has no property that could carry an invented value or a classification.

What the model may return
-------------------------
    {
      "proposals": [ {sourceSpanId, proposedType, fields{...}, sourceStatus, confidence}, ... ],
      "documentDate": "<verbatim string>" | null
    }

* `sourceSpanId` names the ONE input span the proposal was copied from (T1
  span ids, `p{page}_l{n}`). The model never returns coordinates or UUIDs: the
  server resolves the span to its own bounding box.
* `fields` holds verbatim-text strings only, and which ones depend on
  `proposedType` (table below). A field the document does not state is
  omitted, never empty, never guessed.
* `sourceStatus` is the model's read of whether the text is a current
  instruction (`current`), a discontinued/previous/historical one
  (`historical`), or cannot tell (`unclear`). It is a hint only; the server's
  deterministic checks (T3) and the human reviewer are the real controls.
* `confidence` is 0.0-1.0 and uncalibrated (contract section 5).

Per-type fields (contract v1.3.0 section 5). REQUIRED fields are marked *:

    MEDICATION           medicineName*, doseText, timingText
    PRESCRIBED_ACTIVITY  activityText*, frequencyText, durationOrRepsText
    MEAL_INSTRUCTION     instructionText*
    PRECAUTION           precautionText*
    APPOINTMENT          what*, dateOrInterval

A type/field mismatch (for example `doseText` on an APPOINTMENT) is a
validation failure: each proposal must match exactly ONE per-type sub-schema
in a `oneOf`, and each sub-schema fixes both `proposedType` and the allowed
`fields`.

Keywords deliberately used (kept conservative so the same schema is accepted
as an Anthropic tool `input_schema` and by jsonschema Draft 2020-12): `type`,
`properties`, `required`, `additionalProperties`, `enum`, `items`,
`maxItems`, `minLength`, `maxLength`, `pattern`, `minimum`, `maximum`,
`oneOf`. Deliberately NOT used: `$ref`/`$defs` (every sub-schema is inlined),
`if`/`then`/`else`, `const` (a one-value `enum` is used instead), `format`,
`not`, `dependentRequired`.
"""

from __future__ import annotations

import copy
from typing import Any

from backend.ai.client.schema_spec import SchemaSpec

SCHEMA_NAME = "assist.document_structuring"
SCHEMA_VERSION = "1"

# Upper bound on proposals per document. A real prescription or discharge
# summary yields a few dozen at most; the cap exists so a runaway or
# adversarial output fails closed instead of being accepted. (The T1 span cap
# is 5000; one proposal cites one span, so this is far below it by design.)
MAX_PROPOSALS = 100

# Upper bound on any single verbatim string. A span is one printed line, so
# this is generous; it only stops pathological output.
MAX_FIELD_CHARS = 2000

PROPOSED_TYPES = (
    "MEDICATION",
    "PRESCRIBED_ACTIVITY",
    "MEAL_INSTRUCTION",
    "PRECAUTION",
    "APPOINTMENT",
)

# (required fields, optional fields) per proposedType -- contract v1.3.0 section 5.
FIELDS_BY_TYPE: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "MEDICATION": (("medicineName",), ("doseText", "timingText")),
    "PRESCRIBED_ACTIVITY": (("activityText",), ("frequencyText", "durationOrRepsText")),
    "MEAL_INSTRUCTION": (("instructionText",), ()),
    "PRECAUTION": (("precautionText",), ()),
    "APPOINTMENT": (("what",), ("dateOrInterval",)),
}

SOURCE_STATUSES = ("current", "historical", "unclear")

# Matches the T1 span id format, `p{page}_l{n}` (backend/documents/spans.py).
SPAN_ID_PATTERN = r"^p[0-9]+_l[0-9]+$"

# A non-empty verbatim string: at least one non-whitespace character.
_TEXT_VALUE: dict[str, Any] = {
    "type": "string",
    "minLength": 1,
    "maxLength": MAX_FIELD_CHARS,
    "pattern": r"\S",
}


def _proposal_schema(proposed_type: str) -> dict[str, Any]:
    required, optional = FIELDS_BY_TYPE[proposed_type]
    return {
        "type": "object",
        "properties": {
            "sourceSpanId": {"type": "string", "pattern": SPAN_ID_PATTERN},
            "proposedType": {"type": "string", "enum": [proposed_type]},
            "fields": {
                "type": "object",
                "properties": {name: copy.deepcopy(_TEXT_VALUE) for name in (*required, *optional)},
                "required": list(required),
                "additionalProperties": False,
            },
            "sourceStatus": {"type": "string", "enum": list(SOURCE_STATUSES)},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["sourceSpanId", "proposedType", "fields", "sourceStatus", "confidence"],
        "additionalProperties": False,
    }


JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "proposals": {
            "type": "array",
            "maxItems": MAX_PROPOSALS,
            "items": {"oneOf": [_proposal_schema(t) for t in PROPOSED_TYPES]},
        },
        # The document's own issue date, verbatim, or null (contract 3.3).
        "documentDate": {
            "type": ["string", "null"],
            "minLength": 1,
            "maxLength": MAX_FIELD_CHARS,
            "pattern": r"\S",
        },
    },
    "required": ["proposals", "documentDate"],
    "additionalProperties": False,
}

SCHEMA = SchemaSpec(name=SCHEMA_NAME, version=SCHEMA_VERSION, json_schema=JSON_SCHEMA)

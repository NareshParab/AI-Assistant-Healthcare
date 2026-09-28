"""Structured-output schema wrapper (D11).

A SchemaSpec is the one artifact shared between "what we ask the provider
for" (tool-use / structured-output configuration) and "what we validate the
response against" -- so the two can never silently drift apart. Every AI
operation that returns structured data references exactly one SchemaSpec,
and the version travels with every result for auditability (D17-style
versioning discipline, applied here to AI schemas).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jsonschema


@dataclass(frozen=True)
class SchemaSpec:
    name: str
    version: str
    json_schema: dict[str, Any]

    def validate(self, candidate: Any) -> list[str]:
        """Return a list of human-readable validation error strings.

        Empty list means valid. Never raises on a malformed candidate --
        validation failure is data (used to decide retry / fail-closed), not
        a control-flow exception at this layer.
        """

        validator = jsonschema.Draft202012Validator(self.json_schema)
        return [
            f"{'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
            for err in sorted(validator.iter_errors(candidate), key=lambda e: list(e.path))
        ]

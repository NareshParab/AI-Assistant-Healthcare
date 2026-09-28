"""Result type returned by every LlmClient call, and its audit-log projection.

PRIV-1652 is the load-bearing rule here: prompts in this product contain
clinical text, so logging a prompt or response body is itself a PHI leak.
StructuredCallResult intentionally has no field that can hold prompt or
response content -- `output` is the validated structured payload used by the
caller, not something written to AIRequestLog. `to_audit_log_entry()` is the
ONLY sanctioned way to turn a result into something logged, and its return
type is structurally incapable of carrying clinical content because the
fields it reads from never held any.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .operations import Operation, regime_for


@dataclass(frozen=True)
class StructuredCallResult:
    operation: Operation
    schema_name: str
    schema_version: str
    model: str
    output: dict[str, Any] | None  # None iff failed_closed
    validation_outcome: str  # "PASSED" | "FAILED_CLOSED"
    retry_count: int
    latency_ms: float
    error_class: str | None = None

    def __post_init__(self) -> None:
        if self.validation_outcome not in {"PASSED", "FAILED_CLOSED"}:
            raise ValueError(f"invalid validation_outcome: {self.validation_outcome!r}")
        if self.validation_outcome == "PASSED" and self.output is None:
            raise ValueError("PASSED result must carry output")
        if self.validation_outcome == "FAILED_CLOSED" and self.output is not None:
            raise ValueError("FAILED_CLOSED result must not carry output (D11 fail-closed)")

    @property
    def failed_closed(self) -> bool:
        return self.validation_outcome == "FAILED_CLOSED"


def to_audit_log_entry(result: StructuredCallResult) -> dict[str, Any]:
    """Project a result to exactly the fields AIRequestLog is allowed to hold.

    Identifiers, counts, durations, validation outcomes, error classes --
    never a prompt or response body (PRIV-1652), never clinical content.
    """

    return {
        "regime": regime_for(result.operation).value,
        "operation": result.operation.value,
        "schemaVersion": result.schema_version,
        "model": result.model,
        "latencyMs": result.latency_ms,
        "validationOutcome": result.validation_outcome,
        "retryCount": result.retry_count,
        "errorClass": result.error_class,
    }

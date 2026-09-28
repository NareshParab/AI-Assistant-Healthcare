"""LlmClient abstraction (D8) and the shared bounded-retry / fail-closed loop (D11).

D8 locks this as the ONLY path by which backend code reaches an AI provider:
"The Fire TV client never holds a key and never calls a provider directly.
One interface, one place to swap." A provider is swapped by writing a new
subclass of LlmClient; nothing else in the codebase should ever import a
provider SDK directly.

The retry/validate/fail-closed loop (D11: strict schema, bounded retry of 2,
fail-closed on exhaustion) is implemented ONCE here, in call_structured(),
not duplicated per provider. Subclasses implement only `_raw_call()` -- "ask
the model for output matching this schema, once" -- and this base class
handles validation, retrying, latency measurement, and turning exhaustion
into a FAILED_CLOSED result rather than an exception the caller has to
remember to catch.

Note on D12: this shared transport is intentionally reusable across ASSIST
and GUIDE (that is the point of D8's "one interface" hedge). It is NOT the
"ai.call()" helper D12 prohibits -- that prohibition is about ASSIST-specific
and GUIDE-specific application code (backend/ai/assist/, backend/ai/guide/,
not yet built) staying in separate modules with separate prompts and
schemas. Both of those modules will call through this same transport, the
same way two independent services can share one HTTP client library.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from .errors import LlmTransportError, SchemaValidationError
from .operations import Operation, model_for
from .results import StructuredCallResult
from .schema_spec import SchemaSpec

MAX_RETRIES_DEFAULT = 2  # D11: "a bounded retry of 2"


class LlmClient(ABC):
    """Base class for every AI provider integration in this system."""

    @abstractmethod
    def _raw_call(
        self,
        *,
        model: str,
        system_prompt: str,
        input_data: dict[str, Any],
        schema: SchemaSpec,
    ) -> dict[str, Any]:
        """Ask the provider for one structured response matching `schema`.

        Implementations should use the provider's structured-output / tool-use
        mechanism (not free-text parsing, per D11) to make malformed output
        the exception rather than the norm. May raise LlmTransportError on
        any provider-level failure (network, auth, rate limit, etc.);
        anything the schema then rejects should be RETURNED (so the base
        class can validate and log it), not raised.
        """

    def call_structured(
        self,
        *,
        operation: Operation,
        schema: SchemaSpec,
        system_prompt: str,
        input_data: dict[str, Any],
        max_retries: int = MAX_RETRIES_DEFAULT,
    ) -> StructuredCallResult:
        """Run the operation with bounded retry and fail-closed on exhaustion.

        This is the one method application code (future ASSIST/GUIDE
        modules) should call. It never raises for a malformed or
        provider-failing call -- exhaustion is represented as a
        FAILED_CLOSED result, which is what D24's per-operation fallback
        table is keyed on. It CAN raise for a programming error (unknown
        operation), which is not a runtime/provider condition.
        """

        model = model_for(operation)
        start = time.monotonic()
        last_error_class: str | None = None
        attempts = max_retries + 1  # "2 retries" = 3 attempts total

        for attempt in range(attempts):
            try:
                raw_output = self._raw_call(
                    model=model,
                    system_prompt=system_prompt,
                    input_data=input_data,
                    schema=schema,
                )
            except LlmTransportError as exc:
                last_error_class = type(exc).__name__
                continue

            validation_errors = schema.validate(raw_output)
            if not validation_errors:
                latency_ms = (time.monotonic() - start) * 1000
                return StructuredCallResult(
                    operation=operation,
                    schema_name=schema.name,
                    schema_version=schema.version,
                    model=model,
                    output=raw_output,
                    validation_outcome="PASSED",
                    retry_count=attempt,
                    latency_ms=latency_ms,
                    error_class=None,
                )

            last_error_class = SchemaValidationError.__name__

        # Retries exhausted: fail closed (SAFE-920, D11). No output is
        # returned under any circumstance past this point.
        latency_ms = (time.monotonic() - start) * 1000
        return StructuredCallResult(
            operation=operation,
            schema_name=schema.name,
            schema_version=schema.version,
            model=model,
            output=None,
            validation_outcome="FAILED_CLOSED",
            retry_count=attempts - 1,
            latency_ms=latency_ms,
            error_class=last_error_class,
        )

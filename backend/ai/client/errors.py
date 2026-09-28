"""Error types for the LlmClient abstraction (D8/D11)."""

from __future__ import annotations


class LlmTransportError(Exception):
    """The underlying provider call itself failed (network, auth, provider
    outage, etc.) -- distinct from a schema-validation failure. Both are
    retried the same bounded number of times and both end in fail-closed
    (D11) if retries are exhausted.
    """


class SchemaValidationError(Exception):
    """A single call's output did not validate against the requested schema."""

    def __init__(self, message: str, *, validation_errors: list[str] | None = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


class LlmNotConfiguredError(Exception):
    """Raised when a real provider client is used without credentials.

    D25: the backend never falls back to a hardcoded or default key. Missing
    configuration is a fail-closed condition, not a soft-degrade -- there is
    no "try without a key" path.
    """

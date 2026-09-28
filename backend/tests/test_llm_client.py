"""Tests for the D8 LlmClient abstraction and D11's retry/fail-closed contract.

Uses FakeLlmClient exclusively -- no network, no API key, no real provider
call anywhere in this file (consistent with keeping the test suite runnable
without credentials, and with never spending real API budget on tests).
"""

from __future__ import annotations

import pytest

from backend.ai.client.errors import LlmNotConfiguredError, LlmTransportError
from backend.ai.client.fake_client import FakeLlmClient
from backend.ai.client.operations import Operation, Regime, model_for, regime_for
from backend.ai.client.results import to_audit_log_entry
from backend.ai.client.schema_spec import SchemaSpec

SIMPLE_SCHEMA = SchemaSpec(
    name="test.simple",
    version="1.0.0",
    json_schema={
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
        "additionalProperties": False,
    },
)


def _call(client: FakeLlmClient, operation: Operation = Operation.GUIDE_REQUEST_INTERPRETATION):
    return client.call_structured(
        operation=operation,
        schema=SIMPLE_SCHEMA,
        system_prompt="irrelevant for this test",
        input_data={"whatever": "irrelevant for this test"},
    )


def test_valid_first_attempt_passes_with_zero_retries():
    client = FakeLlmClient([{"value": "ok"}])
    result = _call(client)
    assert result.validation_outcome == "PASSED"
    assert result.output == {"value": "ok"}
    assert result.retry_count == 0
    assert not result.failed_closed


def test_recovers_after_one_malformed_response():
    client = FakeLlmClient(
        [
            {"value": 123},  # wrong type -> validation failure, retried
            {"value": "ok"},  # valid on retry
        ]
    )
    result = _call(client)
    assert result.validation_outcome == "PASSED"
    assert result.retry_count == 1
    assert client.calls_made == 2


def test_fails_closed_after_exhausting_retries_never_returns_malformed_output():
    # D11: bounded retry of 2 => 3 attempts total. All three malformed.
    client = FakeLlmClient(
        [
            {"value": 1},
            {"value": 2},
            {"value": 3},
        ]
    )
    result = _call(client)
    assert result.failed_closed
    assert result.validation_outcome == "FAILED_CLOSED"
    assert result.output is None  # the hard guarantee: never a malformed payload
    assert client.calls_made == 3


def test_transport_failures_count_toward_the_same_bounded_retry():
    client = FakeLlmClient(
        [
            LlmTransportError("network blip"),
            LlmTransportError("network blip again"),
            LlmTransportError("still down"),
        ]
    )
    result = _call(client)
    assert result.failed_closed
    assert result.error_class == "LlmTransportError"
    assert client.calls_made == 3


def test_mixed_transport_and_validation_failures_still_recover_within_budget():
    client = FakeLlmClient(
        [
            LlmTransportError("transient"),
            {"value": "ok"},
        ]
    )
    result = _call(client)
    assert result.validation_outcome == "PASSED"
    assert result.retry_count == 1


def test_max_retries_is_configurable_and_still_fails_closed():
    client = FakeLlmClient([{"value": 1}, {"value": 2}])
    result = client.call_structured(
        operation=Operation.GUIDE_REQUEST_INTERPRETATION,
        schema=SIMPLE_SCHEMA,
        system_prompt="x",
        input_data={},
        max_retries=1,  # 2 attempts total
    )
    assert result.failed_closed
    assert client.calls_made == 2


def test_extra_field_rejected_by_strict_schema():
    client = FakeLlmClient([{"value": "ok", "unexpected_field": "should not be here"}])
    result = _call(client)
    assert result.failed_closed


# ---------------------------------------------------------------------------
# Regime and model assignment (SAFE-900, D8)
# ---------------------------------------------------------------------------


def test_every_operation_has_exactly_one_regime():
    for op in Operation:
        assert regime_for(op) in {Regime.ASSIST, Regime.GUIDE}


def test_assist_and_guide_operations_are_correctly_split():
    assist_ops = {op for op in Operation if op.value.startswith("assist.")}
    guide_ops = {op for op in Operation if op.value.startswith("guide.")}
    assert all(regime_for(op) == Regime.ASSIST for op in assist_ops)
    assert all(regime_for(op) == Regime.GUIDE for op in guide_ops)


def test_document_structuring_uses_the_more_capable_model():
    # D8: accuracy matters most for document structuring (feeds D16
    # confirmation review, including verbatim dose text, SAFE-504).
    assert model_for(Operation.ASSIST_DOCUMENT_STRUCTURING) == "claude-sonnet-5"


def test_routine_generation_uses_the_faster_model():
    assert model_for(Operation.GUIDE_ROUTINE_GENERATION) == "claude-haiku-4-5"


# ---------------------------------------------------------------------------
# PRIV-1652: audit log entries can never carry prompt/response/clinical content
# ---------------------------------------------------------------------------


def test_audit_log_entry_contains_no_prompt_or_output_content():
    client = FakeLlmClient([{"value": "this looks like it could be clinical text"}])
    result = _call(client, operation=Operation.ASSIST_DOCUMENT_STRUCTURING)
    entry = to_audit_log_entry(result)

    allowed_keys = {
        "regime",
        "operation",
        "schemaVersion",
        "model",
        "latencyMs",
        "validationOutcome",
        "retryCount",
        "errorClass",
    }
    assert set(entry.keys()) == allowed_keys
    # The type itself cannot carry prompt/output content (no such field
    # exists on the entry), but assert on values too as a second guard
    # against a future refactor accidentally widening the projection.
    serialized = str(entry.values())
    assert "clinical text" not in serialized


def test_audit_log_entry_on_failed_closed_result_still_has_no_output_field():
    client = FakeLlmClient([{"value": 1}, {"value": 2}, {"value": 3}])
    result = _call(client, operation=Operation.ASSIST_DOCUMENT_STRUCTURING)
    entry = to_audit_log_entry(result)
    assert "output" not in entry
    assert entry["validationOutcome"] == "FAILED_CLOSED"


# ---------------------------------------------------------------------------
# Result invariants
# ---------------------------------------------------------------------------


def test_result_construction_rejects_passed_without_output():
    from backend.ai.client.results import StructuredCallResult

    with pytest.raises(ValueError):
        StructuredCallResult(
            operation=Operation.GUIDE_REQUEST_INTERPRETATION,
            schema_name="x",
            schema_version="1.0.0",
            model="claude-haiku-4-5",
            output=None,
            validation_outcome="PASSED",
            retry_count=0,
            latency_ms=1.0,
        )


def test_result_construction_rejects_failed_closed_with_output():
    from backend.ai.client.results import StructuredCallResult

    with pytest.raises(ValueError):
        StructuredCallResult(
            operation=Operation.GUIDE_REQUEST_INTERPRETATION,
            schema_name="x",
            schema_version="1.0.0",
            model="claude-haiku-4-5",
            output={"value": "should not be here"},
            validation_outcome="FAILED_CLOSED",
            retry_count=2,
            latency_ms=1.0,
        )


# ---------------------------------------------------------------------------
# D25: no client runs without credentials, no hardcoded fallback
# ---------------------------------------------------------------------------


def test_anthropic_client_refuses_to_construct_without_api_key(monkeypatch):
    from backend.ai.client.anthropic_client import AnthropicLlmClient

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LlmNotConfiguredError):
        AnthropicLlmClient()


def test_anthropic_client_accepts_explicit_key_without_touching_env(monkeypatch):
    from backend.ai.client.anthropic_client import AnthropicLlmClient

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = AnthropicLlmClient(api_key="test-only-not-a-real-key")
    assert client._api_key == "test-only-not-a-real-key"

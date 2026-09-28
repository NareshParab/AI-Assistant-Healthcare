"""The Anthropic provider implementation of LlmClient (D8).

This is the only file in the repository that imports the `anthropic` SDK
directly, and the only file that reads `ANTHROPIC_API_KEY`. Swapping
provider later (D8's stated reversibility) means writing a sibling file, not
touching call sites.

Credentials (D25/PRIV-1640): read from the environment only, never a
default, never hardcoded, never logged. If the key is absent, construction
fails loudly (LlmNotConfiguredError) rather than silently degrading -- there
is no "try without a key" path, consistent with fail-closed (SAFE-920).

Structured output (D11): uses tool-use with a single forced tool whose input
schema IS the requested SchemaSpec, so the provider is constrained at
generation time, not just checked after the fact. Whatever comes back is
still run through SchemaSpec.validate() by the shared base class -- this
class never trusts "the provider used the tool" as proof of validity.

PRIV-1622 [VERIFY BEFORE SUBMISSION]: confirm current Anthropic API terms
permit the account's usage tier before any non-synthetic document content is
ever sent through this client. Until that is confirmed and recorded, only
synthetic demo documents (HACK-980) may be passed as input_data.
"""

from __future__ import annotations

import os
from typing import Any

from .base import LlmClient
from .errors import LlmNotConfiguredError, LlmTransportError
from .schema_spec import SchemaSpec

_TOOL_NAME = "emit_structured_output"


class AnthropicLlmClient(LlmClient):
    def __init__(self, *, api_key: str | None = None):
        # Explicit param wins (useful for tests that DO want to hit a real
        # client class with a fake key path exercised elsewhere); otherwise
        # read from the environment. Never a hardcoded fallback (D25).
        resolved_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise LlmNotConfiguredError(
                "ANTHROPIC_API_KEY is not set. Per D25/PRIV-1640, credentials are "
                "supplied via environment variables only; this client refuses to "
                "run without one rather than degrade silently."
            )
        self._api_key = resolved_key
        self._sdk_client = None  # constructed lazily so importing this module

        # never requires the `anthropic` package to be installed to run the
        # rest of the AI-client test suite (FakeLlmClient covers that path).

    def _client(self):
        if self._sdk_client is None:
            import anthropic  # local import: keep the SDK optional at module load

            self._sdk_client = anthropic.Anthropic(api_key=self._api_key)
        return self._sdk_client

    def _raw_call(
        self,
        *,
        model: str,
        system_prompt: str,
        input_data: dict[str, Any],
        schema: SchemaSpec,
    ) -> dict[str, Any]:
        try:
            response = self._client().messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                tools=[
                    {
                        "name": _TOOL_NAME,
                        "description": (
                            f"Emit output conforming exactly to the "
                            f"'{schema.name}' v{schema.version} schema."
                        ),
                        "input_schema": schema.json_schema,
                    }
                ],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
                messages=[
                    {
                        "role": "user",
                        "content": self._render_input(input_data),
                    }
                ],
            )
        except Exception as exc:  # provider/network/auth failures, all bounded-retried
            raise LlmTransportError(str(exc)) from exc

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == _TOOL_NAME:
                return block.input

        raise LlmTransportError("provider response contained no tool_use block")

    @staticmethod
    def _render_input(input_data: dict[str, Any]) -> str:
        # Deliberately NOT logged anywhere (PRIV-1652). This only ever
        # travels to the provider over the API call itself.
        import json

        return json.dumps(input_data)

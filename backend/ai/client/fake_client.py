"""A deterministic, no-network LlmClient test double.

Used by this repository's own test suite so tests never depend on network
access, an API key, or a live provider (and never spend real API budget).
Not used by any production code path. Construct it with a queue of canned
raw responses (dicts, or exceptions to simulate a transport failure); each
call to `_raw_call` pops the next one.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from .base import LlmClient
from .errors import LlmTransportError
from .schema_spec import SchemaSpec


class FakeLlmClient(LlmClient):
    def __init__(self, scripted_responses: list[dict[str, Any] | Exception]):
        self._queue: deque[dict[str, Any] | Exception] = deque(scripted_responses)
        self.calls_made = 0

    def _raw_call(
        self,
        *,
        model: str,
        system_prompt: str,
        input_data: dict[str, Any],
        schema: SchemaSpec,
    ) -> dict[str, Any]:
        self.calls_made += 1
        if not self._queue:
            raise LlmTransportError("FakeLlmClient script exhausted")
        next_item = self._queue.popleft()
        if isinstance(next_item, Exception):
            raise next_item
        return next_item

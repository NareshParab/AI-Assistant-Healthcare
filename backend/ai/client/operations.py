"""Named AI operations and their per-task model assignment (D8).

Every AI call in the system must go through one of these named operations --
there is no free-form "call the model with any prompt" path. Naming the
operation is what makes the audit log (AIRequestLog / PRIV-1652) and the
ASSIST/GUIDE regime split (SAFE-900, D12/D13) enforceable rather than
aspirational.

Model selection is task-appropriate per D8: a capable model where accuracy
matters most (document structuring, which drives confirmation review), a
faster model where the task is narrower and latency matters more
(plain-language transform, summarization, routine interpretation/sequencing).
This mapping is the ONLY place a model name is chosen -- callers ask for an
operation, never a model.
"""

from __future__ import annotations

from enum import Enum


class Regime(str, Enum):
    """The two AI regimes (SAFE-900). Every operation belongs to exactly one."""

    ASSIST = "ASSIST"
    GUIDE = "GUIDE"


class Operation(str, Enum):
    # ASSIST (D12) -- transform-only, output is always a proposal (SAFE-913)
    ASSIST_DOCUMENT_STRUCTURING = "assist.document_structuring"  # A1
    ASSIST_PLAIN_LANGUAGE = "assist.plain_language"  # A2, "What this says"
    ASSIST_SUMMARY_INTERPRETATION = "assist.summary_interpretation"  # A3, region 4 only

    # GUIDE (D13) -- catalog-constrained selection/sequencing, IDs only
    GUIDE_REQUEST_INTERPRETATION = "guide.request_interpretation"  # G1
    GUIDE_ROUTINE_GENERATION = "guide.routine_generation"  # G2


# D12: ASSIST and GUIDE are physically separate regimes. This mapping is what
# SAFE-900 ("every AI operation assigned to exactly one regime") means in
# code -- it is consulted by the audit-log builder, never guessed.
OPERATION_REGIME: dict[Operation, Regime] = {
    Operation.ASSIST_DOCUMENT_STRUCTURING: Regime.ASSIST,
    Operation.ASSIST_PLAIN_LANGUAGE: Regime.ASSIST,
    Operation.ASSIST_SUMMARY_INTERPRETATION: Regime.ASSIST,
    Operation.GUIDE_REQUEST_INTERPRETATION: Regime.GUIDE,
    Operation.GUIDE_ROUTINE_GENERATION: Regime.GUIDE,
}

# D8: task-appropriate model per operation. Document structuring is the one
# operation whose output feeds the human confirmation gate (D16) most
# directly and where transcription accuracy (e.g. verbatim dose text,
# SAFE-504) matters most, so it gets the more capable model. Everything else
# here is a narrower, lower-stakes transform or a sequencing task over a
# small fixed catalog, so it gets the faster model.
OPERATION_MODEL: dict[Operation, str] = {
    Operation.ASSIST_DOCUMENT_STRUCTURING: "claude-sonnet-5",
    Operation.ASSIST_PLAIN_LANGUAGE: "claude-haiku-4-5",
    Operation.ASSIST_SUMMARY_INTERPRETATION: "claude-haiku-4-5",
    Operation.GUIDE_REQUEST_INTERPRETATION: "claude-haiku-4-5",
    Operation.GUIDE_ROUTINE_GENERATION: "claude-haiku-4-5",
}


def regime_for(operation: Operation) -> Regime:
    return OPERATION_REGIME[operation]


def model_for(operation: Operation) -> str:
    return OPERATION_MODEL[operation]

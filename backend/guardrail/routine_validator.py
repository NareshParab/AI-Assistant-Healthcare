"""Deterministic GUIDE routine validator.

Implements the five checks specified in ARCHITECTURE_MVP_PLAN.md section 7.3
and locked by decisions D13/D14/D17. This module has no dependency on any AI
provider or prompt: it is deliberately readable and testable independently of
both (SAFE-921), and it is the mechanism that makes SAFE-917 ("deterministic
validation of GUIDE output") literally true.

Nothing here may be loosened to make a demo or feature work (project rule:
"Do not weaken a safety rule simply to make a demo or feature work").

The GUIDE model (when integrated, per D13) is only ever allowed to emit
catalog movement IDs and per-segment durations -- never movement text. This
module is what turns that ID list into a PASS/FAIL result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

# PROD-121 tolerance for total-duration match against the requested budget.
# Kept as a named constant (not a magic number) so any future change to the
# tolerance is a one-line, reviewable change here -- not a silent drift.
DEFAULT_DURATION_TOLERANCE_SEC = 60

# Categories that may legally open a routine (SAFE-811 / PROD-811).
OPENING_CATEGORIES = {"WARMUP"}

# Categories that may legally close a routine when the routine contains any
# exertion segment (SAFE-811 / PROD-811). "Exertion" is any category other
# than WARMUP, BREATHING, RELAXATION -- i.e. MOBILITY, LIGHT_STRENGTH,
# STRETCH count as exertion for the purpose of requiring a calm close.
#
# Owner decision, 2026-09-29: RELAXATION added as a third accepted closer
# alongside COOLDOWN and BREATHING. RELAXATION was already treated as
# non-exertion (below) but had not, until this change, been accepted as a
# valid calm-close category in its own right -- a routine ending in
# RELAXATION after an exertion segment (e.g. WARMUP -> MOBILITY ->
# RELAXATION) previously failed check 3 even though RELAXATION is exactly
# the kind of calm closer this check exists to require.
CLOSING_CATEGORIES = {"COOLDOWN", "BREATHING", "RELAXATION"}
NON_EXERTION_CATEGORIES = {"WARMUP", "BREATHING", "RELAXATION"}


@dataclass(frozen=True)
class RoutineSegment:
    """One proposed segment: a catalog movement ID plus a duration.

    This is exactly the shape the GUIDE model (G2, per D13) is permitted to
    emit: an ID and a duration in seconds. It never carries movement text.
    """

    movement_id: str
    duration_sec: int


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    failure_reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def failed(self) -> bool:
        return not self.passed


def validate_routine(
    segments: Iterable[RoutineSegment],
    *,
    catalog_by_id: dict[str, dict],
    filtered_catalog_ids: set[str],
    requested_budget_sec: int,
    duration_tolerance_sec: int = DEFAULT_DURATION_TOLERANCE_SEC,
) -> ValidationResult:
    """Run all five deterministic checks from ARCHITECTURE_MVP_PLAN.md section 7.3.

    Parameters
    ----------
    segments:
        The proposed ordered routine as (movementId, durationSec) pairs --
        exactly what a GUIDE generation call is allowed to return.
    catalog_by_id:
        The full, versioned movement catalog (shared/movement-catalog/catalog.json),
        keyed by movement id, as authored under D17.
    filtered_catalog_ids:
        The subset of catalog ids that survived the precaution filter
        (SAFE-032) applied BEFORE the AI call, per section 7.3's flow. A
        movement whose id is in catalog_by_id but was filtered out for this
        profile must still fail validation (check 2).
    requested_budget_sec:
        The user's requested time budget, to check total duration against
        (PROD-121).
    duration_tolerance_sec:
        Allowed absolute deviation from requested_budget_sec.

    Returns
    -------
    ValidationResult
        passed=True only if every check passes. On any failure, passed=False
        and failure_reasons lists every check that failed (not just the
        first), so a validation-failure log entry is actually useful without
        ever containing movement/clinical text (PRIV-1652).

    This function never raises on a malformed proposal -- a malformed or
    unsafe routine is a FAIL result, handled by the caller per D24 (discard,
    serve a vetted preset, log the failure). Fail-closed (SAFE-920) means the
    caller must treat "not passed" as "do not use," not that this function
    fails open on an unexpected shape.
    """

    segments = list(segments)
    reasons: list[str] = []

    if not segments:
        return ValidationResult(passed=False, failure_reasons=("empty_routine",))

    # Check 1: every movementId exists in the catalog.
    unknown_ids = [s.movement_id for s in segments if s.movement_id not in catalog_by_id]
    if unknown_ids:
        reasons.append("unknown_movement_id")

    # Check 2: no movement was filtered out for this profile's precautions.
    # Only evaluated for ids that do exist in the catalog -- an unknown id is
    # already caught by check 1 and must not also be reported here.
    filtered_out = [
        s.movement_id
        for s in segments
        if s.movement_id in catalog_by_id and s.movement_id not in filtered_catalog_ids
    ]
    if filtered_out:
        reasons.append("movement_excluded_by_precaution_filter")

    # Checks 3-5 need category/duration-bounds lookups, which only make sense
    # for ids that actually resolve in the catalog. If any id is unknown we
    # still attempt the remaining checks against what does resolve, so a
    # single bad id does not mask other independent problems.
    resolved = [
        (s, catalog_by_id[s.movement_id])
        for s in segments
        if s.movement_id in catalog_by_id
    ]

    # Check 3: opens with WARMUP; closes with COOLDOWN/BREATHING/RELAXATION
    # if the routine contains any exertion segment (SAFE-811 / PROD-811).
    if resolved:
        first_category = resolved[0][1]["category"]
        last_category = resolved[-1][1]["category"]
        has_exertion = any(
            mv["category"] not in NON_EXERTION_CATEGORIES for _, mv in resolved
        )

        if first_category not in OPENING_CATEGORIES:
            reasons.append("does_not_open_with_warmup")

        if has_exertion and last_category not in CLOSING_CATEGORIES:
            reasons.append("does_not_close_with_cooldown_breathing_or_relaxation")

    # Check 4: sum of durations within tolerance of the requested budget
    # (PROD-121).
    total_duration = sum(s.duration_sec for s in segments)
    if abs(total_duration - requested_budget_sec) > duration_tolerance_sec:
        reasons.append("total_duration_outside_tolerance")

    # Check 5: each duration within the movement's own min/max (as authored
    # in the catalog under D17).
    out_of_bounds = [
        s.movement_id
        for s, mv in resolved
        if not (mv["minDurationSec"] <= s.duration_sec <= mv["maxDurationSec"])
    ]
    if out_of_bounds:
        reasons.append("duration_outside_movement_bounds")

    return ValidationResult(passed=not reasons, failure_reasons=tuple(reasons))


def load_catalog_by_id(catalog: dict) -> dict[str, dict]:
    """Index a loaded catalog.json document by movement id."""

    return {mv["id"]: mv for mv in catalog["movements"]}


def filter_catalog_for_precautions(
    catalog: dict, active_precaution_tags: set[str]
) -> set[str]:
    """Apply SAFE-032 as a deterministic filter, BEFORE any AI call.

    Returns the set of movement ids that carry no contraindicationTag
    present in the profile's active confirmed precaution tags. This is the
    join described in ARCHITECTURE_MVP_PLAN.md section 7.1/7.3: a
    Movement's `contraindicationTags` against a confirmed
    Precaution.blocksMovementTags.
    """

    return {
        mv["id"]
        for mv in catalog["movements"]
        if not set(mv.get("contraindicationTags", [])) & active_precaution_tags
    }

"""Tests for the deterministic GUIDE routine validator (D13/D14/D17, section 7.3).

Per D29, these are the highest-value tests in the project: each one proves a
safety boundary, not just a code path. Every test fails if the corresponding
boundary breaks.
"""

import json
from pathlib import Path

import pytest

from backend.guardrail.routine_validator import (
    RoutineSegment,
    filter_catalog_for_precautions,
    load_catalog_by_id,
    validate_routine,
)

CATALOG_PATH = (
    Path(__file__).resolve().parents[2] / "shared" / "movement-catalog" / "catalog.json"
)


@pytest.fixture(scope="module")
def catalog():
    with open(CATALOG_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def catalog_by_id(catalog):
    return load_catalog_by_id(catalog)


@pytest.fixture()
def unfiltered_ids(catalog_by_id):
    return set(catalog_by_id.keys())


# ---------------------------------------------------------------------------
# Catalog authoring invariants (D17) -- these guard the *content*, since the
# catalog itself is documented as "the safety boundary" and must hold even
# before any validator logic runs against it.
# ---------------------------------------------------------------------------


def test_catalog_has_exactly_the_specified_composition(catalog):
    expected = {
        "WARMUP": 6,
        "MOBILITY": 12,
        "LIGHT_STRENGTH": 8,
        "STRETCH": 10,
        "BREATHING": 5,
        "RELAXATION": 4,
    }
    counts: dict[str, int] = {}
    for mv in catalog["movements"]:
        counts[mv["category"]] = counts.get(mv["category"], 0) + 1
    assert counts == expected
    assert len(catalog["movements"]) == 45


def test_catalog_has_no_high_intensity_movement(catalog):
    # SAFE-030: low-to-moderate only. HIGH must never appear.
    for mv in catalog["movements"]:
        assert mv["intensity"] in {"VERY_LOW", "LOW", "MODERATE"}


def test_catalog_movements_require_no_equipment(catalog):
    for mv in catalog["movements"]:
        assert mv["equipment"] == "NONE"


def test_catalog_ids_are_unique(catalog):
    ids = [mv["id"] for mv in catalog["movements"]]
    assert len(ids) == len(set(ids))


def test_catalog_gentler_variant_references_resolve(catalog):
    ids = {mv["id"] for mv in catalog["movements"]}
    for mv in catalog["movements"]:
        variant = mv.get("gentlerVariantId")
        if variant:
            assert variant in ids, f"{mv['id']} points to missing {variant}"


def test_catalog_min_max_bracket_default_duration(catalog):
    for mv in catalog["movements"]:
        assert mv["minDurationSec"] <= mv["defaultDurationSec"] <= mv["maxDurationSec"]


# ---------------------------------------------------------------------------
# validate_routine() -- the five deterministic checks (section 7.3, SAFE-917)
# ---------------------------------------------------------------------------


def _warmup_close_breathing_routine(catalog_by_id):
    """A minimal, legitimately valid routine: WARMUP ... BREATHING, budget-matched."""
    warmup_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "WARMUP"
    )
    breathing_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "BREATHING"
    )
    segments = [
        RoutineSegment(warmup_id, catalog_by_id[warmup_id]["defaultDurationSec"]),
        RoutineSegment(breathing_id, catalog_by_id[breathing_id]["defaultDurationSec"]),
    ]
    budget = sum(s.duration_sec for s in segments)
    return segments, budget


def test_valid_routine_passes(catalog_by_id, unfiltered_ids):
    segments, budget = _warmup_close_breathing_routine(catalog_by_id)
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        requested_budget_sec=budget,
    )
    assert result.passed, result.failure_reasons


def test_unknown_movement_id_fails_closed(catalog_by_id, unfiltered_ids):
    segments = [RoutineSegment("not_a_real_movement_id", 60)]
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        requested_budget_sec=60,
    )
    assert result.failed
    assert "unknown_movement_id" in result.failure_reasons


def test_movement_excluded_by_precaution_filter_fails_even_if_model_returns_it(
    catalog_by_id, unfiltered_ids
):
    # This is the case that matters most: the model ignored the filtered
    # catalog and returned an id that should have been excluded for this
    # profile's confirmed precautions (SAFE-032). The validator must catch
    # it independently of whatever the model did.
    neck_movement_id = next(
        mv["id"]
        for mv in catalog_by_id.values()
        if "no_neck_movement" in mv.get("contraindicationTags", [])
    )
    filtered_ids = filter_catalog_for_precautions(
        {"movements": list(catalog_by_id.values())}, {"no_neck_movement"}
    )
    assert neck_movement_id not in filtered_ids  # sanity: the filter did its job

    warmup_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "WARMUP"
    )
    segments = [
        RoutineSegment(warmup_id, catalog_by_id[warmup_id]["defaultDurationSec"]),
        RoutineSegment(
            neck_movement_id, catalog_by_id[neck_movement_id]["defaultDurationSec"]
        ),
    ]
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=filtered_ids,
        requested_budget_sec=sum(s.duration_sec for s in segments),
    )
    assert result.failed
    assert "movement_excluded_by_precaution_filter" in result.failure_reasons


def test_routine_must_open_with_warmup(catalog_by_id, unfiltered_ids):
    breathing_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "BREATHING"
    )
    segments = [
        RoutineSegment(breathing_id, catalog_by_id[breathing_id]["defaultDurationSec"])
    ]
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        requested_budget_sec=segments[0].duration_sec,
    )
    assert result.failed
    assert "does_not_open_with_warmup" in result.failure_reasons


def test_routine_with_exertion_must_close_with_cooldown_or_breathing(
    catalog_by_id, unfiltered_ids
):
    warmup_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "WARMUP"
    )
    mobility_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "MOBILITY"
    )
    # Opens correctly, but closes on an exertion segment (MOBILITY) instead
    # of BREATHING/COOLDOWN -- must fail even though it opened correctly.
    segments = [
        RoutineSegment(warmup_id, catalog_by_id[warmup_id]["defaultDurationSec"]),
        RoutineSegment(mobility_id, catalog_by_id[mobility_id]["defaultDurationSec"]),
    ]
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        requested_budget_sec=sum(s.duration_sec for s in segments),
    )
    assert result.failed
    assert "does_not_close_with_cooldown_or_breathing" in result.failure_reasons


def test_all_relaxation_or_breathing_routine_has_no_exertion_so_any_close_is_fine(
    catalog_by_id, unfiltered_ids
):
    # A routine with zero exertion segments (e.g. warmup + relaxation) is not
    # required to close on BREATHING/COOLDOWN, since SAFE-811/PROD-811 only
    # impose that requirement "if any exertion segment present."
    warmup_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "WARMUP"
    )
    relax_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "RELAXATION"
    )
    segments = [
        RoutineSegment(warmup_id, catalog_by_id[warmup_id]["defaultDurationSec"]),
        RoutineSegment(relax_id, catalog_by_id[relax_id]["defaultDurationSec"]),
    ]
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        requested_budget_sec=sum(s.duration_sec for s in segments),
    )
    assert result.passed, result.failure_reasons


def test_total_duration_outside_tolerance_fails(catalog_by_id, unfiltered_ids):
    segments, budget = _warmup_close_breathing_routine(catalog_by_id)
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        requested_budget_sec=budget + 1000,  # way outside PROD-121 tolerance
    )
    assert result.failed
    assert "total_duration_outside_tolerance" in result.failure_reasons


def test_duration_within_tolerance_boundary_passes(catalog_by_id, unfiltered_ids):
    segments, budget = _warmup_close_breathing_routine(catalog_by_id)
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        requested_budget_sec=budget + 60,  # exactly at the default tolerance
    )
    assert result.passed, result.failure_reasons


def test_duration_outside_movement_bounds_fails(catalog_by_id, unfiltered_ids):
    warmup_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "WARMUP"
    )
    breathing_id = next(
        mv["id"] for mv in catalog_by_id.values() if mv["category"] == "BREATHING"
    )
    absurd_duration = catalog_by_id[warmup_id]["maxDurationSec"] + 10_000
    segments = [
        RoutineSegment(warmup_id, absurd_duration),
        RoutineSegment(breathing_id, catalog_by_id[breathing_id]["defaultDurationSec"]),
    ]
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        # match the (absurd) total so this test isolates ONLY the
        # per-movement bounds check, not the total-duration check.
        requested_budget_sec=sum(s.duration_sec for s in segments),
    )
    assert result.failed
    assert "duration_outside_movement_bounds" in result.failure_reasons


def test_empty_routine_fails_closed(catalog_by_id, unfiltered_ids):
    result = validate_routine(
        [],
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        requested_budget_sec=600,
    )
    assert result.failed


def test_filter_catalog_for_precautions_excludes_only_tagged_movements(catalog):
    filtered = filter_catalog_for_precautions(catalog, {"avoid_standing"})
    for mv in catalog["movements"]:
        if "avoid_standing" in mv.get("contraindicationTags", []):
            assert mv["id"] not in filtered
        else:
            assert mv["id"] in filtered


def test_filter_catalog_for_precautions_is_noop_with_no_active_precautions(catalog):
    filtered = filter_catalog_for_precautions(catalog, set())
    assert filtered == {mv["id"] for mv in catalog["movements"]}

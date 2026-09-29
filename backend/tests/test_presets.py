"""Tests for the section-7.4 hand-authored presets
(shared/movement-catalog/presets.json), validated against the real
deterministic validator (D13/D14/D17, section 7.3) -- not a separate,
weaker check. A preset that could not pass validate_routine() would be
useless as a D24 fallback, since the fallback's whole point is to always
be safe to serve without further checking.

Scope note: this task authors exactly three presets (10/15/20 min, one
each, goal-agnostic), per the owner's explicit instruction. Section 7.4's
own text ("for each budget AND EACH GOAL") describes a fuller future set;
that gap is reported in this task's report, not resolved here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.guardrail.routine_validator import (
    DEFAULT_DURATION_TOLERANCE_SEC,
    RoutineSegment,
    filter_catalog_for_precautions,
    load_catalog_by_id,
    validate_routine,
)

CATALOG_PATH = (
    Path(__file__).resolve().parents[2] / "shared" / "movement-catalog" / "catalog.json"
)
PRESETS_PATH = (
    Path(__file__).resolve().parents[2] / "shared" / "movement-catalog" / "presets.json"
)


@pytest.fixture(scope="module")
def catalog():
    with open(CATALOG_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def catalog_by_id(catalog):
    return load_catalog_by_id(catalog)


@pytest.fixture(scope="module")
def presets_doc():
    with open(PRESETS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def presets(presets_doc):
    return presets_doc["presets"]


# ---------------------------------------------------------------------------
# Structural / authoring invariants
# ---------------------------------------------------------------------------


def test_presets_file_references_the_current_catalog_version(presets_doc, catalog):
    assert presets_doc["catalogVersion"] == catalog["catalogVersion"]


def test_exactly_three_presets_for_10_15_20_minutes(presets):
    assert len(presets) == 3
    target_durations = sorted(p["targetDurationSec"] for p in presets)
    assert target_durations == [600, 900, 1200]


def test_preset_ids_are_present_stable_and_unique(presets):
    ids = [p["id"] for p in presets]
    assert all(isinstance(i, str) and i for i in ids)
    assert len(ids) == len(set(ids))


def test_preset_titles_and_descriptions_are_plain_and_non_clinical(presets):
    # A cheap, deliberately narrow guard: presets must not smuggle in
    # clinical/medical framing. Not a substitute for human review, but
    # catches an obvious regression (e.g. a title mentioning a condition).
    forbidden_terms = {
        "diagnos", "prescri", "treat", "therapy", "cure", "patient",
        "cardiac", "stroke", "disease", "symptom", "medical",
    }
    for p in presets:
        text = f"{p['title']} {p['description']}".lower()
        hits = [term for term in forbidden_terms if term in text]
        assert not hits, f"preset {p['id']} title/description contains: {hits}"


def test_every_preset_references_only_known_catalog_ids(presets, catalog_by_id):
    """Fails if any preset references an unknown or removed catalog id --
    the explicit regression guard this task's spec calls for.
    """
    for p in presets:
        for seg in p["segments"]:
            assert seg["movementId"] in catalog_by_id, (
                f"preset {p['id']} references unknown movement id "
                f"{seg['movementId']!r} (removed from or never in the catalog)"
            )


def test_preset_movement_tags_are_inspectable_for_a_future_precaution_filter(
    presets, catalog_by_id
):
    """Does not build a filter (explicitly out of scope for this task) --
    only proves the data shape supports one: for every preset segment, the
    referenced catalog movement's contraindicationTags are reachable, so a
    future device-side filter can reject a preset when a confirmed
    precaution's tag intersects any segment's tags.
    """
    for p in presets:
        for seg in p["segments"]:
            movement = catalog_by_id[seg["movementId"]]
            tags = movement.get("contraindicationTags")
            assert isinstance(tags, list), (
                f"preset {p['id']} segment {seg['movementId']} has no "
                f"inspectable contraindicationTags list"
            )


# ---------------------------------------------------------------------------
# Real validator run per preset -- the actual safety-relevant tests.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("preset_index", [0, 1, 2])
def test_each_preset_passes_the_real_validator_with_no_active_precautions(
    presets, catalog_by_id, catalog, preset_index
):
    preset = presets[preset_index]
    unfiltered_ids = filter_catalog_for_precautions(catalog, set())

    segments = [
        RoutineSegment(seg["movementId"], seg["durationSec"])
        for seg in preset["segments"]
    ]
    result = validate_routine(
        segments,
        catalog_by_id=catalog_by_id,
        filtered_catalog_ids=unfiltered_ids,
        requested_budget_sec=preset["targetDurationSec"],
    )
    assert result.passed, (preset["id"], result.failure_reasons)


@pytest.mark.parametrize("preset_index", [0, 1, 2])
def test_each_preset_total_duration_is_within_tolerance_of_its_target(
    presets, preset_index
):
    preset = presets[preset_index]
    total = sum(seg["durationSec"] for seg in preset["segments"])
    diff = abs(total - preset["targetDurationSec"])
    assert diff <= DEFAULT_DURATION_TOLERANCE_SEC, (preset["id"], total, diff)


@pytest.mark.parametrize("preset_index", [0, 1, 2])
def test_each_preset_opens_with_warmup(presets, catalog_by_id, preset_index):
    preset = presets[preset_index]
    first_id = preset["segments"][0]["movementId"]
    assert catalog_by_id[first_id]["category"] == "WARMUP", preset["id"]


@pytest.mark.parametrize("preset_index", [0, 1, 2])
def test_each_preset_closes_with_an_accepted_calming_category(
    presets, catalog_by_id, preset_index
):
    preset = presets[preset_index]
    last_id = preset["segments"][-1]["movementId"]
    closer_category = catalog_by_id[last_id]["category"]
    assert closer_category in {"COOLDOWN", "BREATHING", "RELAXATION"}, preset["id"]


@pytest.mark.parametrize("preset_index", [0, 1, 2])
def test_each_preset_segment_duration_is_within_its_movements_bounds(
    presets, catalog_by_id, preset_index
):
    preset = presets[preset_index]
    for seg in preset["segments"]:
        mv = catalog_by_id[seg["movementId"]]
        assert mv["minDurationSec"] <= seg["durationSec"] <= mv["maxDurationSec"], (
            preset["id"],
            seg["movementId"],
            seg["durationSec"],
        )


@pytest.mark.parametrize("preset_index", [0, 1, 2])
def test_each_preset_uses_only_low_intensity_no_equipment_movements(
    presets, catalog_by_id, preset_index
):
    """SAFE-030: presets are the D24 fallback -- the maximally-conservative
    safety net, not just "as safe as a generated routine." Every preset
    movement must be VERY_LOW/LOW/MODERATE intensity (never HIGH, which
    cannot exist in the catalog at all -- see test_routine_validator.py)
    and require no equipment.
    """
    preset = presets[preset_index]
    for seg in preset["segments"]:
        mv = catalog_by_id[seg["movementId"]]
        assert mv["intensity"] in {"VERY_LOW", "LOW", "MODERATE"}, preset["id"]
        assert mv["equipment"] == "NONE", preset["id"]

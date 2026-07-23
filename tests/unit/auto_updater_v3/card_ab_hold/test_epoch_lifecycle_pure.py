"""Unit-тесты чистой доменной логики epoch lifecycle (§19 / §22)."""

from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    DEFAULT_WARMUP_HOURS,
    MIN_WARMUP_HOURS,
    CardAbHoldSyncStatus,
    all_confirms_complete,
    build_pending_intent_payload,
    build_wb_sync_idempotency_key,
    clamp_warmup_duration_hours,
    clear_epoch_fields_values,
    is_legacy_mvp1_phase,
    is_warmup_elapsed,
    normalize_card_ab_hold_sync_status,
    propose_target_places_from_positions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldPhase,
    is_epoch_managed_ab_hold,
)


@pytest.mark.unit
def test_clamp_warmup_duration_rejects_below_min() -> None:
    """§19: длительность < 24ч отклоняется."""
    with pytest.raises(ValueError, match="24"):
        clamp_warmup_duration_hours(23)
    assert clamp_warmup_duration_hours(24) == 24
    assert clamp_warmup_duration_hours(48) == 48


@pytest.mark.unit
def test_warmup_elapsed_respects_duration() -> None:
    """WARM_UP elapsed по started_at + duration_hours."""
    started = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    now_before = started + datetime.timedelta(hours=23, minutes=59)
    now_after = started + datetime.timedelta(hours=24)
    assert is_warmup_elapsed(started, 24, now=now_before) is False
    assert is_warmup_elapsed(started, 24, now=now_after) is True
    assert is_warmup_elapsed(None, 24) is False


@pytest.mark.unit
def test_idempotency_key_format() -> None:
    """§22.5: ``{adv_id}:{generation}``."""
    assert build_wb_sync_idempotency_key(12345, 3) == "12345:3"


@pytest.mark.unit
def test_pending_intent_payload_shape() -> None:
    """Intent JSON содержит generation и confirmed params."""
    payload = build_pending_intent_payload(
        generation=2,
        keywords=["a", "b"],
        target_places={"a": 10, "b": 12},
        auto_participation=True,
        auto_bid=150.5,
    )
    assert payload["generation"] == 2
    assert payload["keywords"] == ["a", "b"]
    assert payload["target_places"] == {"a": 10, "b": 12}
    assert payload["auto_participation"] is True
    assert payload["auto_bid"] == 150.5


@pytest.mark.unit
def test_null_phase_is_legacy_mvp1() -> None:
    """§18.5: NULL phase → legacy MVP-1, не epoch-managed."""
    assert is_legacy_mvp1_phase(None) is True
    assert is_legacy_mvp1_phase("") is True
    assert is_legacy_mvp1_phase(CardAbHoldPhase.WARM_UP) is False
    assert is_epoch_managed_ab_hold(phase=None) is False
    assert is_epoch_managed_ab_hold(phase=CardAbHoldPhase.WARM_UP) is True


@pytest.mark.unit
def test_clear_epoch_fields_resets_generation_and_sync() -> None:
    """EXIT reset: generation=0, sync_status=none."""
    clears = clear_epoch_fields_values()
    assert clears["card_ab_hold_phase"] is None
    assert clears["card_ab_hold_generation"] == 0
    assert clears["card_ab_hold_sync_status"] == CardAbHoldSyncStatus.NONE.value
    assert clears["card_ab_hold_warmup_duration_hours"] == DEFAULT_WARMUP_HOURS


@pytest.mark.unit
def test_all_confirms_complete_requires_all_fields() -> None:
    """Intent precondition: все confirmed-* поля."""
    incomplete = SimpleNamespace(
        card_ab_hold_confirmed_keywords_json=["kw"],
        card_ab_hold_confirmed_target_places_json=None,
        card_ab_hold_confirmed_auto_participation=True,
        card_ab_hold_confirmed_auto_bid=100.0,
    )
    complete = SimpleNamespace(
        card_ab_hold_confirmed_keywords_json=["kw"],
        card_ab_hold_confirmed_target_places_json={"kw": 5},
        card_ab_hold_confirmed_auto_participation=False,
        card_ab_hold_confirmed_auto_bid=50.0,
    )
    assert all_confirms_complete(incomplete) is False
    assert all_confirms_complete(complete) is True


@pytest.mark.unit
def test_propose_target_places_skips_non_positive() -> None:
    """Proposed TP только для position > 0."""
    out = propose_target_places_from_positions({"a": 14.4, "b": 0.0, "c": -1.0})
    assert "a" in out
    assert "b" not in out
    assert "c" not in out
    assert out["a"] >= 1


@pytest.mark.unit
def test_normalize_sync_status_unknown_to_none() -> None:
    """Unknown sync status → ``none``."""
    assert normalize_card_ab_hold_sync_status(None) == CardAbHoldSyncStatus.NONE
    assert normalize_card_ab_hold_sync_status("complete") == CardAbHoldSyncStatus.COMPLETE
    assert normalize_card_ab_hold_sync_status("bogus") == CardAbHoldSyncStatus.NONE


@pytest.mark.unit
def test_default_warmup_constants() -> None:
    """Default/min WARM_UP = 24 часа."""
    assert DEFAULT_WARMUP_HOURS == MIN_WARMUP_HOURS == 24

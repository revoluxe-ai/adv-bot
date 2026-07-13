"""Unit-тесты Redis coordination DTO / keys (spec ``card-ab-hold-mode``)."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    CardAbHoldLastAbortSnapshot,
    CardAbHoldSignalKind,
    CardAbHoldSignalSnapshot,
    SETUP_LOCK_TTL_SEC,
    setup_lock_redis_key,
)


@pytest.mark.unit
def test_signal_snapshot_roundtrip_json() -> None:
    """3.4: Pydantic snapshot сериализуется/валидируется без MagicMock domain."""
    snap = CardAbHoldSignalSnapshot(signal=CardAbHoldSignalKind.ENTER)
    raw = snap.model_dump_json()
    restored = CardAbHoldSignalSnapshot.model_validate_json(raw)
    assert restored.signal == CardAbHoldSignalKind.ENTER
    assert restored.requested_by == "bot"


@pytest.mark.unit
def test_last_abort_snapshot_defaults_safe() -> None:
    """LastAbort: safe/can_continue по умолчанию True."""
    snap = CardAbHoldLastAbortSnapshot(reason="enter_requested")
    assert snap.safe is True
    assert snap.can_continue is True


@pytest.mark.unit
def test_setup_lock_ttl_five_minutes() -> None:
    """Setup lock TTL ≈ 5 минут."""
    assert SETUP_LOCK_TTL_SEC == 300
    assert setup_lock_redis_key(1) == "CardAbHoldSetupLock:1"

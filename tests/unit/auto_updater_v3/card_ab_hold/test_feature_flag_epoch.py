"""Unit-тесты fail-closed feature flag epoch-managed A/B Hold (§25 / OD-05)."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
    feature_flag,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.feature_flag import (
    can_enter_epoch_managed_ab_hold,
    coerce_shop_id_for_epoch_allowlist,
    evaluate_card_ab_hold_broad_enable_readiness,
    is_card_ab_hold_broad_enable_authorized,
    is_card_ab_hold_epoch_flow_enabled,
)


@pytest.fixture(autouse=True)
def _clear_epoch_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Изолировать env между тестами (fail-closed defaults)."""
    for key in (
        "CARD_AB_HOLD_EPOCH_FLOW_ENABLED",
        "CARD_AB_HOLD_EPOCH_ALLOWLIST_ADV_IDS",
        "CARD_AB_HOLD_EPOCH_ALLOWLIST_SHOP_IDS",
        "CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.unit
def test_epoch_flow_disabled_by_default() -> None:
    """Master flag unset → epoch-managed вход запрещён."""
    assert is_card_ab_hold_epoch_flow_enabled() is False
    assert can_enter_epoch_managed_ab_hold(adv_id=100, shop_id=1) is False


@pytest.mark.unit
def test_epoch_flow_flag_on_empty_allowlist_still_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Flag ON без allowlist и без OD-05 → False (no silent open)."""
    monkeypatch.setenv("CARD_AB_HOLD_EPOCH_FLOW_ENABLED", "true")
    assert is_card_ab_hold_epoch_flow_enabled() is True
    assert can_enter_epoch_managed_ab_hold(adv_id=100, shop_id=1) is False


@pytest.mark.unit
def test_epoch_flow_adv_id_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hit по adv_id allowlist разрешает epoch flow."""
    monkeypatch.setenv("CARD_AB_HOLD_EPOCH_FLOW_ENABLED", "1")
    monkeypatch.setenv("CARD_AB_HOLD_EPOCH_ALLOWLIST_ADV_IDS", "42,99")
    assert can_enter_epoch_managed_ab_hold(adv_id=42, shop_id=None) is True
    assert can_enter_epoch_managed_ab_hold(adv_id=43, shop_id=1) is False


@pytest.mark.unit
def test_epoch_flow_shop_id_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hit по shop_id allowlist разрешает epoch flow."""
    monkeypatch.setenv("CARD_AB_HOLD_EPOCH_FLOW_ENABLED", "yes")
    monkeypatch.setenv("CARD_AB_HOLD_EPOCH_ALLOWLIST_SHOP_IDS", "7")
    assert can_enter_epoch_managed_ab_hold(adv_id=999, shop_id=7) is True
    assert can_enter_epoch_managed_ab_hold(adv_id=999, shop_id=8) is False


@pytest.mark.unit
def test_od05_broad_enable_accepts_all_when_flag_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OD-05 broad enable — True для любой кампании при master flag ON."""
    monkeypatch.setenv("CARD_AB_HOLD_EPOCH_FLOW_ENABLED", "on")
    monkeypatch.setenv("CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED", "true")
    assert is_card_ab_hold_broad_enable_authorized() is True
    assert can_enter_epoch_managed_ab_hold(adv_id=1, shop_id=None) is True
    assert can_enter_epoch_managed_ab_hold(adv_id=999_999, shop_id=123) is True


@pytest.mark.unit
def test_od05_without_master_flag_still_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OD-05 alone MUST NOT open flow без master flag."""
    monkeypatch.setenv("CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED", "1")
    assert is_card_ab_hold_broad_enable_authorized() is True
    assert is_card_ab_hold_epoch_flow_enabled() is False
    assert can_enter_epoch_managed_ab_hold(adv_id=1, shop_id=1) is False


@pytest.mark.unit
def test_broad_enable_readiness_blocked_without_od05(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§25.3/25.4: broad enable без OD-05 блокируется даже при flag+allowlist."""
    monkeypatch.setenv("CARD_AB_HOLD_EPOCH_FLOW_ENABLED", "true")
    monkeypatch.setenv("CARD_AB_HOLD_EPOCH_ALLOWLIST_ADV_IDS", "1,2,3")
    monkeypatch.setenv("CARD_AB_HOLD_EPOCH_ALLOWLIST_SHOP_IDS", "10")
    snap = evaluate_card_ab_hold_broad_enable_readiness()
    assert snap.od05_accepted is False
    assert snap.epoch_master_flag_enabled is True
    assert snap.allowlist_adv_count == 3
    assert snap.allowlist_shop_count == 1
    assert snap.broad_enable_allowed is False
    assert any("OD-05" in reason for reason in snap.blocking_reasons)
    # Allowlist ≠ broad: non-listed campaign still closed.
    assert can_enter_epoch_managed_ab_hold(adv_id=999, shop_id=999) is False


@pytest.mark.unit
def test_broad_enable_readiness_allowed_only_with_od05(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Readiness снимает блок broad enable только после явного OD-05."""
    monkeypatch.setenv("CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED", "yes")
    snap = evaluate_card_ab_hold_broad_enable_readiness()
    assert snap.od05_accepted is True
    assert snap.broad_enable_allowed is True
    assert snap.blocking_reasons == ()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("7", 7),
        (" 42 ", 42),
        (7, 7),
        (None, None),
        ("", None),
        ("   ", None),
        ("not-a-number", None),
        (True, None),
        (False, None),
    ],
)
def test_coerce_shop_id_for_epoch_allowlist(raw: object, expected: int | None) -> None:
    """WBCabinet.shop_id (str) → int; non-numeric / bool → None (fail-closed)."""
    assert coerce_shop_id_for_epoch_allowlist(raw) == expected

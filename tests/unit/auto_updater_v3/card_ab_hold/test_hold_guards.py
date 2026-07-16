"""Unit-тесты hold overspend selection (spec ``card-ab-hold-mode``)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.hold_guards import (
    is_ab_hold_campaign_deep_overspend,
    select_ab_hold_overspend_off_keyword_ids,
)


def _kw(
    *,
    ks_id: int,
    pfo: float | None,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    hard_status: int = 2,
) -> SimpleNamespace:
    return SimpleNamespace(
        keyword_setting_original_id=ks_id,
        pay_for_order=pfo,
        strategy_mode=mode,
        hard_status=hard_status,
    )


@pytest.mark.unit
def test_deep_overspend_gate() -> None:
    """HOLD guard запускается только при fact в зоне pfo_off."""
    assert (
        is_ab_hold_campaign_deep_overspend(
            fact_pay_for_order=150.0, max_pay_for_order=100.0
        )
        is True
    )
    assert (
        is_ab_hold_campaign_deep_overspend(
            fact_pay_for_order=50.0, max_pay_for_order=100.0
        )
        is False
    )
    assert (
        is_ab_hold_campaign_deep_overspend(
            fact_pay_for_order=None, max_pay_for_order=100.0
        )
        is False
    )


@pytest.mark.unit
def test_select_overspend_off_ids() -> None:
    """OFF кандидаты: operable + PFO > max; OFF-режим пропускается."""
    keywords = [
        _kw(ks_id=1, pfo=200.0),
        _kw(ks_id=2, pfo=50.0),
        _kw(ks_id=3, pfo=300.0, mode=KeywordStrategyMode.OFF),
        _kw(ks_id=4, pfo=400.0, hard_status=3),
    ]
    ids = select_ab_hold_overspend_off_keyword_ids(
        keywords,  # type: ignore[arg-type]
        max_pay_for_order=100.0,
    )
    assert ids == [1]

"""Unit: ``try_valid_rollout_up`` — effective UP без NameError на ``catalog``."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    try_valid_rollout_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.auto_updater_v3.test_effective_ladder_steps import _fake_catalog_places
from tests.unit.test_auto_updater_v3 import _calc_kw

TS = datetime(2024, 1, 1, tzinfo=UTC)


def _patch_catalog(
    monkeypatch: pytest.MonkeyPatch, cat: dict
) -> None:
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared=None, _ladder=None: cat,
    )


@pytest.mark.unit
def test_try_valid_rollout_up_min_cpa_to_opt_uses_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MIN_CPA: effective UP в OPT (alias MAX пропущен); ``catalog.get``, не ``cand``."""
    cat = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    prof = [
        PositionProfilePoint(
            position=1, bid=10_000, predicted_conversion=0.13, pay_for_cart=50.0, timestamp=TS
        ),
        PositionProfilePoint(
            position=40, bid=500, predicted_conversion=0.015, pay_for_cart=10.0, timestamp=TS
        ),
    ]
    kw = _calc_kw(
        ks_id=5,
        text="min_up",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=0.05,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = [(ctx, KeywordStrategyMode.MIN_CPA)]

    action = try_valid_rollout_up(
        ctx,
        KeywordStrategyMode.MIN_CPA,
        prepared=prepared,
    )

    assert action is not None
    assert action.action == V3ActionType.UP
    assert action.keyword_setting_id == 5
    assert action.reason == "rollout_step_up"


@pytest.mark.unit
def test_try_valid_rollout_up_min_cpa_collapsed_catalog_no_name_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M=O=C: нет effective UP с другим place — None, без NameError."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    kw = _calc_kw(
        ks_id=6,
        text="collapsed",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=0.05,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=[])
    prepared = [(ctx, KeywordStrategyMode.MIN_CPA)]

    action = try_valid_rollout_up(
        ctx,
        KeywordStrategyMode.MIN_CPA,
        prepared=prepared,
    )

    assert action is None

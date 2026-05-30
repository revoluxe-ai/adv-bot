"""Unit: MOC stats log в ``sync_keyword_target_places_v3`` включает ``o_eq_m``."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place.clickhouse_manager.dto.bid_position import (
    BidPosition,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync import (
    sync_keyword_target_places_v3,
)
from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST
from tests.unit.auto_updater_v3.test_no_data_activation import _kw as _calc_kw

TS = datetime(2024, 1, 1, tzinfo=UTC)


def _patched_sm(session_cm: AsyncMock) -> Callable[..., AsyncMock]:
    def _open(*_a: object, **_k: object) -> AsyncMock:
        return session_cm

    return _open


def _o_eq_m_bid_profiles() -> dict[str, list[BidPosition]]:
    """MIN=OPT place 40, MAX place 1 — ``o_eq_m`` True при RK CPO."""
    bp_max = BidPosition("kw_oem", 1, 10_000, TS)
    bp_max.conv_carts_to_views = 0.13
    bp_min = BidPosition("kw_oem", 40, 500, TS)
    bp_min.conv_carts_to_views = 0.015
    return {"kw_oem": [bp_max, bp_min]}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_moc_stats_log_includes_o_eq_m(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``logger.info`` MOC stats содержит ``o_eq_m`` при alias O=M."""
    caplog.set_level(
        logging.INFO,
        logger="app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync",
    )
    kw = SimpleNamespace(
        id=1,
        text="kw_oem",
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        target_place=None,
        hard_status=2,
    )
    fake_result = MagicMock()
    fake_result.scalars.return_value.all.return_value = [kw]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=fake_result)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync.sm",
        _patched_sm(session_cm),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rk_orders_per_cart_7d",
        AsyncMock(return_value=RK_ORDERS_PER_CART_TEST),
    )

    adv = MagicMock()
    adv.adv_setting_original_id = 1
    adv.adv_id = 99
    adv.complex_adv.adv_setting = MagicMock()

    await sync_keyword_target_places_v3(
        adv=adv,
        bid_profiles=_o_eq_m_bid_profiles(),
        calculated_by_text={
            "kw_oem": _calc_kw(
                ks_id=1,
                text="kw_oem",
                mode=KeywordStrategyMode.MIN_CPA,
                conv=0.05,
                cpm_set_bid=200,
            ),
        },
    )

    moc_logs = [
        r
        for r in caplog.records
        if r.name
        == "app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync"
        and "v3 campaign MOC stats" in r.getMessage()
    ]
    assert len(moc_logs) == 1
    msg = moc_logs[0].getMessage()
    assert "o_eq_m=1" in msg
    assert "o_eq_c=" in msg

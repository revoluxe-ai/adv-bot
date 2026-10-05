"""Unit: V3 bidder safety cap preload and clamp helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place.clickhouse_manager.dto.bid_position import (
    BidPosition,
)
from app.modules.shop_runner.bidder.bidder_func import (
    BidderV3SafetyCapContext,
    _apply_v3_safety_cap,
    build_v3_safety_cap_by_keyword_setting_original_id,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)
from tests.factories.keyword_pipeline import (
    KeywordStatus,
    KeywordStatusReason,
    make_calculated_keyword,
    make_keyword_state,
)


def _make_keyword(
    *,
    keyword_id: int = 11,
    hard_status: int = 2,
    mode: KeywordStrategyMode = KeywordStrategyMode.MAX_CONVERSION,
) -> object:
    """Собрать минимальный ``CalculatedKeyword`` для V3 bid/profile тестов."""
    return make_calculated_keyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text="kw",
            relevant=True,
            hard_status=hard_status,
            id=keyword_id,
            target_place=2,
            strategy_mode=mode,
        ),
        cluster_stat=make_zero_keyword_stat("kw"),
        state=make_keyword_state(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=True,
        ),
        rating=1.0,
        target_pay_for_order=None,
    )


@pytest.mark.asyncio
async def test_build_v3_safety_cap_context_uses_profile_bid(monkeypatch: pytest.MonkeyPatch) -> None:
    keyword = _make_keyword()
    raw_profiles = {
        "kw": [
            BidPosition(
                keyword="kw",
                position=1,
                bid=300,
                timestamp=datetime.now(tz=timezone.utc),
                _conv_carts_to_views=0.1,
            ),
            BidPosition(
                keyword="kw",
                position=2,
                bid=520,
                timestamp=datetime.now(tz=timezone.utc),
                _conv_carts_to_views=0.2,
            ),
        ]
    }
    monkeypatch.setattr(
        "app.modules.shop_runner.bidder.bidder_func.load_v3_wb_context",
        AsyncMock(
            return_value=(
                SimpleNamespace(
                    fact_pay_for_order=1857.99,
                    search_fact_cpo=1857.99,
                    plan=SimpleNamespace(max_pay_for_order=520.0),
                ),
                raw_profiles,
            )
        ),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.bidder.bidder_func.load_campaign_orders_per_cart_7d",
        AsyncMock(return_value=1.0),
    )

    cap_map = await build_v3_safety_cap_by_keyword_setting_original_id(
        SimpleNamespace(
            adv_id=123,
            adv_setting=SimpleNamespace(),
        ),
        [keyword],
        wb_shop_data_manager=SimpleNamespace(),
    )

    assert cap_map[11].current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert cap_map[11].matrix_state_bid == 520
    assert cap_map[11].overspend is True


@pytest.mark.asyncio
async def test_build_v3_safety_cap_context_returns_empty_when_not_overspend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keyword = _make_keyword()
    raw_profiles = {
        "kw": [
            BidPosition(
                keyword="kw",
                position=2,
                bid=520,
                timestamp=datetime.now(tz=timezone.utc),
                _conv_carts_to_views=0.2,
            )
        ]
    }
    monkeypatch.setattr(
        "app.modules.shop_runner.bidder.bidder_func.load_v3_wb_context",
        AsyncMock(
            return_value=(
                SimpleNamespace(
                    fact_pay_for_order=40.0,
                    search_fact_cpo=40.0,
                    plan=SimpleNamespace(max_pay_for_order=50.0),
                ),
                raw_profiles,
            )
        ),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.bidder.bidder_func.load_campaign_orders_per_cart_7d",
        AsyncMock(return_value=1.0),
    )

    cap_map = await build_v3_safety_cap_by_keyword_setting_original_id(
        SimpleNamespace(
            adv_id=123,
            adv_setting=SimpleNamespace(),
        ),
        [keyword],
        wb_shop_data_manager=SimpleNamespace(),
    )

    assert cap_map == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("keyword", "raw_profiles"),
    [
        (
            _make_keyword(mode=KeywordStrategyMode.OFF),
            {
                "kw": [
                    BidPosition(
                        keyword="kw",
                        position=2,
                        bid=520,
                        timestamp=datetime.now(tz=timezone.utc),
                        _conv_carts_to_views=0.2,
                    )
                ]
            },
        ),
        (
            _make_keyword(),
            {},
        ),
        (
            _make_keyword(),
            {
                "kw": [
                    BidPosition(
                        keyword="kw",
                        position=2,
                        bid=0,
                        timestamp=datetime.now(tz=timezone.utc),
                        _conv_carts_to_views=0.2,
                    )
                ]
            },
        ),
    ],
)
async def test_build_v3_safety_cap_context_skips_when_no_usable_row(
    monkeypatch: pytest.MonkeyPatch,
    keyword: object,
    raw_profiles: dict[str, list[BidPosition]],
) -> None:
    monkeypatch.setattr(
        "app.modules.shop_runner.bidder.bidder_func.load_v3_wb_context",
        AsyncMock(
            return_value=(
                SimpleNamespace(
                    fact_pay_for_order=1857.99,
                    search_fact_cpo=1857.99,
                    plan=SimpleNamespace(max_pay_for_order=520.0),
                ),
                raw_profiles,
            )
        ),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.bidder.bidder_func.load_campaign_orders_per_cart_7d",
        AsyncMock(return_value=1.0),
    )

    cap_map = await build_v3_safety_cap_by_keyword_setting_original_id(
        SimpleNamespace(
            adv_id=123,
            adv_setting=SimpleNamespace(),
        ),
        [keyword],
        wb_shop_data_manager=SimpleNamespace(),
    )

    assert cap_map == {}


def test_apply_v3_safety_cap_clamps_and_skips_on_technical_min() -> None:
    cap_context = BidderV3SafetyCapContext(
        keyword_setting_original_id=11,
        current_mode=KeywordStrategyMode.MAX_CONVERSION,
        current_target_place=2,
        matrix_state_bid=520,
        fact_pay_for_order=1857.99,
        max_pay_for_order=520.0,
        overspend=True,
    )

    capped_cpm, reason = _apply_v3_safety_cap(
        new_cpm=4723,
        technical_min_cpm=10,
        cap_context=cap_context,
    )
    assert capped_cpm == 520
    assert reason is None

    skipped_cpm, reason = _apply_v3_safety_cap(
        new_cpm=4723,
        technical_min_cpm=600,
        cap_context=cap_context,
    )
    assert skipped_cpm is None
    assert reason == "v3_safety_cap_below_technical_min"


@pytest.mark.asyncio
async def test_v3_safety_cap_uses_search_cpo_not_aggregate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec leg-cpo-economics: bidder cap обязан смотреть Search CPO, не common CPO."""
    keyword = _make_keyword()
    raw_profiles = {
        "kw": [
            BidPosition(
                keyword="kw",
                position=2,
                bid=520,
                timestamp=datetime.now(tz=timezone.utc),
                _conv_carts_to_views=0.2,
            )
        ]
    }
    context = SimpleNamespace(adv_id=123, adv_setting=SimpleNamespace())
    monkeypatch.setattr(
        "app.modules.shop_runner.bidder.bidder_func.load_campaign_orders_per_cart_7d",
        AsyncMock(return_value=1.0),
    )
    load_context = AsyncMock(
        return_value=(
            SimpleNamespace(
                fact_pay_for_order=999.0,
                search_fact_cpo=40.0,
                plan=SimpleNamespace(max_pay_for_order=50.0),
            ),
            raw_profiles,
        )
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.bidder.bidder_func.load_v3_wb_context",
        load_context,
    )

    good_search = await build_v3_safety_cap_by_keyword_setting_original_id(
        context,
        [keyword],
        wb_shop_data_manager=SimpleNamespace(),
    )
    assert good_search == {}

    load_context.return_value = (
        SimpleNamespace(
            fact_pay_for_order=1.0,
            search_fact_cpo=100.0,
            plan=SimpleNamespace(max_pay_for_order=50.0),
        ),
        raw_profiles,
    )
    bad_search = await build_v3_safety_cap_by_keyword_setting_original_id(
        context,
        [keyword],
        wb_shop_data_manager=SimpleNamespace(),
    )
    assert bad_search[11].overspend is True
    assert bad_search[11].fact_pay_for_order == pytest.approx(100.0)

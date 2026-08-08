"""Unit: post-apply intent hook (pause НЕ вызывается в том же шаге, что OFF)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.apply_hook import (
    maybe_set_empty_keywords_pause_intent,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus


def _kw(mode: KeywordStrategyMode) -> MagicMock:
    kw = MagicMock()
    kw.strategy_mode = mode
    return kw


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_hook_sets_intent_after_last_force_off(
    fake_redis: FakeRedis,
) -> None:
    """Characterization→spec: после OFF последнего ключа — intent, не pause."""
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        set_ok = await maybe_set_empty_keywords_pause_intent(
            adv_id=42,
            bot_active=True,
            keywords=[_kw(KeywordStrategyMode.OFF)],
            post_gate_actions=[
                V3Action(
                    action=V3ActionType.FORCE_OFF,
                    keyword_setting_id=1,
                    reason="t",
                )
            ],
            campaign_status=WBAdvActiveStatus.STARTED,
        )
        assert set_ok is True
        assert await EmptyKeywordsPauseIntentManager().peek_intent(42) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_hook_no_intent_when_keys_remain(
    fake_redis: FakeRedis,
) -> None:
    """Paired: остался активный ключ → intent не ставим."""
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        set_ok = await maybe_set_empty_keywords_pause_intent(
            adv_id=43,
            bot_active=True,
            keywords=[
                _kw(KeywordStrategyMode.OFF),
                _kw(KeywordStrategyMode.OPTIMUM),
            ],
            post_gate_actions=[
                V3Action(
                    action=V3ActionType.FORCE_OFF,
                    keyword_setting_id=1,
                    reason="t",
                )
            ],
            campaign_status=WBAdvActiveStatus.STARTED,
        )
        assert set_ok is False
        assert await EmptyKeywordsPauseIntentManager().peek_intent(43) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_manager_sets_intent_without_wb_pause(
    fake_redis: FakeRedis,
) -> None:
    """Ordering: ApplyManager после OFF ставит intent; WB pause adapters не зовутся."""
    from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
        RedisCalculatedKeywordsCacheManager,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager import (
        ApplyManager,
        V3ApplyInput,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
        CampaignMode,
    )

    complex_adv = MagicMock()
    complex_adv.adv_id = 77
    complex_adv.bot_active = True
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.auto_adv_active_status_str = WBAdvActiveStatus.STARTED
    complex_adv.search_adv_active_status_str = WBAdvActiveStatus.STARTED

    ledger = MagicMock()
    ledger.apply_in_memory = MagicMock()
    ledger.flush_to_db = AsyncMock(return_value=True)
    # Пустой набор после OFF (без MagicMock в Redis cache serialize path).
    ledger.keywords = []

    tick_input = MagicMock(
        plan=MagicMock(),
        fact=MagicMock(),
        shelf_click_mode=MagicMock(),
        aggressiveness=MagicMock(),
        calibration_direct=None,
        max_effective_steps=2,
        campaign_orders_per_cart_7d=None,
    )
    tick_data = MagicMock(
        complex_adv=complex_adv,
        ledger=ledger,
        tick_input=tick_input,
        contexts=[],
        ladder_inputs=None,
        campaign_mode=CampaignMode.NORMAL,
        plan_fact_change=None,
        views_cache=None,
        calibration_step_cache=None,
        views_resolve_succeeded=False,
        current_views=None,
        sales_state=MagicMock(),
        raw_profiles={},
        all_contexts=[],
    )
    force_off = V3Action(
        action=V3ActionType.FORCE_OFF,
        keyword_setting_id=9,
        reason="last",
    )
    pause_spy = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[force_off],
        ),
        patch.object(
            ApplyManager,
            "sync_target_places_if_needed",
            new=AsyncMock(return_value=False),
        ),
        patch.object(RedisCalculatedKeywordsCacheManager, "_client", fake_redis),
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            "app.core.mp.wb.api.managers.WBModifier.pause_auto_campaign",
            new=pause_spy,
        ),
        patch(
            "app.core.mp.wb.api.managers.WBModifier.pause_auction_campaign",
            new=AsyncMock(),
        ) as pause_search_spy,
    ):
        await ApplyManager().apply(
            V3ApplyInput(
                tick_data=tick_data,
                update_context=None,
                pipeline_result=None,
                calibration_executed=False,
                sync_force_zero=False,
            )
        )
        assert await EmptyKeywordsPauseIntentManager().peek_intent(77) is True
        pause_spy.assert_not_awaited()
        pause_search_spy.assert_not_awaited()

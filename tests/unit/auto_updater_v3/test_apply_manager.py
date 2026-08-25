"""Unit: ApplyManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
    _CALCULATED_KEYWORDS_EMPTY_FIELD,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager import (
    ApplyManager,
    V3ApplyInput,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause import (
    EmptyKeywordsPauseIntentManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    CampaignMode,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_runs_post_gate_flush_and_redis(fake_redis: FakeRedis) -> None:
    """Post-gate → flush → plan/fact/views Redis (через fakeredis, без живого Redis)."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 5
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False

    ledger = MagicMock()
    ledger.apply_in_memory = MagicMock()
    ledger.flush_to_db = AsyncMock(return_value=True)
    ledger.keywords = []

    plan = MagicMock()
    fact = MagicMock()
    tick_input = MagicMock(
        plan=plan,
        fact=fact,
        shelf_click_mode=MagicMock(),
        aggressiveness=MagicMock(),
        calibration_direct=MagicMock(),
        max_effective_steps=2,
    )
    plan_fact_change = MagicMock()
    plan_fact_change.set_new_plan_fact = AsyncMock()
    views_cache = MagicMock()
    views_cache.set_views = AsyncMock()
    calibration_cache = MagicMock()
    calibration_cache.set_state = AsyncMock()

    tick_data = MagicMock(
        complex_adv=complex_adv,
        ledger=ledger,
        tick_input=tick_input,
        contexts=[],
        ladder_inputs=None,
        campaign_mode=CampaignMode.NORMAL,
        plan_fact_change=plan_fact_change,
        views_cache=views_cache,
        calibration_step_cache=calibration_cache,
        views_resolve_succeeded=True,
        current_views=500,
        sales_state=MagicMock(name="OPTIMAL"),
        raw_profiles={},
        all_contexts=[],
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch.object(
            ApplyManager,
            "sync_target_places_if_needed",
            new=AsyncMock(return_value=False),
        ),
        # Apply also HEXISTS via EmptyKeywordsPauseIntentManager (not only keywords cache).
        patch.object(RedisCalculatedKeywordsCacheManager, "_client", fake_redis),
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
    ):
        result = await ApplyManager().apply(
            V3ApplyInput(
                tick_data=tick_data,
                update_context=None,
                pipeline_result=None,
                calibration_executed=True,
                sync_force_zero=False,
            )
        )

    ledger.apply_in_memory.assert_called_once()
    ledger.flush_to_db.assert_awaited_once()
    plan_fact_change.set_new_plan_fact.assert_awaited_once()
    views_cache.set_views.assert_awaited_once_with(500)
    calibration_cache.set_state.assert_awaited_once()
    assert result.flushed_to_db is True
    assert result.plan_fact_cached is True
    redis_key = "calculated_keywords:5"
    cached = await fake_redis.hgetall(redis_key)
    assert cached.get(_CALCULATED_KEYWORDS_EMPTY_FIELD) == "1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_resets_calibration_cache_when_preamble_requires_reset() -> None:
    """Skip ``resolve_calibration`` persists zero steps for the next tick."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 6
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False

    ledger = MagicMock()
    ledger.apply_in_memory = MagicMock()
    ledger.flush_to_db = AsyncMock(return_value=False)

    tick_input = MagicMock(
        plan=MagicMock(),
        fact=MagicMock(),
        shelf_click_mode=MagicMock(),
        aggressiveness=MagicMock(),
        calibration_direct=CalibrationDirect.LOOSEN,
        max_effective_steps=5,
    )
    calibration_cache = MagicMock()
    calibration_cache.set_state = AsyncMock()
    pipeline_result = MagicMock(calibration_reset_required=True)
    tick_data = MagicMock(
        complex_adv=complex_adv,
        ledger=ledger,
        tick_input=tick_input,
        contexts=[],
        ladder_inputs=None,
        campaign_mode=CampaignMode.NORMAL,
        plan_fact_change=None,
        views_cache=None,
        calibration_step_cache=calibration_cache,
        views_resolve_succeeded=False,
        current_views=None,
        sales_state=MagicMock(name="OPTIMAL"),
        raw_profiles={},
        all_contexts=[],
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch.object(
            ApplyManager,
            "sync_target_places_if_needed",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await ApplyManager().apply(
            V3ApplyInput(
                tick_data=tick_data,
                update_context=None,
                pipeline_result=pipeline_result,
                calibration_executed=False,
                sync_force_zero=False,
            )
        )

    calibration_cache.set_state.assert_awaited_once()
    saved = calibration_cache.set_state.await_args[0][0]
    assert saved.effective_steps == 0
    assert saved.direct == CalibrationDirect.LOOSEN
    assert result.calibration_cached is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_persists_applied_calibration_steps_not_cap() -> None:
    """Redis stores the реально применённый calibration step, not the resolver cap."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 7
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False

    ledger = MagicMock()
    ledger.apply_in_memory = MagicMock()
    ledger.flush_to_db = AsyncMock(return_value=False)

    tick_input = MagicMock(
        plan=MagicMock(),
        fact=MagicMock(),
        shelf_click_mode=MagicMock(),
        aggressiveness=MagicMock(),
        calibration_direct=CalibrationDirect.TIGHTEN,
        max_effective_steps=8,
        calibration_phase_extra={"applied_steps": 3},
    )
    calibration_cache = MagicMock()
    calibration_cache.set_state = AsyncMock()
    pipeline_result = MagicMock(
        update_context=MagicMock(
            adv_state=MagicMock(
                calibration_phase_extra={"applied_steps": 3},
            )
        ),
        calibration_reset_required=False,
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
        calibration_step_cache=calibration_cache,
        views_resolve_succeeded=False,
        current_views=None,
        sales_state=MagicMock(name="OPTIMAL"),
        raw_profiles={},
        all_contexts=[],
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch.object(
            ApplyManager,
            "sync_target_places_if_needed",
            new=AsyncMock(return_value=False),
        ),
    ):
        await ApplyManager().apply(
            V3ApplyInput(
                tick_data=tick_data,
                update_context=None,
                pipeline_result=pipeline_result,
                calibration_executed=True,
                sync_force_zero=False,
            )
        )

    calibration_cache.set_state.assert_awaited_once()
    saved = calibration_cache.set_state.await_args[0][0]
    assert saved.effective_steps == 3
    assert saved.direct == CalibrationDirect.TIGHTEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_persists_zero_applied_calibration_steps_as_zero() -> None:
    """Zero calibration progress must stay zero in Redis and vanish on read."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 8
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False

    ledger = MagicMock()
    ledger.apply_in_memory = MagicMock()
    ledger.flush_to_db = AsyncMock(return_value=False)

    tick_input = MagicMock(
        plan=MagicMock(),
        fact=MagicMock(),
        shelf_click_mode=MagicMock(),
        aggressiveness=MagicMock(),
        calibration_direct=CalibrationDirect.LOOSEN,
        max_effective_steps=5,
        calibration_phase_extra={"applied_steps": 0},
    )
    calibration_cache = MagicMock()
    calibration_cache.set_state = AsyncMock()
    pipeline_result = MagicMock(
        update_context=MagicMock(
            adv_state=MagicMock(
                calibration_phase_extra={"applied_steps": 0},
            )
        ),
        calibration_reset_required=False,
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
        calibration_step_cache=calibration_cache,
        views_resolve_succeeded=False,
        current_views=None,
        sales_state=MagicMock(name="OPTIMAL"),
        raw_profiles={},
        all_contexts=[],
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch.object(
            ApplyManager,
            "sync_target_places_if_needed",
            new=AsyncMock(return_value=False),
        ),
    ):
        await ApplyManager().apply(
            V3ApplyInput(
                tick_data=tick_data,
                update_context=None,
                pipeline_result=pipeline_result,
                calibration_executed=True,
                sync_force_zero=False,
            )
        )

    calibration_cache.set_state.assert_awaited_once()
    saved = calibration_cache.set_state.await_args[0][0]
    assert saved.effective_steps == 0
    assert saved.direct == CalibrationDirect.LOOSEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_target_places_skips_when_already_synced() -> None:
    """``already_synced=True`` — повторный sync не вызывается."""
    tick_data = MagicMock(
        campaign_mode=CampaignMode.NORMAL,
        dto=MagicMock(),
        complex_adv=MagicMock(individual_keywords_target_place_mode=True),
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.sync_keyword_target_places_v3",
        new=AsyncMock(),
    ) as sync_mock:
        synced = await ApplyManager().sync_target_places_if_needed(
            tick_data,
            sync_force_zero=False,
            already_synced=True,
        )
    sync_mock.assert_not_awaited()
    assert synced is True

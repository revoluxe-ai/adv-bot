"""Персист финального состояния V3: post-gate, flush, Redis, target_place."""

from __future__ import annotations

import logging

from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    resolve_shelf_click_mode_from_adv,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.dto import (
    V3ApplyInput,
    V3ApplyResult,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
    CalibrationStepState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.dto import (
    TickData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.resolve_threshold import (
    compute_resolve_cost_threshold,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    select_v3_post_gate_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.target_place_sync import (
    sync_keyword_target_places_v3,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    is_campaign_full_stop,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO

logger = logging.getLogger(__name__)


def _calculated_keywords_by_text(
    keywords: list[CalculatedKeyword],
) -> dict[str, CalculatedKeyword]:
    """Индекс ключей для ``sync_keyword_target_places_v3``."""
    return {kw.text.lower(): kw for kw in keywords}


async def _safe_sync_target_places_v3(
    complex_adv: ComplexAdv,
    dto: WBAdvDTO,
    raw_profiles: dict[str, list[BidPosition]],
    *,
    keywords: list[CalculatedKeyword],
    force_all_target_place_zero: bool = False,
    target_place_fallback_zero_by_keyword_id: dict[int, bool] | None = None,
) -> None:
    """Best-effort sync ``target_place`` без подмены ошибки из ``try`` (PEP 409)."""
    try:
        await sync_keyword_target_places_v3(
            dto,
            raw_profiles,
            calculated_by_text=_calculated_keywords_by_text(keywords),
            force_all_target_place_zero=force_all_target_place_zero,
            target_place_fallback_zero_by_keyword_id=(
                target_place_fallback_zero_by_keyword_id
            ),
        )
    except Exception:  # type: ignore[misc]
        logger.error(
            "[adv_id=%s] v3: target_place sync failed "
            "(original try exception preserved, not re-raised)",
            complex_adv.adv_id,
            exc_info=True,
        )


class ApplyManager:
    """Post-gate in-memory → flush PG → Redis gates → target_place."""

    async def apply(self, inp: V3ApplyInput) -> V3ApplyResult:
        """Применить post-gate и записать durable side effects."""
        tick = inp.tick_data
        complex_adv = tick.complex_adv
        ledger = tick.ledger
        tick_input = tick.tick_input
        contexts = tick.contexts
        ladder_inputs = tick.ladder_inputs
        plan = tick_input.plan if tick_input is not None else None
        fact = tick_input.fact if tick_input is not None else None
        policy = (
            SelectionPolicy.from_aggressiveness(
                click_mode=tick_input.shelf_click_mode,
                aggressiveness=tick_input.aggressiveness,
            )
            if tick_input is not None
            else None
        )

        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
            build_keyword_v3_contexts,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.ledger_sync import (
            sync_update_context_to_ledger,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
            filter_operable_v3_contexts,
        )

        if inp.update_context is not None:
            sync_update_context_to_ledger(inp.update_context, ledger)
            all_contexts = build_keyword_v3_contexts(
                ledger.keywords,
                tick.raw_profiles,
            )
            contexts = filter_operable_v3_contexts(all_contexts)
            tick.contexts = contexts
            tick.all_contexts = all_contexts
            if (
                tick_input is not None
                and tick_input.campaign_orders_per_cart_7d is not None
            ):
                from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
                    build_target_place_fallback_zero_by_keyword_id,
                )

                tick.sync_fallback_by_id = build_target_place_fallback_zero_by_keyword_id(
                    all_contexts,
                    campaign_orders_per_cart_7d=tick_input.campaign_orders_per_cart_7d,
                )

        post_gate_actions = select_v3_post_gate_actions(
            contexts=contexts,
            shelf_promotion_active=complex_adv.shelf_promotion_active,
            shelf_click_mode=resolve_shelf_click_mode_from_adv(complex_adv)
            if complex_adv.shelf_promotion_active
            else None,
            ladder_inputs=ladder_inputs,
            policy=policy,
        )
        _ = ledger.apply_in_memory(post_gate_actions)
        if (
            post_gate_actions
            and tick_input is not None
            and tick_input.campaign_orders_per_cart_7d is not None
        ):
            from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
                build_target_place_fallback_zero_by_keyword_id,
            )

            all_contexts = build_keyword_v3_contexts(
                ledger.keywords,
                tick.raw_profiles,
            )
            tick.all_contexts = all_contexts
            tick.contexts = filter_operable_v3_contexts(all_contexts)
            tick.sync_fallback_by_id = build_target_place_fallback_zero_by_keyword_id(
                all_contexts,
                campaign_orders_per_cart_7d=tick_input.campaign_orders_per_cart_7d,
            )

        plan_fact_cached = False
        if tick.plan_fact_change is not None and tick.views_resolve_succeeded:
            assert plan is not None and fact is not None
            await tick.plan_fact_change.set_new_plan_fact(plan, fact)
            plan_fact_cached = True

        views_cached = False
        if tick.views_cache is not None and tick.current_views is not None:
            await tick.views_cache.set_views(tick.current_views)
            views_cached = True

        calibration_cached = False
        if (
            tick.calibration_step_cache is not None
            and tick_input is not None
        ):
            calibration_reset_required = (
                inp.pipeline_result is not None
                and inp.pipeline_result.calibration_reset_required is True
            )
            if calibration_reset_required:
                await tick.calibration_step_cache.set_state(
                    CalibrationStepState(
                        effective_steps=0,
                        direct=(
                            tick_input.calibration_direct
                            or CalibrationDirect.TIGHTEN
                        ),
                    )
                )
                calibration_cached = True
            elif tick_input.calibration_direct is not None and inp.calibration_executed:
                applied_steps_raw: object | None = None
                if inp.pipeline_result is not None:
                    applied_steps_raw = (
                        inp.pipeline_result.update_context.adv_state.calibration_phase_extra.get(
                            "applied_steps"
                        )
                    )
                if not isinstance(applied_steps_raw, int):
                    applied_steps_raw = tick_input.calibration_phase_extra.get(
                        "applied_steps"
                    )
                if isinstance(applied_steps_raw, int):
                    applied_steps = int(applied_steps_raw)
                else:
                    applied_steps = int(tick_input.max_effective_steps)
                await tick.calibration_step_cache.set_state(
                    CalibrationStepState(
                        effective_steps=max(0, applied_steps),
                        direct=tick_input.calibration_direct,
                    )
                )
                calibration_cached = True

        self._log_v3_cycle(tick, inp, post_gate_actions)

        flushed_to_db = False
        if not is_campaign_full_stop(tick.campaign_mode):
            flushed_to_db = await ledger.flush_to_db(complex_adv)
            if flushed_to_db:
                logger.info(
                    "[adv_id=%s] v3: netto flush committed",
                    complex_adv.adv_id,
                )
                from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
                    RedisCalculatedKeywordsCacheManager,
                )

                await RedisCalculatedKeywordsCacheManager().set_calculated_keywords(
                    ledger.keywords,
                    int(complex_adv.adv_id),
                )
            # Spec pause-on-empty-keywords: OFF = текущий шаг; intent → pause следующим.
            # Не вызываем WB pause здесь (ADL empty-keywords-pause-write-path).
            from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause import (
                maybe_set_empty_keywords_pause_intent,
            )

            # INC-PAUSE-02: recheck intent после Search start — статус Search-ноги.
            await maybe_set_empty_keywords_pause_intent(
                adv_id=int(complex_adv.adv_id),
                bot_active=bool(complex_adv.bot_active),
                keywords=ledger.keywords,
                post_gate_actions=post_gate_actions,
                campaign_status=complex_adv.search_adv_active_status_str,
            )

        return V3ApplyResult(
            post_gate_actions=post_gate_actions,
            flushed_to_db=flushed_to_db,
            plan_fact_cached=plan_fact_cached,
            views_cached=views_cached,
            calibration_cached=calibration_cached,
        )

    async def sync_target_places_if_needed(
        self,
        tick_data: TickData,
        *,
        sync_force_zero: bool,
        already_synced: bool = False,
    ) -> bool:
        """Best-effort ``target_place`` sync.

        Параметр ``already_synced`` оставлен как защита от повторного вызова
        helper-а в тестах и в редких внешних сценариях. В основном потоке sync
        теперь вызывается один раз из ``finally`` orchestrator-а.
        """
        if already_synced or is_campaign_full_stop(tick_data.campaign_mode):
            return already_synced
        if (
            tick_data.dto is not None
            and tick_data.complex_adv.individual_keywords_target_place_mode
        ):
            await _safe_sync_target_places_v3(
                tick_data.complex_adv,
                tick_data.dto,
                tick_data.raw_profiles,
                keywords=tick_data.ledger.keywords,
                force_all_target_place_zero=sync_force_zero,
                target_place_fallback_zero_by_keyword_id=tick_data.sync_fallback_by_id,
            )
            return True
        return False

    @staticmethod
    def _log_v3_cycle(
        tick: TickData,
        inp: V3ApplyInput,
        post_gate_actions: list[V3Action],
    ) -> None:
        """Лог ``v3_cycle`` с preamble stats и post-gate counts."""
        tick_input = tick.tick_input
        plan = tick_input.plan if tick_input is not None else None
        fact = tick_input.fact if tick_input is not None else None
        pipeline = inp.pipeline_result
        up_count = sum(1 for a in post_gate_actions if a.action.value == "UP")
        down_count = sum(1 for a in post_gate_actions if a.action.value == "DOWN")
        force_off_count = sum(
            1 for a in post_gate_actions if a.action.value == "FORCE_OFF"
        )
        logger.info(
            "[adv_id=%s] v3_cycle state=%s resolve=%s fact_cpa=%s "
            "validate=%s validate_not_full=%s passing_up=%s shelf=%s "
            "realloc=%s enable=%s calibration=%s guard=%s "
            "post_gate up=%s down=%s off=%s",
            tick.complex_adv.adv_id,
            tick.sales_state.name if tick.sales_state else "None",
            compute_resolve_cost_threshold(plan, fact) if plan and fact else None,
            fact.pay_for_order if fact else None,
            pipeline.validate_count if pipeline else 0,
            pipeline.validate_not_full_count if pipeline else 0,
            pipeline.passing_up_count if pipeline else 0,
            pipeline.shelf_count if pipeline else 0,
            pipeline.realloc_count if pipeline else 0,
            pipeline.enable_count if pipeline else 0,
            pipeline.calibration_count if pipeline else 0,
            pipeline.guard_count if pipeline else 0,
            up_count,
            down_count,
            force_off_count,
        )

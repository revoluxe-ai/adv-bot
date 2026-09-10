"""Сборка ``V3TickData``: WB/CH, plan/fact, operable contexts, ``UpdateContextInput``."""

from __future__ import annotations

import logging

from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.plan_fact_change_redis_caches import (
    ChangePlanFact,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    detect_campaign_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
    resolve_shelf_click_mode_from_adv,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    classify_calibration_direct,
    resolve_effective_calibration_steps,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_state_cache import (
    V3CalibrationStepState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_views_cache import (
    ChangePlanFactViews,
    resolve_complex_adv_total_views,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.dto import (
    TickData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.loaders import (
    load_v3_wb_context,
    resolve_v3_fact_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    build_target_place_fallback_zero_by_keyword_id,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContextInput,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.resolve_threshold import (
    compute_resolve_cost_threshold,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
    V3TickKeywordLedger,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    CampaignMode,
    resolve_campaign_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    filter_operable_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3TickReportCollector,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

logger = logging.getLogger(__name__)


class DataUpdateManager:
    """Загрузка всех данных тика V3 для ContextManager и pipeline."""

    async def load(
        self,
        complex_adv: ComplexAdv,
        keywords: list[CalculatedKeyword],
        *,
        wb_shop_data_manager: WBShopDataManager,
        max_last_period: int = 2,
        tick_report: V3TickReportCollector,
    ) -> TickData:
        """Собрать ``V3TickData``: keywords, dto, plan/fact, contexts, NORMAL gates.

        Метод всегда возвращает заполненный ``TickData``. Ранний выход здесь не
        используется: даже если часть внешних данных недоступна, загрузчик
        собирает максимально полный снимок тика и оставляет решение о том, что
        делать дальше, уровню orchestrator/pipeline.
        """
        adv = complex_adv.adv_setting
        ledger = V3TickKeywordLedger.from_keywords(keywords)
        dto, raw_profiles = await load_v3_wb_context(
            complex_adv,
            wb_shop_data_manager=wb_shop_data_manager,
        )

        all_contexts = build_keyword_v3_contexts(ledger.keywords, raw_profiles)
        contexts = all_contexts
        plan = AdvSettingAutoUpdater.get_plan_data(adv)
        from decimal import Decimal

        try:
            promo_fraction = Decimal(
                str(getattr(complex_adv, "promo_fraction", Decimal("0")) or "0")
            )
        except Exception:
            promo_fraction = Decimal("0")
        if (
            getattr(adv, "raise_plan_on_promobonuses", False) is True
            and promo_fraction > 0
        ):
            effective_plan = PlanFactProvider.get_effective_plan_data(
                adv, complex_adv=complex_adv
            )
            if effective_plan is not None:
                plan = effective_plan
        sales_state = None
        fact = None
        fact_source: str | None = None
        campaign_mode = CampaignMode.NOT_READY
        campaign_orders_per_cart_7d: float | None = None
        sync_fallback_by_id: dict[int, bool] | None = None
        tick_report_ready = False

        tick_input: UpdateContextInput | None = None
        plan_fact_change: ChangePlanFact | None = None
        views_cache: ChangePlanFactViews | None = None
        calibration_step_cache: V3CalibrationStepState | None = None
        plan_fact_equal = False
        views_equal = False
        views_resolve_succeeded = False
        current_views: int | None = None
        current_calibration_direct = None
        effective_calibration_steps = 1
        calibration_prev_effective_steps: int | None = None

        if plan is None:
            logger.debug("[adv_id=%s] v3: no plan, skip ladder", complex_adv.adv_id)
        else:
            updater = AdvSettingAutoUpdater(adv, max_last_period)
            fact, fact_source = await resolve_v3_fact_data(
                dto=dto,
                updater=updater,
                keywords=ledger.keywords,
                max_last_period=max_last_period,
            )

            sales_state = detect_campaign_state(plan, fact)
            campaign_mode = resolve_campaign_mode(sales_state)
            logger.info(
                "[adv_id=%s] v3: campaign_mode=%s state=%s fact_source=%s",
                complex_adv.adv_id,
                campaign_mode.value,
                sales_state.name if sales_state is not None else "None",
                fact_source,
            )

        if dto is not None and plan is not None:
            from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
                load_campaign_orders_per_cart_7d,
            )

            campaign_orders_per_cart_7d = await load_campaign_orders_per_cart_7d(adv)
            sync_fallback_by_id = build_target_place_fallback_zero_by_keyword_id(
                all_contexts,
                campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
            )

        if (
            dto is not None
            and plan is not None
            and campaign_mode in (CampaignMode.NO_DATA, CampaignMode.NORMAL)
        ):
            operable_before = len(filter_operable_v3_contexts(all_contexts))
            contexts = filter_operable_v3_contexts(all_contexts)
            tick_report.record_filter(
                total=len(all_contexts),
                operable=operable_before,
            )
            tick_report_ready = True

        if campaign_mode == CampaignMode.NORMAL and dto is not None and plan is not None:
            assert fact is not None
            shelf_active = complex_adv.shelf_promotion_active
            shelf_click_mode = (
                resolve_shelf_click_mode_from_adv(complex_adv) if shelf_active else None
            )
            aggr = normalize_v3_rollout_aggressiveness(
                complex_adv.v3_rollout_aggressiveness
            )
            click_mode = shelf_click_mode or ShelfClickMode.ORGANIC_DOMINANT
            resolve = compute_resolve_cost_threshold(plan, fact)
            plan_fact_change = ChangePlanFact(adv)
            plan_fact_equal = await plan_fact_change.check_equal_in_cache(plan, fact)
            views_cache = ChangePlanFactViews(adv)
            try:
                current_views = await resolve_complex_adv_total_views(
                    complex_adv,
                    max_last_period=max_last_period,
                )
                cached_views = await views_cache.get_cached_views()
                views_equal = cached_views is not None and cached_views == current_views
                views_resolve_succeeded = True
            except Exception:
                logger.warning(
                    "[adv_id=%s] v3: views resolve failed, "
                    "calibration/enable gated off; plan/fact snapshot deferred",
                    complex_adv.adv_id,
                    exc_info=True,
                )
                views_equal = True
                current_views = None
                views_resolve_succeeded = False
            calibration_step_cache = V3CalibrationStepState(adv)
            current_calibration_direct = classify_calibration_direct(
                fact.pay_for_order,
                resolve,
            )
            calibration_prev_state = await calibration_step_cache.get_state()
            calibration_prev_effective_steps = (
                calibration_prev_state.effective_steps
                if calibration_prev_state is not None
                else None
            )
            effective_calibration_steps = resolve_effective_calibration_steps(
                complex_adv.keyword_calibration_max_step,
                prev=calibration_prev_state,
                current_direct=current_calibration_direct,
            )
            logger.debug(
                "[adv_id=%s] v3 calibration steps: effective=%s base_max=%s "
                "direct=%s prev_direct=%s",
                complex_adv.adv_id,
                effective_calibration_steps,
                complex_adv.keyword_calibration_max_step,
                current_calibration_direct.value,
                calibration_prev_state.direct.value
                if calibration_prev_state is not None
                else None,
            )
            calibration_phase_extra: dict[str, object] = {
                "calibration_direct": current_calibration_direct.value,
                "effective_steps": effective_calibration_steps,
                "prev_effective_steps": calibration_prev_effective_steps,
            }
            from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
                load_rec_orders_per_view_for_v3,
            )

            rec_orders_per_view = await load_rec_orders_per_view_for_v3(
                adv,
                rec_system_promotion_mode_active=complex_adv.rec_system_promotion_mode_active,
                complex_adv=complex_adv,
            )
            tick_input = UpdateContextInput(
                keywords=[ctx.keyword for ctx in contexts],
                plan=plan,
                fact=fact,
                raw_profiles=raw_profiles,
                campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                rec_orders_per_view=rec_orders_per_view,
                shelf_active=shelf_active,
                shelf_click_mode=click_mode,
                aggressiveness=aggr,
                plan_fact_equal=plan_fact_equal,
                views_equal=views_equal,
                calibration_direct=current_calibration_direct,
                max_effective_steps=effective_calibration_steps,
                configured_keyword_calibration_max_step=int(
                    complex_adv.keyword_calibration_max_step
                ),
                calibration_phase_extra=calibration_phase_extra,
                v3_substitute_fact_cpo_for_max=bool(adv.substitute_fact_cpo_for_max),
            )
        elif (
            campaign_mode == CampaignMode.NO_DATA
            and plan is not None
            and fact is not None
        ):
            tick_input = UpdateContextInput(
                keywords=[ctx.keyword for ctx in contexts],
                plan=plan,
                fact=fact,
                raw_profiles=raw_profiles,
                campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
                v3_substitute_fact_cpo_for_max=bool(adv.substitute_fact_cpo_for_max),
            )

        return TickData(
            complex_adv=complex_adv,
            ledger=ledger,
            dto=dto,
            raw_profiles=raw_profiles,
            campaign_mode=campaign_mode,
            sales_state=sales_state,
            contexts=contexts,
            all_contexts=all_contexts,
            tick_input=tick_input,
            sync_fallback_by_id=sync_fallback_by_id,
            plan_fact_change=plan_fact_change,
            views_cache=views_cache,
            calibration_step_cache=calibration_step_cache,
            views_resolve_succeeded=views_resolve_succeeded,
            current_views=current_views,
            tick_report_ready=tick_report_ready,
            fact_source=fact_source,
        )

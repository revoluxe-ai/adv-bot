"""Сборка fresh decision snapshot для Auto Shelf Bid Control (вне manager)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlSettings,
    AutoShelfBidControlState,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_recommendation_read_service import (
    AutoShelfBidRecommendationReadService,
)
from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.settings import settings

from .dto.decision_snapshot_dto import (
    AutoShelfBidControlDecisionSnapshot,
    cast_rec_dict,
    resolve_bid_sync_status,
    resolve_expected_bid_minor,
    snapshot_can_count_progress,
    snapshot_from_state_fallback,
)
from .dto.optimization_metric import OptimizationMetric, resolve_optimization_metric
from .qualified_tested_bids import (
    INSUFFICIENT_QUALIFIED_TESTED_BIDS_EXPLANATION,
    build_cycle_metric_rec_recommendation,
    collect_qualified_tested_bid_minors,
    count_qualified_tested_bids,
    filter_rec_recommendation_to_qualified_bids,
    has_sufficient_qualified_tested_bids,
    rank_qualified_tested_bid_stats,
    resolve_main_bid_from_qualified_ranking,
)
from .rec_bid_plan_context import build_rec_bid_plan_context

logger = logging.getLogger(__name__)


def _resolve_cycle_metric_for_snapshot(
    complex_adv: ComplexAdv,
) -> OptimizationMetric:
    """Resolve ranking metric for snapshot-qualified bids.

    Explicit Auto Shelf strategies must stay explicit even when the
    day-analytics strategy resolver cannot return a bid. In particular, a
    fallback in `CTR` mode must keep using CTR-ranked qualified bids, and a
    fallback in `CPC` mode must keep using CPC-ranked qualified bids, instead
    of silently switching back to the legacy dynamic metric chosen from
    `fact_cpo/resolve_cpo`.
    """
    strategy = complex_adv.auto_shelf_bid_control_strategy
    if strategy == AutoShelfBidControlStrategy.CTR:
        return OptimizationMetric.CTR
    if strategy in {
        AutoShelfBidControlStrategy.CPC,
        AutoShelfBidControlStrategy.CYCLE_METRIC,
    }:
        return OptimizationMetric.CPC
    return resolve_optimization_metric(
        complex_adv.fact_pay_for_order,
        complex_adv.resolve_cpo,
    )


async def fetch_plan_distance_rec_result(
    manager: Any,
    complex_adv: ComplexAdv,
) -> dict[str, object] | None:
    """Загрузить rec-bid recommendation для PLAN_DISTANCE без state fallback."""
    try:
        rec_repository = manager._analytics
        now = manager._now()
        rec_date_to = now
        rec_date_from = rec_date_to - timedelta(days=7)
        ctr_by_bid = await rec_repository.fetch_rec_bid_ctr_by_bid_for_nmid(
            nmid=complex_adv.main_nmid,
            mode=None,
            date_from=rec_date_from,
            date_to=rec_date_to,
        )
        if not ctr_by_bid:
            return None
        click_to_order_cr_7d = (
            await rec_repository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(
                nmid=complex_adv.main_nmid,
                mode=None,
                date_from=rec_date_from,
                date_to=rec_date_to,
            )
        )
        plan_fact_summary = await PlanFactReader().get_latest_plan_fact(
            complex_adv.auto_adv_id
        )
        fact_predict_orders = (
            plan_fact_summary.fact_predict_orders if plan_fact_summary else None
        )
        overlay = PlanFactProvider.get_effective_promo_plan(
            complex_adv.adv_setting, complex_adv=complex_adv
        )
        plan_overlay = overlay.plan
        plan_context = build_rec_bid_plan_context(
            sales_plan=float(complex_adv.adv_setting.plan_for_sales_for_day or 0.0),
            current_fact_sales=float(fact_predict_orders or 0.0),
            current_sales_forecast=float(fact_predict_orders or 0.0),
            target_price_for_order=(
                plan_overlay.target_pay_for_order
                if plan_overlay is not None
                else complex_adv.adv_setting.target_price_for_order
            ),
            max_price_for_order=(
                plan_overlay.max_pay_for_order
                if plan_overlay is not None
                else complex_adv.adv_setting.max_price_for_order
            ),
            max_order_cost=complex_adv.original_max_cpo,
            click_to_order_cr_7d=click_to_order_cr_7d,
        )
        rec_service = AutoShelfBidRecommendationReadService(rec_repository)
        return await rec_service.get_rec_bid_recommendations(
            nmid=complex_adv.main_nmid,
            mode=None,
            date_from=rec_date_from,
            date_to=rec_date_to,
            plan_context=plan_context,
            ctr_by_bid=ctr_by_bid,
        )
    except Exception:
        logger.warning(
            "auto_shelf_bid_control_plan_distance_unavailable auto_adv_id=%s nmid=%s",
            complex_adv.auto_adv_id,
            complex_adv.main_nmid,
            exc_info=True,
        )
        return None


async def build_decision_snapshot(
    manager: Any,
    complex_adv: ComplexAdv,
    *,
    settings_obj: AutoShelfBidControlSettings,
    state: AutoShelfBidControlState,
    min_bid_minor: int,
    actual_bid_minor: int | None,
    control_enabled: bool,
    bid_units_confirmed: bool | None = None,
) -> AutoShelfBidControlDecisionSnapshot:
    """Пересчитать fresh decision snapshot из текущих входов (без state bids)."""
    now = manager._now()
    max_bid_minor = int(settings_obj.max_bid_minor)
    if bid_units_confirmed is None:
        bid_units_confirmed = settings.AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED
    target_test_impressions = int(settings_obj.target_test_impressions)
    target_test_observation_minutes = manager._target_observation_minutes_or_default(
        settings_obj.target_test_observation_minutes
    )
    target_test_observation_hours = manager._target_observation_hours_from_minutes(
        target_test_observation_minutes
    )
    optimization_metric = _resolve_cycle_metric_for_snapshot(complex_adv)

    cycle_bid_stats = await manager._analytics.get_bid_stats(
        nmid=complex_adv.main_nmid,
        from_ts=state.current_cycle_started_at,
        currency=state.currency,
    )
    qualified_tested_bids_count = count_qualified_tested_bids(
        cycle_bid_stats,
        target_test_impressions=target_test_impressions,
        metric=optimization_metric,
    )
    sufficient_qualified_tested = has_sufficient_qualified_tested_bids(
        cycle_bid_stats,
        target_test_impressions=target_test_impressions,
        metric=optimization_metric,
    )

    rec_bid_recommendation: dict[str, object] | None = None
    best_plan_bid_minor: int | None = None
    fresh_best_main_bid_minor: int | None = None
    main_target_explanation: str | None = None
    current_main_bid_minor = getattr(state, "current_main_bid_minor", None)

    if not sufficient_qualified_tested:
        fresh_best_main_bid_minor = None
        best_plan_bid_minor = None
        main_target_explanation = (
            main_target_explanation or INSUFFICIENT_QUALIFIED_TESTED_BIDS_EXPLANATION
        )
        if (
            complex_adv.auto_shelf_bid_control_strategy
            == AutoShelfBidControlStrategy.PLAN_DISTANCE
        ):
            rec_result = await manager._fetch_plan_distance_rec_result(complex_adv)
            if rec_result is not None:
                rec_bid_recommendation = cast_rec_dict(
                    rec_result.get("view", rec_result)
                )
        else:
            ranked_stats = rank_qualified_tested_bid_stats(
                cycle_bid_stats,
                target_test_impressions=target_test_impressions,
                metric=optimization_metric,
            )
            if ranked_stats:
                rec_bid_recommendation = build_cycle_metric_rec_recommendation(
                    ranked_stats
                )
    elif (
        complex_adv.auto_shelf_bid_control_strategy
        == AutoShelfBidControlStrategy.PLAN_DISTANCE
    ):
        rec_result = await manager._fetch_plan_distance_rec_result(complex_adv)
        if rec_result is not None:
            raw_rec = cast_rec_dict(rec_result.get("view", rec_result))
            best_plan_raw = rec_result.get("best_plan_bid")
            if isinstance(best_plan_raw, int) and not isinstance(best_plan_raw, bool):
                best_plan_bid_minor = int(best_plan_raw)
            qualified_bids = collect_qualified_tested_bid_minors(
                cycle_bid_stats,
                target_test_impressions=target_test_impressions,
                metric=optimization_metric,
            )
            rec_bid_recommendation = filter_rec_recommendation_to_qualified_bids(
                raw_rec,
                qualified_bids,
            )
            fresh_best_main_bid_minor, _ranked_top, clamp_explanation = (
                resolve_main_bid_from_qualified_ranking(
                    rec_bid_recommendation,
                    min_bid_minor=min_bid_minor,
                    max_bid_minor=max_bid_minor,
                )
            )
            main_target_explanation = clamp_explanation
    else:
        ranked_stats = rank_qualified_tested_bid_stats(
            cycle_bid_stats,
            target_test_impressions=target_test_impressions,
            metric=optimization_metric,
        )
        rec_bid_recommendation = build_cycle_metric_rec_recommendation(ranked_stats)
        fresh_best_main_bid_minor = await manager._choose_main_bid_by_strategy(
            complex_adv=complex_adv,
            currency=state.currency,
            current_cycle_started_at=state.current_cycle_started_at,
            previous_cycle_started_at=getattr(state, "previous_cycle_started_at", None),
            current_main_bid_minor=current_main_bid_minor,
            actual_bid_minor=actual_bid_minor,
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
        )
        if fresh_best_main_bid_minor is None:
            _fallback_main_bid_minor, _ranked_top, clamp_explanation = (
                resolve_main_bid_from_qualified_ranking(
                    rec_bid_recommendation,
                    min_bid_minor=min_bid_minor,
                    max_bid_minor=max_bid_minor,
                )
            )
        else:
            _ranked_top = fresh_best_main_bid_minor
            clamp_explanation = None
        main_target_explanation = clamp_explanation
        if fresh_best_main_bid_minor is None:
            fresh_best_main_bid_minor = _fallback_main_bid_minor # pyright: ignore
            if fresh_best_main_bid_minor is None:
                main_target_explanation = (
                    main_target_explanation
                    or INSUFFICIENT_QUALIFIED_TESTED_BIDS_EXPLANATION
                )

    _coverages, _current_layer, _covered_anchor_count, coverage_next_test = (
        await manager._build_coverage_snapshot(
            nmid=complex_adv.main_nmid,
            currency=str(settings_obj.currency),
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
            target_test_impressions=target_test_impressions,
            target_test_observation_hours=target_test_observation_hours,
            min_bid_distance_minor=int(settings_obj.min_bid_distance_minor),
            date_to=now,
            epoch_start=manager._shelf_exhausted_epoch_start(state),
        )
    )
    covered_bids = [
        item.bid_minor
        for item in cycle_bid_stats
        if item.impressions >= target_test_impressions
    ]
    legacy_cycle_next_test_bid_minor = manager.choose_next_test_bid(
        min_bid=min_bid_minor,
        max_bid=int(settings_obj.max_bid_minor),
        covered_bids=covered_bids,
        min_distance=int(settings_obj.min_bid_distance_minor),
    )
    if (
        complex_adv.auto_shelf_bid_control_strategy
        == AutoShelfBidControlStrategy.PLAN_DISTANCE
    ):
        fresh_next_test_bid_minor = coverage_next_test
    else:
        fresh_next_test_bid_minor = legacy_cycle_next_test_bid_minor

    expected_bid_minor = resolve_expected_bid_minor(
        current_mode=state.current_mode,
        fresh_best_main_bid_minor=fresh_best_main_bid_minor,
        fresh_next_test_bid_minor=fresh_next_test_bid_minor,
        control_enabled=control_enabled,
    )
    bid_sync_status = resolve_bid_sync_status(
        actual_bid_minor,
        expected_bid_minor,
    )
    return AutoShelfBidControlDecisionSnapshot(
        nmid=complex_adv.main_nmid,
        auto_adv_id=int(complex_adv.auto_adv_id),
        current_mode=state.current_mode,
        actual_bid_minor=actual_bid_minor,
        min_bid_minor=min_bid_minor,
        max_bid_minor=max_bid_minor,
        fresh_best_main_bid_minor=fresh_best_main_bid_minor,
        fresh_next_test_bid_minor=fresh_next_test_bid_minor,
        expected_bid_minor=expected_bid_minor,
        bid_sync_status=bid_sync_status,
        can_count_progress=snapshot_can_count_progress(
            expected_bid_minor=expected_bid_minor,
            actual_bid_minor=actual_bid_minor,
            bid_sync_status=bid_sync_status,
        ),
        main_target_explanation=main_target_explanation,
        best_plan_bid_minor=best_plan_bid_minor,
        legacy_cycle_next_test_bid_minor=legacy_cycle_next_test_bid_minor,
        coverage_selected_next_test_bid_minor=coverage_next_test,
        rec_bid_recommendation=rec_bid_recommendation,
        qualified_tested_bids_count=qualified_tested_bids_count,
        computed_at=now,
    )


async def apply_bid_sync_from_snapshot(
    manager: Any,
    complex_adv: ComplexAdv,
    *,
    state: AutoShelfBidControlState,
    snapshot: AutoShelfBidControlDecisionSnapshot,
    control_enabled: bool,
    bid_units_confirmed: bool,
    min_bid_minor: int,
    max_bid_minor: int,
    now: datetime,
) -> bool:
    """Синхронизировать WB-ставку с fresh expected bid из snapshot."""
    if not control_enabled:
        return False
    if not bid_units_confirmed:
        return False
    if snapshot.expected_bid_minor is not None and snapshot.actual_bid_minor is None:
        return False
    return await manager._reconcile_expected_bid_for_current_mode(
        complex_adv,
        state=state,
        actual_bid_minor=snapshot.actual_bid_minor,
        min_bid_minor=min_bid_minor,
        max_bid_minor=max_bid_minor,
        now=now,
        expected_bid_minor=snapshot.expected_bid_minor,
    )


__all__ = [
    "apply_bid_sync_from_snapshot",
    "build_decision_snapshot",
    "fetch_plan_distance_rec_result",
    "snapshot_from_state_fallback",
]

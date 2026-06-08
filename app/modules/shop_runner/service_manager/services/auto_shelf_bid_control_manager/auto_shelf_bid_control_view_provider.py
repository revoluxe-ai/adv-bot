"""Read-only provider данных для Telegram-экрана Auto Shelf Bid Control."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import cast

from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_recommendation_read_service import (
    AutoShelfBidRecommendationReadService,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_min_bids_cache_manager import (
    MinBidsCacheManager,
)

from .auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)
from .auto_shelf_bid_control_manager import AutoShelfBidControlManager
from .bid_selection import resolve_cycle_best_bids
from .dto import OptimizationMetric, resolve_optimization_metric
from .settings_normalizer import compute_settings_repair, repair_state_test_bid_minor
from .auto_shelf_bid_control_repository import AutoShelfBidControlRepository
from .rec_bid_plan_context import build_rec_bid_plan_context
from .bid_units import (
    report_day_start_utc,
    resolve_test_segment_start_utc,
    truncate_datetime_to_seconds,
    wb_min_cpm_rub_to_bid_minor,
)
from .dto import AutoShelfBidControlViewDTO, BidPointStatsDTO, BidStatsDTO
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.settings import settings
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost

logger = logging.getLogger(__name__)


class AutoShelfBidControlViewProvider:
    """Собирает read-only DTO экрана управления ставкой полок."""

    def __init__(
        self,
        *,
        redis_client: RedisClient,
        repository: AutoShelfBidControlRepository | None = None,
        analytics_repository: AutoShelfBidControlAnalyticsRepository | None = None,
    ) -> None:
        self._repository = repository or AutoShelfBidControlRepository()
        self._analytics = analytics_repository or AutoShelfBidControlAnalyticsRepository()
        self._bid_cache = RedisAutoRecommendationsBidValueManager(redis_client=redis_client)
        self._min_bids_cache = MinBidsCacheManager(redis_client)
        self._rec_bid_recommendation_service = AutoShelfBidRecommendationReadService(
            self._analytics
        )

    async def _fetch_wb_min_bid_minor(self, auto_adv_id: int, nmid: int) -> int | None:
        """Минимальная ставка WB для Auto-РК из Redis min_bids (рубли → bid_minor)."""
        v2 = await self._min_bids_cache.get_min_bid_for_adv_placement_nmid(
            auto_adv_id,
            AdvPlacementType.AUTO_ADV,
            nmid,
        )
        if v2 is not None and int(v2) > 0:
            return wb_min_cpm_rub_to_bid_minor(int(v2))
        legacy = await self._min_bids_cache.get_min_bid_for_nmid(nmid)
        if legacy is not None:
            auto_cpm, _search_cpm = legacy
            if int(auto_cpm) > 0:
                return wb_min_cpm_rub_to_bid_minor(int(auto_cpm))
        return None

    @staticmethod
    def _target_main_impressions(test_impressions: int, test_share: float) -> int | None:
        if test_share <= 0 or test_share > 0.49:
            return None
        return int(test_impressions * (1 - test_share) / test_share)

    @staticmethod
    def _target_main_observation_minutes(
        test_observation_minutes: int, test_share: float
    ) -> int | None:
        if test_share <= 0 or test_share > 0.49:
            return None
        return int(test_observation_minutes * (1 - test_share) / test_share)

    @staticmethod
    def _elapsed_minutes(started_at: datetime | None, now: datetime) -> int | None:
        if started_at is None:
            return None
        return max(0, int((now - started_at).total_seconds() // 60))

    @staticmethod
    def _app_dry_run() -> bool:
        """Глобальный dry-run control-модуля (env AUTO_SHELF_BID_CONTROL_DRY_RUN)."""
        return bool(settings.AUTO_SHELF_BID_CONTROL_DRY_RUN)

    @staticmethod
    def _nullable_int(value: int | None) -> int | None:
        """Вернуть int для non-null значения или None без падения на SQL NULL."""
        return None if value is None else int(value)

    @staticmethod
    def _map_bid_stats_to_points(
        bid_stats: list[BidStatsDTO],
        *,
        target_test: int | None,
        best: BidStatsDTO | None,
        state: object | None,
    ) -> list[BidPointStatsDTO]:
        """Собрать DTO точек ставки для Telegram из агрегатов CH."""
        return [
            BidPointStatsDTO(
                bid_minor=item.bid_minor,
                currency=item.currency,
                last_interval_at=item.last_interval_at,
                impressions=item.impressions,
                clicks=item.clicks,
                carts=item.carts,
                orders=item.orders,
                spend=item.spend,
                cart_cpa=item.cart_cpa,
                ctr=item.ctr,
                cart_cr=item.cart_cr,
                is_covered=(target_test is not None and item.impressions >= target_test),
                is_best=(best is not None and item.bid_minor == best.bid_minor),
                is_current_main=(
                    state is not None
                    and getattr(state, "current_main_bid_minor", None) == item.bid_minor
                ),
                is_current_test=(
                    state is not None
                    and getattr(state, "current_test_bid_minor", None) == item.bid_minor
                ),
            )
            for item in bid_stats
        ]

    async def build_view(self, adv_setting_original_id: int) -> AutoShelfBidControlViewDTO:
        """Собрать DTO для read-only Telegram экрана."""
        app_dry_run = self._app_dry_run()
        bid_units_confirmed = bool(
            getattr(settings, "AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", False)
        )
        adv = await self._repository.get_adv_setting_by_original_id(adv_setting_original_id)
        if adv is None:
            return AutoShelfBidControlViewDTO(
                nmid=0,
                auto_adv_id=None,
                enabled=False,
                has_settings=False,
                has_state=False,
                dry_run=app_dry_run,
                bid_units_confirmed=bid_units_confirmed,
                actual_bid_minor=None,
                min_bid_minor=None,
                max_bid_minor=None,
                current_main_bid_minor=None,
                current_test_bid_minor=None,
                cycle_best_bid_minor=None,
                global_best_bid_minor=None,
                next_test_bid_minor=None,
                currency="RUB",
                current_mode=None,
                current_cycle_started_at=None,
                test_started_at=None,
                main_started_at=None,
                test_share=None,
                target_test_impressions=None,
                target_test_observation_minutes=None,
                target_main_impressions=None,
                target_main_observation_minutes=None,
                min_bid_distance_minor=None,
                test_impressions=None,
                main_impressions=None,
                test_elapsed_minutes=None,
                main_elapsed_minutes=None,
                covered_points_count=0,
                bid_points_total=0,
                bid_points=[],
                cycle_covered_points_count=0,
                cycle_bid_points=[],
                last_reason="adv_setting_not_found",
                warnings=["adv_setting_not_found"],
                rec_bid_recommendation=None,
                optimization_metric=OptimizationMetric.CPC,
                fact_cpo=None,
                resolve_cpo=None,
            )

        nmids = list(adv.nmids or [])
        nmids.sort()
        warnings: list[str] = []
        if len(nmids) != 1:
            warnings.append("single_nmid_guard_skip")
        nmid = nmids[0] if nmids else 0
        auto_adv_id = int(adv.adv_id)

        # Получаем plan-fact данные для определения метрики оптимизации
        fact_cpo: float | None = None
        fact_predict_orders: float | None = None
        plan_fact_reader = PlanFactReader()
        plan_fact_summary = await plan_fact_reader.get_latest_plan_fact(auto_adv_id)
        if plan_fact_summary is not None:
            fact_predict_orders = plan_fact_summary.fact_predict_orders
            fact_cpo = plan_fact_summary.fact_pay_for_order
        resolve_cpo = resolve_target_cost(
            adv.plan_for_sales_for_day,
            adv.target_price_for_order,
            adv.max_price_for_order,
            fact_predict_orders,
        )
        optimization_metric = resolve_optimization_metric(fact_cpo, resolve_cpo)

        state = await self._repository.get_state(nmid) if nmid else None
        settings_obj = None
        if nmid and len(nmids) == 1:
            settings_obj = await self._repository.get_or_create_default_settings(nmid)
        elif nmid:
            settings_obj = await self._repository.get_settings(nmid)
        if state is None:
            warnings.append("state_missing")
        now_utc = datetime.now(UTC)
        rec_bid_recommendation: dict[str, object] | None = None

        actual_bid_minor: int | None = None
        if nmid:
            cached = await self._bid_cache.get_bid(auto_adv_id=auto_adv_id, nmid=nmid)
            if cached is not None:
                actual_bid_minor = int(cached.bid_minor)
            else:
                warnings.append("no_actual_bid")
        else:
            warnings.append("no_auto_adv")

        currency = settings_obj.currency if settings_obj is not None else "RUB"
        target_test = int(settings_obj.target_test_impressions) if settings_obj else None
        target_test_observation_minutes = (
            self._nullable_int(settings_obj.target_test_observation_minutes)
            if settings_obj
            else None
        )
        stats_from_ts = report_day_start_utc()
        bid_stats = (
            await self._analytics.get_bid_stats(
                nmid=nmid,
                from_ts=stats_from_ts,
                currency=currency,
            )
            if nmid
            else []
        )
        if nmid and optimization_metric == OptimizationMetric.CTR:
            best = await self._analytics.get_best_bid_by_ctr(
                nmid=nmid,
                from_ts=stats_from_ts,
                currency=currency,
            )
        elif nmid:
            best = await self._analytics.get_best_bid_by_cart_cpa(
                nmid=nmid,
                from_ts=stats_from_ts,
                currency=currency,
            )
        else:
            best = None
        target_main = (
            self._target_main_impressions(target_test, float(settings_obj.test_share))
            if settings_obj and target_test is not None
            else None
        )
        target_main_observation_minutes = (
            self._target_main_observation_minutes(
                target_test_observation_minutes,
                float(settings_obj.test_share),
            )
            if settings_obj and target_test_observation_minutes is not None
            else None
        )
        if settings_obj and target_main is None:
            warnings.append("invalid_test_share")

        cycle_bid_stats: list[BidStatsDTO] = []
        cycle_best: BidStatsDTO | None = None
        global_best: BidStatsDTO | None = None
        cycle_from_ts = state.current_cycle_started_at if state is not None else None
        if cycle_from_ts is not None and nmid:
            cycle_bid_stats = await self._analytics.get_bid_stats(
                nmid=nmid,
                from_ts=cycle_from_ts,
                currency=currency,
            )
            if state is not None:
                cycle_best, _, global_best = await resolve_cycle_best_bids(
                    self._analytics,
                    nmid=nmid,
                    currency=currency,
                    current_cycle_started_at=cycle_from_ts,
                    previous_cycle_started_at=state.previous_cycle_started_at,
                    fact_cpo=fact_cpo,
                    resolve_cpo=resolve_cpo,
                )

        covered_points_count = 0
        if target_test is not None and cycle_bid_stats:
            covered_points_count = len(
                [item for item in cycle_bid_stats if item.impressions >= target_test]
            )

        min_bid_minor_value: int | None = None
        if nmid:
            min_bid_minor_value = await self._fetch_wb_min_bid_minor(auto_adv_id, nmid)
        if min_bid_minor_value is None:
            warnings.append("no_min_bid")

        if settings_obj is not None and min_bid_minor_value is not None:
            preview = compute_settings_repair(
                settings_obj,
                min_bid_minor=min_bid_minor_value,
                actual_bid_minor=actual_bid_minor,
            )
            if preview.changed:
                settings_obj = await self._repository.update_settings(
                    nmid=nmid,
                    max_bid_minor=preview.max_bid_minor,
                    min_bid_distance_minor=preview.min_bid_distance_minor,
                )
            if state is not None:
                if repair_state_test_bid_minor(
                    state,
                    min_bid_minor=min_bid_minor_value,
                    max_bid_minor=int(settings_obj.max_bid_minor),
                    actual_bid_minor=actual_bid_minor,
                ):
                    state = await self._repository.save_state(state)

        next_test_bid_minor: int | None = None
        if settings_obj is not None and min_bid_minor_value is not None:
            if int(settings_obj.max_bid_minor) < min_bid_minor_value:
                warnings.append("max_bid_lower_than_min_bid")
            covered_bids = (
                [
                    item.bid_minor
                    for item in cycle_bid_stats
                    if item.impressions >= target_test
                ]
                if target_test is not None
                else []
            )
            next_test_bid_minor = AutoShelfBidControlManager.choose_next_test_bid(
                min_bid=min_bid_minor_value,
                max_bid=int(settings_obj.max_bid_minor),
                covered_bids=covered_bids,
                min_distance=int(settings_obj.min_bid_distance_minor),
            )
        if app_dry_run:
            warnings.append("dry_run_enabled")
        if not bid_units_confirmed:
            warnings.append("bid_units_gate_not_confirmed")

        bid_points_total = len(bid_stats)
        bid_points = self._map_bid_stats_to_points(
            bid_stats,
            target_test=target_test,
            best=best,
            state=state,
        )

        cycle_covered_points_count = covered_points_count
        cycle_bid_points = self._map_bid_stats_to_points(
            cycle_bid_stats,
            target_test=target_test,
            best=global_best,
            state=state,
        )

        test_impressions: int | None = None
        test_elapsed_minutes: int | None = None
        if state is not None:
            test_from_ts = resolve_test_segment_start_utc(
                test_started_at=state.test_started_at,
                current_cycle_started_at=state.current_cycle_started_at,
            )
            test_elapsed_minutes = self._elapsed_minutes(test_from_ts, now_utc)
            test_bid_minor = state.current_test_bid_minor
            if test_bid_minor is None:
                test_bid_minor = actual_bid_minor
            assert test_bid_minor is not None
            test_impressions = await self._analytics.get_impressions(
                nmid=nmid,
                from_ts=test_from_ts,
                currency=currency,
                bid_minor=test_bid_minor,
            )
        elif nmid and actual_bid_minor is not None:
            test_impressions = await self._analytics.get_impressions(
                nmid=nmid,
                from_ts=stats_from_ts,
                currency=currency,
                bid_minor=actual_bid_minor,
            )
        main_impressions: int | None = None
        main_elapsed_minutes: int | None = None
        if state is not None and state.main_started_at is not None:
            main_started_at = state.main_started_at
            main_elapsed_minutes = self._elapsed_minutes(main_started_at, now_utc)
            main_bid_minor = state.current_main_bid_minor
            if main_bid_minor is None:
                main_bid_minor = actual_bid_minor
            assert main_bid_minor is not None
            main_impressions = await self._analytics.get_impressions(
                nmid=nmid,
                from_ts=main_started_at,
                currency=currency,
                bid_minor=main_bid_minor,
                mode="main",
            )

        if nmid:
            try:
                rec_repository = self._analytics
                rec_mode: str | None = None
                rec_date_to = now_utc
                rec_date_from = rec_date_to - timedelta(days=7)
                logger.info(
                    "rec_bid_recommendation_mode_scope=all nmid=%s adv_setting_original_id=%s",
                    nmid,
                    adv_setting_original_id,
                )
                ctr_by_bid = await rec_repository.fetch_rec_bid_ctr_by_bid_for_nmid(
                    nmid=nmid,
                    mode=rec_mode,
                    date_from=rec_date_from,
                    date_to=rec_date_to,
                )
                if not ctr_by_bid:
                    logger.warning(
                        "rec_bid_recommendation_missing_ctr nmid=%s adv_setting_original_id=%s",
                        nmid,
                        adv_setting_original_id,
                    )
                else:
                    click_to_order_cr_7d = (
                        await rec_repository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(
                            nmid=nmid,
                            mode=rec_mode,
                            date_from=rec_date_from,
                            date_to=rec_date_to,
                        )
                    )
                    plan_context = build_rec_bid_plan_context(
                        sales_plan=float(adv.plan_for_sales_for_day or 0.0),
                        current_fact_sales=float(fact_predict_orders or 0.0),
                        current_sales_forecast=float(fact_predict_orders or 0.0),
                        target_price_for_order=adv.target_price_for_order,
                        max_price_for_order=adv.max_price_for_order,
                        click_to_order_cr_7d=click_to_order_cr_7d,
                    )
                    rec_result = await self._rec_bid_recommendation_service.get_rec_bid_recommendations(
                        nmid=nmid,
                        mode=rec_mode,
                        date_from=rec_date_from,
                        date_to=rec_date_to,
                        plan_context=plan_context,
                        ctr_by_bid=ctr_by_bid,
                    )
                    rec_bid_recommendation = cast(
                        dict[str, object], rec_result["view"]
                    )
            except Exception:
                logger.warning(
                    "rec_bid_recommendation_failed nmid=%s adv_setting_original_id=%s",
                    nmid,
                    adv_setting_original_id,
                    exc_info=True,
                )
        else:
            logger.warning(
                "rec_bid_recommendation_missing_nmid adv_setting_original_id=%s",
                adv_setting_original_id,
            )
        if rec_bid_recommendation is None:
            logger.warning(
                "rec_bid_recommendation_none nmid=%s adv_setting_original_id=%s",
                nmid,
                adv_setting_original_id,
            )
        else:
            diagnostics = cast(
                dict[str, object],
                rec_bid_recommendation.get("diagnostics", {}),
            )
            logger.warning(
                "rec_bid_recommendation_not_none nmid=%s adv_setting_original_id=%s diagnostics=%s",
                nmid,
                adv_setting_original_id,
                diagnostics,
            )

        return AutoShelfBidControlViewDTO(
            nmid=nmid,
            auto_adv_id=auto_adv_id,
            enabled=bool(adv.auto_shelf_bid_control_enabled),
            has_settings=settings_obj is not None,
            has_state=state is not None,
            dry_run=app_dry_run,
            bid_units_confirmed=bid_units_confirmed,
            actual_bid_minor=actual_bid_minor,
            min_bid_minor=min_bid_minor_value,
            max_bid_minor=(int(settings_obj.max_bid_minor) if settings_obj else None),
            current_main_bid_minor=(state.current_main_bid_minor if state else None),
            current_test_bid_minor=(state.current_test_bid_minor if state else None),
            cycle_best_bid_minor=(
                cycle_best.bid_minor if cycle_best is not None else None
            ),
            global_best_bid_minor=(
                global_best.bid_minor
                if global_best is not None
                else (best.bid_minor if best is not None else None)
            ),
            next_test_bid_minor=next_test_bid_minor,
            currency=currency,
            current_mode=(state.current_mode if state else None),
            current_cycle_started_at=truncate_datetime_to_seconds(
                state.current_cycle_started_at if state else None
            ),
            test_started_at=truncate_datetime_to_seconds(
                state.test_started_at if state else None
            ),
            main_started_at=truncate_datetime_to_seconds(
                state.main_started_at if state else None
            ),
            test_share=(float(settings_obj.test_share) if settings_obj else None),
            target_test_impressions=target_test,
            target_test_observation_minutes=target_test_observation_minutes,
            target_main_impressions=target_main,
            target_main_observation_minutes=target_main_observation_minutes,
            min_bid_distance_minor=(
                int(settings_obj.min_bid_distance_minor) if settings_obj else None
            ),
            test_impressions=test_impressions,
            main_impressions=main_impressions,
            test_elapsed_minutes=test_elapsed_minutes,
            main_elapsed_minutes=main_elapsed_minutes,
            covered_points_count=covered_points_count,
            bid_points_total=bid_points_total,
            bid_points=bid_points,
            cycle_covered_points_count=cycle_covered_points_count,
            cycle_bid_points=cycle_bid_points,
            last_reason=(state.last_reason if state else None),
            warnings=warnings,
            rec_bid_recommendation=rec_bid_recommendation,
            optimization_metric=optimization_metric,
            fact_cpo=fact_cpo,
            resolve_cpo=resolve_cpo,
        )

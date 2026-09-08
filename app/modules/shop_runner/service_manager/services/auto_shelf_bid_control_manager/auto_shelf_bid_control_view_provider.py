"""Read-only provider данных для Telegram-экрана Auto Shelf Bid Control."""

from __future__ import annotations

import inspect
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from types import SimpleNamespace

from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.core.mp.wb.min_bid_defaults import default_min_bid_rub
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_recommendation_read_service import (
    AutoShelfBidRecommendationReadService,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_min_bids_cache_manager import (
    MinBidsCacheManager,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)

from .auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)
from .auto_shelf_bid_control_manager import AutoShelfBidControlManager
from .auto_shelf_bid_setter import AutoShelfBidSetter
from .bid_coverage_selector import (
    BidCoverage,
    build_bid_universe,
    build_coverage_selector_seed,
    choose_next_test_bid_by_coverage_layers,
    closed_layers_for_bid,
)
from .bid_selection import resolve_cycle_best_bids
from .dto import OptimizationMetric, resolve_optimization_metric
from .dto import CoverageLayerBidDTO
from .settings_normalizer import compute_settings_repair, repair_state_test_bid_minor
from .auto_shelf_bid_control_repository import AutoShelfBidControlRepository
from .rec_bid_plan_context import build_rec_bid_plan_context
from .bid_units import (
    report_day_start_utc,
    resolve_test_segment_start_utc,
    truncate_datetime_to_seconds,
    wb_min_cpm_rub_to_bid_minor,
)
from .exhausted_pause.decision import coverage_date_from_for_epoch
from .dto import (
    AutoShelfBidControlViewDTO,
    AutoShelfBidSelectedCpoContract,
    BidPointStatsDTO,
    BidStatsDTO,
)
from .dto import resolve_selected_cpo_contract_from_view
from .dto.decision_snapshot_dto import (
    resolve_bid_sync_detail,
    resolve_expected_bid_minor,
    resolve_primary_status,
)
from .dto.selected_cpo_contract import (
    as_object_dict,
    coerce_finite_float,
    extract_selected_cpo_details_from_view,
)
from app.modules.auto_budget_manager.redis_promo_state_manager import (
    RedisPromoStateManager,
)
from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.shared.domains.wb.utils.promo_overlay import fraction_from_cached_state
from app.settings import settings
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv.complex_adv import (
    resolve_auto_shelf_bid_control_strategy,
)

logger = logging.getLogger(__name__)


class AutoShelfBidControlViewProvider:
    """Собирает read-only DTO экрана управления ставкой полок."""

    def __init__(
        self,
        *,
        redis_client: RedisClient,
        repository: AutoShelfBidControlRepository | None = None,
        analytics_repository: AutoShelfBidControlAnalyticsRepository | None = None,
        plan_fact_reader: PlanFactReader | None = None,
    ) -> None:
        """Инициализировать read-only зависимости экрана, включая Redis overlay-клиент."""
        self._redis_client = redis_client
        self._repository = repository or AutoShelfBidControlRepository()
        self._analytics = analytics_repository or AutoShelfBidControlAnalyticsRepository()
        self._bid_cache = RedisAutoRecommendationsBidValueManager(redis_client=redis_client)
        self._min_bids_cache = MinBidsCacheManager(redis_client)
        self._rec_bid_recommendation_service = AutoShelfBidRecommendationReadService(
            self._analytics
        )
        self._plan_fact_reader = plan_fact_reader

    def _get_plan_fact_reader(self) -> PlanFactReader:
        """Вернуть injected reader или лениво создать дефолтный для тестов/CLI."""
        if self._plan_fact_reader is None:
            self._plan_fact_reader = PlanFactReader()
        return self._plan_fact_reader

    @staticmethod
    def _shop_id_from_adv(adv: Any) -> str | int | None:
        """Ключ Redis overlay: ``WBCabinet.shop_id``.

        У ``AdvSetting`` нет колонки ``shop_id``; Telegram-репозиторий уже
        делает ``joinedload(wb_cabinet)``. Fallback ``adv.shop_id`` — для
        DTO вроде ``ComplexAdv``.
        """
        cabinet = getattr(adv, "wb_cabinet", None)
        if cabinet is not None:
            cabinet_shop_id = getattr(cabinet, "shop_id", None)
            if isinstance(cabinet_shop_id, (str, int)) and cabinet_shop_id != "":
                return cabinet_shop_id
        shop_id = getattr(adv, "shop_id", None)
        if isinstance(shop_id, (str, int)) and shop_id != "":
            return shop_id
        return None

    async def _resolve_live_promo_fraction(self, adv: Any) -> Decimal:
        """Фактическая promo-доля из Redis overlay-кэша. Miss/ошибка → 0 (M=1)."""
        shop_id = self._shop_id_from_adv(adv)
        if shop_id is None:
            return Decimal("0")
        try:
            cached = await RedisPromoStateManager(self._redis_client).get(shop_id)
        except Exception:
            logger.debug(
                "promo overlay cache miss/error for rec-bid shop_id=%s",
                shop_id,
                exc_info=True,
            )
            return Decimal("0")
        return fraction_from_cached_state(
            cached,
            getattr(adv, "adv_id", None),
            getattr(adv, "search_adv_id", None),
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
        default_rub = default_min_bid_rub(AdvPlacementType.AUTO_ADV)
        logger.warning(
            "min_bids using default context=auto_shelf_bid_control_view "
            "placement=%s nmid=%s default_rub=%s",
            AdvPlacementType.AUTO_ADV.value,
            nmid,
            default_rub,
        )
        return wb_min_cpm_rub_to_bid_minor(default_rub)

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
    def _parse_best_plan_bid_minor(value: object) -> int | None:
        """Parse recommendation ``best_plan_bid`` to internal kopecks or reject invalid values."""
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        if value <= 0 or value % 100 != 0:
            return None
        return value

    @classmethod
    def _sanitize_rec_bid_recommendation(
        cls, recommendation: dict[str, object]
    ) -> tuple[dict[str, object], int | None]:
        """Remove invalid best-plan bid from the UI payload and return sanitized bid_minor."""
        sanitized = dict(recommendation)
        if "best_plan_bid" not in sanitized:
            return sanitized, None
        best_plan_bid_minor = cls._parse_best_plan_bid_minor(
            sanitized["best_plan_bid"]
        )
        sanitized["best_plan_bid"] = best_plan_bid_minor
        return sanitized, best_plan_bid_minor

    @staticmethod
    def _parse_plan_ranked_scores(
        recommendation: dict[str, object] | None,
    ) -> dict[int, float]:
        """Extract valid plan-ranked bid scores for coverage row ordering."""
        if recommendation is None:
            return {}
        raw_rows = recommendation.get("plan_ranked")
        if not isinstance(raw_rows, list):
            return {}
        rows = cast(list[object], raw_rows)
        scores: dict[int, float] = {}
        for raw_item in rows:
            if not isinstance(raw_item, dict):
                continue
            item = cast(dict[str, object], raw_item)
            bid_value = item.get("bid")
            score_value = item.get("plan_distance_score")
            if isinstance(bid_value, bool) or not isinstance(bid_value, int):
                continue
            if isinstance(score_value, bool) or not isinstance(
                score_value, (int, float, str)
            ):
                continue
            try:
                score = float(score_value)
            except (TypeError, ValueError):
                continue
            scores[int(bid_value)] = score
        return scores

    @staticmethod
    def _resolve_display_optimization_metric(
        *,
        strategy: AutoShelfBidControlStrategy | None,
        fact_cpo: float | None,
        resolve_cpo: float | None,
    ) -> OptimizationMetric:
        """Resolve the UI metric so display matches the selected strategy.

        Explicit CTR/CPC modes must keep their own metric for all Telegram
        highlights and "best bid" labels. Legacy `cycle_metric` is normalized
        to CPC for backward compatibility, so only a missing strategy value may
        fall back to the historic dynamic metric derived from
        `fact_cpo/resolve_cpo`.
        """
        normalized_strategy = resolve_auto_shelf_bid_control_strategy(strategy)
        if normalized_strategy == AutoShelfBidControlStrategy.CTR:
            return OptimizationMetric.CTR
        if normalized_strategy == AutoShelfBidControlStrategy.CPC:
            return OptimizationMetric.CPC
        return resolve_optimization_metric(fact_cpo, resolve_cpo)

    @staticmethod
    def _coerce_optional_float(value: object) -> float | None:
        """Convert loosely typed recommendation values into float-compatible data."""
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_plan_ranked_forecasts(
        recommendation: dict[str, object] | None,
    ) -> dict[int, dict[str, object]]:
        """Extract forecast fields from plan-ranked rows by bid.

        The provider keeps render-time logic dumb: if a field is absent in the
        recommendation payload, the UI gets ``None`` and prints ``—``.
        """
        if recommendation is None:
            return {}
        raw_rows = recommendation.get("plan_ranked")
        if not isinstance(raw_rows, list):
            return {}
        rows = cast(list[object], raw_rows)
        forecasts: dict[int, dict[str, object]] = {}
        for raw_item in rows:
            if not isinstance(raw_item, dict):
                continue
            item = cast(dict[str, object], raw_item)
            bid_value = item.get("bid")
            if isinstance(bid_value, bool) or not isinstance(bid_value, int):
                continue
            bid_minor = int(bid_value)
            expected_daily_impressions = AutoShelfBidControlViewProvider._coerce_optional_float(
                item.get("expected_daily_impressions")
                if item.get("expected_daily_impressions") is not None
                else item.get("expected_impressions")
            )
            expected_daily_clicks = AutoShelfBidControlViewProvider._coerce_optional_float(
                item.get("expected_daily_clicks")
                if item.get("expected_daily_clicks") is not None
                else item.get("expected_clicks")
            )
            expected_daily_orders = AutoShelfBidControlViewProvider._coerce_optional_float(
                item.get("expected_daily_orders")
                if item.get("expected_daily_orders") is not None
                else item.get("expected_orders")
            )
            expected_order_cost_rub = AutoShelfBidControlViewProvider._coerce_optional_float(
                item.get("cpo_rub")
                if item.get("cpo_rub") is not None
                else item.get("expected_order_cost_rub")
            )
            plan_distance_score = AutoShelfBidControlViewProvider._coerce_optional_float(
                item.get("plan_distance_score")
            )
            forecasts[bid_minor] = {
                "expected_daily_impressions": expected_daily_impressions,
                "expected_daily_clicks": expected_daily_clicks,
                "expected_daily_orders": expected_daily_orders,
                "expected_order_cost_rub": expected_order_cost_rub,
                "ctr": AutoShelfBidControlViewProvider._coerce_optional_float(
                    item.get("ctr")
                ),
                "plan_distance_score": plan_distance_score,
                "status_text": item.get("status_text"),
            }
        return forecasts

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

    @staticmethod
    def _coverage_bid_label(
        *,
        bid_minor: int,
        current_main_bid_minor: int | None,
        current_test_bid_minor: int | None,
        selected_next_test_bid_minor: int | None,
        best_plan_bid_minor: int | None,
        min_bid_minor: int | None,
        max_bid_minor: int | None,
    ) -> str:
        labels: list[str] = []
        if current_main_bid_minor is not None and bid_minor == int(current_main_bid_minor):
            labels.append("current_main_bid_minor")
        if current_test_bid_minor is not None and bid_minor == int(current_test_bid_minor):
            labels.append("current_test_bid_minor")
        if best_plan_bid_minor is not None and bid_minor == int(best_plan_bid_minor):
            labels.append("best_plan_bid_minor")
        if (
            selected_next_test_bid_minor is not None
            and bid_minor == int(selected_next_test_bid_minor)
        ):
            labels.append("selected_next_test_bid_minor")
        if min_bid_minor is not None and bid_minor == int(min_bid_minor):
            labels.append("min_bid_minor")
        if max_bid_minor is not None and bid_minor == int(max_bid_minor):
            labels.append("max_bid_minor")
        if not labels:
            return "bid"
        return " / ".join(labels)

    @staticmethod
    def _build_coverage_layer_rows(
        *,
        universe: list[int],
        coverages: list[BidCoverage],
        current_layer: int,
        selected_next_test_bid_minor: int | None,
        current_main_bid_minor: int | None,
        current_test_bid_minor: int | None,
        best_plan_bid_minor: int | None,
        global_best_bid_minor: int | None,
        min_bid_minor: int | None,
        max_bid_minor: int | None,
        target_test_impressions: int,
        target_test_observation_hours: int,
        forecast_by_bid: dict[int, dict[str, object]] | None = None,
    ) -> list[CoverageLayerBidDTO]:
        coverage_map = {int(item.bid_minor): item for item in coverages}
        forecast_by_bid = forecast_by_bid or {}
        rows: list[CoverageLayerBidDTO] = []
        for bid_minor in universe:
            coverage = coverage_map.get(bid_minor)
            if coverage is None:
                impressions = 0
                valid_hours = 0
            else:
                impressions = int(coverage.impressions)
                valid_hours = int(coverage.valid_hours)
            closed_layers = closed_layers_for_bid(
                impressions=impressions,
                valid_hours=valid_hours,
                target_test_impressions=target_test_impressions,
                target_test_observation_hours=target_test_observation_hours,
            )
            rows.append(
                CoverageLayerBidDTO(
                    label=AutoShelfBidControlViewProvider._coverage_bid_label(
                        bid_minor=bid_minor,
                        current_main_bid_minor=current_main_bid_minor,
                        current_test_bid_minor=current_test_bid_minor,
                        selected_next_test_bid_minor=selected_next_test_bid_minor,
                        best_plan_bid_minor=best_plan_bid_minor,
                        min_bid_minor=min_bid_minor,
                        max_bid_minor=max_bid_minor,
                    ),
                    bid_minor=bid_minor,
                    impressions=impressions,
                    valid_hours=valid_hours,
                    closed_layers=closed_layers,
                    undercovered=(closed_layers == current_layer),
                    is_current_main=(
                        current_main_bid_minor is not None
                        and bid_minor == int(current_main_bid_minor)
                    ),
                    is_current_test=(
                        current_test_bid_minor is not None
                        and bid_minor == int(current_test_bid_minor)
                    ),
                    is_selected_next_test=(
                        selected_next_test_bid_minor is not None
                        and bid_minor == int(selected_next_test_bid_minor)
                    ),
                    is_best_plan=(
                        best_plan_bid_minor is not None
                        and bid_minor == int(best_plan_bid_minor)
                    ),
                    is_global_best=(
                        global_best_bid_minor is not None
                        and bid_minor == int(global_best_bid_minor)
                    ),
                    status_text=(
                        "selected_next_test"
                        if selected_next_test_bid_minor is not None
                        and bid_minor == int(selected_next_test_bid_minor)
                        else (
                            "best_plan"
                            if best_plan_bid_minor is not None
                            and bid_minor == int(best_plan_bid_minor)
                            else ("eligible" if closed_layers == current_layer else "covered")
                        )
                    ),
                )
            )
            forecast = forecast_by_bid.get(bid_minor, {})
            rows[-1] = CoverageLayerBidDTO(
                label=rows[-1].label,
                bid_minor=rows[-1].bid_minor,
                impressions=rows[-1].impressions,
                valid_hours=rows[-1].valid_hours,
                closed_layers=rows[-1].closed_layers,
                undercovered=rows[-1].undercovered,
                is_current_main=rows[-1].is_current_main,
                is_current_test=rows[-1].is_current_test,
                is_selected_next_test=rows[-1].is_selected_next_test,
                is_best_plan=rows[-1].is_best_plan,
                is_global_best=rows[-1].is_global_best,
                status_text=rows[-1].status_text,
                expected_daily_impressions=AutoShelfBidControlViewProvider._coerce_optional_float(
                    forecast.get("expected_daily_impressions")
                ),
                expected_daily_clicks=AutoShelfBidControlViewProvider._coerce_optional_float(
                    forecast.get("expected_daily_clicks")
                ),
                expected_daily_orders=AutoShelfBidControlViewProvider._coerce_optional_float(
                    forecast.get("expected_daily_orders")
                ),
                expected_order_cost_rub=AutoShelfBidControlViewProvider._coerce_optional_float(
                    forecast.get("expected_order_cost_rub")
                ),
                ctr=AutoShelfBidControlViewProvider._coerce_optional_float(
                    forecast.get("ctr")
                ),
                plan_distance_score=AutoShelfBidControlViewProvider._coerce_optional_float(
                    forecast.get("plan_distance_score")
                ),
            )
        return rows

    @staticmethod
    def _sort_coverage_layer_rows(
        rows: list[CoverageLayerBidDTO],
        *,
        plan_ranked_scores: dict[int, float],
        selected_next_test_bid_minor: int | None,
    ) -> list[CoverageLayerBidDTO]:
        """Sort dense coverage rows for diagnostics without dropping any bids."""
        covered_anchors = [
            row.bid_minor for row in rows if not row.undercovered
        ]
        anchor_distance_by_bid: dict[int, int] = {}
        for row in rows:
            if not row.undercovered or not covered_anchors:
                continue
            anchor_distance_by_bid[row.bid_minor] = min(
                abs(int(row.bid_minor) - int(anchor_bid))
                for anchor_bid in covered_anchors
            )

        def _is_important(row: CoverageLayerBidDTO) -> bool:
            return (
                row.is_current_main
                or row.is_current_test
                or row.is_best_plan
                or row.is_global_best
                or "min_bid_minor" in row.label
                or "max_bid_minor" in row.label
            )

        def _sort_key(row: CoverageLayerBidDTO) -> tuple[float, ...]:
            if row.bid_minor in plan_ranked_scores:
                return (0.0, float(plan_ranked_scores[row.bid_minor]), float(row.bid_minor))
            if (
                selected_next_test_bid_minor is not None
                and row.bid_minor == int(selected_next_test_bid_minor)
            ):
                return (1.0, 0.0, float(row.bid_minor))
            if _is_important(row):
                return (2.0, 0.0, float(row.bid_minor))
            if row.undercovered:
                return (
                    3.0,
                    float(-anchor_distance_by_bid.get(row.bid_minor, -row.bid_minor)),
                    float(row.bid_minor),
                )
            return (4.0, 0.0, float(row.bid_minor))

        return sorted(rows, key=_sort_key)

    async def build_view(self, adv_setting_original_id: int) -> AutoShelfBidControlViewDTO:
        """Собрать DTO для read-only Telegram экрана.

        Rec-bid ``plan_context`` использует scaled overlay CPO: live
        ``promo_fraction`` из Redis overlay-кэша передаётся в
        ``get_effective_promo_plan(..., fraction=)``, как ``overlay_for_adv``.
        """
        app_dry_run = self._app_dry_run()
        bid_units_confirmed = settings.AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED

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
                best_plan_bid_minor=None,
                state_updated_at=None,
            )

        nmids = list(adv.nmids or [])
        nmids.sort()
        warnings: list[str] = []
        if len(nmids) != 1:
            warnings.append("single_nmid_guard_skip")
        nmid = nmids[0] if nmids else 0
        auto_adv_id = int(adv.adv_id)
        normalized_strategy = resolve_auto_shelf_bid_control_strategy(
            getattr(adv, "auto_shelf_bid_control_strategy", None)
        )

        # Получаем plan-fact данные для определения метрики оптимизации
        fact_cpo: float | None = None
        fact_predict_orders: float | None = None
        resolve_cpo: float | None = None
        plan_fact_summary = await self._get_plan_fact_reader().get_latest_plan_fact(
            auto_adv_id
        )
        if plan_fact_summary is not None:
            fact_predict_orders = plan_fact_summary.fact_predict_orders
            fact_cpo = plan_fact_summary.fact_pay_for_order
        resolve_cpo = resolve_target_cost(
            adv.plan_for_sales_for_day,
            adv.target_price_for_order,
            adv.max_price_for_order,
            fact_predict_orders,
        )
        optimization_metric = self._resolve_display_optimization_metric(
            strategy=normalized_strategy,
            fact_cpo=fact_cpo,
            resolve_cpo=resolve_cpo,
        )

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
        best_plan_bid_minor: int | None = None

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
            AutoShelfBidControlManager._target_observation_minutes_or_default( # type: ignore
                settings_obj.target_test_observation_minutes
            )
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

        if state is not None and AutoShelfBidControlManager.repair_cycle_started_at(state):
            state = await self._repository.save_state(state)

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
                    metric=optimization_metric,
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
        legacy_cycle_next_test_bid_minor: int | None = None
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
            legacy_cycle_next_test_bid_minor = AutoShelfBidControlManager.choose_next_test_bid(
                min_bid=min_bid_minor_value,
                max_bid=int(settings_obj.max_bid_minor),
                covered_bids=covered_bids,
                min_distance=int(settings_obj.min_bid_distance_minor),
            )
            next_test_bid_minor = legacy_cycle_next_test_bid_minor
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
            if test_bid_minor is not None:
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
            if main_bid_minor is not None:
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
                    logger.debug(
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
                    live_fraction = await self._resolve_live_promo_fraction(adv)
                    overlay = PlanFactProvider.get_effective_promo_plan(
                        adv, fraction=live_fraction
                    )
                    plan_overlay = overlay.plan
                    plan_context = build_rec_bid_plan_context(
                        sales_plan=float(adv.plan_for_sales_for_day or 0.0),
                        current_fact_sales=float(fact_predict_orders or 0.0),
                        current_sales_forecast=float(fact_predict_orders or 0.0),
                        target_price_for_order=(
                            plan_overlay.target_pay_for_order
                            if plan_overlay is not None
                            else adv.target_price_for_order
                        ),
                        max_price_for_order=(
                            plan_overlay.max_pay_for_order
                            if plan_overlay is not None
                            else adv.max_price_for_order
                        ),
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
                    rec_bid_recommendation = cast(dict[str, object], rec_result["view"])
                    (
                        rec_bid_recommendation,
                        best_plan_bid_minor,
                    ) = self._sanitize_rec_bid_recommendation(rec_bid_recommendation)
            except Exception:
                logger.warning(
                    "rec_bid_recommendation_failed nmid=%s adv_setting_original_id=%s",
                    nmid,
                    adv_setting_original_id,
                    exc_info=True,
                )
        else:
            logger.debug(
                "rec_bid_recommendation_missing_nmid adv_setting_original_id=%s",
                adv_setting_original_id,
            )
        if rec_bid_recommendation is None:
            logger.debug(
                "rec_bid_recommendation_none nmid=%s adv_setting_original_id=%s",
                nmid,
                adv_setting_original_id,
            )
        else:
            diagnostics = cast(
                dict[str, object],
                rec_bid_recommendation.get("diagnostics", {}),
            )
            logger.debug(
                "rec_bid_recommendation_not_none nmid=%s adv_setting_original_id=%s diagnostics=%s",
                nmid,
                adv_setting_original_id,
                diagnostics,
            )

        coverage_first_available_bucket_start: datetime | None = None
        coverage_current_layer: int | None = None
        coverage_undercovered_count: int | None = None
        coverage_selected_next_test_bid_minor: int | None = None
        coverage_bid_rows: list[CoverageLayerBidDTO] = []
        coverage_get_first = getattr(
            self._analytics,
            "get_first_available_bid_bucket_start",
            None,
        )
        coverage_get_coverages = getattr(self._analytics, "get_bid_coverages", None)
        if (
            settings_obj is not None
            and min_bid_minor_value is not None
            and target_test is not None
            and inspect.iscoroutinefunction(coverage_get_first)
            and inspect.iscoroutinefunction(coverage_get_coverages)
        ):
            max_bid_minor_value = int(settings_obj.max_bid_minor)
            target_test_impressions_value = int(target_test)
            target_test_observation_minutes_value = (
                int(target_test_observation_minutes)
                if target_test_observation_minutes is not None
                else 60
            )
            target_test_observation_hours_value = (
                max(1, (int(target_test_observation_minutes_value) + 59) // 60)
            )
            coverage_first_available_bucket_start = await self._analytics.get_first_available_bid_bucket_start(
                nmid=nmid,
                currency=currency,
                price_minor=None,
                mode=None,
            )
            coverage_rows: list[BidCoverage] = []
            if coverage_first_available_bucket_start is not None:
                # После Auto start / mark_shelf_exhausted_epoch_started окно
                # coverage MUST учитывать epoch_start, иначе pre-epoch CH
                # история закрывает ставки новой эпохи (ROOT-001).
                epoch_start = (
                    getattr(state, "shelf_exhausted_epoch_start", None)
                    if state is not None
                    else None
                )
                epoch_window_from = coverage_date_from_for_epoch(
                    now=now_utc,
                    epoch_start=epoch_start
                    if isinstance(epoch_start, datetime)
                    else None,
                )
                coverage_date_from = max(
                    coverage_first_available_bucket_start,
                    epoch_window_from,
                )
                coverage_rows = await self._analytics.get_bid_coverages(
                    nmid=nmid,
                    date_from=coverage_date_from,
                    date_to=now_utc,
                    currency=currency,
                    price_minor=None,
                    mode=None,
                )
            coverage_selected_next_test_bid_minor = choose_next_test_bid_by_coverage_layers(
                min_bid_minor=min_bid_minor_value,
                max_bid_minor=max_bid_minor_value,
                bid_unit_minor=100,
                coverages=coverage_rows,
                target_test_impressions=target_test_impressions_value,
                target_test_observation_hours=target_test_observation_hours_value,
                min_bid_distance_minor=int(settings_obj.min_bid_distance_minor),
                random_seed=build_coverage_selector_seed(
                    nmid=nmid,
                    currency=currency,
                    price_minor=None,
                    min_bid_minor=min_bid_minor_value,
                    max_bid_minor=max_bid_minor_value,
                    min_bid_distance_minor=int(settings_obj.min_bid_distance_minor),
                    target_test_impressions=target_test_impressions_value,
                    target_test_observation_hours=target_test_observation_hours_value,
                ),
            )
            if adv.auto_shelf_bid_control_strategy == AutoShelfBidControlStrategy.PLAN_DISTANCE:
                next_test_bid_minor = coverage_selected_next_test_bid_minor
            else:
                next_test_bid_minor = legacy_cycle_next_test_bid_minor
            universe = build_bid_universe(
                min_bid_minor_value,
                max_bid_minor_value,
                bid_unit_minor=100,
            )
            coverage_map = {int(item.bid_minor): item for item in coverage_rows}
            closed_by_bid: dict[int, int] = {}
            for bid in universe:
                coverage = coverage_map.get(bid)
                impressions = 0 if coverage is None else int(coverage.impressions)
                valid_hours = 0 if coverage is None else int(coverage.valid_hours)
                closed_by_bid[bid] = closed_layers_for_bid(
                    impressions=impressions,
                    valid_hours=valid_hours,
                    target_test_impressions=target_test_impressions_value,
                    target_test_observation_hours=target_test_observation_hours_value,
                )
            coverage_current_layer = min(closed_by_bid.values()) if closed_by_bid else 0
            coverage_undercovered_count = sum(
                1 for closed in closed_by_bid.values() if closed == coverage_current_layer
            )
            coverage_bid_rows = AutoShelfBidControlViewProvider._build_coverage_layer_rows(
                universe=universe,
                coverages=coverage_rows,
                current_layer=coverage_current_layer,
                selected_next_test_bid_minor=coverage_selected_next_test_bid_minor,
                current_main_bid_minor=(state.current_main_bid_minor if state else None),
                current_test_bid_minor=(state.current_test_bid_minor if state else None),
                best_plan_bid_minor=best_plan_bid_minor,
                global_best_bid_minor=(
                    global_best.bid_minor
                    if global_best is not None
                    else (best.bid_minor if best is not None else None)
                ),
                min_bid_minor=min_bid_minor_value,
                max_bid_minor=max_bid_minor_value,
                target_test_impressions=target_test_impressions_value,
                target_test_observation_hours=target_test_observation_hours_value,
                forecast_by_bid=AutoShelfBidControlViewProvider._parse_plan_ranked_forecasts(
                    rec_bid_recommendation
                ),
            )
            coverage_bid_rows = AutoShelfBidControlViewProvider._sort_coverage_layer_rows(
                coverage_bid_rows,
                plan_ranked_scores=AutoShelfBidControlViewProvider._parse_plan_ranked_scores(
                    rec_bid_recommendation
                ),
                selected_next_test_bid_minor=coverage_selected_next_test_bid_minor,
            )

        control_enabled = bool(adv.auto_shelf_bid_control_enabled)
        recommended_main_bid_minor: int | None = None
        main_target_explanation: str | None = None
        recommended_next_test_bid_minor = coverage_selected_next_test_bid_minor
        fresh_best_main_bid_minor: int | None = None
        fresh_next_test_bid_minor = recommended_next_test_bid_minor
        qualified_tested_bids_count: int | None = None
        can_count_progress = False
        snapshot_min_bid_minor = min_bid_minor_value
        if snapshot_min_bid_minor is None and cycle_bid_stats:
            snapshot_min_bid_minor = min(
                int(item.bid_minor) for item in cycle_bid_stats
            )
        if (
            state is not None
            and settings_obj is not None
            and snapshot_min_bid_minor is not None
            and nmid
            and inspect.iscoroutinefunction(
                getattr(self._analytics, "fetch_rec_bid_ctr_by_bid_for_nmid", None)
            )
        ):
            try:
                snapshot_manager = AutoShelfBidControlManager(
                    bid_cache_manager=self._bid_cache,
                    wb_bid_setter=AutoShelfBidSetter(
                        wb_modifier=cast(Any, object()),
                        bid_cache_manager=None,
                    ),
                    repository=self._repository,
                    analytics_repository=self._analytics,
                )
                complex_adv_like = cast(
                    ComplexAdv,
                    type(
                        "_ViewComplexAdv",
                        (),
                        {
                            "main_nmid": nmid,
                            "auto_adv_id": auto_adv_id,
                            "nmids": [nmid],
                            "bot_active": bool(getattr(adv, "bot_active", True)),
                            "auto_adv_active_status": bool(
                                getattr(adv, "auto_adv_active_status", True)
                            ),
                            "auto_shelf_bid_control_enabled": control_enabled,
                            "auto_shelf_bid_control_strategy": normalized_strategy,
                            "adv_setting": adv,
                            "fact_pay_for_order": fact_cpo,
                            "resolve_cpo": resolve_cpo,
                            "original_max_cpo": getattr(adv, "original_max_cpo", None),
                            "min_nmids_bids": None,
                        },
                    )(),
                )
                decision_snapshot = await snapshot_manager.build_decision_snapshot(
                    complex_adv_like,
                    settings_obj=settings_obj,
                    state=state,
                    min_bid_minor=snapshot_min_bid_minor,
                    actual_bid_minor=actual_bid_minor,
                    control_enabled=control_enabled,
                    bid_units_confirmed=bid_units_confirmed,
                )
                if decision_snapshot.rec_bid_recommendation is not None:
                    rec_bid_recommendation = decision_snapshot.rec_bid_recommendation
                recommended_main_bid_minor = decision_snapshot.fresh_best_main_bid_minor
                fresh_best_main_bid_minor = decision_snapshot.fresh_best_main_bid_minor
                qualified_tested_bids_count = (
                    decision_snapshot.qualified_tested_bids_count
                )
                if decision_snapshot.fresh_next_test_bid_minor is not None:
                    recommended_next_test_bid_minor = (
                        decision_snapshot.fresh_next_test_bid_minor
                    )
                    fresh_next_test_bid_minor = recommended_next_test_bid_minor
                    next_test_bid_minor = recommended_next_test_bid_minor
                if decision_snapshot.main_target_explanation is not None:
                    main_target_explanation = decision_snapshot.main_target_explanation
                can_count_progress = decision_snapshot.can_count_progress
            except Exception:
                logger.warning(
                    "decision_snapshot_failed nmid=%s adv_setting_original_id=%s",
                    nmid,
                    adv_setting_original_id,
                    exc_info=True,
                )

        expected_enforced_bid_minor = resolve_expected_bid_minor(
            current_mode=(state.current_mode if state else None),
            fresh_best_main_bid_minor=recommended_main_bid_minor,
            fresh_next_test_bid_minor=recommended_next_test_bid_minor,
            control_enabled=control_enabled,
        )
        bid_sync_detail = resolve_bid_sync_detail(
            actual_bid_minor,
            expected_enforced_bid_minor,
            control_enabled=control_enabled,
        )
        primary_status = resolve_primary_status(
            control_enabled=control_enabled,
            last_reason=(state.last_reason if state else None),
        )

        # derive some extra diagnostics fields required by UI semantics
        best_cpo_bid_rub_value: float | None = None
        if rec_bid_recommendation is not None:
            # prefer top plan_ranked row CPO when available (best recommendation)
            plan_ranked_list = cast(list[object], rec_bid_recommendation.get("plan_ranked", []))
            if plan_ranked_list:
                top_row = as_object_dict(plan_ranked_list[0])
                if top_row is not None:
                    cpo_raw = top_row.get("cpo_rub")
                    if cpo_raw is None:
                        cpo_raw = top_row.get("expected_order_cost_rub")
                    best_cpo_bid_rub_value = coerce_finite_float(cpo_raw)

        # current WB bid in rubles (from actual_bid_minor)
        current_bid_rub_value: float | None = None
        if actual_bid_minor is not None:
            current_bid_rub_value = float(int(actual_bid_minor)) / 100.0

        # expected/control bid in rubles
        expected_bid_rub_value: float | None = None
        if expected_enforced_bid_minor is not None:
            expected_bid_rub_value = float(int(expected_enforced_bid_minor)) / 100.0

        # selected CPO details (search recommendation rows regardless of sync/applied)
        selected_cpo_value: float | None = None
        unavailable_reason_value: str | None = None
        try:
            selected_cpo_value, unavailable_reason_value = extract_selected_cpo_details_from_view(
                cast(AutoShelfBidControlViewDTO, SimpleNamespace(  # type: ignore[name-defined]
                    expected_enforced_bid_minor=expected_enforced_bid_minor,
                    rec_bid_recommendation=rec_bid_recommendation,
                ))
            )
        except Exception:
            selected_cpo_value, unavailable_reason_value = None, "selected_cpo_extraction_failed"

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
            retest_interval_days=(
                int(getattr(settings_obj, "retest_interval_days", 7))
                if settings_obj
                else 7
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
            coverage_first_available_bucket_start=coverage_first_available_bucket_start,
            coverage_current_layer=coverage_current_layer,
            coverage_undercovered_count=coverage_undercovered_count,
            coverage_selected_next_test_bid_minor=coverage_selected_next_test_bid_minor,
            coverage_bid_rows=coverage_bid_rows,
            last_reason=(state.last_reason if state else None),
            warnings=warnings,
            rec_bid_recommendation=rec_bid_recommendation,
            optimization_metric=optimization_metric,
            fact_cpo=fact_cpo,
            resolve_cpo=resolve_cpo,
            auto_shelf_bid_control_strategy=normalized_strategy,
            best_plan_bid_minor=best_plan_bid_minor,
            fresh_best_main_bid_minor=fresh_best_main_bid_minor,
            fresh_next_test_bid_minor=fresh_next_test_bid_minor,
            recommended_main_bid_minor=recommended_main_bid_minor,
            recommended_next_test_bid_minor=recommended_next_test_bid_minor,
            expected_enforced_bid_minor=expected_enforced_bid_minor,
            primary_status=primary_status,
            bid_sync_detail=bid_sync_detail,
            # new diagnostics fields
            best_cpo_bid_rub=best_cpo_bid_rub_value,
            current_bid_rub=current_bid_rub_value,
            expected_bid_rub=expected_bid_rub_value,
            selected_cpo_rub=selected_cpo_value,
            bid_sync_status=bid_sync_detail,
            unavailable_reason=unavailable_reason_value,
            can_count_progress=can_count_progress,
            main_target_explanation=main_target_explanation,
            legacy_cycle_next_test_bid_minor=legacy_cycle_next_test_bid_minor,
            state_updated_at=truncate_datetime_to_seconds(
                state.updated_at if state else None
            ),
            qualified_tested_bids_count=qualified_tested_bids_count,
        )

    async def build_selected_cpo_contract(
        self,
        adv_setting_original_id: int,
    ) -> AutoShelfBidSelectedCpoContract:
        """Собрать read-only контракт для selected/current/applied CPO."""
        view = await self.build_view(adv_setting_original_id)
        return resolve_selected_cpo_contract_from_view(view)

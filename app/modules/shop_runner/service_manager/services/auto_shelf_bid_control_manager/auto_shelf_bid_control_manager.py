"""Оркестратор управления общей ставкой полок Auto-РК (main/test)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, UTC, timedelta

from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlSettings,
    AutoShelfBidControlState,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_recommendation_read_service import (
    AutoShelfBidRecommendationReadService,
)
from app.core.mp.wb.dto import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost

from .auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)
from .bid_selection import resolve_cycle_best_bids
from .bid_units import (
    report_day_start_utc,
    resolve_test_segment_start_utc,
    wb_min_cpm_rub_to_bid_minor,
)
from .auto_shelf_bid_control_repository import AutoShelfBidControlRepository
from .settings_normalizer import repair_state_test_bid_minor
from .auto_shelf_bid_setter import AutoShelfBidSetter
from .dto import BidStatsDTO

logger = logging.getLogger(__name__)


class ControlReason:
    """Строковые причины переходов/скипов control-модуля."""

    INITIALIZED = "initialized"
    DISABLED = "disabled"
    NO_SETTINGS = "no_settings"
    SINGLE_NMID_GUARD_SKIP = "single_nmid_guard_skip"
    NO_AUTO_ADV = "no_auto_adv"
    NO_MIN_BID = "no_min_bid"
    NO_ACTUAL_BID = "no_actual_bid"
    INVALID_BID_RANGE = "invalid_bid_range"
    INVALID_TEST_SHARE = "invalid_test_share"
    TEST_WAITING_IMPRESSIONS = "test_waiting_impressions"
    TEST_WAITING_OBSERVATION_TIME = "test_waiting_observation_time"
    TEST_COMPLETED_SWITCH_TO_MAIN = "test_completed_switch_to_main"
    MAIN_WAITING_IMPRESSIONS = "main_waiting_impressions"
    MAIN_WAITING_OBSERVATION_TIME = "main_waiting_observation_time"
    MAIN_COMPLETED_SWITCH_TO_TEST = "main_completed_switch_to_test"
    CYCLE_COMPLETED = "cycle_completed"
    BEST_BID_SELECTED = "best_bid_selected"
    BEST_BID_NOT_FOUND = "best_bid_not_found"
    SET_BID_OK = "set_bid_ok"
    SET_BID_FAILED = "set_bid_failed"
    EXTERNAL_BID_CHANGED_REAPPLY = "external_bid_changed_reapply"
    MANUAL_CYCLE_RESET = "manual_cycle_reset"
    SETTINGS_UPDATED = "settings_updated"


class AutoShelfBidControlManager:
    """Управляет циклом main/test для ставки полок по single-nmid."""

    def __init__(
        self,
        *,
        bid_cache_manager: RedisAutoRecommendationsBidValueManager,
        wb_bid_setter: AutoShelfBidSetter,
        repository: AutoShelfBidControlRepository | None = None,
        analytics_repository: AutoShelfBidControlAnalyticsRepository | None = None,
    ) -> None:
        self._bid_cache_manager = bid_cache_manager
        self._setter = wb_bid_setter
        self._repository = repository or AutoShelfBidControlRepository()
        self._analytics = analytics_repository or AutoShelfBidControlAnalyticsRepository()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _middle_bid(min_bid: int, max_bid: int) -> int:
        return int(round((min_bid + max_bid) / 2))

    @staticmethod
    def _clamp_bid_minor(
        bid_minor: int,
        *,
        min_bid_minor: int,
        max_bid_minor: int,
    ) -> int:
        """Ограничить ставку окном [min_bid_minor, max_bid_minor] (копейки).

        Исторические точки из CH и устаревший state могут быть вне текущего
        диапазона пользователя / минимума WB.
        """
        lo = int(min_bid_minor)
        hi = int(max_bid_minor)
        if hi < lo:
            hi = lo
        value = int(bid_minor)
        if value < lo:
            return lo
        if value > hi:
            return hi
        return value

    @staticmethod
    def _calc_target_main_impressions(
        target_test_impressions: int,
        test_share: float,
    ) -> int | None:
        if test_share <= 0 or test_share > 0.49:
            return None
        return int(target_test_impressions * (1 - test_share) / test_share)

    @staticmethod
    def _calc_target_main_observation_minutes(
        target_test_observation_minutes: int,
        test_share: float,
    ) -> int | None:
        if test_share <= 0 or test_share > 0.49:
            return None
        return int(target_test_observation_minutes * (1 - test_share) / test_share)

    @staticmethod
    def _target_observation_minutes_or_default(
        value: int | None,
    ) -> int:
        """Вернуть безопасный fallback для nullable observation minutes.

        В БД поле nullable, поэтому отсутствие значения не должно останавливать
        control loop. Для такого случая используем 0, чтобы дальше сработали
        обычные проверки по impressions.
        """
        return 0 if value is None else int(value)

    @staticmethod
    def _elapsed_minutes(started_at: datetime | None, now: datetime) -> int | None:
        if started_at is None:
            return None
        elapsed = int((now - started_at).total_seconds() // 60)
        return max(0, elapsed)

    async def _get_actual_bid(self, auto_adv_id: int, nmid: int) -> int | None:
        cached = await self._bid_cache_manager.get_bid(auto_adv_id, nmid)
        if cached is None:
            return None
        return int(cached.bid_minor)

    @staticmethod
    def resolve_wb_min_bid_minor(
        min_bids: AdvMinNmidsBids | None,
        nmid: int,
    ) -> int | None:
        """Минимальная ставка WB (auto/полки) в ``bid_minor`` (копейки).

        ``AdvMinNmidsBids.auto`` — legacy CPM в рублях; конвертируем ×100.
        """
        if min_bids is None:
            return None
        value = min_bids.auto.get(nmid)
        if value is None or int(value) <= 0:
            return None
        return wb_min_cpm_rub_to_bid_minor(int(value))

    @staticmethod
    def _resolve_min_bid_minor(complex_adv: ComplexAdv, nmid: int) -> int | None:
        """Нижняя граница диапазона тестов — только минимальная ставка WB."""
        return AutoShelfBidControlManager.resolve_wb_min_bid_minor(
            complex_adv.min_nmids_bids,
            nmid,
        )

    @classmethod
    def choose_next_test_bid(
        cls,
        min_bid: int,
        max_bid: int,
        covered_bids: list[int],
        min_distance: int,
    ) -> int | None:
        """Выбрать середину самого широкого зазора между покрытыми ставками цикла.

        Кандидат не может совпадать с уже покрытой ставкой (``covered_bids``).
        """
        if max_bid < min_bid:
            return None
        if not covered_bids:
            return cls._middle_bid(min_bid, max_bid)
        covered = sorted(set(int(x) for x in covered_bids))
        covered_set = set(covered)
        candidates: list[tuple[int, int]] = []
        if min_bid not in covered_set:
            candidates.append((abs(covered[0] - min_bid), min_bid))
        if max_bid not in covered_set:
            candidates.append((abs(max_bid - covered[-1]), max_bid))
        for left, right in zip(covered, covered[1:]):
            mid = int(round((left + right) / 2))
            if mid in covered_set:
                continue
            distance = min(abs(mid - left), abs(right - mid))
            candidates.append((distance, mid))
        if not candidates:
            return None
        max_distance, bid = max(candidates, key=lambda x: (x[0], -x[1]))
        if max_distance < min_distance:
            return None
        return bid

    @classmethod
    def is_coroutine_candidate(cls, complex_adv: ComplexAdv) -> bool:
        """Кампании для тика ``auto_shelf_bid_control`` (без лишних skip-логов)."""
        if not complex_adv.auto_shelf_bid_control_enabled:
            return False
        if len(complex_adv.nmids) != 1:
            return False
        if not complex_adv.bot_active:
            return False
        if not complex_adv.auto_adv_active_status:
            return False
        if complex_adv.auto_adv_id is None:
            return False
        return True

    def _is_eligible(self, complex_adv: ComplexAdv) -> tuple[bool, str]:
        if not complex_adv.bot_active:
            return False, ControlReason.DISABLED
        if not complex_adv.auto_adv_active_status:
            return False, ControlReason.DISABLED
        if not complex_adv.auto_shelf_bid_control_enabled:
            return False, ControlReason.DISABLED
        if complex_adv.auto_adv_id is None:
            return False, ControlReason.NO_AUTO_ADV
        if len(complex_adv.nmids) != 1:
            return False, ControlReason.SINGLE_NMID_GUARD_SKIP
        return True, ControlReason.SETTINGS_UPDATED

    async def _set_target_bid(
        self,
        complex_adv: ComplexAdv,
        bid_minor: int,
        currency: str,
    ) -> None:
        await self._setter.set_bid(
            complex_adv,
            bid_minor=bid_minor,
            currency=currency,
        )

    async def _persist_state_then_set_bid(
        self,
        complex_adv: ComplexAdv,
        *,
        state: AutoShelfBidControlState,
        bid_minor: int,
    ) -> None:
        """Сохранить фазу цикла в PG, затем PATCH WB.

        Единый порядок для test↔main: при сбое PATCH increment/control на
        следующем тике видят верный ``current_mode`` и дожимают ставку.
        """
        await self._repository.save_state(state)
        await self._set_target_bid(
            complex_adv,
            bid_minor=bid_minor,
            currency=state.currency,
        )

    async def _choose_best_bid_with_fallback(
        self,
        *,
        nmid: int,
        currency: str,
        cycle_started_at: datetime,
        previous_cycle_started_at: datetime | None,
        current_main_bid_minor: int | None,
        actual_bid_minor: int | None,
        min_bid_minor: int,
        max_bid_minor: int,
        fact_cpo: float | None = None,
        resolve_cpo: float | None = None,
    ) -> int:
        def _in_window(bid: int) -> int:
            return self._clamp_bid_minor(
                bid,
                min_bid_minor=min_bid_minor,
                max_bid_minor=max_bid_minor,
            )

        report_from = report_day_start_utc()
        _, _, global_best = await resolve_cycle_best_bids(
            self._analytics,
            nmid=nmid,
            currency=currency,
            current_cycle_started_at=cycle_started_at,
            previous_cycle_started_at=previous_cycle_started_at,
            fact_cpo=fact_cpo,
            resolve_cpo=resolve_cpo,
        )
        if global_best is not None:
            return _in_window(global_best.bid_minor)

        # Fallback к статистике за день с учётом метрики оптимизации
        from .dto import OptimizationMetric, resolve_optimization_metric
        metric = resolve_optimization_metric(fact_cpo, resolve_cpo)

        if metric == OptimizationMetric.CTR:
            best = await self._analytics.get_best_bid_by_ctr(
                nmid=nmid,
                from_ts=report_from,
                currency=currency,
            )
        else:
            best = await self._analytics.get_best_bid_by_cart_cpa(
                nmid=nmid,
                from_ts=report_from,
                currency=currency,
            )
        if best is not None:
            return _in_window(best.bid_minor)
        if current_main_bid_minor is not None:
            return _in_window(current_main_bid_minor)
        if actual_bid_minor is not None:
            return _in_window(actual_bid_minor)
        return self._middle_bid(min_bid_minor, max_bid_minor)

    async def _choose_main_bid_by_strategy(
        self,
        *,
        complex_adv: ComplexAdv,
        current_cycle_started_at: datetime,
        previous_cycle_started_at: datetime | None,
        current_main_bid_minor: int | None,
        actual_bid_minor: int | None,
        min_bid_minor: int,
        max_bid_minor: int,
    ) -> int | None:
        """Выбрать main bid по стратегии кампании.

        PLAN_DISTANCE использует rec-bid plan-ranked recommendation.
        Если рекомендация недоступна, возвращает ``None`` без cycle fallback.
        """
        strategy = complex_adv.auto_shelf_bid_control_strategy
        if strategy == AutoShelfBidControlStrategy.CYCLE_METRIC:
            return await self._choose_best_bid_with_fallback(
                nmid=complex_adv.main_nmid,
                currency=complex_adv.adv_setting.currency,
                cycle_started_at=current_cycle_started_at,
                previous_cycle_started_at=previous_cycle_started_at,
                current_main_bid_minor=current_main_bid_minor,
                actual_bid_minor=actual_bid_minor,
                min_bid_minor=min_bid_minor,
                max_bid_minor=max_bid_minor,
                fact_cpo=complex_adv.fact_pay_for_order,
                resolve_cpo=complex_adv.resolve_cpo,
            )

        try:
            rec_repository = self._analytics
            now = self._now()
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
            target_order_cost = resolve_target_cost(
                complex_adv.adv_setting.plan_for_sales_for_day,
                complex_adv.adv_setting.target_price_for_order,
                complex_adv.adv_setting.max_price_for_order,
                fact_predict_orders,
            )
            if target_order_cost is None:
                target_order_cost = float(complex_adv.adv_setting.max_price_for_order or 0.0)
            plan_context = PlanContext(
                sales_plan=float(complex_adv.adv_setting.plan_for_sales_for_day or 0.0),
                current_fact_sales=float(fact_predict_orders or 0.0),
                current_sales_forecast=float(fact_predict_orders or 0.0),
                target_order_cost=target_order_cost,
                max_order_cost=float(complex_adv.adv_setting.max_price_for_order or 0.0),
                click_to_order_cr_7d=click_to_order_cr_7d,
            )
            rec_service = AutoShelfBidRecommendationReadService(rec_repository)
            rec_result = await rec_service.get_rec_bid_recommendations(
                nmid=complex_adv.main_nmid,
                mode=None,
                date_from=rec_date_from,
                date_to=rec_date_to,
                plan_context=plan_context,
                ctr_by_bid=ctr_by_bid,
            )
            best_plan_bid = rec_result.get("best_plan_bid")
            if best_plan_bid is None:
                return None
            return self._clamp_bid_minor(
                int(best_plan_bid),
                min_bid_minor=min_bid_minor,
                max_bid_minor=max_bid_minor,
            )
        except Exception:
            logger.warning(
                "auto_shelf_bid_control_plan_distance_unavailable auto_adv_id=%s nmid=%s strategy=%s",
                complex_adv.auto_adv_id,
                complex_adv.main_nmid,
                strategy,
                exc_info=True,
            )
            return None

    async def _initialize_state(
        self,
        *,
        complex_adv: ComplexAdv,
        settings_obj: AutoShelfBidControlSettings,
        min_bid_minor: int,
        actual_bid_minor: int | None,
    ) -> AutoShelfBidControlState:
        max_bid_minor = int(settings_obj.max_bid_minor)
        middle_bid = self._middle_bid(min_bid_minor, max_bid_minor)
        test_bid = middle_bid
        if (
            actual_bid_minor is not None
            and min_bid_minor <= int(actual_bid_minor) <= max_bid_minor
        ):
            test_bid = int(actual_bid_minor)
        main_bid = int(actual_bid_minor) if actual_bid_minor is not None else middle_bid
        now = self._now()
        state = await self._repository.build_state(
            nmid=complex_adv.main_nmid,
            currency=settings_obj.currency,
            current_mode="test",
            current_main_bid_minor=main_bid,
            current_test_bid_minor=test_bid,
            current_cycle_started_at=now,
            previous_cycle_started_at=None,
            main_started_at=None,
            test_started_at=now,
            last_reason=ControlReason.INITIALIZED,
        )
        saved = await self._repository.save_state(state)
        if actual_bid_minor != test_bid:
            await self._set_target_bid(
                complex_adv,
                bid_minor=test_bid,
                currency=settings_obj.currency,
            )
        return saved

    async def update(self, complex_adv: ComplexAdv) -> None:
        """Сделать один тик управления ставкой для одной кампании."""
        eligible, reason = self._is_eligible(complex_adv)
        if not eligible:
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s",
                complex_adv.auto_adv_id,
                (complex_adv.nmids[0] if complex_adv.nmids else None),
                reason,
            )
            return None
        nmid = complex_adv.main_nmid
        auto_adv_id = complex_adv.auto_adv_id
        settings_obj = await self._repository.get_settings(nmid)
        if settings_obj is None:
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s",
                auto_adv_id,
                nmid,
                ControlReason.NO_SETTINGS,
            )
            return None
        actual_bid_minor = await self._get_actual_bid(auto_adv_id, nmid)
        min_bid_minor = self._resolve_min_bid_minor(complex_adv, nmid)
        if min_bid_minor is None:
            await self._repository.update_state_reason(nmid, ControlReason.NO_MIN_BID)
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s",
                auto_adv_id,
                nmid,
                ControlReason.NO_MIN_BID,
            )
            return None
        settings_obj = await self._repository.repair_settings_units(
            nmid=nmid,
            min_bid_minor=min_bid_minor,
            actual_bid_minor=actual_bid_minor,
        )
        state = await self._repository.get_state(nmid)
        if state is not None:
            if repair_state_test_bid_minor(
                state,
                min_bid_minor=min_bid_minor,
                max_bid_minor=int(settings_obj.max_bid_minor),
                actual_bid_minor=actual_bid_minor,
            ):
                state = await self._repository.save_state(state)
        if int(settings_obj.max_bid_minor) < min_bid_minor:
            await self._repository.update_state_reason(nmid, ControlReason.INVALID_BID_RANGE)
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s min=%s max=%s",
                auto_adv_id,
                nmid,
                ControlReason.INVALID_BID_RANGE,
                min_bid_minor,
                settings_obj.max_bid_minor,
            )
            return None
        if actual_bid_minor is None:
            await self._repository.update_state_reason(nmid, ControlReason.NO_ACTUAL_BID)
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s",
                auto_adv_id,
                nmid,
                ControlReason.NO_ACTUAL_BID,
            )
            return None

        if state is None:
            initialized = await self._initialize_state(
                complex_adv=complex_adv,
                settings_obj=settings_obj,
                min_bid_minor=min_bid_minor,
                actual_bid_minor=actual_bid_minor,
            )
            logger.info(
                "auto_shelf_bid_control_initialized auto_adv_id=%s nmid=%s mode=%s main_bid=%s test_bid=%s reason=%s",
                auto_adv_id,
                nmid,
                initialized.current_mode,
                initialized.current_main_bid_minor,
                initialized.current_test_bid_minor,
                initialized.last_reason,
            )
            return None

        if state.current_mode == "test":
            await self._handle_test_mode(
                complex_adv=complex_adv,
                settings_obj=settings_obj,
                state=state,
                min_bid_minor=min_bid_minor,
                actual_bid_minor=actual_bid_minor,
            )
            return None

        await self._handle_main_mode(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=min_bid_minor,
            actual_bid_minor=actual_bid_minor,
        )
        return None

    async def _handle_test_mode(
        self,
        *,
        complex_adv: ComplexAdv,
        settings_obj: AutoShelfBidControlSettings,
        state: AutoShelfBidControlState,
        min_bid_minor: int,
        actual_bid_minor: int,
    ) -> None:
        nmid = complex_adv.main_nmid
        auto_adv_id = complex_adv.auto_adv_id
        now = self._now()
        test_bid = state.current_test_bid_minor
        if test_bid is None:
            test_bid = self._middle_bid(min_bid_minor, int(settings_obj.max_bid_minor))
            state.current_test_bid_minor = test_bid
            state.test_started_at = state.test_started_at or now
        test_started_at = resolve_test_segment_start_utc(
            test_started_at=state.test_started_at,
            current_cycle_started_at=state.current_cycle_started_at,
            fallback_now=now,
        )
        test_elapsed_minutes = self._elapsed_minutes(test_started_at, now)
        target_test_observation_minutes = self._target_observation_minutes_or_default(
            settings_obj.target_test_observation_minutes
        )
        test_impressions = await self._analytics.get_impressions(
            nmid=nmid,
            from_ts=test_started_at,
            currency=state.currency,
            bid_minor=test_bid,
        )
        if (
            test_elapsed_minutes is None
            or test_elapsed_minutes < target_test_observation_minutes
        ):
            state.last_reason = ControlReason.TEST_WAITING_OBSERVATION_TIME
            if actual_bid_minor != test_bid:
                await self._set_target_bid(
                    complex_adv,
                    bid_minor=test_bid,
                    currency=state.currency,
                )
                state.last_reason = ControlReason.EXTERNAL_BID_CHANGED_REAPPLY
            await self._repository.save_state(state)
            logger.info(
                "auto_shelf_bid_control_test_wait_time auto_adv_id=%s nmid=%s mode=%s test_elapsed_minutes=%s target=%s reason=%s",
                auto_adv_id,
                nmid,
                state.current_mode,
                test_elapsed_minutes,
                target_test_observation_minutes,
                state.last_reason,
            )
            return None
        if test_impressions < int(settings_obj.target_test_impressions):
            if actual_bid_minor != test_bid:
                await self._set_target_bid(
                    complex_adv,
                    bid_minor=test_bid,
                    currency=state.currency,
                )
                state.last_reason = ControlReason.EXTERNAL_BID_CHANGED_REAPPLY
            else:
                state.last_reason = ControlReason.TEST_WAITING_IMPRESSIONS
            await self._repository.save_state(state)
            logger.info(
                "auto_shelf_bid_control_test_wait auto_adv_id=%s nmid=%s mode=%s test_impressions=%s target=%s reason=%s",
                auto_adv_id,
                nmid,
                state.current_mode,
                test_impressions,
                settings_obj.target_test_impressions,
                state.last_reason,
            )
            return None

        best_bid = await self._choose_main_bid_by_strategy(
            complex_adv=complex_adv,
            current_cycle_started_at=state.current_cycle_started_at,
            previous_cycle_started_at=state.previous_cycle_started_at,
            current_main_bid_minor=state.current_main_bid_minor,
            actual_bid_minor=actual_bid_minor,
            min_bid_minor=min_bid_minor,
            max_bid_minor=int(settings_obj.max_bid_minor),
        )
        if best_bid is None:
            state.last_reason = ControlReason.BEST_BID_NOT_FOUND
            await self._repository.save_state(state)
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s strategy=%s",
                auto_adv_id,
                nmid,
                state.last_reason,
                complex_adv.auto_shelf_bid_control_strategy,
            )
            return None
        state.current_main_bid_minor = best_bid
        state.current_mode = "main"
        state.main_started_at = now
        state.last_reason = ControlReason.TEST_COMPLETED_SWITCH_TO_MAIN
        await self._persist_state_then_set_bid(
            complex_adv,
            state=state,
            bid_minor=best_bid,
        )
        logger.info(
            "auto_shelf_bid_control_switch_to_main auto_adv_id=%s nmid=%s main_bid=%s reason=%s",
            auto_adv_id,
            nmid,
            best_bid,
            state.last_reason,
        )
        return None

    async def _handle_main_mode(
        self,
        *,
        complex_adv: ComplexAdv,
        settings_obj: AutoShelfBidControlSettings,
        state: AutoShelfBidControlState,
        min_bid_minor: int,
        actual_bid_minor: int,
    ) -> None:
        nmid = complex_adv.main_nmid
        auto_adv_id = complex_adv.auto_adv_id
        now = self._now()
        target_main_impressions = self._calc_target_main_impressions(
            int(settings_obj.target_test_impressions),
            float(settings_obj.test_share),
        )
        if target_main_impressions is None:
            state.last_reason = ControlReason.INVALID_TEST_SHARE
            await self._repository.save_state(state)
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s test_share=%s",
                auto_adv_id,
                nmid,
                state.last_reason,
                settings_obj.test_share,
            )
            return None

        max_bid = int(settings_obj.max_bid_minor)
        main_bid = state.current_main_bid_minor
        if main_bid is None:
            main_bid = self._middle_bid(min_bid_minor, max_bid)
            state.current_main_bid_minor = main_bid
            state.main_started_at = state.main_started_at or now
        else:
            clamped_main = self._clamp_bid_minor(
                main_bid,
                min_bid_minor=min_bid_minor,
                max_bid_minor=max_bid,
            )
            if clamped_main != int(main_bid):
                main_bid = clamped_main
                state.current_main_bid_minor = main_bid
        if state.current_main_bid_minor is not None and state.main_started_at is None:
            state.main_started_at = now
            state.last_reason = ControlReason.MAIN_WAITING_OBSERVATION_TIME
            await self._repository.save_state(state)
            logger.info(
                "auto_shelf_bid_control_main_bootstrap_started_at auto_adv_id=%s nmid=%s mode=%s main_bid=%s reason=%s",
                auto_adv_id,
                nmid,
                state.current_mode,
                state.current_main_bid_minor,
                state.last_reason,
            )
            return None
        main_started_at = state.main_started_at
        main_elapsed_minutes = self._elapsed_minutes(main_started_at, now)
        target_main_observation_minutes = self._calc_target_main_observation_minutes(
            self._target_observation_minutes_or_default(
                settings_obj.target_test_observation_minutes
            ),
            float(settings_obj.test_share),
        )
        if target_main_observation_minutes is None:
            state.last_reason = ControlReason.INVALID_TEST_SHARE
            await self._repository.save_state(state)
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s test_share=%s",
                auto_adv_id,
                nmid,
                state.last_reason,
                settings_obj.test_share,
            )
            return None
        if (
            main_elapsed_minutes is None
            or main_elapsed_minutes < target_main_observation_minutes
        ):
            if actual_bid_minor != main_bid:
                await self._set_target_bid(
                    complex_adv,
                    bid_minor=main_bid,
                    currency=state.currency,
                )
                state.last_reason = ControlReason.EXTERNAL_BID_CHANGED_REAPPLY
            else:
                state.last_reason = ControlReason.MAIN_WAITING_OBSERVATION_TIME
            await self._repository.save_state(state)
            logger.info(
                "auto_shelf_bid_control_main_wait_time auto_adv_id=%s nmid=%s mode=%s main_elapsed_minutes=%s target=%s reason=%s",
                auto_adv_id,
                nmid,
                state.current_mode,
                main_elapsed_minutes,
                target_main_observation_minutes,
                state.last_reason,
            )
            return None
        main_impressions = await self._analytics.get_impressions(
            nmid=nmid,
            from_ts=main_started_at,
            currency=state.currency,
            bid_minor=main_bid,
            mode="main",
        )
        if main_impressions < target_main_impressions:
            if actual_bid_minor != main_bid:
                await self._set_target_bid(
                    complex_adv,
                    bid_minor=main_bid,
                    currency=state.currency,
                )
                state.last_reason = ControlReason.EXTERNAL_BID_CHANGED_REAPPLY
            else:
                state.last_reason = ControlReason.MAIN_WAITING_IMPRESSIONS
            await self._repository.save_state(state)
            logger.info(
                "auto_shelf_bid_control_main_wait auto_adv_id=%s nmid=%s mode=%s main_impressions=%s target=%s reason=%s",
                auto_adv_id,
                nmid,
                state.current_mode,
                main_impressions,
                target_main_impressions,
                state.last_reason,
            )
            return None

        target_main_bid = await self._choose_main_bid_by_strategy(
            complex_adv=complex_adv,
            current_cycle_started_at=state.current_cycle_started_at,
            previous_cycle_started_at=state.previous_cycle_started_at,
            current_main_bid_minor=state.current_main_bid_minor,
            actual_bid_minor=actual_bid_minor,
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid,
        )
        if target_main_bid is None:
            state.last_reason = ControlReason.BEST_BID_NOT_FOUND
            await self._repository.save_state(state)
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s strategy=%s",
                auto_adv_id,
                nmid,
                state.last_reason,
                complex_adv.auto_shelf_bid_control_strategy,
            )
            return None
        if int(main_bid) != target_main_bid:
            main_bid = target_main_bid
            state.current_main_bid_minor = main_bid
            state.main_started_at = now

        cycle_from_ts = state.current_cycle_started_at
        if cycle_from_ts is None:
            cycle_from_ts = now
        covered_stats = await self._analytics.get_bid_stats(
            nmid=nmid,
            from_ts=cycle_from_ts,
            currency=state.currency,
        )
        covered_bids = [
            row.bid_minor
            for row in covered_stats
            if row.impressions >= int(settings_obj.target_test_impressions)
        ]
        next_test_bid = self.choose_next_test_bid(
            min_bid=min_bid_minor,
            max_bid=int(settings_obj.max_bid_minor),
            covered_bids=covered_bids,
            min_distance=int(settings_obj.min_bid_distance_minor),
        )
        if next_test_bid is None:
            best_bid = await self._choose_main_bid_by_strategy(
                complex_adv=complex_adv,
                current_cycle_started_at=state.current_cycle_started_at,
                previous_cycle_started_at=state.previous_cycle_started_at,
                current_main_bid_minor=state.current_main_bid_minor,
                actual_bid_minor=actual_bid_minor,
                min_bid_minor=min_bid_minor,
                max_bid_minor=int(settings_obj.max_bid_minor),
            )
            if best_bid is None:
                state.last_reason = ControlReason.BEST_BID_NOT_FOUND
                await self._repository.save_state(state)
                logger.warning(
                    "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s strategy=%s",
                    auto_adv_id,
                    nmid,
                    state.last_reason,
                    complex_adv.auto_shelf_bid_control_strategy,
                )
                return None
            new_test_bid = self._middle_bid(min_bid_minor, int(settings_obj.max_bid_minor))
            state.previous_cycle_started_at = state.current_cycle_started_at
            state.current_cycle_started_at = now
            state.current_mode = "test"
            state.current_test_bid_minor = new_test_bid
            state.current_main_bid_minor = best_bid
            state.test_started_at = now
            state.main_started_at = None
            state.last_reason = ControlReason.CYCLE_COMPLETED
            await self._persist_state_then_set_bid(
                complex_adv,
                state=state,
                bid_minor=new_test_bid,
            )
            logger.info(
                "auto_shelf_bid_control_cycle_completed auto_adv_id=%s nmid=%s new_test_bid=%s best_main_bid=%s reason=%s",
                auto_adv_id,
                nmid,
                new_test_bid,
                best_bid,
                state.last_reason,
            )
            return None

        state.current_test_bid_minor = next_test_bid
        state.current_mode = "test"
        state.test_started_at = now
        state.last_reason = ControlReason.MAIN_COMPLETED_SWITCH_TO_TEST
        await self._persist_state_then_set_bid(
            complex_adv,
            state=state,
            bid_minor=next_test_bid,
        )
        logger.info(
            "auto_shelf_bid_control_switch_to_test auto_adv_id=%s nmid=%s next_test_bid=%s reason=%s",
            auto_adv_id,
            nmid,
            next_test_bid,
            state.last_reason,
        )
        return None

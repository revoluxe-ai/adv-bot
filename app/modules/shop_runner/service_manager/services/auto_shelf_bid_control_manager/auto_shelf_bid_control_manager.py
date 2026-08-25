"""Оркестратор управления общей ставкой полок Auto-РК (main/test)."""

from __future__ import annotations

import inspect
import logging
from datetime import datetime, UTC
from enum import StrEnum

from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlSettings,
    AutoShelfBidControlState,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.redis_auto_recommendations_bid_value_manager import (
    RedisAutoRecommendationsBidValueManager,
)

from app.core.mp.wb.dto import AdvMinNmidsBids
from app.core.mp.wb.min_bid_defaults import default_min_bid_rub, resolve_auto_min_bid_rub
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from .auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)
from .bid_coverage_selector import (
    BidCoverage,
    build_coverage_selector_seed,
    build_bid_universe,
    closed_layers_for_bid,
    choose_next_test_bid_by_coverage_layers,
)
from .bid_selection import resolve_cycle_best_bids
from .bid_units import (
    report_day_start_utc,
    wb_min_cpm_rub_to_bid_minor,
)
from .auto_shelf_bid_control_repository import AutoShelfBidControlRepository
from .exhausted_pause.decision import coverage_date_from_for_epoch
from .settings_normalizer import repair_state_test_bid_minor
from .auto_shelf_bid_setter import AutoShelfBidSetter
from .dto.decision_snapshot_dto import (
    AutoShelfBidControlDecisionSnapshot,
    can_set_observation_waiting_reason,
    cast_rec_dict,
    resolve_observation_sync_block_reason,
    resolve_recommended_main_bid_minor,
    snapshot_from_state_fallback,
)
from .auto_shelf_bid_control_decision_snapshot_builder import (
    apply_bid_sync_from_snapshot as _apply_bid_sync_from_snapshot,
    build_decision_snapshot as _build_decision_snapshot,
    fetch_plan_distance_rec_result as _fetch_plan_distance_rec_result,
)
from .dto.optimization_metric import OptimizationMetric, resolve_optimization_metric
from .qualified_tested_bids import collect_qualified_tested_bid_minors

from app.settings import settings

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
    TEST_COMPLETED_SWITCH_TO_TEST = "test_completed_switch_to_test"
    MAIN_WAITING_IMPRESSIONS = "main_waiting_impressions"
    MAIN_WAITING_OBSERVATION_TIME = "main_waiting_observation_time"
    MAIN_COMPLETED_SWITCH_TO_TEST = "main_completed_switch_to_test"
    CYCLE_COMPLETED = "cycle_completed"
    BEST_BID_SELECTED = "best_bid_selected"
    BEST_BID_NOT_FOUND = "best_bid_not_found"
    INSUFFICIENT_QUALIFIED_TESTED_BIDS = "insufficient_qualified_tested_bids"
    SET_BID_OK = "set_bid_ok"
    SET_BID_FAILED = "set_bid_failed"
    EXTERNAL_BID_CHANGED_REAPPLY = "external_bid_changed_reapply"
    BID_SYNC_MISMATCH_NOT_APPLIED = "bid_sync_mismatch_not_applied"
    PROGRESS_BLOCKED = "progress_blocked"
    MANUAL_CYCLE_RESET = "manual_cycle_reset"
    SETTINGS_UPDATED = "settings_updated"
    MAIN_BID_REFRESHED = "main_bid_refreshed"


class MainBidRefreshResult(StrEnum):
    """Результат попытки refresh/apply main bid."""

    APPLIED = "applied"
    NO_CHANGE = "no_change"
    SKIPPED_NOT_MAIN = "skipped_not_main"
    SKIPPED_DISABLED = "skipped_disabled"
    SKIPPED_NO_DESIRED_BID = "skipped_no_desired_bid"


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
    def _snap_bid_minor_to_unit(
        bid_minor: int,
        *,
        bid_unit_minor: int = 100,
    ) -> int:
        """Snap a bid to the bid grid, preferring the lower bid on exact ties."""
        if bid_unit_minor <= 0:
            raise ValueError("bid_unit_minor must be positive")
        value = int(bid_minor)
        unit = int(bid_unit_minor)
        remainder = value % unit
        if remainder == 0:
            return value
        lower = value - remainder
        upper = lower + unit
        return lower if remainder * 2 <= unit else upper

    @staticmethod
    def _middle_bid(min_bid: int, max_bid: int) -> int:
        midpoint = int(round((int(min_bid) + int(max_bid)) / 2))
        return AutoShelfBidControlManager._snap_bid_minor_to_unit(midpoint)

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

        SQL NULL и значения ниже минимального порога не должны обходить time gate.
        Бизнесовый минимум observation window — 60 минут.
        """
        if value is None:
            return 60
        normalized = int(value)
        return max(60, normalized)

    @staticmethod
    def _target_observation_hours_from_minutes(minutes: int) -> int:
        """Округлить required observation window вверх до полных часов."""
        normalized_minutes = int(minutes)
        return max(1, (normalized_minutes + 59) // 60)

    @staticmethod
    def _elapsed_minutes(started_at: datetime | None, now: datetime) -> int | None:
        if started_at is None:
            return None
        elapsed = int((now - started_at).total_seconds() // 60)
        return max(0, elapsed)

    @staticmethod
    def _shelf_exhausted_epoch_start(state: object | None) -> datetime | None:
        """Достать typed ``shelf_exhausted_epoch_start`` из state (или None)."""
        if state is None:
            return None
        raw = getattr(state, "shelf_exhausted_epoch_start", None)
        return raw if isinstance(raw, datetime) else None

    @staticmethod
    def _coverage_date_from(
        *,
        first_bucket_start: datetime,
        date_to: datetime,
        epoch_start: datetime | None,
    ) -> datetime:
        """``date_from`` для coverage: max(first_bucket, epoch window clamp)."""
        return max(
            first_bucket_start,
            coverage_date_from_for_epoch(now=date_to, epoch_start=epoch_start),
        )

    async def _closed_layers_for_bid_at(
        self,
        *,
        nmid: int,
        currency: str,
        bid_minor: int,
        date_to: datetime,
        target_test_impressions: int,
        target_test_observation_hours: int,
        epoch_start: datetime | None = None,
    ) -> int:
        """Compute closed layers for one bid at a given point in time."""
        price_minor: int | None = None
        mode: str | None = None
        first_bucket_start = await self._analytics.get_first_available_bid_bucket_start(
            nmid=nmid,
            currency=currency,
            price_minor=price_minor,
            mode=mode,
        )
        if first_bucket_start is None:
            return 0
        coverages = await self._analytics.get_bid_coverages(
            nmid=nmid,
            date_from=self._coverage_date_from(
                first_bucket_start=first_bucket_start,
                date_to=date_to,
                epoch_start=epoch_start,
            ),
            date_to=date_to,
            currency=currency,
            price_minor=price_minor,
            mode=mode,
        )
        coverage_by_bid = {int(item.bid_minor): item for item in coverages}
        coverage = coverage_by_bid.get(
            int(bid_minor),
            BidCoverage(bid_minor=int(bid_minor), impressions=0, valid_hours=0),
        )
        return closed_layers_for_bid(
            impressions=coverage.impressions,
            valid_hours=coverage.valid_hours,
            target_test_impressions=int(target_test_impressions),
            target_test_observation_hours=int(target_test_observation_hours),
        )

    async def _build_coverage_snapshot(
        self,
        *,
        nmid: int,
        currency: str,
        min_bid_minor: int,
        max_bid_minor: int,
        target_test_impressions: int,
        target_test_observation_hours: int,
        min_bid_distance_minor: int,
        date_to: datetime,
        epoch_start: datetime | None = None,
    ) -> tuple[list[BidCoverage], int, int, int | None]:
        """Load accumulated coverage and derive current layer diagnostics."""
        price_minor: int | None = None
        mode: str | None = None
        first_bucket_start = await self._analytics.get_first_available_bid_bucket_start(
            nmid=nmid,
            currency=currency,
            price_minor=price_minor,
            mode=mode,
        )
        coverages: list[BidCoverage]
        if first_bucket_start is None:
            coverages = []
        else:
            coverages = await self._analytics.get_bid_coverages(
                nmid=nmid,
                date_from=self._coverage_date_from(
                    first_bucket_start=first_bucket_start,
                    date_to=date_to,
                    epoch_start=epoch_start,
                ),
                date_to=date_to,
                currency=currency,
                price_minor=price_minor,
                mode=mode,
            )
        next_test_bid = choose_next_test_bid_by_coverage_layers(
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
            bid_unit_minor=100,
            coverages=coverages,
            target_test_impressions=target_test_impressions,
            target_test_observation_hours=target_test_observation_hours,
            min_bid_distance_minor=min_bid_distance_minor,
            random_seed=build_coverage_selector_seed(
                nmid=nmid,
                currency=currency,
                price_minor=price_minor,
                min_bid_minor=min_bid_minor,
                max_bid_minor=max_bid_minor,
                min_bid_distance_minor=min_bid_distance_minor,
                target_test_impressions=target_test_impressions,
                target_test_observation_hours=target_test_observation_hours,
            ),
        )
        coverage_by_bid = {int(item.bid_minor): item for item in coverages}
        current_layer: int | None = None
        covered_anchor_count = 0
        for bid in range(int(min_bid_minor), int(max_bid_minor) + 1, 100):
            coverage = coverage_by_bid.get(
                bid,
                BidCoverage(bid_minor=bid, impressions=0, valid_hours=0),
            )
            closed_layers = closed_layers_for_bid(
                impressions=coverage.impressions,
                valid_hours=coverage.valid_hours,
                target_test_impressions=target_test_impressions,
                target_test_observation_hours=target_test_observation_hours,
            )
            if current_layer is None or closed_layers < current_layer:
                current_layer = closed_layers
        assert current_layer is not None
        for bid in range(int(min_bid_minor), int(max_bid_minor) + 1, 100):
            coverage = coverage_by_bid.get(
                bid,
                BidCoverage(bid_minor=bid, impressions=0, valid_hours=0),
            )
            closed_layers = closed_layers_for_bid(
                impressions=coverage.impressions,
                valid_hours=coverage.valid_hours,
                target_test_impressions=target_test_impressions,
                target_test_observation_hours=target_test_observation_hours,
            )
            if closed_layers > current_layer:
                covered_anchor_count += 1
        return coverages, current_layer, covered_anchor_count, next_test_bid

    @staticmethod
    def repair_cycle_started_at(state: AutoShelfBidControlState) -> bool:
        """Откатить corrupted cycle start назад, не трогая историю test/main."""
        test_started_at = getattr(state, "test_started_at", None)
        current_cycle_started_at = getattr(state, "current_cycle_started_at", None)
        previous_cycle_started_at = getattr(state, "previous_cycle_started_at", None)
        if not isinstance(test_started_at, datetime):
            return False
        if not isinstance(current_cycle_started_at, datetime):
            return False
        if test_started_at >= current_cycle_started_at:
            return False
        if isinstance(previous_cycle_started_at, datetime) and previous_cycle_started_at <= test_started_at:
            state.current_cycle_started_at = previous_cycle_started_at
        else:
            state.current_cycle_started_at = test_started_at
        state.last_reason = "repair_cycle_started_after_test_started"
        return True

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
        При miss — ``settings.MIN_BID_AUTO_DEFAULT``.
        """
        rub = resolve_auto_min_bid_rub(nmid, min_bids)
        if rub <= 0:
            rub = default_min_bid_rub(AdvPlacementType.AUTO_ADV)
        return wb_min_cpm_rub_to_bid_minor(int(rub))

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
            mid = cls._snap_bid_minor_to_unit(int(round((left + right) / 2)))
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
        if not complex_adv.bot_active:
            return False
        if not complex_adv.auto_shelf_bid_control_enabled:
            return False
        return True

    def _is_eligible(self, complex_adv: ComplexAdv) -> tuple[bool, str]:
        if not complex_adv.bot_active:
            return False, ControlReason.DISABLED
        if not complex_adv.auto_adv_active_status:
            return False, ControlReason.DISABLED
        if not complex_adv.auto_shelf_bid_control_enabled:
            return False, ControlReason.DISABLED
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
        bid_minor: int | None,
    ) -> None:
        """Сохранить фазу цикла в PG, затем PATCH WB.

        Единый порядок для test↔main: при сбое PATCH increment/control на
        следующем тике видят верный ``current_mode`` и дожимают ставку.
        """
        _ = await self._repository.save_state(state)
        if bid_minor is None:
            raise ValueError("bid_minor is required for setter path")
        await self._set_target_bid(
            complex_adv,
            bid_minor=bid_minor,
            currency=state.currency,
        )

    async def _block_observation_progress(
        self,
        *,
        state: AutoShelfBidControlState,
        control_enabled: bool,
        snapshot: AutoShelfBidControlDecisionSnapshot,
    ) -> None:
        """Сохранить sync/block reason и остановить observation/progress-path."""
        state.last_reason = resolve_observation_sync_block_reason(
            control_enabled=control_enabled,
            snapshot=snapshot,
        )
        _ = await self._repository.save_state(state)

    async def _reconcile_expected_bid_for_current_mode(
        self,
        complex_adv: ComplexAdv,
        *,
        state: AutoShelfBidControlState,
        actual_bid_minor: int | None,
        min_bid_minor: int,
        max_bid_minor: int,
        now: datetime,
        expected_bid_minor: int | None,
    ) -> bool:
        """Reapply fresh expected bid for the active mode before progress checks.

        Returns ``True`` when the method had to reapply or refresh the mode
        observation window and the caller must stop processing the tick.
        """
        if expected_bid_minor is None:
            return False
        mode = state.current_mode
        clamped_expected_bid = self._clamp_bid_minor(
            int(expected_bid_minor),
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
        )
        if mode == "test":
            if actual_bid_minor == clamped_expected_bid:
                return False
            state.current_test_bid_minor = clamped_expected_bid
            state.test_started_at = now
            state.last_reason = ControlReason.TEST_WAITING_OBSERVATION_TIME
            await self._persist_state_then_set_bid(
                complex_adv,
                state=state,
                bid_minor=clamped_expected_bid,
            )
            logger.info(
                "auto_shelf_bid_control_reconcile_expected_bid "
                "auto_adv_id=%s nmid=%s mode=%s expected_bid=%s clamped_expected_bid=%s actual_bid=%s reason=%s",
                complex_adv.auto_adv_id,
                complex_adv.main_nmid,
                mode,
                expected_bid_minor,
                clamped_expected_bid,
                actual_bid_minor,
                state.last_reason,
            )
            return True
        if mode == "main":
            if actual_bid_minor == clamped_expected_bid:
                return False
            state.current_main_bid_minor = clamped_expected_bid
            state.main_started_at = now
            state.last_reason = ControlReason.MAIN_WAITING_OBSERVATION_TIME
            await self._persist_state_then_set_bid(
                complex_adv,
                state=state,
                bid_minor=clamped_expected_bid,
            )
            logger.info(
                "auto_shelf_bid_control_reconcile_expected_bid "
                "auto_adv_id=%s nmid=%s mode=%s expected_bid=%s clamped_expected_bid=%s actual_bid=%s reason=%s",
                complex_adv.auto_adv_id,
                complex_adv.main_nmid,
                mode,
                expected_bid_minor,
                clamped_expected_bid,
                actual_bid_minor,
                state.last_reason,
            )
            return True
        return False

    async def apply_bid_sync_from_snapshot(
        self,
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
        return await _apply_bid_sync_from_snapshot(
            self,
            complex_adv,
            state=state,
            snapshot=snapshot,
            control_enabled=control_enabled,
            bid_units_confirmed=bid_units_confirmed,
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
            now=now,
        )

    async def build_decision_snapshot(
        self,
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
        return await _build_decision_snapshot(
            self,
            complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=min_bid_minor,
            actual_bid_minor=actual_bid_minor,
            control_enabled=control_enabled,
            bid_units_confirmed=bid_units_confirmed,
        )

    async def _fetch_plan_distance_rec_result(
        self,
        complex_adv: ComplexAdv,
    ) -> dict[str, object] | None:
        """Загрузить rec-bid recommendation для PLAN_DISTANCE без state fallback."""
        return await _fetch_plan_distance_rec_result(self, complex_adv)

    async def _maybe_continue_main_exploration(
        self,
        complex_adv: ComplexAdv,
        *,
        settings_obj: AutoShelfBidControlSettings,
        state: AutoShelfBidControlState,
        min_bid_minor: int,
        now: datetime,
        coverage_snapshot: tuple[list[BidCoverage], int, int, int | None] | None = None,
    ) -> tuple[bool, tuple[list[BidCoverage], int, int, int | None] | None]:
        """Переключить main обратно в test, если PLAN_DISTANCE ещё должен исследовать."""
        if (
            complex_adv.auto_shelf_bid_control_strategy
            != AutoShelfBidControlStrategy.PLAN_DISTANCE
        ):
            return False, coverage_snapshot
        get_first = getattr(self._analytics, "get_first_available_bid_bucket_start", None)
        get_coverages = getattr(self._analytics, "get_bid_coverages", None)
        if not inspect.iscoroutinefunction(get_first) or not inspect.iscoroutinefunction(
            get_coverages
        ):
            return False, coverage_snapshot
        target_test_observation_minutes = self._target_observation_minutes_or_default(
            settings_obj.target_test_observation_minutes
        )
        target_test_observation_hours = self._target_observation_hours_from_minutes(
            target_test_observation_minutes
        )
        bid_universe = build_bid_universe(
            min_bid_minor,
            int(settings_obj.max_bid_minor),
            bid_unit_minor=100,
        )
        if coverage_snapshot is None:
            coverage_snapshot = await self._build_coverage_snapshot(
                nmid=complex_adv.main_nmid,
                currency=state.currency,
                min_bid_minor=min_bid_minor,
                max_bid_minor=int(settings_obj.max_bid_minor),
                target_test_impressions=int(settings_obj.target_test_impressions),
                target_test_observation_hours=target_test_observation_hours,
                min_bid_distance_minor=int(settings_obj.min_bid_distance_minor),
                date_to=now,
                epoch_start=self._shelf_exhausted_epoch_start(state),
            )
        _coverages, _current_layer, covered_anchor_count, next_test_bid = coverage_snapshot
        should_continue_test = (
            len(bid_universe) > 1
            and covered_anchor_count < 2
            and next_test_bid is not None
            and next_test_bid != state.current_test_bid_minor
        )
        if not should_continue_test:
            return False, coverage_snapshot
        state.current_mode = "test"
        state.current_test_bid_minor = next_test_bid
        state.test_started_at = now
        state.main_started_at = None
        state.last_reason = ControlReason.TEST_COMPLETED_SWITCH_TO_TEST
        _ = await self._repository.save_state(state)
        logger.info(
            "auto_shelf_bid_control_continue_test_coverage_bootstrap auto_adv_id=%s nmid=%s covered_anchor_count=%s next_test_bid=%s reason=%s",
            complex_adv.auto_adv_id,
            complex_adv.main_nmid,
            covered_anchor_count,
            next_test_bid,
            state.last_reason,
        )
        return True, coverage_snapshot

    async def apply_main_bid_refresh_if_needed(
        self,
        complex_adv: ComplexAdv,
        *,
        state: AutoShelfBidControlState,
        min_bid_minor: int,
        max_bid_minor: int,
        actual_bid_minor: int | None,
        now: datetime,
    ) -> MainBidRefreshResult:
        """Refresh main bid target and apply it through the safe setter path.

        Returns:
            Explicit refresh outcome for tick/UI orchestration.
        """
        if state.current_mode != "main":
            return MainBidRefreshResult.SKIPPED_NOT_MAIN
        if (
            not getattr(complex_adv, "bot_active", True)
            or not getattr(complex_adv, "auto_adv_active_status", True)
            or not getattr(complex_adv, "auto_shelf_bid_control_enabled", False)
        ):
            return MainBidRefreshResult.SKIPPED_DISABLED
        desired_bid_minor = await self._choose_main_bid_by_strategy(
            complex_adv=complex_adv,
            currency=state.currency,
            current_cycle_started_at=state.current_cycle_started_at,
            previous_cycle_started_at=state.previous_cycle_started_at,
            current_main_bid_minor=state.current_main_bid_minor,
            actual_bid_minor=actual_bid_minor,
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
        )
        if desired_bid_minor is None:
            return MainBidRefreshResult.SKIPPED_NO_DESIRED_BID
        clamped_bid_minor = self._clamp_bid_minor(
            int(desired_bid_minor),
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
        )
        if (
            state.current_main_bid_minor == clamped_bid_minor
            and actual_bid_minor == clamped_bid_minor
        ):
            return MainBidRefreshResult.NO_CHANGE
        state.current_main_bid_minor = clamped_bid_minor
        state.main_started_at = now
        state.last_reason = ControlReason.MAIN_BID_REFRESHED
        await self._persist_state_then_set_bid(
            complex_adv,
            state=state,
            bid_minor=clamped_bid_minor,
        )
        return MainBidRefreshResult.APPLIED

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
        if actual_bid_minor is not None:
            return _in_window(actual_bid_minor)
        return self._middle_bid(min_bid_minor, max_bid_minor)

    async def _choose_main_bid_by_strategy(
        self,
        *,
        complex_adv: ComplexAdv,
        currency: str,
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
                currency=currency,
                cycle_started_at=current_cycle_started_at,
                previous_cycle_started_at=previous_cycle_started_at,
                current_main_bid_minor=current_main_bid_minor,
                actual_bid_minor=actual_bid_minor,
                min_bid_minor=min_bid_minor,
                max_bid_minor=max_bid_minor,
                fact_cpo=complex_adv.fact_pay_for_order,
                resolve_cpo=complex_adv.resolve_cpo,
            )
        if strategy == AutoShelfBidControlStrategy.CTR:
            best = await self._analytics.get_best_bid_by_ctr(
                nmid=complex_adv.main_nmid,
                from_ts=report_day_start_utc(),
                currency=currency,
            )
            return (
                None
                if best is None
                else self._clamp_bid_minor(
                    int(best.bid_minor),
                    min_bid_minor=min_bid_minor,
                    max_bid_minor=max_bid_minor,
                )
            )
        if strategy == AutoShelfBidControlStrategy.CPC:
            best = await self._analytics.get_best_bid_by_cart_cpa(
                nmid=complex_adv.main_nmid,
                from_ts=report_day_start_utc(),
                currency=currency,
            )
            return (
                None
                if best is None
                else self._clamp_bid_minor(
                    int(best.bid_minor),
                    min_bid_minor=min_bid_minor,
                    max_bid_minor=max_bid_minor,
                )
            )

        rec_result = await self._fetch_plan_distance_rec_result(complex_adv)
        if rec_result is None:
            return None
        rec_view = cast_rec_dict(rec_result.get("view", rec_result))
        return resolve_recommended_main_bid_minor(
            rec_view,
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid_minor,
        )

    async def _initialize_state(
        self,
        *,
        complex_adv: ComplexAdv,
        settings_obj: AutoShelfBidControlSettings,
        min_bid_minor: int,
        actual_bid_minor: int | None,
    ) -> AutoShelfBidControlState:
        """Создать и сохранить начальный state; ставку применяет следующий update через sync-path."""
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
        return await self._repository.save_state(state)

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
            snapshot = await self.build_decision_snapshot(
                complex_adv,
                settings_obj=settings_obj,
                state=state,
                min_bid_minor=min_bid_minor,
                actual_bid_minor=actual_bid_minor,
                control_enabled=True,
            )
            if await self.apply_bid_sync_from_snapshot(
                complex_adv,
                state=state,
                snapshot=snapshot,
                control_enabled=True,
                bid_units_confirmed=settings.AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED,
                min_bid_minor=min_bid_minor,
                max_bid_minor=int(settings_obj.max_bid_minor),
                now=self._now(),
            ):
                return None
            await self._handle_test_mode(
                complex_adv=complex_adv,
                settings_obj=settings_obj,
                state=state,
                min_bid_minor=min_bid_minor,
                actual_bid_minor=actual_bid_minor,
                snapshot=snapshot,
            )
            await self._apply_shelf_exhausted_tick(
                complex_adv=complex_adv,
                settings_obj=settings_obj,
                state=state,
                snapshot=snapshot,
            )
            return None

        snapshot = await self.build_decision_snapshot(
            complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=min_bid_minor,
            actual_bid_minor=actual_bid_minor,
            control_enabled=True,
        )
        if await self.apply_bid_sync_from_snapshot(
            complex_adv,
            state=state,
            snapshot=snapshot,
            control_enabled=True,
            bid_units_confirmed=settings.AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED,
            min_bid_minor=min_bid_minor,
            max_bid_minor=int(settings_obj.max_bid_minor),
            now=self._now(),
        ):
            return None
        await self._handle_main_mode(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=min_bid_minor,
            actual_bid_minor=actual_bid_minor,
            snapshot=snapshot,
        )
        await self._apply_shelf_exhausted_tick(
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=state,
            snapshot=snapshot,
        )
        return None

    async def _apply_shelf_exhausted_tick(
        self,
        *,
        complex_adv: ComplexAdv,
        settings_obj: AutoShelfBidControlSettings,
        state: AutoShelfBidControlState,
        snapshot: AutoShelfBidControlDecisionSnapshot,
    ) -> None:
        """Detect/latch/clear shelf-exhausted our-block (PG SoT; без WB pause).

        Terminal plan-fit MUST see the real qualified-tested set (list, possibly
        empty). Passing ``None`` would treat all ``plan_ranked`` rows as fit
        candidates and can skip latch / false-clear our-block.
        """
        from .exhausted_pause.apply_tick import apply_shelf_exhausted_tick

        # Перечитать state: mode handler мог сохранить cycle-поля.
        fresh = await self._repository.get_state(int(state.nmid))
        if fresh is None:
            return None

        # ORM SoT: current_cycle_started_at is Mapped[datetime] (non-Optional).
        cycle_started_at = fresh.current_cycle_started_at
        cycle_bid_stats = await self._analytics.get_bid_stats(
            nmid=int(complex_adv.main_nmid),
            from_ts=cycle_started_at,
            currency=str(fresh.currency),
        )
        # Metric ownership mirrors snapshot builder (explicit strategy first).
        strategy = complex_adv.auto_shelf_bid_control_strategy
        if strategy == AutoShelfBidControlStrategy.CTR:
            cycle_metric = OptimizationMetric.CTR
        elif strategy in {
            AutoShelfBidControlStrategy.CPC,
            AutoShelfBidControlStrategy.CYCLE_METRIC,
        }:
            cycle_metric = OptimizationMetric.CPC
        else:
            cycle_metric = resolve_optimization_metric(
                getattr(complex_adv, "fact_pay_for_order", None),
                getattr(complex_adv, "resolve_cpo", None),
            )
        qualified_tested_bid_minors = collect_qualified_tested_bid_minors(
            cycle_bid_stats,
            target_test_impressions=int(settings_obj.target_test_impressions),
            metric=cycle_metric,
        )

        await apply_shelf_exhausted_tick(
            repository=self._repository,
            complex_adv=complex_adv,
            settings_obj=settings_obj,
            state=fresh,
            snapshot=snapshot,
            now=self._now(),
            qualified_tested_bid_minors=qualified_tested_bid_minors,
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
        snapshot: AutoShelfBidControlDecisionSnapshot | None = None,
    ) -> None:
        snapshot_provided = snapshot is not None
        if snapshot is None:
            snapshot = snapshot_from_state_fallback(
                complex_adv=complex_adv,
                state=state,
                min_bid_minor=min_bid_minor,
                max_bid_minor=int(settings_obj.max_bid_minor),
                actual_bid_minor=actual_bid_minor,
            )
        nmid = complex_adv.main_nmid
        auto_adv_id = complex_adv.auto_adv_id
        now = self._now()
        if snapshot_provided:
            test_bid = snapshot.fresh_next_test_bid_minor
            if test_bid is None:
                test_bid = snapshot.expected_bid_minor
        else:
            test_bid = snapshot.fresh_next_test_bid_minor
            if test_bid is None:
                test_bid = state.current_test_bid_minor
        if test_bid is None:
            test_bid = self._middle_bid(min_bid_minor, int(settings_obj.max_bid_minor))
        if not isinstance(state.test_started_at, datetime):
            state.test_started_at = now
        test_started_at = state.test_started_at
        target_test_observation_minutes = self._target_observation_minutes_or_default(
            settings_obj.target_test_observation_minutes
        )
        target_test_observation_hours = self._target_observation_hours_from_minutes(
            target_test_observation_minutes
        )
        closed_layers_at_test_start = await self._closed_layers_for_bid_at(
            nmid=nmid,
            currency=state.currency,
            bid_minor=test_bid,
            date_to=test_started_at,
            target_test_impressions=int(settings_obj.target_test_impressions),
            target_test_observation_hours=target_test_observation_hours,
            epoch_start=self._shelf_exhausted_epoch_start(state),
        )
        closed_layers_now = await self._closed_layers_for_bid_at(
            nmid=nmid,
            currency=state.currency,
            bid_minor=test_bid,
            date_to=now,
            target_test_impressions=int(settings_obj.target_test_impressions),
            target_test_observation_hours=target_test_observation_hours,
            epoch_start=self._shelf_exhausted_epoch_start(state),
        )
        if closed_layers_now <= closed_layers_at_test_start:
            if not can_set_observation_waiting_reason(
                control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
                snapshot=snapshot,
            ):
                await self._block_observation_progress(
                    state=state,
                    control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
                    snapshot=snapshot,
                )
                return None
            wait_reason = ControlReason.TEST_WAITING_OBSERVATION_TIME
            state.last_reason = wait_reason
            _ = await self._repository.save_state(state)
            logger.info(
                "auto_shelf_bid_control_test_wait_coverage auto_adv_id=%s nmid=%s mode=%s test_bid=%s closed_layers_start=%s closed_layers_now=%s reason=%s",
                auto_adv_id,
                nmid,
                state.current_mode,
                test_bid,
                closed_layers_at_test_start,
                closed_layers_now,
                state.last_reason,
            )
            return None

        if (
            complex_adv.auto_shelf_bid_control_strategy
            == AutoShelfBidControlStrategy.PLAN_DISTANCE
        ):
            bid_universe = build_bid_universe(
                min_bid_minor,
                int(settings_obj.max_bid_minor),
                bid_unit_minor=100,
            )
            _coverages, _current_layer, covered_anchor_count, next_test_bid = (
                await self._build_coverage_snapshot(
                    nmid=nmid,
                    currency=state.currency,
                    min_bid_minor=min_bid_minor,
                    max_bid_minor=int(settings_obj.max_bid_minor),
                    target_test_impressions=int(settings_obj.target_test_impressions),
                    target_test_observation_hours=target_test_observation_hours,
                    min_bid_distance_minor=int(settings_obj.min_bid_distance_minor),
                    date_to=now,
                    epoch_start=self._shelf_exhausted_epoch_start(state),
                )
            )
            should_continue_test = (
                len(bid_universe) > 1
                and covered_anchor_count < 2
                and next_test_bid is not None
                and next_test_bid != test_bid
            )
            if should_continue_test:
                state.current_mode = "test"
                state.current_test_bid_minor = next_test_bid
                state.test_started_at = now
                state.main_started_at = None
                state.last_reason = ControlReason.TEST_COMPLETED_SWITCH_TO_TEST
                _ = await self._repository.save_state(state)
                logger.info(
                    "auto_shelf_bid_control_continue_test_coverage_bootstrap auto_adv_id=%s nmid=%s covered_anchor_count=%s next_test_bid=%s reason=%s",
                    auto_adv_id,
                    nmid,
                    covered_anchor_count,
                    next_test_bid,
                    state.last_reason,
                )
                return None

        best_bid = snapshot.fresh_best_main_bid_minor
        if best_bid is None:
            next_test_bid = snapshot.fresh_next_test_bid_minor
            if next_test_bid is not None and next_test_bid != test_bid:
                state.current_test_bid_minor = next_test_bid
                state.test_started_at = now
            state.current_mode = "test"
            state.main_started_at = None
            state.last_reason = ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
            _ = await self._repository.save_state(state)
            logger.info(
                "auto_shelf_bid_control_continue_test_insufficient_qualified auto_adv_id=%s nmid=%s qualified_count=%s next_test_bid=%s reason=%s",
                auto_adv_id,
                nmid,
                snapshot.qualified_tested_bids_count,
                state.current_test_bid_minor,
                state.last_reason,
            )
            return None
        state.current_main_bid_minor = best_bid
        state.current_mode = "main"
        state.main_started_at = now
        state.last_reason = ControlReason.TEST_COMPLETED_SWITCH_TO_MAIN
        _ = await self._repository.save_state(state)
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
        snapshot: AutoShelfBidControlDecisionSnapshot | None = None,
    ) -> None:
        if snapshot is None:
            snapshot = snapshot_from_state_fallback(
                complex_adv=complex_adv,
                state=state,
                min_bid_minor=min_bid_minor,
                max_bid_minor=int(settings_obj.max_bid_minor),
                actual_bid_minor=actual_bid_minor,
            )
        nmid = complex_adv.main_nmid
        auto_adv_id = complex_adv.auto_adv_id
        now = self._now()
        target_main_impressions = self._calc_target_main_impressions(
            int(settings_obj.target_test_impressions),
            float(settings_obj.test_share),
        )
        if target_main_impressions is None:
            state.last_reason = ControlReason.INVALID_TEST_SHARE
            _ = await self._repository.save_state(state)
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s test_share=%s",
                auto_adv_id,
                nmid,
                state.last_reason,
                settings_obj.test_share,
            )
            return None

        if self.repair_cycle_started_at(state):
            _ = await self._repository.save_state(state)

        max_bid = int(settings_obj.max_bid_minor)
        if snapshot.fresh_best_main_bid_minor is None:
            next_test_bid = snapshot.fresh_next_test_bid_minor
            if next_test_bid is None:
                next_test_bid = state.current_test_bid_minor
            if next_test_bid is None:
                state.last_reason = ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
                _ = await self._repository.save_state(state)
                logger.info(
                    "auto_shelf_bid_control_revert_main_blocked_no_test_bid auto_adv_id=%s nmid=%s qualified_count=%s reason=%s",
                    auto_adv_id,
                    nmid,
                    snapshot.qualified_tested_bids_count,
                    state.last_reason,
                )
                return None
            state.current_test_bid_minor = next_test_bid
            state.test_started_at = now
            state.current_mode = "test"
            state.main_started_at = None
            state.last_reason = ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
            _ = await self._repository.save_state(state)
            logger.info(
                "auto_shelf_bid_control_revert_main_to_test_insufficient_qualified auto_adv_id=%s nmid=%s qualified_count=%s next_test_bid=%s reason=%s",
                auto_adv_id,
                nmid,
                snapshot.qualified_tested_bids_count,
                state.current_test_bid_minor,
                state.last_reason,
            )
            return None

        main_bid_value = self._clamp_bid_minor(
            int(snapshot.fresh_best_main_bid_minor),
            min_bid_minor=min_bid_minor,
            max_bid_minor=max_bid,
        )
        state.current_main_bid_minor = main_bid_value
        if state.main_started_at is None:
            state.main_started_at = now

        fresh_worker_snapshot = snapshot.computed_at is not None

        main_coverage_snapshot: tuple[list[BidCoverage], int, int, int | None] | None = None
        bootstrap_continue, main_coverage_snapshot = await self._maybe_continue_main_exploration(
            complex_adv,
            settings_obj=settings_obj,
            state=state,
            min_bid_minor=min_bid_minor,
            now=now,
            coverage_snapshot=main_coverage_snapshot,
        )
        if bootstrap_continue:
            return None
        if fresh_worker_snapshot:
            if not can_set_observation_waiting_reason(
                control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
                snapshot=snapshot,
            ):
                await self._block_observation_progress(
                    state=state,
                    control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
                    snapshot=snapshot,
                )
                return None
        else:
            refresh_result = await self.apply_main_bid_refresh_if_needed(
                complex_adv,
                state=state,
                min_bid_minor=min_bid_minor,
                max_bid_minor=max_bid,
                actual_bid_minor=actual_bid_minor,
                now=now,
            )
            if refresh_result == MainBidRefreshResult.APPLIED:
                return None
            if refresh_result in {
                MainBidRefreshResult.SKIPPED_DISABLED,
                MainBidRefreshResult.SKIPPED_NOT_MAIN,
            }:
                return None
            if await self._reconcile_expected_bid_for_current_mode(
                complex_adv,
                state=state,
                actual_bid_minor=actual_bid_minor,
                min_bid_minor=min_bid_minor,
                max_bid_minor=max_bid,
                now=now,
                expected_bid_minor=snapshot.expected_bid_minor,
            ):
                return None
        main_bid: int = main_bid_value
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
            _ = await self._repository.save_state(state)
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
            if not can_set_observation_waiting_reason(
                control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
                snapshot=snapshot,
            ):
                await self._block_observation_progress(
                    state=state,
                    control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
                    snapshot=snapshot,
                )
                return None
            wait_reason = ControlReason.MAIN_WAITING_OBSERVATION_TIME
            state.last_reason = wait_reason
            _ = await self._repository.save_state(state)
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
            if not can_set_observation_waiting_reason(
                control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
                snapshot=snapshot,
            ):
                await self._block_observation_progress(
                    state=state,
                    control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
                    snapshot=snapshot,
                )
                return None
            wait_reason = ControlReason.MAIN_WAITING_IMPRESSIONS
            state.last_reason = wait_reason
            _ = await self._repository.save_state(state)
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
        target_test_observation_minutes = self._target_observation_minutes_or_default(
            settings_obj.target_test_observation_minutes
        )
        target_test_observation_hours = self._target_observation_hours_from_minutes(
            target_test_observation_minutes
        )
        if main_coverage_snapshot is None:
            coverage_price_minor: int | None = None
            first_bucket_start = (
                await self._analytics.get_first_available_bid_bucket_start(
                    nmid=nmid,
                    currency=state.currency,
                    price_minor=coverage_price_minor,
                    mode=None,
                )
            )
            coverages: list[BidCoverage]
            if first_bucket_start is None:
                coverages = []
            else:
                coverages = await self._analytics.get_bid_coverages(
                    nmid=nmid,
                    date_from=self._coverage_date_from(
                        first_bucket_start=first_bucket_start,
                        date_to=now,
                        epoch_start=self._shelf_exhausted_epoch_start(state),
                    ),
                    date_to=now,
                    currency=state.currency,
                    price_minor=coverage_price_minor,
                    mode=None,
                )
            main_coverage_snapshot = (
                coverages,
                0,
                0,
                choose_next_test_bid_by_coverage_layers(
                    min_bid_minor=min_bid_minor,
                    max_bid_minor=int(settings_obj.max_bid_minor),
                    bid_unit_minor=100,
                    coverages=coverages,
                    target_test_impressions=int(settings_obj.target_test_impressions),
                    target_test_observation_hours=target_test_observation_hours,
                    min_bid_distance_minor=int(settings_obj.min_bid_distance_minor),
                    random_seed=build_coverage_selector_seed(
                        nmid=nmid,
                        currency=state.currency,
                        price_minor=coverage_price_minor,
                        min_bid_minor=min_bid_minor,
                        max_bid_minor=int(settings_obj.max_bid_minor),
                        min_bid_distance_minor=int(settings_obj.min_bid_distance_minor),
                        target_test_impressions=int(settings_obj.target_test_impressions),
                        target_test_observation_hours=target_test_observation_hours,
                    ),
                ),
            )
        coverages, _current_layer, _covered_anchor_count, next_test_bid = (
            main_coverage_snapshot
        )
        if next_test_bid is not None:
            state.current_mode = "test"
            state.current_test_bid_minor = next_test_bid
            state.current_main_bid_minor = main_bid
            state.test_started_at = now
            state.main_started_at = None
            state.last_reason = ControlReason.MAIN_COMPLETED_SWITCH_TO_TEST
            _ = await self._repository.save_state(state)
            logger.info(
                "auto_shelf_bid_control_switch_to_test auto_adv_id=%s nmid=%s next_test_bid=%s reason=%s",
                auto_adv_id,
                nmid,
                next_test_bid,
                state.last_reason,
            )
            return None
        if (
            complex_adv.auto_shelf_bid_control_strategy
            != AutoShelfBidControlStrategy.PLAN_DISTANCE
        ):
            if snapshot.qualified_tested_bids_count < 2:
                next_test_bid = snapshot.fresh_next_test_bid_minor
                if next_test_bid is None:
                    next_test_bid = state.current_test_bid_minor
                if next_test_bid is None:
                    state.last_reason = ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
                    _ = await self._repository.save_state(state)
                    logger.warning(
                        "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s strategy=%s qualified_count=%s blocked=no_test_bid",
                        auto_adv_id,
                        nmid,
                        state.last_reason,
                        complex_adv.auto_shelf_bid_control_strategy,
                        snapshot.qualified_tested_bids_count,
                    )
                    return None
                state.current_test_bid_minor = next_test_bid
                state.test_started_at = now
                state.current_mode = "test"
                state.main_started_at = None
                state.last_reason = ControlReason.INSUFFICIENT_QUALIFIED_TESTED_BIDS
            else:
                state.last_reason = ControlReason.BEST_BID_NOT_FOUND
            _ = await self._repository.save_state(state)
            logger.warning(
                "auto_shelf_bid_control_skip auto_adv_id=%s nmid=%s reason=%s strategy=%s qualified_count=%s",
                auto_adv_id,
                nmid,
                state.last_reason,
                complex_adv.auto_shelf_bid_control_strategy,
                snapshot.qualified_tested_bids_count,
            )
            return None
        state.current_mode = "main"
        state.main_started_at = now
        if not can_set_observation_waiting_reason(
            control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
            snapshot=snapshot,
        ):
            await self._block_observation_progress(
                state=state,
                control_enabled=bool(complex_adv.auto_shelf_bid_control_enabled),
                snapshot=snapshot,
            )
            return None
        state.last_reason = ControlReason.MAIN_WAITING_OBSERVATION_TIME
        _ = await self._repository.save_state(state)
        logger.info(
            "auto_shelf_bid_control_main_bid_kept auto_adv_id=%s nmid=%s main_bid=%s reason=%s",
            auto_adv_id,
            nmid,
            main_bid,
            state.last_reason,
        )
        return None

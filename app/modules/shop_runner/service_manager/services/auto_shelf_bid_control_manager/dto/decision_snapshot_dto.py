"""DTO свежего decision snapshot для Auto Shelf Bid Control."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, cast

from .control_view_dto import CoverageLayerBidDTO

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
        AutoShelfBidControlState,
    )
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
        ComplexAdv,
    )


class BidSyncStatus(StrEnum):
    """Статус синхронизации фактической WB-ставки с ожидаемой."""

    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"
    MISMATCH_NOT_APPLIED = "mismatch_not_applied"
    NO_ACTUAL_BID = "no_actual_bid"


def _as_str_object_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    mapping = cast(Mapping[object, object], value)
    return {str(key): item for key, item in mapping.items()}


def _as_object_sequence(value: object) -> Sequence[object] | None:
    if isinstance(value, (str, bytes, bytearray)):
        return None
    if isinstance(value, Sequence):
        return cast(Sequence[object], value)
    return None


def _empty_coverage_bid_rows() -> list[CoverageLayerBidDTO]:
    return []


def parse_plan_ranked_top_bid_minor(
    recommendation: Mapping[str, object] | None,
) -> int | None:
    """Вернуть bid первой строки ``plan_ranked`` (свежий победитель ранжирования)."""
    if recommendation is None:
        return None
    plan_ranked_raw = recommendation.get("plan_ranked")
    rows = _as_object_sequence(plan_ranked_raw)
    if not rows:
        return None
    first_raw = rows[0]
    first_row = _as_str_object_dict(first_raw)
    if first_row is None:
        return None
    bid_raw = first_row.get("bid")
    if isinstance(bid_raw, bool) or not isinstance(bid_raw, int):
        return None
    if bid_raw <= 0:
        return None
    return int(bid_raw)


def resolve_recommended_main_bid_minor(
    recommendation: Mapping[str, object] | None,
    *,
    min_bid_minor: int | None = None,
    max_bid_minor: int | None = None,
) -> int | None:
    """Свежая main-рекомендация из ``plan_ranked[0]`` без зависимости от control/state/actual."""
    ranked_top = parse_plan_ranked_top_bid_minor(recommendation)
    if ranked_top is None:
        return None
    if min_bid_minor is not None and max_bid_minor is not None:
        return max(int(min_bid_minor), min(int(max_bid_minor), int(ranked_top)))
    return int(ranked_top)


def resolve_primary_status(
    *,
    control_enabled: bool,
    last_reason: str | None,
) -> str:
    """Первичный статус UI: при выключенном control не показываем active last_reason."""
    if not control_enabled:
        return "disabled"
    return last_reason or "—"


def resolve_bid_sync_detail(
    actual_bid_minor: int | None,
    expected_enforced_bid_minor: int | None,
    *,
    control_enabled: bool,
) -> str | None:
    """Диагностика синхронизации для UI (не стирает recommendation)."""
    if not control_enabled or expected_enforced_bid_minor is None:
        return None
    if actual_bid_minor is None:
        return "no_actual_bid"
    if int(actual_bid_minor) == int(expected_enforced_bid_minor):
        return "synced"
    return "pending"


def cast_rec_dict(value: object | None) -> dict[str, object] | None:
    """Нормализовать recommendation mapping для UI/diagnostics."""
    if value is None:
        return None
    return _as_str_object_dict(value)


def cast_coverage_rows(
    rows: list[CoverageLayerBidDTO],
) -> list[CoverageLayerBidDTO]:
    return rows


def resolve_expected_bid_minor(
    *,
    current_mode: str | None,
    fresh_best_main_bid_minor: int | None,
    fresh_next_test_bid_minor: int | None,
    control_enabled: bool,
) -> int | None:
    """Ожидаемая ставка для активного режима при включённом control."""
    if not control_enabled:
        return None
    if current_mode == "main":
        return fresh_best_main_bid_minor
    if current_mode == "test":
        return fresh_next_test_bid_minor
    return None


def resolve_bid_sync_status(
    actual_bid_minor: int | None,
    expected_bid_minor: int | None,
    *,
    setter_failed: bool = False,
) -> BidSyncStatus:
    """Вычислить sync-статус между фактической и ожидаемой ставкой."""
    if setter_failed:
        return BidSyncStatus.FAILED
    if expected_bid_minor is None:
        return BidSyncStatus.SYNCED
    if actual_bid_minor is None:
        return BidSyncStatus.PENDING
    if int(actual_bid_minor) == int(expected_bid_minor):
        return BidSyncStatus.SYNCED
    return BidSyncStatus.PENDING


def snapshot_can_count_progress(bid_sync_status: BidSyncStatus) -> bool:
    """Прогресс test/main считается только при синхронизированной ставке."""
    return bid_sync_status == BidSyncStatus.SYNCED


def can_set_observation_waiting_reason(
    *,
    control_enabled: bool,
    snapshot: AutoShelfBidControlDecisionSnapshot,
) -> bool:
    """Можно ли ставить *WAITING_OBSERVATION_TIME на progress-path (не reconcile)."""
    if not control_enabled:
        return False
    if snapshot.expected_bid_minor is None:
        return False
    if snapshot.actual_bid_minor is None:
        return False
    if int(snapshot.actual_bid_minor) != int(snapshot.expected_bid_minor):
        return False
    if snapshot.bid_sync_status != BidSyncStatus.SYNCED:
        return False
    return snapshot.can_count_progress


def resolve_observation_sync_block_reason(
    *,
    control_enabled: bool,
    snapshot: AutoShelfBidControlDecisionSnapshot,
) -> str:
    """Причина блокировки observation/progress-path при нарушении sync-инварианта."""
    if not control_enabled:
        return "disabled"
    if snapshot.expected_bid_minor is None:
        return "expected_bid_missing"
    if snapshot.actual_bid_minor is None:
        return "no_actual_bid"
    if int(snapshot.actual_bid_minor) != int(snapshot.expected_bid_minor):
        return "bid_sync_mismatch_not_applied"
    if snapshot.bid_sync_status == BidSyncStatus.MISMATCH_NOT_APPLIED:
        return "bid_sync_mismatch_not_applied"
    if snapshot.bid_sync_status == BidSyncStatus.NO_ACTUAL_BID:
        return "no_actual_bid"
    if snapshot.bid_sync_status != BidSyncStatus.SYNCED:
        return f"bid_sync_{snapshot.bid_sync_status.value}"
    if not snapshot.can_count_progress:
        return "progress_blocked"
    return "bid_sync_blocked"


@dataclass(slots=True)
class AutoShelfBidControlDecisionSnapshot:
    """Единый пересчитанный снимок ставок и диагностики control."""

    nmid: int
    auto_adv_id: int
    current_mode: str | None
    actual_bid_minor: int | None
    min_bid_minor: int
    max_bid_minor: int
    fresh_best_main_bid_minor: int | None
    fresh_next_test_bid_minor: int | None
    expected_bid_minor: int | None
    bid_sync_status: BidSyncStatus
    can_count_progress: bool
    main_target_explanation: str | None = None
    best_plan_bid_minor: int | None = None
    legacy_cycle_next_test_bid_minor: int | None = None
    coverage_selected_next_test_bid_minor: int | None = None
    rec_bid_recommendation: dict[str, object] | None = None
    coverage_bid_rows: list[CoverageLayerBidDTO] = field(
        default_factory=_empty_coverage_bid_rows
    )
    computed_at: datetime | None = None

    @property
    def expected_bid_applied(self) -> bool:
        return self.bid_sync_status == BidSyncStatus.SYNCED

    def ranked_plan_top_bid_minor(self) -> int | None:
        """Сырой победитель ``plan_ranked`` до clamp (для диагностики)."""
        return parse_plan_ranked_top_bid_minor(self.rec_bid_recommendation)


def as_view_main_target(snapshot: AutoShelfBidControlDecisionSnapshot) -> int | None:
    """Лучшая свежая main-ставка для Telegram render."""
    return snapshot.fresh_best_main_bid_minor


def as_view_next_test(snapshot: AutoShelfBidControlDecisionSnapshot) -> int | None:
    """Следующая свежая test-ставка для Telegram render."""
    return snapshot.fresh_next_test_bid_minor


def snapshot_from_state_fallback(
    *,
    complex_adv: ComplexAdv,
    state: AutoShelfBidControlState,
    min_bid_minor: int,
    max_bid_minor: int,
    actual_bid_minor: int | None,
    control_enabled: bool = True,
) -> AutoShelfBidControlDecisionSnapshot:
    """Legacy fallback только когда handler вызван без worker snapshot (snapshot is None).

    ``expected_bid_minor`` для sync-guard берётся из ``state.current_*_bid_minor``;
    ``fresh_*`` остаются None — progression не подменяется.
    """
    fresh_main = None
    fresh_test = None
    expected = resolve_expected_bid_minor(
        current_mode=state.current_mode,
        fresh_best_main_bid_minor=fresh_main,
        fresh_next_test_bid_minor=fresh_test,
        control_enabled=control_enabled,
    )
    if expected is None and control_enabled:
        if state.current_mode == "main":
            expected = getattr(state, "current_main_bid_minor", None)
        elif state.current_mode == "test":
            expected = getattr(state, "current_test_bid_minor", None)
    status = resolve_bid_sync_status(actual_bid_minor, expected)
    return AutoShelfBidControlDecisionSnapshot(
        nmid=complex_adv.main_nmid,
        auto_adv_id=int(complex_adv.auto_adv_id),
        current_mode=state.current_mode,
        actual_bid_minor=actual_bid_minor,
        min_bid_minor=min_bid_minor,
        max_bid_minor=max_bid_minor,
        fresh_best_main_bid_minor=fresh_main,
        fresh_next_test_bid_minor=fresh_test,
        expected_bid_minor=expected,
        bid_sync_status=status,
        can_count_progress=snapshot_can_count_progress(status),
        computed_at=None,
    )

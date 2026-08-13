"""Apply shelf-exhausted detect/clear на тике AutoShelfBidControlManager.

Ownership: shelf PG SoT only — MUST NOT вызывать WB pause/start.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.decision import (
    DEFAULT_RETEST_INTERVAL_DAYS,
    ResolveCpoKind,
    TerminalDetectInput,
    clear_our_block_due_to_calendar,
    clear_our_block_due_to_plan_fit,
    has_resolve_cpo_plan_fit,
    parse_plan_ranked_rows,
    should_latch_terminal_block,
)
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost_and_threshold_kind

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
        AutoShelfBidControlSettings,
        AutoShelfBidControlState,
    )
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
        AutoShelfBidControlRepository,
    )
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.decision_snapshot_dto import (
        AutoShelfBidControlDecisionSnapshot,
    )
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
        ComplexAdv,
    )

logger = logging.getLogger(__name__)


def _resolve_cpo_from_adv(
    complex_adv: ComplexAdv,
) -> tuple[float, ResolveCpoKind] | None:
    """Текущий resolve CPO (target|max) из плана/прогноза кампании."""
    plan = getattr(complex_adv, "plan", None)
    plan_orders = getattr(plan, "orders", None) if plan is not None else None
    plan_target = (
        getattr(plan, "target_pay_for_order", None) if plan is not None else None
    )
    plan_max = getattr(plan, "max_pay_for_order", None) if plan is not None else None
    # ComplexAdv часто несёт resolved scalars / fact predict на себе.
    fact_predict = getattr(complex_adv, "fact_predict_orders", None)
    if fact_predict is None:
        fact_predict = getattr(complex_adv, "resolved_fact_predict_orders", None)
    pair = resolve_target_cost_and_threshold_kind(
        plan_orders,
        plan_target,
        plan_max,
        float(fact_predict) if fact_predict is not None else None,
    )
    if pair is None:
        # Fallback: уже посчитанный resolve_cpo на ComplexAdv.
        resolved = getattr(complex_adv, "resolve_cpo", None)
        if resolved is None:
            resolved = getattr(complex_adv, "resolved_target_pay_for_order", None)
        if resolved is None:
            return None
        kind_raw = getattr(complex_adv, "resolve_cpo_kind", None)
        kind: ResolveCpoKind = "max" if kind_raw == "max" else "target"
        if kind_raw in ("target", "max"):
            kind = kind_raw
        return (float(resolved), kind)
    return (float(pair[0]), pair[1])


async def apply_shelf_exhausted_tick(
    *,
    repository: AutoShelfBidControlRepository,
    complex_adv: ComplexAdv,
    settings_obj: AutoShelfBidControlSettings,
    state: AutoShelfBidControlState,
    snapshot: AutoShelfBidControlDecisionSnapshot,
    now: datetime,
    qualified_tested_bid_minors: list[int] | None = None,
) -> str:
    """Detect/latch/clear our-block на тике полок.

    Returns:
        Короткий outcome-code для логов
        (``latched`` / ``cleared_fit`` / ``cleared_calendar`` /
        ``kept_block`` / ``noop_*``).
    """
    nmid = int(state.nmid)
    module_enabled = bool(complex_adv.auto_shelf_bid_control_enabled)
    strategy = complex_adv.auto_shelf_bid_control_strategy
    resolve_pair = _resolve_cpo_from_adv(complex_adv)
    resolve_value = resolve_pair[0] if resolve_pair else None
    resolve_kind = resolve_pair[1] if resolve_pair else None
    plan_ranked = parse_plan_ranked_rows(snapshot.rec_bid_recommendation)
    plan_fit = has_resolve_cpo_plan_fit(
        plan_ranked=plan_ranked,
        qualified_tested_bid_minors=qualified_tested_bid_minors,
        resolve_cpo_value=resolve_value,
    )

    block_active = bool(state.shelf_exhausted_pause_active)
    if block_active:
        if clear_our_block_due_to_plan_fit(block_active=True, has_plan_fit=plan_fit):
            await repository.clear_shelf_exhausted_pause(nmid)
            logger.info(
                "shelf_exhausted_clear_fit auto_adv_id=%s nmid=%s",
                complex_adv.auto_adv_id,
                nmid,
            )
            return "cleared_fit"
        if clear_our_block_due_to_calendar(
            block_active=True,
            due_at=state.shelf_exhausted_due_at,
            now=now,
        ):
            await repository.clear_shelf_exhausted_pause(nmid)
            logger.info(
                "shelf_exhausted_clear_calendar auto_adv_id=%s nmid=%s",
                complex_adv.auto_adv_id,
                nmid,
            )
            return "cleared_calendar"
        logger.debug(
            "shelf_exhausted_keep_block auto_adv_id=%s nmid=%s plan_fit=%s",
            complex_adv.auto_adv_id,
            nmid,
            plan_fit,
        )
        return "kept_block"

    detect = should_latch_terminal_block(
        TerminalDetectInput(
            module_enabled=module_enabled,
            strategy=strategy,
            next_test_bid_minor=snapshot.fresh_next_test_bid_minor,
            plan_ranked=plan_ranked,
            qualified_tested_bid_minors=qualified_tested_bid_minors,
            resolve_cpo_value=resolve_value,
            resolve_cpo_kind=resolve_kind,
        )
    )
    if not detect.should_latch:
        return f"noop_{detect.reason}"

    assert resolve_kind is not None and resolve_value is not None
    interval = int(
        getattr(settings_obj, "retest_interval_days", DEFAULT_RETEST_INTERVAL_DAYS)
        or DEFAULT_RETEST_INTERVAL_DAYS
    )
    due_at = now + timedelta(days=interval)
    await repository.latch_shelf_exhausted_pause(
        nmid,
        now=now,
        due_at=due_at,
        resolve_cpo_kind=resolve_kind,
        resolve_cpo_value=resolve_value,
    )
    logger.info(
        "shelf_exhausted_latched auto_adv_id=%s nmid=%s resolve_kind=%s "
        "resolve_value=%s due_at=%s",
        complex_adv.auto_adv_id,
        nmid,
        resolve_kind,
        resolve_value,
        due_at.isoformat(),
    )
    return "latched"

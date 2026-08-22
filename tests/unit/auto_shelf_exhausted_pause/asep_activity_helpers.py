"""Activity-control helpers for ASEP clear → start / no-start scenario seams."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
    PlanFactSummary,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from tests.unit.auto_shelf_exhausted_pause.wb_pause_auto_contract import (
    RecordingWbAutoLifecycle,
)

_SERVICE_MODULE = (
    "app.modules.shop_runner.service_manager.services.auto_adv_active_control."
    "auto_adv_active_control_service"
)


def make_adv(
    *,
    auto_status: str,
    shelf_enabled: bool = True,
    auto_budget_daily_limit: int = 1000,
) -> SimpleNamespace:
    """Minimal ComplexAdv-shaped object for ensure_campaigns_active."""
    return SimpleNamespace(
        bot_active=True,
        auto_budget_watchdog_enabled=True,
        auto_adv_id=501,
        search_adv_id=None,
        shop_id="shop-asep",
        shop_name="Shop",
        main_nmid=9001,
        nmids=[9001],
        auto_adv_active_status_str=auto_status,
        search_adv_active_status_str=WBAdvActiveStatus.PAUSE,
        use_common_budget=False,
        auto_budget_daily_limit=auto_budget_daily_limit,
        search_auto_budget_daily_limit=0,
        rec_system_promotion_mode_active=True,
        adv_setting=SimpleNamespace(
            id=77,
            name="Camp",
            wb_cabinet_id=1,
            auto_shelf_bid_control_enabled=shelf_enabled,
            rec_system_mode=True,
            plan_for_sales_for_day=10,
            target_price_for_order=100,
            max_price_for_order=200,
            sales_predict_method=None,
        ),
        search_adv=None,
        get_keywords=AsyncMock(return_value=[]),
    )


def make_state(
    *,
    pause_active: bool,
    epoch_pending: bool = False,
    notify_sent: bool = True,
) -> SimpleNamespace:
    """PG SoT snapshot for shelf-exhausted fields."""
    return SimpleNamespace(
        shelf_exhausted_pause_active=pause_active,
        shelf_exhausted_notify_sent_at=(
            datetime.now(UTC) if notify_sent else None
        ),
        shelf_exhausted_resolve_cpo_kind="max",
        shelf_exhausted_resolve_cpo_value=250.0,
        shelf_exhausted_due_at=datetime.now(UTC) + timedelta(days=7),
        shelf_exhausted_epoch_pending=epoch_pending,
    )


async def run_ensure_with_shelf_state(
    *,
    wb: RecordingWbAutoLifecycle,
    state: SimpleNamespace,
    auto_status: str,
    spend_today: float,
    auto_budget_daily_limit: int = 1000,
) -> MagicMock:
    """Run ``ensure_campaigns_active`` with injected shelf repo + RecordingWb.

    Returns reason_manager mock for optional asserts.
    """
    adv = make_adv(
        auto_status=auto_status,
        auto_budget_daily_limit=auto_budget_daily_limit,
    )
    repo = MagicMock()
    repo.get_state = AsyncMock(return_value=state)
    repo.mark_shelf_exhausted_notify_sent = AsyncMock()
    repo.mark_shelf_exhausted_epoch_started = AsyncMock()
    reason_manager = MagicMock()
    reason_manager.set = AsyncMock()
    plan_fact = MagicMock(spec=PlanFactReader)
    plan_fact.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=501, fact_predict_orders=12.0, fact_pay_for_order=90.0
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb,  # type: ignore[arg-type]
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact,
        redis_campaign_activity_reason_manager=reason_manager,
        shelf_bid_control_repository=repo,
    )

    class _FakeSessionCM:
        async def __aenter__(self) -> Any:
            return MagicMock()

        async def __aexit__(self, *a: object) -> bool:
            return False

    async def _run(handlers: list, *a: object, **k: object) -> list:
        for h in handlers:
            await h()
        return []

    mock_ts = MagicMock()
    mock_ts.load_for_adv_ids = AsyncMock(return_value={77: None})
    with patch(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    ), patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.intent.EmptyKeywordsPauseIntentManager.peek_intent",
        AsyncMock(return_value=False),
    ), patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.intent.EmptyKeywordsPauseIntentManager.consume_intent",
        AsyncMock(return_value=False),
    ), patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.decision.is_warmup_false_empty_keywords",
        AsyncMock(return_value=False),
    ), patch(
        f"{_SERVICE_MODULE}.get_session_maker",
        lambda *a, **k: _FakeSessionCM(),
    ), patch(f"{_SERVICE_MODULE}.run_tasks", new=_run), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=50.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=spend_today),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts):
        await service.ensure_campaigns_active([adv])  # type: ignore[list-item]

    # Attach repo on reason_manager for callers that need epoch asserts.
    reason_manager.shelf_repo = repo  # type: ignore[attr-defined]
    return reason_manager

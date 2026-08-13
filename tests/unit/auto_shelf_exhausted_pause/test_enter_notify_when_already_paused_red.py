"""RED regression: shelf-exhausted enter MUST notify when Auto already not STARTED.

Bug ROOT-001 / BUGCASE-ASEP-ENTER-NOTIFY: ``_maybe_apply_shelf_exhausted_pause``
notifies paid Telegram only on ``auto_status==STARTED``. When Auto is already
PAUSE / READY (budget/schedule/balance paused first), it re-asserts Redis reason
and returns without notify — first shelf-exhausted enter is silent despite PG
``shelf_exhausted_pause_active`` and ``notify_sent_at is None``.

Fingerprint: ``shelf_exhausted_enter_notify_only_on_started_transition``.
Distinct from sticky ``notify_sent_at`` after clear (BUGCASE-ASEP-NOTIFY).
"""

from __future__ import annotations

# Unit tests probe private activity-control seams by design (ASEP notify).
# pyright: reportPrivateUsage=false

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

_NMID = 9001
_NOW = datetime(2026, 8, 13, 3, 0, 0, tzinfo=UTC)
_DUE = _NOW + timedelta(days=7)


def _pg_our_block_awaiting_first_notify() -> SimpleNamespace:
    """Active PG our-block with notify latch unset (first enter)."""
    return SimpleNamespace(
        shelf_exhausted_pause_active=True,
        shelf_exhausted_notify_sent_at=None,
        shelf_exhausted_resolve_cpo_kind="max",
        shelf_exhausted_resolve_cpo_value=250.0,
        shelf_exhausted_due_at=_DUE,
        shelf_exhausted_epoch_pending=False,
    )


def _adv(*, auto_status: str = WBAdvActiveStatus.PAUSE) -> SimpleNamespace:
    return SimpleNamespace(
        bot_active=True,
        auto_budget_watchdog_enabled=True,
        auto_adv_id=501,
        shop_id="shop-x",
        shop_name="Shop",
        main_nmid=_NMID,
        nmids=[_NMID],
        auto_adv_active_status_str=auto_status,
        use_common_budget=False,
        rec_system_promotion_mode_active=True,
        adv_setting=SimpleNamespace(
            id=77,
            name="Camp",
            auto_shelf_bid_control_enabled=True,
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auto_status",
    [
        WBAdvActiveStatus.PAUSE,
        WBAdvActiveStatus.READY_FOR_START,
    ],
)
async def test_shelf_exhausted_enter_notifies_when_auto_already_not_started(
    auto_status: str,
) -> None:
    """PG our-block enter + notify_sent_at None MUST notify even if Auto not STARTED.

    Protects: first shelf-exhausted enter after budget/schedule/balance pause
    must still deliver paid Telegram notify (dedup latch still applies).
    """
    state = _pg_our_block_awaiting_first_notify()
    repo = MagicMock()
    repo.get_state = AsyncMock(return_value=state)
    reason_manager = MagicMock()
    reason_manager.set = AsyncMock()

    service = AutoAdvActiveControlService(
        wb_modifier=MagicMock(),
        tasks_manager=MagicMock(),
        plan_fact_reader=MagicMock(),
        redis_campaign_activity_reason_manager=reason_manager,
        shelf_bid_control_repository=repo,
    )
    notify_spy = AsyncMock()
    service._notify_shelf_exhausted_enter = notify_spy  # type: ignore[method-assign]
    service._wb_modifier.pause_auto_campaign = AsyncMock()  # type: ignore[method-assign]
    service._set_auto_reason = AsyncMock()  # type: ignore[method-assign]

    blocked = await service._maybe_apply_shelf_exhausted_pause(
        _adv(),  # type: ignore[arg-type]
        auto_adv_id=501,
        auto_status=auto_status,
    )

    assert blocked is True
    # Already not STARTED: must not re-pause WB; Redis re-assert still ok.
    service._wb_modifier.pause_auto_campaign.assert_not_awaited()
    service._set_auto_reason.assert_awaited_once()
    # Causal claim ROOT-001: paid notify MUST fire on enter when latch unset.
    notify_spy.assert_awaited_once()


def _schedule_closed(_db: object) -> bool:
    """Stub: time window closed (forces schedule early-return if reached)."""
    return False


@pytest.mark.asyncio
async def test_ensure_notifies_shelf_exhausted_before_schedule_early_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ensure_campaigns_active MUST enter-notify before schedule early-return.

    PBH-007: schedule/balance/budget returns previously skipped
    ``_maybe_apply_shelf_exhausted_pause``, so first enter stayed silent while
    Auto was already held by a higher-priority gate.
    """
    from typing import Any
    from unittest.mock import patch

    from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
        PlanFactReader,
        PlanFactSummary,
    )
    from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
        AutoReasonCode,
        CampaignActivityCommand,
    )

    _service_mod = (
        "app.modules.shop_runner.service_manager.services.auto_adv_active_control."
        "auto_adv_active_control_service"
    )

    state = _pg_our_block_awaiting_first_notify()
    repo = MagicMock()
    repo.get_state = AsyncMock(return_value=state)
    repo.mark_shelf_exhausted_notify_sent = AsyncMock()
    reason_manager = MagicMock()
    reason_manager.set = AsyncMock()
    plan_fact = MagicMock(spec=PlanFactReader)
    plan_fact.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=501, fact_predict_orders=12.0, fact_pay_for_order=90.0
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=MagicMock(),
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact,
        redis_campaign_activity_reason_manager=reason_manager,
        shelf_bid_control_repository=repo,
    )
    notify_spy = AsyncMock()
    service._notify_shelf_exhausted_enter = notify_spy  # type: ignore[method-assign]

    adv = _adv(auto_status=WBAdvActiveStatus.PAUSE)
    # Fields required by ensure_campaigns_active / Auto handler wiring.
    adv.search_adv_id = None
    adv.search_adv_active_status_str = WBAdvActiveStatus.PAUSE
    adv.auto_budget_daily_limit = 1000
    adv.search_auto_budget_daily_limit = 0
    adv.search_adv = None
    adv.get_keywords = AsyncMock(return_value=[])
    adv.adv_setting.wb_cabinet_id = 1
    adv.adv_setting.rec_system_mode = True
    adv.adv_setting.plan_for_sales_for_day = 10
    adv.adv_setting.target_price_for_order = 100
    adv.adv_setting.max_price_for_order = 200
    adv.adv_setting.sales_predict_method = None

    class _FakeSessionCM:
        async def __aenter__(self) -> Any:
            return MagicMock()

        async def __aexit__(self, *a: object) -> bool:
            return False

    async def _run(handlers: list[Any], *a: object, **k: object) -> list[Any]:
        for h in handlers:
            await h()
        return []

    mock_ts = MagicMock()
    # Non-None db_state so schedule check is consulted (would early-return).
    mock_ts.load_for_adv_ids = AsyncMock(return_value={77: MagicMock()})
    monkeypatch.setattr(f"{_service_mod}.allowed_now_from_db_state", _schedule_closed)

    def _session_maker(*_a: object, **_k: object) -> _FakeSessionCM:
        return _FakeSessionCM()

    with patch(
        f"{_service_mod}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    ), patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.intent.EmptyKeywordsPauseIntentManager.peek_intent",
        AsyncMock(return_value=False),
    ), patch(
        f"{_service_mod}.get_session_maker",
        _session_maker,
    ), patch(f"{_service_mod}.run_tasks", new=_run), patch(
        f"{_service_mod}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=50.0),
    ), patch(
        f"{_service_mod}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_service_mod}._time_settings_repo", mock_ts):
        await service.ensure_campaigns_active([adv])  # type: ignore[list-item]

    notify_spy.assert_awaited_once()
    reason_manager.set.assert_awaited()
    args = reason_manager.set.await_args.args
    assert args[1] == "auto"
    assert args[2].reason_code == AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN
    assert args[2].command == CampaignActivityCommand.PAUSE

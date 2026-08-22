"""Unit tests: shelf-exhausted pause decision + activity thin-end (INC-AUTO-SHELF-PAUSE-01).

Spec: ``auto-shelf-exhausted-pause``. Evidence: unit_component + scenario_seam /
side_effect_proof for pause_auto_campaign; Search forbidden sibling.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.decision import (
    DEFAULT_RETEST_INTERVAL_DAYS,
    TerminalDetectInput,
    clear_our_block_due_to_calendar,
    clear_our_block_due_to_plan_fit,
    coverage_date_from_for_epoch,
    gate_allows_shelf_exhausted_path,
    has_resolve_cpo_plan_fit,
    is_shelf_exhausted_reason,
    should_latch_terminal_block,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.messages import (
    RESET_PAUSE_BUTTON_TEXT,
    build_shelf_exhausted_pause_message,
    build_shelf_exhausted_reset_callback_data,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
    PlanFactSummary,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
    AutoReasonCode,
    CampaignActivityCommand,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from tests.unit.auto_shelf_exhausted_pause.wb_pause_auto_contract import (
    RecordingWbAutoLifecycle,
)

_SERVICE_MODULE = (
    "app.modules.shop_runner.service_manager.services.auto_adv_active_control."
    "auto_adv_active_control_service"
)


def test_default_retest_interval_is_seven_days() -> None:
    """Scenario: Default interval is seven days."""
    assert DEFAULT_RETEST_INTERVAL_DAYS == 7


def test_gate_module_off_no_path() -> None:
    """Scenario: Module off — no shelf-exhausted pause."""
    assert not gate_allows_shelf_exhausted_path(
        module_enabled=False,
        strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
    )
    result = should_latch_terminal_block(
        TerminalDetectInput(
            module_enabled=False,
            strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
            next_test_bid_minor=None,
            plan_ranked=[{"bid": 100, "cpo_rub": 999.0}],
            qualified_tested_bid_minors=[100],
            resolve_cpo_value=200.0,
            resolve_cpo_kind="max",
        )
    )
    assert result.should_latch is False


def test_gate_non_best_plan_no_path() -> None:
    """Scenario: Non-Best plan mode — no shelf-exhausted pause."""
    assert not gate_allows_shelf_exhausted_path(
        module_enabled=True,
        strategy=AutoShelfBidControlStrategy.CTR,
    )


def test_still_have_bids_to_test_no_latch() -> None:
    """Scenario: Still have bids to test — no terminal pause."""
    result = should_latch_terminal_block(
        TerminalDetectInput(
            module_enabled=True,
            strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
            next_test_bid_minor=150,
            plan_ranked=[{"bid": 100, "cpo_rub": 999.0}],
            qualified_tested_bid_minors=[100],
            resolve_cpo_value=200.0,
            resolve_cpo_kind="max",
        )
    )
    assert result.should_latch is False
    assert result.reason == "still_have_bids_to_test"


def test_terminal_latch_when_exhausted_no_plan_fit() -> None:
    """Scenario: Exhausted epoch and no resolve-CPO fit."""
    result = should_latch_terminal_block(
        TerminalDetectInput(
            module_enabled=True,
            strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
            next_test_bid_minor=None,
            plan_ranked=[{"bid": 100, "cpo_rub": 350.0}],
            qualified_tested_bid_minors=[100],
            resolve_cpo_value=200.0,
            resolve_cpo_kind="target",
        )
    )
    assert result.should_latch is True
    assert result.has_plan_fit is False


def test_plan_fit_uses_resolve_not_always_max() -> None:
    """Resolve CPO target vs max — fit under target when forecast meets plan."""
    assert has_resolve_cpo_plan_fit(
        plan_ranked=[{"bid": 100, "cpo_rub": 180.0}],
        qualified_tested_bid_minors=[100],
        resolve_cpo_value=200.0,
    )
    assert not has_resolve_cpo_plan_fit(
        plan_ranked=[{"bid": 100, "cpo_rub": 250.0}],
        qualified_tested_bid_minors=[100],
        resolve_cpo_value=200.0,
    )


def test_keep_block_and_clear_signals() -> None:
    """Scenarios: keep-block / calendar / plan-fit clear."""
    now = datetime(2026, 8, 11, tzinfo=UTC)
    assert clear_our_block_due_to_plan_fit(block_active=True, has_plan_fit=True)
    assert not clear_our_block_due_to_plan_fit(block_active=True, has_plan_fit=False)
    assert clear_our_block_due_to_calendar(
        block_active=True,
        due_at=now - timedelta(seconds=1),
        now=now,
    )
    assert not clear_our_block_due_to_calendar(
        block_active=True,
        due_at=now + timedelta(days=1),
        now=now,
    )


def test_coverage_epoch_clamp() -> None:
    """date_from = max(now-7d, epoch_start)."""
    now = datetime(2026, 8, 11, tzinfo=UTC)
    epoch = now - timedelta(days=2)
    assert coverage_date_from_for_epoch(now=now, epoch_start=epoch) == epoch
    old_epoch = now - timedelta(days=30)
    assert coverage_date_from_for_epoch(
        now=now, epoch_start=old_epoch
    ) == now - timedelta(days=7)


def test_reason_distinct_from_cost_and_empty_keywords() -> None:
    """Scenario: Reason is not masked as cost or empty-keywords."""
    assert AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN.value == "shelf_exhausted_no_plan"
    assert AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN != AutoReasonCode.COST_RULE_FAILED
    assert AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN != AutoReasonCode.EMPTY_KEYWORDS
    assert is_shelf_exhausted_reason(AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN)
    assert not is_shelf_exhausted_reason(AutoReasonCode.COST_RULE_FAILED)


def test_telegram_payload_limits_and_no_tech_leak() -> None:
    """T1–T6: notify + callback_data limits / escaping / no raw adapters."""
    shop = "Магазин " + ("Ж" * 200) + " <script>&"
    camp = "Кампания " + ("Ы" * 200)
    due = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    text = build_shelf_exhausted_pause_message(
        shop_name=shop,
        campaign_name=camp,
        resolve_cpo_kind="target",
        resolve_cpo_value=999999.99,
        due_at=due,
    )
    assert len(text) <= 4096
    assert "<script>" not in text
    assert "&amp;" in text or "&lt;" in text
    assert "pause_auto_campaign" not in text
    assert "SHELF_EXHAUSTED" not in text
    assert "shelf_exhausted_no_plan" not in text
    assert RESET_PAUSE_BUTTON_TEXT in text
    cb = build_shelf_exhausted_reset_callback_data(12_345_678)
    assert 1 <= len(cb.encode("utf-8")) <= 64


@pytest.mark.asyncio
async def test_activity_terminal_pause_auto_not_search_side_effect_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Exhausted → pause_auto_campaign; Search MUST NOT pause.

    PA_SIDE_EFFECT_PROOF: this-run Auto pause + forbidden sibling non-effect.
    """
    adv = SimpleNamespace(
        bot_active=True,
        auto_budget_watchdog_enabled=True,
        auto_adv_id=501,
        search_adv_id=None,
        shop_id="shop-x",
        shop_name="Shop",
        main_nmid=9001,
        nmids=[9001],
        auto_adv_active_status_str=WBAdvActiveStatus.STARTED,
        search_adv_active_status_str=WBAdvActiveStatus.PAUSE,
        use_common_budget=False,
        auto_budget_daily_limit=100,
        search_auto_budget_daily_limit=0,
        rec_system_promotion_mode_active=True,
        adv_setting=SimpleNamespace(
            id=77,
            name="Camp",
            wb_cabinet_id=1,
            auto_shelf_bid_control_enabled=True,
            rec_system_mode=True,
            plan_for_sales_for_day=10,
            target_price_for_order=100,
            max_price_for_order=200,
            sales_predict_method=None,
        ),
        search_adv=None,
        get_keywords=AsyncMock(return_value=[]),
    )
    state = SimpleNamespace(
        shelf_exhausted_pause_active=True,
        shelf_exhausted_notify_sent_at=datetime.now(UTC),  # skip notify fanout
        shelf_exhausted_resolve_cpo_kind="max",
        shelf_exhausted_resolve_cpo_value=250.0,
        shelf_exhausted_due_at=datetime.now(UTC) + timedelta(days=7),
        shelf_exhausted_epoch_pending=False,
    )
    repo = MagicMock()
    repo.get_state = AsyncMock(return_value=state)
    repo.mark_shelf_exhausted_notify_sent = AsyncMock()
    wb = RecordingWbAutoLifecycle()
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
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.intent.EmptyKeywordsPauseIntentManager.peek_intent",
        AsyncMock(return_value=False),
    )

    # get_session_maker is @asynccontextmanager — call returns ACM, not coroutine.
    class _FakeSessionCM:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.get_session_maker",
        lambda *a, **k: _FakeSessionCM(),
    )

    async def _run(handlers, *a, **k):
        for h in handlers:
            await h()
        return []

    mock_ts = MagicMock()
    mock_ts.load_for_adv_ids = AsyncMock(return_value={77: None})
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=50.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts):
        await service.ensure_campaigns_active([adv])  # type: ignore[list-item]

    assert "pause_auto_campaign" in wb.methods_called()
    assert "pause_auction_campaign" not in wb.methods_called()
    reason_manager.set.assert_awaited()
    args = reason_manager.set.await_args.args
    assert args[1] == "auto"
    assert args[2].reason_code == AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN
    assert args[2].command == CampaignActivityCommand.PAUSE


@pytest.mark.asyncio
async def test_activity_control_pauses_auto_when_shelf_exhausted_without_fact_predict_orders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED ROOT-001: PG shelf our-block MUST pause Auto even if cost data missing.

    Masking happy-path supplies fact_predict_orders; this case uses None so the
    early-return before _maybe_apply_shelf_exhausted_pause is exercised.
    """
    adv = SimpleNamespace(
        bot_active=True,
        auto_budget_watchdog_enabled=True,
        auto_adv_id=501,
        search_adv_id=None,
        shop_id="shop-x",
        shop_name="Shop",
        main_nmid=9001,
        nmids=[9001],
        auto_adv_active_status_str=WBAdvActiveStatus.STARTED,
        search_adv_active_status_str=WBAdvActiveStatus.PAUSE,
        use_common_budget=False,
        auto_budget_daily_limit=100,
        search_auto_budget_daily_limit=0,
        rec_system_promotion_mode_active=True,
        adv_setting=SimpleNamespace(
            id=77,
            name="Camp",
            wb_cabinet_id=1,
            auto_shelf_bid_control_enabled=True,
            rec_system_mode=True,
            plan_for_sales_for_day=10,
            target_price_for_order=100,
            max_price_for_order=200,
            sales_predict_method=None,
        ),
        search_adv=None,
        get_keywords=AsyncMock(return_value=[]),
    )
    state = SimpleNamespace(
        shelf_exhausted_pause_active=True,
        shelf_exhausted_notify_sent_at=datetime.now(UTC),  # skip notify fanout
        shelf_exhausted_resolve_cpo_kind="max",
        shelf_exhausted_resolve_cpo_value=250.0,
        shelf_exhausted_due_at=datetime.now(UTC) + timedelta(days=7),
        shelf_exhausted_epoch_pending=False,
    )
    repo = MagicMock()
    repo.get_state = AsyncMock(return_value=state)
    repo.mark_shelf_exhausted_notify_sent = AsyncMock()
    wb = RecordingWbAutoLifecycle()
    reason_manager = MagicMock()
    reason_manager.set = AsyncMock()
    plan_fact = MagicMock(spec=PlanFactReader)
    plan_fact.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=501, fact_predict_orders=None, fact_pay_for_order=None
        )
    )
    service = AutoAdvActiveControlService(
        wb_modifier=wb,  # type: ignore[arg-type]
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact,
        redis_campaign_activity_reason_manager=reason_manager,
        shelf_bid_control_repository=repo,
    )
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.intent.EmptyKeywordsPauseIntentManager.peek_intent",
        AsyncMock(return_value=False),
    )

    class _FakeSessionCM:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.get_session_maker",
        lambda *a, **k: _FakeSessionCM(),
    )

    async def _run(handlers, *a, **k):
        for h in handlers:
            await h()
        return []

    mock_ts = MagicMock()
    mock_ts.load_for_adv_ids = AsyncMock(return_value={77: None})
    with patch(f"{_SERVICE_MODULE}.run_tasks", new=_run), patch(
        f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=50.0),
    ), patch(
        f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
        new=AsyncMock(return_value=0.0),
    ), patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts):
        await service.ensure_campaigns_active([adv])  # type: ignore[list-item]

    assert "pause_auto_campaign" in wb.methods_called(), (
        "PG shelf-exhausted our-block MUST still pause Auto when "
        "fact_predict_orders is missing (must not early-return before "
        "_maybe_apply_shelf_exhausted_pause)"
    )
    assert "pause_auction_campaign" not in wb.methods_called()
    reason_manager.set.assert_awaited()
    args = reason_manager.set.await_args.args
    assert args[1] == "auto"
    assert args[2].reason_code == AutoReasonCode.SHELF_EXHAUSTED_NO_PLAN
    assert args[2].command == CampaignActivityCommand.PAUSE


@pytest.mark.asyncio
async def test_legacy_cost_pause_when_shelf_module_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Shelf module off — legacy cost pause may apply."""
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.intent.EmptyKeywordsPauseIntentManager.consume_intent",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.intent.EmptyKeywordsPauseIntentManager.peek_intent",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.intent.EmptyKeywordsPauseIntentManager.set_intent",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "empty_keywords_pause.decision.is_warmup_false_empty_keywords",
        AsyncMock(return_value=False),
    )

    class _FakeSessionCM:
        async def __aenter__(self):
            return MagicMock()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.get_session_maker",
        lambda *a, **k: _FakeSessionCM(),
    )
    from tests.app.modules.shop_runner.service_manager.test_auto_adv_active_control import (
        _run_auto_cost_rule_case,
    )

    wb_modifier = await _run_auto_cost_rule_case(
        avg_cost=150.0,
        fact_pay_for_order=120.0,
        auto_shelf_bid_control_enabled=False,
    )
    wb_modifier.pause_auto_campaign.assert_awaited_once()

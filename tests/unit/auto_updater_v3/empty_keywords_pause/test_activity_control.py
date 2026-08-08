"""Unit: activity-control исполняет empty-keywords pause как следующий шаг."""

from __future__ import annotations

from typing import Any, Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.shop_runner.service_manager.services.auto_adv_active_control import (
    AutoAdvActiveControlService,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.decision import (
    is_empty_keywords_reason,
    stats_window_compatible_with_recheck,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
    PlanFactSummary,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
    AutoReasonCode,
    CampaignActivityCommand,
    RedisCampaignActivityReasonManager,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

_SERVICE_MODULE = (
    "app.modules.shop_runner.service_manager.services.auto_adv_active_control"
    ".auto_adv_active_control_service"
)


class _FakeAdvSetting:
    def __init__(self, active_status: str, adv_id: int) -> None:
        self.active_status = active_status
        self.adv_id = adv_id
        self.id = adv_id
        self.wb_cabinet_id = 1
        self.plan_for_sales_for_day = 10
        self.target_price_for_order = 100
        self.max_price_for_order = 200
        self.rec_system_mode = True
        self.sales_predict_method = FactMethods.DIRECT_SALES
        self.auto_shelf_bid_control_enabled = False
        self.bidder_coroutine_type = BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
        self.name = "Тестовая РК"
        self.card_ab_hold_mode = "active"


class _FakeComplexAdv:
    def __init__(self, *, auto_status: str, auto_adv_id: int = 9001) -> None:
        self.bot_active = True
        self.auto_budget_watchdog_enabled = True
        self._auto_budget_daily_limit = 100
        self._search_auto_budget_daily_limit = 0
        self._adv_setting = _FakeAdvSetting(auto_status, auto_adv_id)
        self.search_adv = None
        self.shop_id = "shop-empty-kw"
        self.auto_adv_id = auto_adv_id
        self.search_adv_id = None
        self.auto_adv_active_status_str = WBAdvActiveStatus(auto_status)
        self.search_adv_active_status_str = None
        self._use_common_budget = False
        self._common_budget_daily_limit = None

    @property
    def adv_setting(self) -> _FakeAdvSetting:
        return self._adv_setting

    @property
    def auto_budget_daily_limit(self) -> int:
        return self._auto_budget_daily_limit

    @property
    def search_auto_budget_daily_limit(self) -> int:
        return self._search_auto_budget_daily_limit

    @property
    def use_common_budget(self) -> bool:
        return self._use_common_budget

    @property
    def common_budget_daily_limit(self) -> int | None:
        return self._common_budget_daily_limit

    @property
    def rec_system_promotion_mode_active(self) -> bool:
        return self._adv_setting.rec_system_mode


async def _run_tasks(
    handlers: list[Callable[[], Awaitable[None]]], *args: Any, **kwargs: Any
) -> list[object]:
    return [await h() for h in handlers]


async def _mock_load_time_settings(session: object, adv_ids: list[int]) -> dict[int, None]:
    return {aid: None for aid in adv_ids}


@pytest.fixture(autouse=True)
def _positive_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_intent_triggers_pause_with_empty_keywords_reason(
    fake_redis: FakeRedis,
) -> None:
    """Следующий шаг после OFF: consume intent → pause + EMPTY_KEYWORDS в Redis.

    ``_set_auto_reason`` → real ``RedisCampaignActivityReasonManager`` (fakeredis),
    не MagicMock-only: roundtrip ``get`` доказывает durable reason boundary.
    """
    adv = _FakeComplexAdv(auto_status="started")
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        await EmptyKeywordsPauseIntentManager().set_intent(9001)

        wb_modifier = MagicMock()
        wb_modifier.pause_auto_campaign = AsyncMock()
        wb_modifier.start_auto_campaign = AsyncMock()
        plan_fact_reader = MagicMock(spec=PlanFactReader)
        plan_fact_reader.get_latest_plan_fact = AsyncMock(
            return_value=PlanFactSummary(
                adv_id=9001,
                fact_predict_orders=12.0,
                fact_pay_for_order=50.0,
            )
        )
        service = AutoAdvActiveControlService(
            wb_modifier=wb_modifier,
            tasks_manager=MagicMock(),
            plan_fact_reader=plan_fact_reader,
            redis_campaign_activity_reason_manager=reason_manager,
        )
        mock_ts = MagicMock()
        mock_ts.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings)
        notify_mock = AsyncMock()

        with (
            patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks),
            patch(
                f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
                new=AsyncMock(return_value=0.0),
            ),
            patch(
                f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
                new=AsyncMock(return_value=40.0),
            ),
            patch(f"{_SERVICE_MODULE}.resolve_target_cost", return_value=100.0),
            patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts),
            patch(
                "app.modules.shop_runner.service_manager.services.auto_updater_v3"
                ".empty_keywords_pause.notify_empty_keywords_pause",
                new=notify_mock,
            ),
        ):
            await service.ensure_campaigns_active([adv])

        wb_modifier.pause_auto_campaign.assert_awaited_once()
        wb_modifier.start_auto_campaign.assert_not_awaited()
        stored = await reason_manager.get(9001, "auto")
        assert stored is not None
        assert stored.command == CampaignActivityCommand.PAUSE
        assert is_empty_keywords_reason(stored.reason_code)
        assert stored.reason_code == AutoReasonCode.EMPTY_KEYWORDS
        assert stored.reason_code != AutoReasonCode.TIME_SCHEDULE
        assert stored.reason_code != AutoReasonCode.COMMON_SPEND_EXCEEDED
        raw = await fake_redis.get("campaign-activity-reason:9001:auto")
        assert raw is not None
        assert "empty_keywords" in raw
        notify_mock.assert_awaited_once()
        assert await EmptyKeywordsPauseIntentManager().peek_intent(9001) is False
        # Orthogonality: Hold mode не EXIT в OFF из-за empty-keywords pause
        assert adv.adv_setting.card_ab_hold_mode == "active"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recheck_starts_when_paused_without_intent(
    fake_redis: FakeRedis,
) -> None:
    """Recheck: PAUSE без intent → start (empty-keywords не блокирует resume)."""
    adv = _FakeComplexAdv(auto_status="pause")
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        wb_modifier = MagicMock()
        wb_modifier.pause_auto_campaign = AsyncMock()
        wb_modifier.start_auto_campaign = AsyncMock()
        reason_manager = MagicMock()
        reason_manager.set = AsyncMock()
        plan_fact_reader = MagicMock(spec=PlanFactReader)
        plan_fact_reader.get_latest_plan_fact = AsyncMock(
            return_value=PlanFactSummary(
                adv_id=9001,
                fact_predict_orders=12.0,
                fact_pay_for_order=50.0,
            )
        )
        service = AutoAdvActiveControlService(
            wb_modifier=wb_modifier,
            tasks_manager=MagicMock(),
            plan_fact_reader=plan_fact_reader,
            redis_campaign_activity_reason_manager=reason_manager,
        )
        mock_ts = MagicMock()
        mock_ts.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings)

        with (
            patch(f"{_SERVICE_MODULE}.run_tasks", new=_run_tasks),
            patch(
                f"{_SERVICE_MODULE}.AutoAdvActiveControlService._get_spend_for_adv",
                new=AsyncMock(return_value=0.0),
            ),
            patch(
                f"{_SERVICE_MODULE}.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
                new=AsyncMock(return_value=40.0),
            ),
            patch(f"{_SERVICE_MODULE}.resolve_target_cost", return_value=100.0),
            patch(f"{_SERVICE_MODULE}._time_settings_repo", mock_ts),
            patch(
                f"{_SERVICE_MODULE}.AutoAdvActiveControlService"
                "._start_auto_campaign_maybe_retry",
                new=AsyncMock(),
            ) as start_retry,
        ):
            await service.ensure_campaigns_active([adv])

        start_retry.assert_awaited_once()
        wb_modifier.pause_auto_campaign.assert_not_awaited()


@pytest.mark.unit
def test_recheck_7d_stats_window_gate() -> None:
    """Spec Seven-day: цикл recheck совместим с ≤7d; >7 не требуется."""
    assert stats_window_compatible_with_recheck(7) is True
    assert stats_window_compatible_with_recheck(3) is True
    # Gate: удаление верхней границы ломает контракт «не ждать >7d»
    assert stats_window_compatible_with_recheck(8) is False


@pytest.mark.unit
def test_empty_reason_not_masked_as_schedule_budget() -> None:
    """Regression 1.6: EMPTY_KEYWORDS ≠ TIME_SCHEDULE / budget / cost."""
    assert AutoReasonCode.EMPTY_KEYWORDS.value == "empty_keywords"
    assert AutoReasonCode.EMPTY_KEYWORDS != AutoReasonCode.TIME_SCHEDULE
    assert is_empty_keywords_reason(AutoReasonCode.EMPTY_KEYWORDS)
    assert not is_empty_keywords_reason(AutoReasonCode.COST_RULE_FAILED)
    display = __import__(
        "app.modules.shop_runner.service_manager.services"
        ".redis_campaign_activity_reason_manager.reason_display",
        fromlist=["reason_code_to_display_text"],
    ).reason_code_to_display_text(AutoReasonCode.EMPTY_KEYWORDS.value)
    assert "ключ" in display.lower() or "акт" in display.lower()
    assert "расп" not in display.lower()

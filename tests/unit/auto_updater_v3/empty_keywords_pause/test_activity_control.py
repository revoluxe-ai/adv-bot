"""Unit: activity-control исполняет empty-keywords pause на Search (INC-PAUSE-02)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
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
    AuctionReasonCode,
    AutoReasonCode,
    CampaignActivityCommand,
    RedisCampaignActivityReasonManager,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.dto.campaign_activity_reason import (
    CampaignActivityReason,
)
from app.shared.domains.wb.enums import AdvType
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from tests.unit.auto_updater_v3.empty_keywords_pause.notify_empty_keywords_contract import (
    NOTIFY_AFTER_SEARCH_PAUSE_CASE,
    assert_notify_mock_matches_case,
)
from tests.unit.auto_updater_v3.empty_keywords_pause.wb_search_lifecycle_contract import (
    WB_SEARCH_LIFECYCLE_CASES,
    RecordingWbLifecycleModifier,
)

_SERVICE_MODULE = (
    "app.modules.shop_runner.service_manager.services.auto_adv_active_control"
    ".auto_adv_active_control_service"
)
_NOTIFY_PATH = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3"
    ".empty_keywords_pause.notify_empty_keywords_pause"
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
    """Комплект с Auto + Search; empty-keywords бьёт только в Search."""

    def __init__(
        self,
        *,
        auto_status: str,
        search_status: str | None = "started",
        auto_adv_id: int = 9001,
        search_adv_id: int | None = 9002,
        search_limit: int = 100,
        active_keywords: list[Any] | None = None,
    ) -> None:
        self.bot_active = True
        self.auto_budget_watchdog_enabled = True
        self._auto_budget_daily_limit = 100
        self._search_auto_budget_daily_limit = search_limit
        self._adv_setting = _FakeAdvSetting(auto_status, auto_adv_id)
        self.search_adv = None if search_adv_id is None else MagicMock()
        self.shop_id = "shop-empty-kw"
        self.auto_adv_id = auto_adv_id
        self.search_adv_id = search_adv_id
        self.auto_adv_active_status_str = WBAdvActiveStatus(auto_status)
        self.search_adv_active_status_str = (
            None if search_status is None else WBAdvActiveStatus(search_status)
        )
        self._use_common_budget = False
        self._common_budget_daily_limit = None
        # Empty: skip shelf-exhausted epoch open (needs nmids attribute parity
        # with ComplexAdv after Auto pause→start; avoid PG get_state in unit).
        self.nmids: list[int] = []
        # Default empty: positive empty-keywords pause path expects revalidation OK.
        self._active_keywords: list[Any] = (
            list(active_keywords) if active_keywords is not None else []
        )

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

    @property
    def auction_adv_id(self) -> int | None:
        return self.search_adv_id

    def get_adv_id_by_type(self, adv_type: AdvType) -> int:
        """Parity с ComplexAdv для boundary / recording asserts."""
        if adv_type == AdvType.AUTO:
            return self.auto_adv_id
        if adv_type == AdvType.SEARCH:
            if self.search_adv_id is None:
                raise ValueError("search missing")
            return self.search_adv_id
        raise ValueError(adv_type)

    async def get_keywords(self, *, cache_only: bool = True) -> list[Any]:
        """Active keywords seam for empty-keywords revalidation before pause."""
        _ = cache_only
        return list(self._active_keywords)


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


def _plan_fact_reader(adv_id: int = 9001) -> MagicMock:
    plan_fact_reader = MagicMock(spec=PlanFactReader)
    plan_fact_reader.get_latest_plan_fact = AsyncMock(
        return_value=PlanFactSummary(
            adv_id=adv_id,
            fact_predict_orders=12.0,
            fact_pay_for_order=50.0,
        )
    )
    return plan_fact_reader


def _contract(case_id: str):
    for case in WB_SEARCH_LIFECYCLE_CASES:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)


def _active_keyword() -> MagicMock:
    """Один активный (не OFF) ключ — для сценария recovery / non-empty set."""
    kw = MagicMock()
    kw.strategy_mode = KeywordStrategyMode.OPTIMUM
    return kw


@asynccontextmanager
async def _ensure_active(
    *,
    adv: _FakeComplexAdv,
    wb: RecordingWbLifecycleModifier,
    reason_manager: RedisCampaignActivityReasonManager | MagicMock,
    notify: AsyncMock | None = None,
) -> AsyncIterator[AutoAdvActiveControlService]:
    """Запуск ensure_campaigns_active с стандартными activity-control patches."""
    service = AutoAdvActiveControlService(
        wb_modifier=wb,  # type: ignore[arg-type]
        tasks_manager=MagicMock(),
        plan_fact_reader=_plan_fact_reader(),
        redis_campaign_activity_reason_manager=reason_manager,
    )
    mock_ts = MagicMock()
    mock_ts.load_for_adv_ids = AsyncMock(side_effect=_mock_load_time_settings)
    notify_mock = notify if notify is not None else AsyncMock()
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
        patch(_NOTIFY_PATH, new=notify_mock),
    ):
        yield service
    _ = adv  # kept for call-site clarity / future hooks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_intent_triggers_search_pause_with_empty_keywords_reason(
    fake_redis: FakeRedis,
) -> None:
    """Positive: consume intent → pause_auction_campaign + Search-lane EMPTY_KEYWORDS."""
    adv = _FakeComplexAdv(auto_status="started", search_status="started")
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    wb = RecordingWbLifecycleModifier()
    notify_mock = AsyncMock()
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        await EmptyKeywordsPauseIntentManager().set_intent(9001)
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager, notify=notify_mock
        ) as service:
            await service.ensure_campaigns_active([adv])

        wb.assert_matches_case(
            _contract("pause_search_allowed"),
            complex_adv=adv,
            must_have_been_called=True,
        )
        wb.assert_matches_case(
            _contract("pause_auto_forbidden"),
            complex_adv=adv,
            must_have_been_called=False,
        )
        stored_search = await reason_manager.get(9002, "search")
        assert stored_search is not None
        assert stored_search.command == CampaignActivityCommand.PAUSE
        assert is_empty_keywords_reason(stored_search.reason_code)
        # parse_reason_code предпочитает Auto enum при shared value — value-контракт.
        assert stored_search.reason_code.value == AuctionReasonCode.EMPTY_KEYWORDS.value
        assert stored_search.reason_code.value != AuctionReasonCode.TIME_SCHEDULE.value
        stored_auto = await reason_manager.get(9001, "auto")
        assert stored_auto is None or not is_empty_keywords_reason(
            stored_auto.reason_code
        )
        raw = await fake_redis.get("campaign-activity-reason:9002:search")
        assert raw is not None
        assert "empty_keywords" in raw
        assert_notify_mock_matches_case(
            notify_mock,
            NOTIFY_AFTER_SEARCH_PAUSE_CASE,
            require_intent_manager=True,
        )
        assert await EmptyKeywordsPauseIntentManager().peek_intent(9001) is False
        assert adv.adv_setting.card_ab_hold_mode == "active"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_keywords_path_must_not_call_pause_auto_campaign(
    fake_redis: FakeRedis,
) -> None:
    """Wrong-adapter regression: pause_auto_campaign Forbidden for EMPTY_KEYWORDS."""
    adv = _FakeComplexAdv(auto_status="started", search_status="started")
    wb = RecordingWbLifecycleModifier()
    notify_mock = AsyncMock()
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        await EmptyKeywordsPauseIntentManager().set_intent(9001)
        async with _ensure_active(
            adv=adv,
            wb=wb,
            reason_manager=MagicMock(set=AsyncMock()),
            notify=notify_mock,
        ) as service:
            await service.ensure_campaigns_active([adv])

        wb.assert_matches_case(
            _contract("pause_auto_forbidden"),
            complex_adv=adv,
            must_have_been_called=False,
        )
        wb.assert_matches_case(
            _contract("pause_search_allowed"),
            complex_adv=adv,
            must_have_been_called=True,
        )
        assert_notify_mock_matches_case(
            notify_mock,
            NOTIFY_AFTER_SEARCH_PAUSE_CASE,
            require_intent_manager=True,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_search_leg_does_not_pause_auto(
    fake_redis: FakeRedis,
) -> None:
    """Missing Search → consume intent, MUST NOT pause Auto."""
    adv = _FakeComplexAdv(
        auto_status="started",
        search_status=None,
        search_adv_id=None,
    )
    wb = RecordingWbLifecycleModifier()
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        await EmptyKeywordsPauseIntentManager().set_intent(9001)
        async with _ensure_active(
            adv=adv,
            wb=wb,
            reason_manager=MagicMock(set=AsyncMock()),
        ) as service:
            await service.ensure_campaigns_active([adv])

        assert "pause_auto_campaign" not in wb.methods_called()
        assert "pause_auction_campaign" not in wb.methods_called()
        assert await EmptyKeywordsPauseIntentManager().peek_intent(9001) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recheck_starts_search_when_paused_without_intent(
    fake_redis: FakeRedis,
) -> None:
    """Recheck: Search PAUSE без intent → start_auction_campaign (не патчим seam)."""
    adv = _FakeComplexAdv(auto_status="started", search_status="pause")
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    await reason_manager.set(
        9002,
        "search",
        CampaignActivityReason(
            command=CampaignActivityCommand.PAUSE,
            reason_code=AuctionReasonCode.EMPTY_KEYWORDS,
        ),
    )
    wb = RecordingWbLifecycleModifier()
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        wb.assert_matches_case(
            _contract("start_search_recheck"),
            complex_adv=adv,
            must_have_been_called=True,
        )
        wb.assert_matches_case(
            _contract("pause_search_allowed"),
            complex_adv=adv,
            must_have_been_called=False,
        )
        wb.assert_matches_case(
            _contract("pause_auto_forbidden"),
            complex_adv=adv,
            must_have_been_called=False,
        )
        stored = await reason_manager.get(9002, "search")
        assert stored is not None
        assert stored.command == CampaignActivityCommand.STARTED
        assert stored.reason_code == AuctionReasonCode.SEARCH_LIMIT_OK


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recheck_resume_then_repause_when_still_empty(
    fake_redis: FakeRedis,
) -> None:
    """Scenario: recheck start Search → still empty intent → Search re-pause."""
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    await reason_manager.set(
        9002,
        "search",
        CampaignActivityReason(
            command=CampaignActivityCommand.PAUSE,
            reason_code=AuctionReasonCode.EMPTY_KEYWORDS,
        ),
    )
    wb = RecordingWbLifecycleModifier()
    notify_mock = AsyncMock()
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        # Tick 1: Search PAUSE, no intent → start Search (recheck).
        adv = _FakeComplexAdv(auto_status="started", search_status="pause")
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])
        assert "start_auction_campaign" in wb.methods_called()

        # V3 apply still empty → intent; Search appears STARTED after recheck start.
        await EmptyKeywordsPauseIntentManager().set_intent(9001)
        adv.search_adv_active_status_str = WBAdvActiveStatus.STARTED
        wb.calls.clear()

        # Tick 2: intent → pause Search again with EMPTY_KEYWORDS.
        async with _ensure_active(
            adv=adv,
            wb=wb,
            reason_manager=reason_manager,
            notify=notify_mock,
        ) as service:
            await service.ensure_campaigns_active([adv])

        wb.assert_matches_case(
            _contract("pause_search_allowed"),
            complex_adv=adv,
            must_have_been_called=True,
        )
        assert_notify_mock_matches_case(
            notify_mock,
            NOTIFY_AFTER_SEARCH_PAUSE_CASE,
            require_intent_manager=True,
        )
        stored = await reason_manager.get(9002, "search")
        assert stored is not None
        assert stored.command == CampaignActivityCommand.PAUSE
        assert is_empty_keywords_reason(stored.reason_code)
        assert await EmptyKeywordsPauseIntentManager().peek_intent(9001) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recheck_continue_when_keywords_active_no_empty_pause(
    fake_redis: FakeRedis,
) -> None:
    """Scenario: after recheck start, no intent → Search stays up (not empty-pause)."""
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    await reason_manager.set(
        9002,
        "search",
        CampaignActivityReason(
            command=CampaignActivityCommand.PAUSE,
            reason_code=AuctionReasonCode.EMPTY_KEYWORDS,
        ),
    )
    wb = RecordingWbLifecycleModifier()
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        adv = _FakeComplexAdv(auto_status="started", search_status="pause")
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])
        assert "start_auction_campaign" in wb.methods_called()

        # Keywords became active: non-empty set + no intent → Search stays up.
        adv._active_keywords = [_active_keyword()]
        adv.search_adv_active_status_str = WBAdvActiveStatus.STARTED
        wb.calls.clear()
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        assert "pause_auction_campaign" not in wb.methods_called()
        stored = await reason_manager.get(9002, "search")
        assert stored is not None
        assert stored.command == CampaignActivityCommand.STARTED
        assert stored.reason_code == AuctionReasonCode.SEARCH_LIMIT_OK
        assert not is_empty_keywords_reason(stored.reason_code)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auto_only_start_does_not_satisfy_empty_keywords_recheck(
    fake_redis: FakeRedis,
) -> None:
    """Scenario: Search PAUSE empty-keywords → MUST start Search, not Auto-only."""
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    await reason_manager.set(
        9002,
        "search",
        CampaignActivityReason(
            command=CampaignActivityCommand.PAUSE,
            reason_code=AuctionReasonCode.EMPTY_KEYWORDS,
        ),
    )
    # Auto already STARTED — only Search needs recheck start.
    adv = _FakeComplexAdv(auto_status="started", search_status="pause")
    wb = RecordingWbLifecycleModifier()
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        # Causal boundary intact: start goes through wb_modifier.start_auction_campaign.
        wb.assert_matches_case(
            _contract("start_search_recheck"),
            complex_adv=adv,
            must_have_been_called=True,
        )
        # Auto-only would leave Search reason as PAUSE empty_keywords — production
        # clears it only via Search start path to SEARCH_LIMIT_OK.
        assert "start_auto_campaign" not in wb.methods_called()
        stored = await reason_manager.get(9002, "search")
        assert stored is not None
        assert stored.command == CampaignActivityCommand.STARTED
        assert stored.reason_code == AuctionReasonCode.SEARCH_LIMIT_OK


@pytest.mark.unit
def test_recheck_7d_stats_window_gate() -> None:
    """Spec Seven-day: цикл recheck совместим с ≤7d; >7 не требуется."""
    assert stats_window_compatible_with_recheck(7) is True
    assert stats_window_compatible_with_recheck(3) is True
    assert stats_window_compatible_with_recheck(8) is False


@pytest.mark.unit
def test_empty_reason_not_masked_as_schedule_budget() -> None:
    """EMPTY_KEYWORDS ≠ TIME_SCHEDULE / budget / cost (Search + Auto enums)."""
    assert AuctionReasonCode.EMPTY_KEYWORDS.value == "empty_keywords"
    assert AuctionReasonCode.EMPTY_KEYWORDS != AuctionReasonCode.TIME_SCHEDULE
    assert is_empty_keywords_reason(AuctionReasonCode.EMPTY_KEYWORDS)
    assert is_empty_keywords_reason(AutoReasonCode.EMPTY_KEYWORDS)
    assert not is_empty_keywords_reason(AuctionReasonCode.COMMON_SPEND_EXCEEDED)
    display = __import__(
        "app.modules.shop_runner.service_manager.services"
        ".redis_campaign_activity_reason_manager.reason_display",
        fromlist=["reason_code_to_display_text"],
    ).reason_code_to_display_text(AuctionReasonCode.EMPTY_KEYWORDS.value)
    assert "ключ" in display.lower() or "акт" in display.lower()
    assert "расп" not in display.lower()

"""Unit: stale empty-keywords intent must not pause after keyword recovery.

ROOT-001: ``_maybe_pause_for_empty_keywords_intent`` must re-read active keywords
before ``pause_auction_campaign`` / Search ``EMPTY_KEYWORDS`` / notify. Intent TTL
6h allows keywords to recover while intent is still pending.

Patterns adapted from ``test_activity_control.py``; causal boundary intact
(``consume_intent`` → pause path via production ``ensure_campaigns_active``).
"""

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
    count_active_keywords,
    is_empty_keywords_reason,
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
    CampaignActivityCommand,
    RedisCampaignActivityReasonManager,
)
from app.shared.domains.wb.enums import AdvType
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from tests.unit.auto_updater_v3.empty_keywords_pause.wb_search_lifecycle_contract import (
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

TEST_ID = "ROOT-001::test_stale_intent_requires_empty_revalidation"


class _FakeAdvSetting:
    """Минимальный adv_setting для activity-control unit path."""

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


def _active_keyword() -> MagicMock:
    """Один активный (не OFF) ключ — recovered non-empty set."""
    kw = MagicMock()
    kw.strategy_mode = KeywordStrategyMode.OPTIMUM
    return kw


class _FakeComplexAdv:
    """Комплект Auto+Search с recoverable keywords для revalidation assert."""

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
        self.shop_id = "shop-stale-intent"
        self.auto_adv_id = auto_adv_id
        self.search_adv_id = search_adv_id
        self.auto_adv_active_status_str = WBAdvActiveStatus(auto_status)
        self.search_adv_active_status_str = (
            None if search_status is None else WBAdvActiveStatus(search_status)
        )
        self._use_common_budget = False
        self._common_budget_daily_limit = None
        # Empty: skip shelf-exhausted epoch open (ComplexAdv.nmids parity).
        self.nmids: list[int] = []
        self._active_keywords: list[Any] = (
            list(active_keywords) if active_keywords is not None else [_active_keyword()]
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
        """Parity с ComplexAdv для boundary asserts."""
        if adv_type == AdvType.AUTO:
            return self.auto_adv_id
        if adv_type == AdvType.SEARCH:
            if self.search_adv_id is None:
                raise ValueError("search missing")
            return self.search_adv_id
        raise ValueError(adv_type)

    async def get_keywords(self, *, cache_only: bool = True) -> list[Any]:
        """Active keywords from Redis-shaped cache (shop-runner production seam)."""
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
    _ = adv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stale_intent_requires_empty_revalidation(
    fake_redis: FakeRedis,
) -> None:
    """Stale intent + recovered non-empty keywords ⇒ no Search pause / no EMPTY_KEYWORDS.

    Causal boundary left intact: peek/consume → pause path is exercised via
    production ``ensure_campaigns_active`` (not patched away). Keywords on
    ``ComplexAdv.get_keywords`` are non-empty so revalidation must skip pause.
    """
    recovered = [_active_keyword(), _active_keyword()]
    assert count_active_keywords(recovered) >= 1

    adv = _FakeComplexAdv(
        auto_status="started",
        search_status="started",
        active_keywords=recovered,
    )
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    wb = RecordingWbLifecycleModifier()
    notify_mock = AsyncMock()

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        await EmptyKeywordsPauseIntentManager().set_intent(9001)
        assert await EmptyKeywordsPauseIntentManager().peek_intent(9001) is True

        assert count_active_keywords(await adv.get_keywords()) >= 1

        async with _ensure_active(
            adv=adv,
            wb=wb,
            reason_manager=reason_manager,
            notify=notify_mock,
        ) as service:
            await service.ensure_campaigns_active([adv])

        assert "pause_auction_campaign" not in wb.methods_called(), (
            f"{TEST_ID}: pending empty-keywords intent with non-empty active keywords "
            "must NOT call pause_auction_campaign (stale-intent pause)"
        )
        stored_search = await reason_manager.get(9002, "search")
        assert stored_search is None or not is_empty_keywords_reason(
            stored_search.reason_code
        ), (
            f"{TEST_ID}: must NOT stamp Search EMPTY_KEYWORDS solely from stale intent "
            f"(got {stored_search!r})"
        )
        if stored_search is not None:
            assert stored_search.reason_code != AuctionReasonCode.EMPTY_KEYWORDS
            assert stored_search.command != CampaignActivityCommand.PAUSE or (
                not is_empty_keywords_reason(stored_search.reason_code)
            )
        assert notify_mock.await_count == 0, (
            f"{TEST_ID}: must NOT notify empty-keywords pause from stale intent "
            "when keywords recovered"
        )
        assert await EmptyKeywordsPauseIntentManager().peek_intent(9001) is False

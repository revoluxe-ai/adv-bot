"""ROOT-001: tick2 empty-keywords intent when Search is not STARTED.

BUGCASE-EMPTY-KW-TICK2-NOTIFY-NO-STARTED: residual of two-tick confirmation.

GIVEN tick1 latched empty-keywords intent while Search STARTED
AND between ticks Search becomes not STARTED (budget/schedule pause)
AND keywords remain settled-empty
WHEN ``ensure_campaigns_active`` runs tick2
THEN ``pause_auction_campaign`` is skipped (already not STARTED) AND
MUST NOT write Search-lane EMPTY_KEYWORDS, MUST NOT call
``notify_empty_keywords_pause`` (resume episode gate), and MUST NOT
overwrite a prior non-empty-keywords pause reason.

Current production gates only ``pause_auction_campaign`` on STARTED, then
unconditionally ``_set_search_reason(EMPTY_KEYWORDS)`` + notify — RED fails
until fixed. No ``app/**`` edits from this suite.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.decision import (
    count_active_keywords,
    is_empty_keywords_reason,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
    AuctionReasonCode,
    CampaignActivityCommand,
    RedisCampaignActivityReasonManager,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.dto.campaign_activity_reason import (
    CampaignActivityReason,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from tests.unit.auto_updater_v3.empty_keywords_pause.test_activity_control import (
    _SERVICE_MODULE,
    _FakeComplexAdv,
    _ensure_active,
)
from tests.unit.auto_updater_v3.empty_keywords_pause.wb_search_lifecycle_contract import (
    RecordingWbLifecycleModifier,
)

_AUTO_ADV_ID = 93001
_SEARCH_ADV_ID = 93002


def _all_off_settled_keywords(*, n: int = 3) -> list[Any]:
    """Settled-empty: keyword objects present, all strategy_mode=OFF."""
    out: list[Any] = []
    for i in range(n):
        kw = MagicMock(name=f"off_kw_{i}")
        kw.strategy_mode = KeywordStrategyMode.OFF
        out.append(kw)
    assert count_active_keywords(out) == 0
    return out


@pytest.fixture(autouse=True)
def _positive_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same balance seam as activity-control suite."""
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tick2_empty_intent_skips_empty_kw_side_effects_when_search_not_started(
    fake_redis: FakeRedis,
) -> None:
    """RED: tick2 not-STARTED must not EMPTY_KEYWORDS-reason / notify / resume gate.

    Repro: latch on tick1 while Search STARTED; between ticks Search → PAUSE
    with prior TIME_SCHEDULE reason (budget/schedule pause stand-in); tick2
    still empty with pending intent. Unrepaired code skips WB pause but still
    stamps EMPTY_KEYWORDS + pause notify (resume-gate arming proxy).
    """
    settled_empty = _all_off_settled_keywords()
    adv = _FakeComplexAdv(
        auto_status="started",
        search_status="started",
        auto_adv_id=_AUTO_ADV_ID,
        search_adv_id=_SEARCH_ADV_ID,
        active_keywords=settled_empty,
    )
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    wb = RecordingWbLifecycleModifier()
    intent_mgr = EmptyKeywordsPauseIntentManager()
    notify_mock = AsyncMock()

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        assert await intent_mgr.peek_intent(_AUTO_ADV_ID) is False

        # --- Tick 1: latch confirmation while Search STARTED ---
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager, notify=notify_mock
        ) as service:
            await service.ensure_campaigns_active([adv])

        assert "pause_auction_campaign" not in wb.methods_called(), (
            "tick1 MUST NOT pause Search (two-tick latch only)"
        )
        assert await intent_mgr.peek_intent(_AUTO_ADV_ID) is True, (
            "tick1 MUST latch empty-keywords intent while Search STARTED"
        )
        assert notify_mock.await_count == 0

        # --- Between ticks: Search paused for schedule (not empty-keywords) ---
        wb.calls.clear()
        notify_mock.reset_mock()
        adv.search_adv_active_status_str = WBAdvActiveStatus.PAUSE
        await reason_manager.set(
            _SEARCH_ADV_ID,
            "search",
            CampaignActivityReason(
                command=CampaignActivityCommand.PAUSE,
                reason_code=AuctionReasonCode.TIME_SCHEDULE,
            ),
        )
        prior = await reason_manager.get(_SEARCH_ADV_ID, "search")
        assert prior is not None
        assert prior.reason_code == AuctionReasonCode.TIME_SCHEDULE
        assert not is_empty_keywords_reason(prior.reason_code)

        # --- Tick 2: still empty, intent pending, Search not STARTED ---
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager, notify=notify_mock
        ) as service:
            await service.ensure_campaigns_active([adv])

        assert "pause_auction_campaign" not in wb.methods_called(), (
            "tick2 Search not STARTED: pause_auction_campaign must stay skipped "
            f"(methods={wb.methods_called()})"
        )

        stored_search = await reason_manager.get(_SEARCH_ADV_ID, "search")
        assert stored_search is not None
        assert not is_empty_keywords_reason(stored_search.reason_code), (
            "ROOT-001: tick2 consume when Search not STARTED MUST NOT write "
            f"Search-lane EMPTY_KEYWORDS (got {stored_search!r})"
        )
        assert stored_search.reason_code == AuctionReasonCode.TIME_SCHEDULE, (
            "ROOT-001: prior schedule/budget pause reason must not be masked by "
            f"EMPTY_KEYWORDS (got {stored_search!r})"
        )

        assert notify_mock.await_count == 0, (
            "ROOT-001: tick2 Search not STARTED MUST NOT call "
            "notify_empty_keywords_pause (resume episode gate arming); "
            f"await_count={notify_mock.await_count}"
        )
        assert await intent_mgr.was_notified(_AUTO_ADV_ID) is False, (
            "ROOT-001: resume episode gate (was_notified) must stay unarmed when "
            "pause notify is forbidden"
        )

"""ROOT-001 / tasks §10.2: two-tick empty confirmation before Search pause.

Owner ``D_TWO_TICK_EMPTY_CONFIRMATION`` /
``TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE``
(BUGCASE-EMPTY-KW-PUNA-EMPTY-SHAPE):

GIVEN Search STARTED, no prior V3 empty-keywords intent, settled empty
(active_count==0 from all-OFF keyword objects — not Redis ``__empty__`` warmup)
WHEN ``ensure_campaigns_active`` runs twice while still empty
THEN tick1 may latch/record confirmation intent but MUST NOT call
``pause_auction_campaign``; tick2 still empty MUST call
``pause_auction_campaign`` (Search EMPTY_KEYWORDS).

Later tick with active keywords: Search start/resume path remains available
(existing recheck). Warmup ``__empty__`` is non-settled (section 7) — not
used as tick1 confirmation here.

No prod Redis; no ``app/**`` edits (RED-only).
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
    _active_keyword,
    _contract,
    _ensure_active,
)
from tests.unit.auto_updater_v3.empty_keywords_pause.wb_search_lifecycle_contract import (
    RecordingWbLifecycleModifier,
)

_AUTO_ADV_ID = 92001
_SEARCH_ADV_ID = 92002


def _all_off_settled_keywords(*, n: int = 3) -> list[Any]:
    """Settled-empty fixture: keyword objects present, all strategy_mode=OFF.

    Prefer this over bare ``[]`` so the empty signal is bot-driven OFF objects
    (count_active_keywords==0), not an absent list that can be confused with
    Redis warmup ``__empty__`` → ``[]`` reads. No ``__empty__`` Redis field.
    """
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
async def test_two_tick_empty_confirmation_tick1_no_pause_tick2_pause(
    fake_redis: FakeRedis,
) -> None:
    """RED: tick1 latch only (no pause); tick2 still empty → pause Search.

    Current product same-tick set_intent→consume→pause_auction_campaign on
    first empty observe violates Owner two-tick confirmation (tasks §10.2).
    """
    # Precondition: no Redis warmup __empty__ (settled all-OFF, not warmup).
    assert not await fake_redis.hexists(
        f"calculated_keywords:{_AUTO_ADV_ID}", "__empty__"
    )

    settled_empty = _all_off_settled_keywords()
    adv = _FakeComplexAdv(
        auto_status="started",
        search_status="started",
        auto_adv_id=_AUTO_ADV_ID,
        search_adv_id=_SEARCH_ADV_ID,
        active_keywords=settled_empty,
    )
    # Explicit: not a warmup false-empty seam.
    assert getattr(adv, "redis_keywords_empty_marker", False) is False
    assert getattr(adv, "keywords_source", None) != "redis_warmup_empty_marker"

    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    wb = RecordingWbLifecycleModifier()
    intent_mgr = EmptyKeywordsPauseIntentManager()

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        assert await intent_mgr.peek_intent(_AUTO_ADV_ID) is False, (
            "precondition: no prior V3 empty-keywords intent"
        )

        # --- Tick 1: first settled-empty observe ---
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        tick1_methods = list(wb.methods_called())
        assert "pause_auction_campaign" not in tick1_methods, (
            "TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE: tick1 empty + Search "
            "STARTED + no prior intent MUST NOT call pause_auction_campaign "
            f"(methods={tick1_methods})"
        )
        # Latch/record confirmation (durable intent) is allowed / expected so
        # tick2 can pause; same-tick consume that clears intent is a product gap.
        assert await intent_mgr.peek_intent(_AUTO_ADV_ID) is True, (
            "TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE: tick1 may/must latch "
            "confirmation intent for tick2 (peek_intent expected True after "
            "first empty observe without pause)"
        )
        stored_search_t1 = await reason_manager.get(_SEARCH_ADV_ID, "search")
        assert stored_search_t1 is None or not is_empty_keywords_reason(
            getattr(stored_search_t1, "reason_code", None)
        ), (
            "tick1 MUST NOT write Search-lane EMPTY_KEYWORDS yet "
            f"(search_reason={stored_search_t1})"
        )

        # --- Tick 2: still settled empty ---
        wb.calls.clear()
        # Search remains STARTED (tick1 did not pause).
        assert adv.search_adv_active_status_str == WBAdvActiveStatus.STARTED
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        wb.assert_matches_case(
            _contract("pause_search_allowed"),
            complex_adv=adv,
            must_have_been_called=True,
        )
        assert "pause_auction_campaign" in wb.methods_called(), (
            "TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE: tick2 still empty MUST "
            f"call pause_auction_campaign (methods={wb.methods_called()})"
        )
        wb.assert_matches_case(
            _contract("pause_auto_forbidden"),
            complex_adv=adv,
            must_have_been_called=False,
        )
        stored_search_t2 = await reason_manager.get(_SEARCH_ADV_ID, "search")
        assert stored_search_t2 is not None
        assert is_empty_keywords_reason(stored_search_t2.reason_code)
        assert (
            stored_search_t2.reason_code.value
            == AuctionReasonCode.EMPTY_KEYWORDS.value
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_later_tick_with_keywords_allows_search_start_resume(
    fake_redis: FakeRedis,
) -> None:
    """Later tick: keywords return → Search start/resume path available.

    Existing EMPTY_KEYWORDS recheck start (Search PAUSE + active keys) must
    remain reachable; ticks continue after the two-tick pause lifecycle.
    """
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    await reason_manager.set(
        _SEARCH_ADV_ID,
        "search",
        CampaignActivityReason(
            command=CampaignActivityCommand.PAUSE,
            reason_code=AuctionReasonCode.EMPTY_KEYWORDS,
        ),
    )
    adv = _FakeComplexAdv(
        auto_status="started",
        search_status="pause",
        auto_adv_id=_AUTO_ADV_ID,
        search_adv_id=_SEARCH_ADV_ID,
        active_keywords=[_active_keyword()],
    )
    wb = RecordingWbLifecycleModifier()

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        assert (
            await EmptyKeywordsPauseIntentManager().peek_intent(_AUTO_ADV_ID)
            is False
        )
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        wb.assert_matches_case(
            _contract("start_search_recheck"),
            complex_adv=adv,
            must_have_been_called=True,
        )
        assert "pause_auction_campaign" not in wb.methods_called()
        stored = await reason_manager.get(_SEARCH_ADV_ID, "search")
        assert stored is not None
        assert stored.command == CampaignActivityCommand.STARTED
        assert not is_empty_keywords_reason(stored.reason_code)

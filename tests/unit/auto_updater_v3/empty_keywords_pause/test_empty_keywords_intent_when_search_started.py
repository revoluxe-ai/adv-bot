"""ROOT-001: empty keywords + Search STARTED → two-tick latch then Search pause.

Owner ``TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE``: no-prior observe empty
latches intent on tick1 (no pause); tick2 still empty arms this-run
``pause_auction_campaign`` (pause_search_allowed).

Also guards false-green that accepted Redis intent / durable EMPTY_KEYWORDS
reason without this-run WB pause. Puna-like IDs; no prod Redis.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.decision import (
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
from tests.unit.auto_updater_v3.empty_keywords_pause.test_activity_control import (
    _SERVICE_MODULE,
    _FakeComplexAdv,
    _contract,
    _ensure_active,
)
from tests.unit.auto_updater_v3.empty_keywords_pause.wb_search_lifecycle_contract import (
    RecordingWbLifecycleModifier,
)

# Puna prod IDs from intake (nmid=85970344); no prod Redis dependency.
_PUNA_AUTO_ADV_ID = 17906286
_PUNA_SEARCH_ADV_ID = 20646357


@pytest.fixture(autouse=True)
def _positive_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same balance seam as test_activity_control (module-local autouse)."""
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )


def _empty_kw_search_pause_armed(
    *,
    wb: RecordingWbLifecycleModifier,
    stored_search: object | None,
) -> bool:
    """True only when this-run WB Search pause (``pause_auction_campaign``) fired.

    Durable Search-lane PAUSE+EMPTY_KEYWORDS alone must not count as armed
    (ROOT-001 false-green). ``stored_search`` is retained for call-site
    diagnostics / assert messages; it is not an OR success path.
    """
    _ = stored_search  # call-site diagnostic only; not a success predicate
    return "pause_auction_campaign" in wb.methods_called()


@pytest.mark.unit
def test_empty_kw_search_pause_armed_rejects_durable_reason_without_this_run_wb_call() -> None:
    """False-green guard: pre-existing EMPTY_KEYWORDS PAUSE ≠ this-run arm.

    Old helper returned True when stored Search reason was PAUSE+EMPTY_KEYWORDS
    even with zero ``pause_auction_campaign`` calls — Search could stay STARTED
    on WB while ROOT-001 suite greened.
    """
    wb = RecordingWbLifecycleModifier()
    stored_search = SimpleNamespace(
        command=CampaignActivityCommand.PAUSE,
        reason_code=AuctionReasonCode.EMPTY_KEYWORDS,
    )
    assert _empty_kw_search_pause_armed(wb=wb, stored_search=stored_search) is False, (
        "ROOT-001 false-green: durable Search EMPTY_KEYWORDS PAUSE must not count "
        "as this-run pause arm without pause_auction_campaign"
    )
    assert "pause_auction_campaign" not in wb.methods_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_keywords_intent_and_search_pause_armed_when_search_started(
    fake_redis: FakeRedis,
) -> None:
    """ROOT-001: empty + Search STARTED → tick1 latch, tick2 this-run Search pause.

    GIVEN paid Auto+Search комплект (Puna-like IDs), bot on, Auto=pause,
    Search=STARTED, active keywords empty, **no** prior Redis empty-keywords intent
    WHEN ``ensure_campaigns_active`` runs twice while still empty
    THEN tick1 latches intent without pause; tick2 fires pause_search_allowed
    (not Redis intent alone; not durable EMPTY_KEYWORDS reason alone).
    """
    adv = _FakeComplexAdv(
        auto_status="pause",
        search_status="started",
        auto_adv_id=_PUNA_AUTO_ADV_ID,
        search_adv_id=_PUNA_SEARCH_ADV_ID,
        active_keywords=[],
    )
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    wb = RecordingWbLifecycleModifier()
    notify_mock = AsyncMock()
    intent_mgr = EmptyKeywordsPauseIntentManager()

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        assert await intent_mgr.peek_intent(_PUNA_AUTO_ADV_ID) is False, (
            "precondition: no prior intent (reproduce Puna miss)"
        )

        # Tick1: latch only.
        async with _ensure_active(
            adv=adv,
            wb=wb,
            reason_manager=reason_manager,
            notify=notify_mock,
        ) as service:
            await service.ensure_campaigns_active([adv])

        assert "pause_auction_campaign" not in wb.methods_called(), (
            "TWO_TICK: tick1 MUST NOT pause Search "
            f"methods={wb.methods_called()}"
        )
        assert await intent_mgr.peek_intent(_PUNA_AUTO_ADV_ID) is True, (
            "TWO_TICK: tick1 MUST latch confirmation intent"
        )

        # Tick2: still empty → this-run WB Search pause.
        wb.calls.clear()
        async with _ensure_active(
            adv=adv,
            wb=wb,
            reason_manager=reason_manager,
            notify=notify_mock,
        ) as service:
            await service.ensure_campaigns_active([adv])

        stored_search = await reason_manager.get(_PUNA_SEARCH_ADV_ID, "search")
        pause_path_armed = _empty_kw_search_pause_armed(
            wb=wb, stored_search=stored_search
        )

        wb.assert_matches_case(
            _contract("pause_search_allowed"),
            complex_adv=adv,
            must_have_been_called=True,
        )
        assert pause_path_armed, (
            "ROOT-001: tick2 empty + Search STARTED did not arm this-run "
            "Search pause "
            f"(auto={_PUNA_AUTO_ADV_ID}, search={_PUNA_SEARCH_ADV_ID}, "
            f"methods={wb.methods_called()}, search_reason={stored_search})"
        )

        assert stored_search is not None
        assert is_empty_keywords_reason(stored_search.reason_code)
        assert (
            stored_search.reason_code.value
            == AuctionReasonCode.EMPTY_KEYWORDS.value
        )

        wb.assert_matches_case(
            _contract("pause_auto_forbidden"),
            complex_adv=adv,
            must_have_been_called=False,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_keywords_no_silent_skip_when_auto_started_search_started(
    fake_redis: FakeRedis,
) -> None:
    """Paired: Auto STARTED — tick1 latch, tick2 pause_search_allowed."""
    adv = _FakeComplexAdv(
        auto_status="started",
        search_status="started",
        auto_adv_id=_PUNA_AUTO_ADV_ID,
        search_adv_id=_PUNA_SEARCH_ADV_ID,
        active_keywords=[],
    )
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    wb = RecordingWbLifecycleModifier()
    intent_mgr = EmptyKeywordsPauseIntentManager()

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        assert "pause_auction_campaign" not in wb.methods_called()
        assert await intent_mgr.peek_intent(_PUNA_AUTO_ADV_ID) is True

        wb.calls.clear()
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        stored_search = await reason_manager.get(_PUNA_SEARCH_ADV_ID, "search")
        pause_path_armed = _empty_kw_search_pause_armed(
            wb=wb, stored_search=stored_search
        )
        wb.assert_matches_case(
            _contract("pause_search_allowed"),
            complex_adv=adv,
            must_have_been_called=True,
        )
        assert pause_path_armed, (
            "ROOT-001 (Auto STARTED): tick2 Search EMPTY_KEYWORDS pause missing "
            f"methods={wb.methods_called()} search_reason={stored_search}"
        )
        assert "pause_auto_campaign" not in wb.methods_called()

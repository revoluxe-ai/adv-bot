"""HUNT-001: resume notify when Search already STARTED + keywords recover.

SAME_INVARIANT sibling of ROOT-001 (resume after delivered pause notify).

Gap: ``_maybe_notify_empty_keywords_resume_after_search_start`` is wired only on
Search PAUSE/READY_FOR_START → start. After a delivered pause-notify episode,
recheck can start Search while keywords are still empty (resume gate skips).
When keywords later become active while ``search_status==STARTED``, both STARTED
branches only ``_set_search_reason`` and never emit resume notify.

These tests MUST fail on unrepaired production (RED for HUNT-001).
Do not edit ``app/**`` from this suite.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
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
    _ensure_active,
)
from tests.unit.auto_updater_v3.empty_keywords_pause.wb_search_lifecycle_contract import (
    RecordingWbLifecycleModifier,
)

TEST_ID_SEARCH_LIMIT = (
    "tests/unit/auto_updater_v3/empty_keywords_pause/"
    "test_notify_resume_when_search_already_started.py::"
    "test_resume_notify_when_search_started_and_keywords_recover_search_limit"
)
TEST_ID_COMMON = (
    "tests/unit/auto_updater_v3/empty_keywords_pause/"
    "test_notify_resume_when_search_already_started.py::"
    "test_resume_notify_when_search_started_and_keywords_recover_common_budget"
)

_RESUME_NOTIFY_PATH = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3"
    ".empty_keywords_pause.notify_empty_keywords_resume"
)

_AUTO_ADV_ID = 9001
_SEARCH_ADV_ID = 9002
_SHOP_ID = "shop-empty-kw"


@pytest.fixture(autouse=True)
def _positive_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same balance seam as activity-control suite."""
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )


async def _seed_delivered_pause_episode(fake_redis: FakeRedis, adv_id: int) -> None:
    """Mark delivered empty-keywords pause notify (was_notified=True)."""
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        first = await EmptyKeywordsPauseIntentManager().mark_notified(adv_id)
        assert first is True
        assert await EmptyKeywordsPauseIntentManager().was_notified(adv_id) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resume_notify_when_search_started_and_keywords_recover_search_limit(
    fake_redis: FakeRedis,
) -> None:
    """Search-limit STARTED + keyword recovery MUST call resume notify.

    Given: delivered pause-notify episode; Search already STARTED; active
    keywords recovered; no empty-keywords pause intent.
    When: ``ensure_campaigns_active`` hits the search-limit STARTED branch.
    Then: ``notify_empty_keywords_resume`` MUST be invoked (HUNT-001 gap today).
    """
    await _seed_delivered_pause_episode(fake_redis, _AUTO_ADV_ID)
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    # Durable Search reason already STARTED (post-recheck); keywords recover now.
    await reason_manager.set(
        _SEARCH_ADV_ID,
        "search",
        CampaignActivityReason(
            command=CampaignActivityCommand.STARTED,
            reason_code=AuctionReasonCode.SEARCH_LIMIT_OK,
        ),
    )
    adv = _FakeComplexAdv(
        auto_status="started",
        search_status="started",
        auto_adv_id=_AUTO_ADV_ID,
        search_adv_id=_SEARCH_ADV_ID,
        search_limit=100,
        active_keywords=[_active_keyword()],
    )
    assert adv.search_adv_active_status_str == WBAdvActiveStatus.STARTED
    wb = RecordingWbLifecycleModifier()
    resume_mock = AsyncMock()

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(_RESUME_NOTIFY_PATH, new=resume_mock),
    ):
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

    assert resume_mock.await_count >= 1, (
        f"{TEST_ID_SEARCH_LIMIT}: after delivered pause notify, Search already "
        f"STARTED + active keyword recovery MUST call notify_empty_keywords_resume "
        f"(search-limit STARTED branch); got await_count={resume_mock.await_count}. "
        f"HUNT-001: resume helper is only wired on PAUSE/READY→start today."
    )
    kwargs = resume_mock.await_args.kwargs
    assert kwargs.get("adv_id") == _AUTO_ADV_ID
    assert kwargs.get("shop_id") == _SHOP_ID
    assert "pause_auction_campaign" not in wb.methods_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resume_notify_when_search_started_and_keywords_recover_common_budget(
    fake_redis: FakeRedis,
) -> None:
    """Common-budget STARTED + keyword recovery MUST call resume notify.

    Same invariant as search-limit; covers the common-budget STARTED branch
    that only ``_set_search_reason`` today (no resume helper).
    """
    await _seed_delivered_pause_episode(fake_redis, _AUTO_ADV_ID)
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    adv = _FakeComplexAdv(
        auto_status="started",
        search_status="started",
        auto_adv_id=_AUTO_ADV_ID,
        search_adv_id=_SEARCH_ADV_ID,
        search_limit=100,
        active_keywords=[_active_keyword()],
    )
    adv._use_common_budget = True
    adv._common_budget_daily_limit = 500
    wb = RecordingWbLifecycleModifier()
    resume_mock = AsyncMock()

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(_RESUME_NOTIFY_PATH, new=resume_mock),
    ):
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

    assert resume_mock.await_count >= 1, (
        f"{TEST_ID_COMMON}: after delivered pause notify, Search already "
        f"STARTED + active keyword recovery MUST call notify_empty_keywords_resume "
        f"(common-budget STARTED branch); got await_count={resume_mock.await_count}. "
        f"HUNT-001: resume helper is only wired on PAUSE/READY→start today."
    )
    kwargs = resume_mock.await_args.kwargs
    assert kwargs.get("adv_id") == _AUTO_ADV_ID
    assert kwargs.get("shop_id") == _SHOP_ID
    assert "pause_auction_campaign" not in wb.methods_called()

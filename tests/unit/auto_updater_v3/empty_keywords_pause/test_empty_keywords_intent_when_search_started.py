"""ROOT-001: empty keywords + Search STARTED must arm empty-keywords pause.

Regression for BUGCASE-EMPTY-KW-NO-PAUSE-PUNA — prod miss when Auto is paused,
Search remains STARTED, active keywords empty, and no empty-keywords
intent/pause is written (silent skip). Distinct from stale-intent
revalidation and notify-debounce suites.
"""

from __future__ import annotations

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
    """True if Search pause path was executed with EMPTY_KEYWORDS reason/adapter."""
    search_paused = "pause_auction_campaign" in wb.methods_called()
    if stored_search is None:
        return search_paused
    return search_paused or (
        stored_search.command == CampaignActivityCommand.PAUSE  # type: ignore[attr-defined]
        and is_empty_keywords_reason(stored_search.reason_code)  # type: ignore[attr-defined]
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_keywords_intent_and_search_pause_armed_when_search_started(
    fake_redis: FakeRedis,
) -> None:
    """ROOT-001 RED: empty active keywords + Search STARTED → intent + Search pause arm.

    GIVEN paid Auto+Search комплект (Puna-like IDs), bot on, Auto=pause,
    Search=STARTED, active keywords empty, **no** prior Redis empty-keywords intent
    WHEN AutoAdvActiveControlService.ensure_campaigns_active runs
    THEN empty-keywords intent MUST be written and/or Search pause path MUST be
    armed with EMPTY_KEYWORDS (not silent skip; not Auto pause).

    Intent may be consumed in-tick if pause already applied — either signal
    proves the detect→arm path ran (ADL: intent then Search pause).
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

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        assert (
            await EmptyKeywordsPauseIntentManager().peek_intent(_PUNA_AUTO_ADV_ID)
            is False
        ), "precondition: no prior intent (reproduce Puna miss)"

        async with _ensure_active(
            adv=adv,
            wb=wb,
            reason_manager=reason_manager,
            notify=notify_mock,
        ) as service:
            await service.ensure_campaigns_active([adv])

        intent_after = await EmptyKeywordsPauseIntentManager().peek_intent(
            _PUNA_AUTO_ADV_ID
        )
        stored_search = await reason_manager.get(_PUNA_SEARCH_ADV_ID, "search")
        pause_path_armed = _empty_kw_search_pause_armed(
            wb=wb, stored_search=stored_search
        )

        # Contract: must not silently skip while Search STARTED and keywords empty.
        assert intent_after or pause_path_armed, (
            "ROOT-001 silent skip: empty keywords + Search STARTED left no "
            "empty-keywords intent and did not arm Search pause "
            f"(auto={_PUNA_AUTO_ADV_ID}, search={_PUNA_SEARCH_ADV_ID}, "
            f"methods={wb.methods_called()}, search_reason={stored_search})"
        )

        if pause_path_armed and stored_search is not None:
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
    """Paired RED: same miss with Auto STARTED (no prior intent)."""
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

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        intent_after = await EmptyKeywordsPauseIntentManager().peek_intent(
            _PUNA_AUTO_ADV_ID
        )
        stored_search = await reason_manager.get(_PUNA_SEARCH_ADV_ID, "search")
        pause_path_armed = _empty_kw_search_pause_armed(
            wb=wb, stored_search=stored_search
        )
        assert intent_after or pause_path_armed, (
            "ROOT-001 silent skip (Auto STARTED): no intent / Search EMPTY_KEYWORDS pause"
        )
        assert "pause_auto_campaign" not in wb.methods_called()

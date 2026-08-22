"""ROOT-001: Redis ``__empty__`` warmup must NOT arm empty-keywords Search pause.

SPEC_GAP / tasks §7.3 / scenario «Warmup __empty__ marker does not arm Search pause».

GIVEN Search STARTED, Redis keywords hash is warmup marker ``__empty__``
(``get_keywords`` → ``[]`` each tick), no prior V3 intent, no bot-driven OFF
WHEN activity-control evaluates no-prior-intent empty-keywords arm
THEN MUST NOT set intent and MUST NOT call ``pause_auction_campaign`` /
MUST NOT write Search-lane EMPTY_KEYWORDS.

Paired: bot-driven settled empty (prior V3 intent) still pauses Search.
No prod Redis; no ``app/**`` edits (RED-only).
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
    RedisCampaignActivityReasonManager,
)
from tests.unit.auto_updater_v3.empty_keywords_pause.test_activity_control import (
    _SERVICE_MODULE,
    _FakeComplexAdv,
    _ensure_active,
)
from tests.unit.auto_updater_v3.empty_keywords_pause.wb_search_lifecycle_contract import (
    RecordingWbLifecycleModifier,
)

# Field name matches RedisCalculatedKeywordsCacheManager empty-hash marker.
_REDIS_EMPTY_MARKER_FIELD = "__empty__"

_AUTO_ADV_ID = 91001
_SEARCH_ADV_ID = 91002


class _WarmupEmptyMarkerComplexAdv(_FakeComplexAdv):
    """ComplexAdv seam: Redis ``__empty__`` → ``[]`` every read (no instance cache).

    Mirrors production ``ComplexAdv.get_keywords`` when the calculated-keywords
    hash holds only the warmup marker: empty list, re-fetched each tick while
    snapshot warmup may still populate keywords.
    """

    def __init__(
        self,
        *,
        auto_status: str,
        search_status: str | None = "started",
        auto_adv_id: int = _AUTO_ADV_ID,
        search_adv_id: int | None = _SEARCH_ADV_ID,
    ) -> None:
        """Init with empty active set; mark source as Redis warmup false-empty."""
        super().__init__(
            auto_status=auto_status,
            search_status=search_status,
            auto_adv_id=auto_adv_id,
            search_adv_id=search_adv_id,
            active_keywords=[],
        )
        self.redis_keywords_empty_marker = True
        self.keywords_source = "redis_warmup_empty_marker"

    async def get_keywords(self, *, cache_only: bool = True) -> list[object]:
        """Return [] each call — warmup ``__empty__`` is not instance-cached."""
        _ = cache_only
        assert self.redis_keywords_empty_marker is True
        return []


@pytest.fixture(autouse=True)
def _positive_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same balance seam as activity-control suite."""
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )


async def _seed_redis_warmup_empty_marker(fake_redis: FakeRedis, adv_id: int) -> None:
    """Write ``calculated_keywords:{adv_id}`` hash with only ``__empty__``=1."""
    key = f"calculated_keywords:{adv_id}"
    _ = await fake_redis.delete(key)
    _ = await fake_redis.hset(key, _REDIS_EMPTY_MARKER_FIELD, "1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_warmup_empty_marker_must_not_arm_or_pause_search_when_started(
    fake_redis: FakeRedis,
) -> None:
    """RED: ``__empty__`` + Search STARTED + no prior intent → no pause / no arm.

    Current product no-prior-intent reconcile treats ``active_count==0`` as
    settled empty and calls ``pause_auction_campaign`` — this assertion must fail
    until settled-empty vs warmup guard lands (tasks §7.2).
    """
    await _seed_redis_warmup_empty_marker(fake_redis, _AUTO_ADV_ID)
    marker = await fake_redis.hget(
        f"calculated_keywords:{_AUTO_ADV_ID}", _REDIS_EMPTY_MARKER_FIELD
    )
    assert marker in (b"1", "1"), "precondition: Redis warmup __empty__ marker present"

    adv = _WarmupEmptyMarkerComplexAdv(
        auto_status="started",
        search_status="started",
        auto_adv_id=_AUTO_ADV_ID,
        search_adv_id=_SEARCH_ADV_ID,
    )
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    wb = RecordingWbLifecycleModifier()
    notify_mock = AsyncMock()

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        intent_mgr = EmptyKeywordsPauseIntentManager()
        assert await intent_mgr.peek_intent(_AUTO_ADV_ID) is False, (
            "precondition: no prior V3 empty-keywords intent"
        )

        async with _ensure_active(
            adv=adv,
            wb=wb,
            reason_manager=reason_manager,
            notify=notify_mock,
        ) as service:
            await service.ensure_campaigns_active([adv])

        intent_after = await intent_mgr.peek_intent(_AUTO_ADV_ID)
        stored_search = await reason_manager.get(_SEARCH_ADV_ID, "search")
        methods = wb.methods_called()

        assert "pause_auction_campaign" not in methods, (
            "ROOT-001 warmup false-empty: MUST NOT call pause_auction_campaign "
            f"while Redis __empty__ + Search STARTED + no prior intent "
            f"(methods={methods}, intent_after={intent_after}, "
            f"search_reason={stored_search})"
        )
        assert intent_after is False, (
            "ROOT-001 warmup false-empty: MUST NOT arm empty-keywords intent "
            f"(intent_after={intent_after}, methods={methods})"
        )
        if stored_search is not None:
            assert not is_empty_keywords_reason(stored_search.reason_code), (
                "ROOT-001 warmup false-empty: MUST NOT set Search-lane "
                f"EMPTY_KEYWORDS (search_reason={stored_search})"
            )
        notify_mock.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_warmup_empty_marker_must_not_pause_when_auto_paused_search_started(
    fake_redis: FakeRedis,
) -> None:
    """Paired RED: same forbid with Auto=pause, Search=STARTED (reconcile window)."""
    await _seed_redis_warmup_empty_marker(fake_redis, _AUTO_ADV_ID)
    adv = _WarmupEmptyMarkerComplexAdv(
        auto_status="pause",
        search_status="started",
        auto_adv_id=_AUTO_ADV_ID,
        search_adv_id=_SEARCH_ADV_ID,
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
            _AUTO_ADV_ID
        )
        methods = wb.methods_called()
        assert "pause_auction_campaign" not in methods, (
            "ROOT-001 (Auto pause): warmup __empty__ MUST NOT pause Search "
            f"methods={methods} intent_after={intent_after}"
        )
        assert intent_after is False, (
            "ROOT-001 (Auto pause): warmup __empty__ MUST NOT arm intent "
            f"intent_after={intent_after}"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_paired_prior_intent_settled_empty_still_pauses_search(
    fake_redis: FakeRedis,
) -> None:
    """Paired allowed: prior V3 intent (settled empty) still pauses Search.

    Control that the RED forbid targets warmup false-empty only — not the
    bot-driven settled-empty path that already has Redis intent.
    """
    adv = _FakeComplexAdv(
        auto_status="started",
        search_status="started",
        auto_adv_id=_AUTO_ADV_ID,
        search_adv_id=_SEARCH_ADV_ID,
        active_keywords=[],
    )
    reason_manager = RedisCampaignActivityReasonManager(
        redis_client=RedisClient(redis_client=fake_redis)
    )
    wb = RecordingWbLifecycleModifier()

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        await EmptyKeywordsPauseIntentManager().set_intent(_AUTO_ADV_ID)
        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        assert "pause_auction_campaign" in wb.methods_called(), (
            "paired settled-empty: prior intent MUST still pause Search "
            f"methods={wb.methods_called()}"
        )
        stored_search = await reason_manager.get(_SEARCH_ADV_ID, "search")
        assert stored_search is not None
        assert is_empty_keywords_reason(stored_search.reason_code)
        assert "pause_auto_campaign" not in wb.methods_called()

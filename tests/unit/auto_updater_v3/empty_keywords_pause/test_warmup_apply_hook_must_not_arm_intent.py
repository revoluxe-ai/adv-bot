"""HC-WARMUP-APPLY-HOOK-ARM: V3 apply_hook MUST NOT arm on Redis ``__empty__``.

SAME_INVARIANT as ROOT-001 (``INV/warmup-empty-marker-no-prior-search-pause``).

GIVEN Redis ``calculated_keywords:{adv}`` holds only warmup marker ``__empty__``,
ledger/keywords active_count==0, Search STARTED, bot_active, no FORCE_OFF
(no settled-empty confirmation)
WHEN ``maybe_set_empty_keywords_pause_intent`` runs (V3 post-apply producer)
THEN MUST NOT write empty-keywords intent.

Chain: if intent were armed, activity-control consume (has_intent) would
``pause_auction_campaign`` and bypass the ROOT-001 no-prior warmup gate —
that false-pause is also forbidden.

Paired allowed: bot-driven FORCE_OFF + empty set still arms (settled empty),
even when Redis hash later holds ``__empty__`` from settled flush.

No ``app/**`` edits (RED-only). No prod Redis.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.apply_hook import (
    maybe_set_empty_keywords_pause_intent,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.decision import (
    is_empty_keywords_reason,
    is_warmup_false_empty_keywords,
    redis_has_calculated_keywords_empty_marker,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
    RedisCampaignActivityReasonManager,
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

_REDIS_EMPTY_MARKER_FIELD = "__empty__"
_AUTO_ADV_ID = 92011
_SEARCH_ADV_ID = 92012


def _kw(mode: KeywordStrategyMode) -> MagicMock:
    """Minimal CalculatedKeyword-shaped stub for strategy_mode counting."""
    kw = MagicMock()
    kw.strategy_mode = mode
    return kw


async def _seed_redis_warmup_empty_marker(fake_redis: FakeRedis, adv_id: int) -> None:
    """Write ``calculated_keywords:{adv_id}`` hash with only ``__empty__``=1."""
    key = f"calculated_keywords:{adv_id}"
    _ = await fake_redis.delete(key)
    _ = await fake_redis.hset(key, _REDIS_EMPTY_MARKER_FIELD, "1")


@pytest.fixture(autouse=True)
def _positive_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same balance seam as activity-control suite (consume-chain test)."""
    monkeypatch.setattr(
        f"{_SERVICE_MODULE}.balance_manager.get_cabinet_balance_and_bonuses",
        AsyncMock(return_value=(1000.0, 0.0)),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_hook_must_not_arm_intent_on_redis_empty_warmup_when_search_started(
    fake_redis: FakeRedis,
) -> None:
    """RED: apply_hook + ``__empty__`` + Search STARTED + no FORCE_OFF → no intent.

    Production seam: ``ApplyManager`` passes ``ledger.keywords`` (can be ``[]``
    while Redis hash holds only warmup ``__empty__``) and Search status into
    ``maybe_set_empty_keywords_pause_intent`` without ``is_warmup_false_empty``.
    Predicate then arms on ``campaign_is_started`` + ``active_count==0``.
    """
    await _seed_redis_warmup_empty_marker(fake_redis, _AUTO_ADV_ID)
    assert await redis_has_calculated_keywords_empty_marker(
        fake_redis, _AUTO_ADV_ID
    ), "precondition: Redis warmup __empty__ marker present"
    assert await is_warmup_false_empty_keywords(
        adv=object(),
        redis_client=fake_redis,
        adv_id=_AUTO_ADV_ID,
    ), "precondition: warmup false-empty detector True on Redis marker"

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        intent_mgr = EmptyKeywordsPauseIntentManager()
        assert await intent_mgr.peek_intent(_AUTO_ADV_ID) is False, (
            "precondition: no prior V3 empty-keywords intent"
        )

        set_ok = await maybe_set_empty_keywords_pause_intent(
            adv_id=_AUTO_ADV_ID,
            bot_active=True,
            keywords=[],
            post_gate_actions=[],
            campaign_status=WBAdvActiveStatus.STARTED,
        )

        intent_after = await intent_mgr.peek_intent(_AUTO_ADV_ID)
        assert set_ok is False, (
            "HC-WARMUP-APPLY-HOOK-ARM: apply_hook MUST NOT arm intent on "
            f"Redis __empty__ + Search STARTED + no FORCE_OFF (set_ok={set_ok}, "
            f"intent_after={intent_after})"
        )
        assert intent_after is False, (
            "HC-WARMUP-APPLY-HOOK-ARM: Redis empty-keywords intent MUST stay unset "
            f"(intent_after={intent_after})"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_hook_warmup_arm_must_not_false_pause_search_via_consume(
    fake_redis: FakeRedis,
) -> None:
    """RED chain: apply_hook warmup arm → consume MUST NOT pause Search.

    Documents SAME_INVARIANT bypass: prior-intent consume trusts Redis intent
    and skips ROOT-001 no-prior warmup gate; therefore apply_hook must not arm
    on warmup false-empty in the first place.
    """
    await _seed_redis_warmup_empty_marker(fake_redis, _AUTO_ADV_ID)

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
        # Current bug: apply_hook arms without warmup gate; consume then pauses.
        set_ok = await maybe_set_empty_keywords_pause_intent(
            adv_id=_AUTO_ADV_ID,
            bot_active=True,
            keywords=[],
            post_gate_actions=None,
            campaign_status=WBAdvActiveStatus.STARTED,
        )

        async with _ensure_active(
            adv=adv, wb=wb, reason_manager=reason_manager
        ) as service:
            await service.ensure_campaigns_active([adv])

        methods = wb.methods_called()
        intent_after = await EmptyKeywordsPauseIntentManager().peek_intent(
            _AUTO_ADV_ID
        )
        stored_search = await reason_manager.get(_SEARCH_ADV_ID, "search")
        assert "pause_auction_campaign" not in methods, (
            "HC-WARMUP-APPLY-HOOK-ARM: consume MUST NOT false-pause Search after "
            f"warmup apply_hook path (set_ok={set_ok}, methods={methods}, "
            f"intent_after={intent_after}, search_reason={stored_search})"
        )
        assert set_ok is False and intent_after is False, (
            "HC-WARMUP-APPLY-HOOK-ARM: apply_hook must refuse warmup arm "
            f"(set_ok={set_ok}, intent_after={intent_after})"
        )
        if stored_search is not None:
            assert not is_empty_keywords_reason(stored_search.reason_code), (
                "HC-WARMUP-APPLY-HOOK-ARM: MUST NOT write Search-lane EMPTY_KEYWORDS "
                f"(search_reason={stored_search})"
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_paired_apply_hook_force_off_still_arms_with_empty_marker(
    fake_redis: FakeRedis,
) -> None:
    """Paired allowed: bot-driven FORCE_OFF settled empty still arms intent.

    Warmup forbid must not weaken settled-empty producer after last FORCE_OFF
    (``__empty__`` may also be written by settled flush).
    """
    await _seed_redis_warmup_empty_marker(fake_redis, _AUTO_ADV_ID)

    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        set_ok = await maybe_set_empty_keywords_pause_intent(
            adv_id=_AUTO_ADV_ID,
            bot_active=True,
            keywords=[_kw(KeywordStrategyMode.OFF)],
            post_gate_actions=[
                V3Action(
                    action=V3ActionType.FORCE_OFF,
                    keyword_setting_id=1,
                    reason="last",
                )
            ],
            campaign_status=WBAdvActiveStatus.STARTED,
        )
        assert set_ok is True, (
            "paired settled-empty: FORCE_OFF + empty set MUST still arm intent "
            f"(set_ok={set_ok})"
        )
        assert await EmptyKeywordsPauseIntentManager().peek_intent(_AUTO_ADV_ID) is True

"""FINDING-PBH-003 RED: AutoReset freeze is ACTIVE-only (post-confirm gap).

После ``confirm_auto_bid`` режим остаётся ``PENDING_SETUP``, а фаза уходит в
``PENDING_INTENT`` / ``WB_SYNC`` (ещё до ``activate_after_successful_sync`` →
``ACTIVE``). Ordinary Auto CPM mutators (``AutoResetBidService.ensure_auto_bids_minimum``)
должны быть заморожены с момента Auto-bid-confirm до ACTIVE, а не только при
``ACTIVE`` (ADL confirmed-epoch-parameters-sot §6–§7).

Текущий ``should_freeze_auto_bid_mutations`` keyed только на ``mode == ACTIVE``,
поэтому post-confirm pre-ACTIVE окно остаётся ungated: AutoReset MAY всё ещё
вызывать ``update_auto_adv_cpm``, race с ``sync_intent_to_wb``.

До фикса эти assertions обязаны падать. После фикса — freeze покрывает
post-confirm pre-ACTIVE (phase и/или confirmed-bid), и AutoReset исключает
таких кандидатов.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.services.auto_reset_bid_service import (
    AutoResetBidService,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.auto_bid_freeze import (
    should_freeze_auto_bid_mutations,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
    normalize_card_ab_hold_mode,
    normalize_card_ab_hold_phase,
)

# Post-confirm / pre-ACTIVE epoch phases (mode still PENDING_SETUP).
_POST_CONFIRM_PRE_ACTIVE_PHASES: tuple[CardAbHoldPhase, ...] = (
    CardAbHoldPhase.PENDING_INTENT,
    CardAbHoldPhase.WB_SYNC,
    CardAbHoldPhase.READY_ACTIVE,
)


def _desired_freeze_post_confirm(
    mode: CardAbHoldMode | str | None,
    phase: CardAbHoldPhase | str | None = None,
) -> bool:
    """Желаемый контракт FINDING-PBH-003: freeze от Auto-bid-confirm до ACTIVE.

    Args:
        mode: durable ``card_ab_hold_mode``.
        phase: durable ``card_ab_hold_phase`` (post-confirm markers).

    Returns:
        True, если ordinary Auto bid mutators MUST NOT выполняться.
    """
    normalized_mode = normalize_card_ab_hold_mode(mode)
    if normalized_mode == CardAbHoldMode.ACTIVE:
        return True
    if normalized_mode != CardAbHoldMode.PENDING_SETUP:
        return False
    normalized_phase = normalize_card_ab_hold_phase(phase)
    return normalized_phase in _POST_CONFIRM_PRE_ACTIVE_PHASES


async def _run_handlers_inline(
    handlers: Sequence[Callable[[], Awaitable[Any]]],
    **_: Any,
) -> list[Any]:
    """Синхронный run_tasks stub для unit-изоляции AutoReset."""
    return [await handler() for handler in handlers]


def _make_adv(
    *,
    auto_adv_id: int,
    cpm: int = 900,
    card_ab_hold_mode: str = "off",
    card_ab_hold_phase: str | None = None,
) -> MagicMock:
    """Minimal ComplexAdv-like object for AutoReset candidate filter."""
    adv = MagicMock()
    adv.bot_active = True
    adv.bidder_for_auto = True
    adv.nmids = [10]
    adv.auto_adv_id = auto_adv_id
    adv.adv_setting.cpm = cpm
    adv.shop_id = f"shop-{auto_adv_id}"
    adv.card_ab_hold_mode = card_ab_hold_mode
    adv.card_ab_hold_phase = card_ab_hold_phase
    return adv


@pytest.mark.unit
@pytest.mark.parametrize("phase", list(_POST_CONFIRM_PRE_ACTIVE_PHASES))
def test_should_freeze_covers_post_confirm_pre_active_phases(
    phase: CardAbHoldPhase,
) -> None:
    """FINDING-PBH-003: freeze MUST cover PENDING_SETUP + post-confirm phase.

    Production ``should_freeze_auto_bid_mutations`` ignores phase and returns
    False for ``PENDING_SETUP`` → ACTIVE-only gap (RED until fixed).
    """
    mode = CardAbHoldMode.PENDING_SETUP
    desired = _desired_freeze_post_confirm(mode, phase)
    assert desired is True

    actual = should_freeze_auto_bid_mutations(mode)
    assert actual is desired, (
        f"FINDING-PBH-003: should_freeze_auto_bid_mutations({mode!r}) must "
        f"freeze post-confirm pre-ACTIVE (phase={phase.value}); got {actual!r}. "
        "Ordinary AutoReset may still rewrite Auto CPM before activate "
        "(race with sync_intent_to_wb→update_auto_adv_cpm)."
    )


@pytest.mark.unit
def test_should_freeze_still_active_for_active_mode() -> None:
    """ACTIVE остаётся hard freeze (контракт не ослабляем)."""
    assert should_freeze_auto_bid_mutations(CardAbHoldMode.ACTIVE) is True
    assert _desired_freeze_post_confirm(CardAbHoldMode.ACTIVE, None) is True


@pytest.mark.unit
def test_desired_freeze_allows_pre_confirm_pending_setup() -> None:
    """До Auto-bid-confirm (ранние PENDING phases) AutoReset MAY работать."""
    assert (
        _desired_freeze_post_confirm(
            CardAbHoldMode.PENDING_SETUP,
            CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM,
        )
        is False
    )
    assert (
        _desired_freeze_post_confirm(
            CardAbHoldMode.PENDING_SETUP,
            CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM,
        )
        is False
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "phase",
    ["pending_intent", "wb_sync", "ready_active"],
)
async def test_ensure_auto_bids_minimum_skips_post_confirm_pending_setup(
    phase: str,
) -> None:
    """FINDING-PBH-003: AutoReset MUST NOT rewrite CPM post-confirm pre-ACTIVE.

    Candidate filter сегодня смотрит только ``should_freeze_auto_bid_mutations``
    (ACTIVE-only), поэтому ``pending_setup`` + post-confirm phase всё ещё
    попадает в candidates и может вызвать ``update_auto_adv_cpm``.
    """
    hub = MagicMock()
    hub.wb_manager = MagicMock()
    hub.wb_modifier = MagicMock()
    hub.wb_modifier.update_auto_adv_cpm = AsyncMock()

    post_confirm = _make_adv(
        auto_adv_id=701,
        card_ab_hold_mode="pending_setup",
        card_ab_hold_phase=phase,
    )
    off_adv = _make_adv(auto_adv_id=702, card_ab_hold_mode="off")

    hub.wb_manager.get_min_bids_cache_only = AsyncMock(
        return_value=AdvMinNmidsBids(auto={10: 150}, search={})
    )

    service = AutoResetBidService(hub, MagicMock())

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_reset_bid_service.run_tasks",
        new=_run_handlers_inline,
    ):
        await service.ensure_auto_bids_minimum([post_confirm, off_adv])

    get_min_call = hub.wb_manager.get_min_bids_cache_only.await_args
    candidate_ids = [adv.auto_adv_id for adv in get_min_call.args[0]]
    assert 701 not in candidate_ids, (
        f"FINDING-PBH-003: post-confirm PENDING_SETUP (phase={phase}) must be "
        f"excluded from AutoReset candidates; got {candidate_ids!r}. "
        "ACTIVE-only freeze leaves confirmed Auto bid mutable until activate."
    )
    assert candidate_ids == [702]

    hub.wb_modifier.update_auto_adv_cpm.assert_awaited_once()
    assert hub.wb_modifier.update_auto_adv_cpm.await_args.args[0] == 702

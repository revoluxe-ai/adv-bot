"""A/B Hold: freeze автоматических и ручных мутаций ставки авто-РК (spec §21).

Decision ``ab-hold-confirmed-epoch-parameters-sot`` / tasks §21 / FINDING-PBH-003:
- ordinary Auto bid mutators (AutoReset и т.п.) заморожены с Auto-bid-confirm
  через ``PENDING_INTENT`` / ``WB_SYNC`` / ``READY_ACTIVE`` до и включая ``ACTIVE``;
- до Auto-bid-confirm (``PENDING_SETUP`` + awaiting_*/warm_up) и при ``OFF``
  AutoReset MAY работать (writer inventory);
- ручной Telegram ``change_auto_bid`` заблокирован в ``PENDING_SETUP`` и ``ACTIVE``
  (семейство structural freeze) с пояснением пользователю.
"""

from __future__ import annotations

from typing import Any

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
    is_ab_hold_structural_freeze,
    normalize_card_ab_hold_mode,
    normalize_card_ab_hold_phase,
)

AB_HOLD_MANUAL_AUTO_BID_BLOCKED_MSG = (
    "Ставка в автокампании не изменена: при A/B Hold параметры авто-РК "
    "заморожены. Чтобы изменить ставку вручную, отключите A/B Hold "
    "на экране режима."
)

# Post-confirm / pre-ACTIVE epoch phases (mode still PENDING_SETUP).
_POST_CONFIRM_PRE_ACTIVE_PHASES: frozenset[CardAbHoldPhase] = frozenset(
    {
        CardAbHoldPhase.PENDING_INTENT,
        CardAbHoldPhase.WB_SYNC,
        CardAbHoldPhase.READY_ACTIVE,
    }
)

# Sentinel: phase argument omitted (vs explicit None = legacy MVP-1).
_PHASE_OMITTED: Any = object()


def should_freeze_auto_bid_mutations(
    mode: CardAbHoldMode | str | None,
    phase: CardAbHoldPhase | str | None = _PHASE_OMITTED,
) -> bool:
    """True, когда ordinary Auto bid mutators MUST NOT выполняться.

    Freeze покрывает:
    - ``ACTIVE`` (всегда);
    - ``PENDING_SETUP`` + post-confirm phase (``PENDING_INTENT`` / ``WB_SYNC`` /
      ``READY_ACTIVE``) — FINDING-PBH-003: окно после ``confirm_auto_bid`` до
      ``activate_after_successful_sync``;
    - ``PENDING_SETUP`` при вызове без ``phase`` (callers, которые ещё не
      прокидывают phase — conservative freeze).

    Не freeze:
    - ``OFF``;
    - ``PENDING_SETUP`` + pre-confirm phase (awaiting_*/warm_up);
    - ``PENDING_SETUP`` + явный ``phase=None`` (legacy MVP-1 без epoch phase).

    Args:
        mode: durable ``card_ab_hold_mode``.
        phase: durable ``card_ab_hold_phase``; omit для one-arg callers.

    Returns:
        True, если ordinary Auto CPM mutators MUST NOT выполняться.
    """
    normalized_mode = normalize_card_ab_hold_mode(mode)
    if normalized_mode == CardAbHoldMode.ACTIVE:
        return True
    if normalized_mode != CardAbHoldMode.PENDING_SETUP:
        return False
    if phase is _PHASE_OMITTED:
        return True
    normalized_phase = normalize_card_ab_hold_phase(phase)
    return normalized_phase in _POST_CONFIRM_PRE_ACTIVE_PHASES


def is_ab_hold_auto_bid_manual_blocked(mode: CardAbHoldMode | str | None) -> bool:
    """True, если ручной Telegram ``change_auto_bid`` MUST NOT выполнять write.

    Контракт: block+explain для ``PENDING_SETUP`` и ``ACTIVE`` (семейство
    structural freeze); при ``OFF`` ручное изменение ставки разрешено как раньше.
    """
    return is_ab_hold_structural_freeze(mode)

"""A/B Hold: freeze автоматических и ручных мутаций ставки авто-РК (spec §21).

Decision ``ab-hold-confirmed-epoch-parameters-sot`` / tasks §21:
- при ``ACTIVE`` ordinary Auto bid mutators (AutoReset и т.п.) MUST NOT выполняться;
- ручной Telegram ``change_auto_bid`` заблокирован в ``PENDING_SETUP`` и ``ACTIVE``
  (семейство structural freeze) с пояснением пользователю.
"""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    is_ab_hold_structural_freeze,
    normalize_card_ab_hold_mode,
)

AB_HOLD_MANUAL_AUTO_BID_BLOCKED_MSG = (
    "Ставка в автокампании не изменена: при A/B Hold параметры авто-РК "
    "заморожены. Чтобы изменить ставку вручную, отключите A/B Hold "
    "на экране режима."
)


def should_freeze_auto_bid_mutations(mode: CardAbHoldMode | str | None) -> bool:
    """True, когда A/B Hold ACTIVE — ordinary Auto bid mutators MUST NOT выполняться.

    Spec/decision ``ab-hold-confirmed-epoch-parameters-sot`` § Auto bid freeze.
    Только ``ACTIVE`` (не ``PENDING_SETUP``): до подтверждения эпохи AutoReset
    MAY продолжать работать; после перехода в ACTIVE freeze обязателен.
    """
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.ACTIVE


def is_ab_hold_auto_bid_manual_blocked(mode: CardAbHoldMode | str | None) -> bool:
    """True, если ручной Telegram ``change_auto_bid`` MUST NOT выполнять write.

    Контракт: block+explain для ``PENDING_SETUP`` и ``ACTIVE`` (семейство
    structural freeze); при ``OFF`` ручное изменение ставки разрешено как раньше.
    """
    return is_ab_hold_structural_freeze(mode)

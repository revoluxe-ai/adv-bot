"""Enum причины прохождения гейта (инвайт-система)."""

from enum import StrEnum


class PassedGateReason(StrEnum):
    """Причина, по которой пользователь прошёл гейт."""

    BALANCE_TOP_UP = "BALANCE_TOP_UP"  # пополнение баланса
    INVITE_CODE_ENTRY = "INVITE_CODE_ENTRY"  # введение инвайт-кода

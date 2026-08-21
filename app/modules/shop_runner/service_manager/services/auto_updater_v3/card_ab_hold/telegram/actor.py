"""Извлечение Telegram actor id из CallbackQuery для A/B Hold handlers.

Единая точка для write-path fail-closed gate: missing/invalid ``from_user.id``
не должны доходить до ownership/PG mutation как ``AttributeError``.
"""

from __future__ import annotations

from aiogram.types import CallbackQuery

MISSING_ACTOR_NOTICE = "Не удалось подтвердить владельца кабинета"


def callback_actor_id(query: CallbackQuery) -> int | None:
    """Извлечь integer Telegram actor из CallbackQuery или test double.

    Args:
        query: входящий CallbackQuery handler'а.

    Returns:
        ``User.id`` или ``None``, если actor отсутствует / не int (incl. bool).
    """
    raw_actor_id = getattr(getattr(query, "from_user", None), "id", None)
    if isinstance(raw_actor_id, bool) or not isinstance(raw_actor_id, int):
        return None
    return raw_actor_id

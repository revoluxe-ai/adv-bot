"""Вспомогательная функция сортировки WB-токенов для legacy-ротации.

Политика: write-токены (не read_only) ставятся перед read-only;
внутри каждой группы более поздний expires идёт первым (текущее поведение).

Используется в BaseAPI и ABC_WB_API — двух legacy-базовых классах.
Не затрагивает httpx-путь (AuthClientHandler), который уже фильтрует
категории секции и отсекает read_only самостоятельно.
"""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import WBToken


def sort_tokens_write_first(tokens: "list[WBToken]") -> "list[WBToken]":
    """Отсортировать токены: write (не read_only) раньше read-only, внутри — по expires desc.

    Если у токена нет атрибута ``read_only`` (mock / заглушка), считаем его write-токеном.

    Args:
        tokens: список WBToken, уже прошедших фильтр (personal, valid, и т.д.).

    Returns:
        Новый список с корректным порядком для ротации.
    """
    return sorted(
        tokens,
        key=lambda t: (
            # 0 = write (not read_only) → идёт первым (меньше → раньше при sort)
            # 1 = read_only            → идёт последним
            1 if getattr(t, "read_only", False) else 0,
            # Внутри группы: больший expires → раньше (инвертируем)
            -t.expires.timestamp(),
        ),
    )

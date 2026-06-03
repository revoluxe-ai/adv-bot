"""Env-конфиг Telegram-уведомлений процесса updater (баланс, токены).

Читается ``updater.py`` → ``run_main_coroutines``:
``balance_expiration_informer_update``, ``process_token_expiration_check``.
"""

from __future__ import annotations

import os

_ENV_ENABLED = "BALANCE_EXPIRATION_INFORMER_ENABLED"
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def updater_user_notifications_enabled() -> bool:
    """Включены ли пользовательские Telegram-уведомления из updater.

    Покрывает balance_exp_informer (D1/D3/expired, «баланс в минусе») и ежедневную
    проверку просроченных/истекающих WB-токенов (9:00 МСК).

    По умолчанию ``True``. Для отключения:
    ``BALANCE_EXPIRATION_INFORMER_ENABLED=false`` (или ``0`` / ``no`` / ``off``).
    """
    raw = os.getenv(_ENV_ENABLED)
    if raw is None:
        return True
    return raw.strip().lower() not in _FALSE_VALUES


def balance_expiration_informer_enabled() -> bool:
    """Алиас :func:`updater_user_notifications_enabled` (обратная совместимость)."""
    return updater_user_notifications_enabled()

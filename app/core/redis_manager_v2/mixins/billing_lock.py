"""Global billing lock mixin (single process-wide lock).

Простой глобальный лок: либо занят, либо нет. Никакой привязки к дате.
Используется только для предотвращения параллельного запуска биллинга.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Protocol, AsyncIterator

DEFAULT_GLOBAL_BILLING_LOCK_TTL = 900  # 15 минут по умолчанию
_GLOBAL_LOCK_KEY = "billing_lock:global"

if TYPE_CHECKING:  # pragma: no cover
    from ..base_protocol import BaseRedisManagerProtocol


class BillingLockMixin:
    """Mixin с одной глобальной блокировкой.

    Требования к классу-наследнику:
      - `_client` реализует: set_if_not_exists(key, value, ex=ttl), delete(key), exists(key), expire(key, ttl)
    Закрываем абстрактный _get_key базового менеджера.
    """

    def _get_key(self: 'BaseRedisManagerProtocol') -> str:  # noqa: D401
        """Вернуть фиксированный ключ глобального лока."""
        return _GLOBAL_LOCK_KEY

    # ---- Операции лока ----
    async def acquire_lock(
            self: 'BaseRedisManagerProtocol',
            ttl: int = DEFAULT_GLOBAL_BILLING_LOCK_TTL,
    ) -> bool:
        key = self._get_key()
        try:
            return await self._client.set_if_not_exists(key, "1", ex=ttl)
        except AttributeError as e:  # pragma: no cover
            raise RuntimeError("RedisClient должен реализовывать set_if_not_exists(key, value, ex=ttl)") from e

    async def release_lock(self: 'BaseRedisManagerProtocol') -> None:
        key = self._get_key()
        try:
            await self._client.delete(key)
        except Exception:  # pragma: no cover
            pass

    async def is_locked(self: 'BaseRedisManagerProtocol') -> bool:
        key = self._get_key()
        try:
            return bool(await self._client.exists(key))
        except Exception:  # pragma: no cover
            return False

    async def extend_lock(
            self: 'BaseRedisManagerProtocol',
            ttl: int = DEFAULT_GLOBAL_BILLING_LOCK_TTL,
    ) -> bool:
        key = self._get_key()
        try:
            if await self._client.exists(key):
                return bool(await self._client.expire(key, ttl))
            return False
        except Exception:  # pragma: no cover
            return False

    # ---- Контекстный менеджер (вариант 1) ----
    class _Lockable(Protocol):  # локальный протокол только с нужными методами
        async def acquire_lock(self, ttl: int) -> bool: ...  # noqa: D401,E701
        async def release_lock(self) -> None: ...  # noqa: D401,E701

    @asynccontextmanager
    async def billing_lock(self: _Lockable, ttl: int = DEFAULT_GLOBAL_BILLING_LOCK_TTL) -> AsyncIterator[bool]:
        """Асинхронный контекстный менеджер для глобального лока.

        Возвращает True если лок был получен, иначе False (release не вызывается).

        Пример:
            async with manager.billing_lock() as acquired:
                if not acquired:
                    return
                # критическая секция
        """
        locked = await self.acquire_lock(ttl)
        try:
            yield locked
        finally:
            if locked:
                try:
                    await self.release_lock()
                except Exception:  # pragma: no cover
                    pass

"""Redis Signal / LastAbort для cross-pod A/B Hold (bot ↔ shop-runner).

Spec: ``card-ab-hold-mode``. Паттерн как ``LastV3UpdaterAction``:
``AdvSettingRedisCache`` + ``RedisCacheBase``, ключ ``{prefix}:{adv_id}``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldSetupBlockKind,
)

_SIGNAL_TTL_SEC = int(timedelta(minutes=15).total_seconds())
_ABORT_TTL_SEC = int(timedelta(hours=1).total_seconds())
_SETUP_BLOCK_TTL_SEC = int(timedelta(minutes=30).total_seconds())
# One-shot ENTER common-bid reset marker переживает hold-эпизод до EXIT.
_COMMON_BID_ENTER_RESET_TTL_SEC = int(timedelta(days=7).total_seconds())
SETUP_LOCK_TTL_SEC = int(timedelta(minutes=5).total_seconds())
SETUP_LOCK_KEY_PREFIX = "CardAbHoldSetupLock"
_COMMON_BID_ENTER_RESET_DONE = "done"


class CardAbHoldSignalKind(StrEnum):
    """Тип сигнала ENTER/EXIT/CANCEL."""

    ENTER = "enter"
    EXIT = "exit"
    CANCEL = "cancel"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CardAbHoldSignalSnapshot(BaseModel):
    """Снимок Redis-сигнала A/B Hold."""

    signal: CardAbHoldSignalKind
    requested_at: datetime = Field(default_factory=_now_utc)
    requested_by: str = "bot"

    model_config = {"extra": "forbid"}


class CardAbHoldLastAbortSnapshot(BaseModel):
    """Ack безопасной остановки ordinary structural tick."""

    stopped_at: datetime = Field(default_factory=_now_utc)
    reason: str
    safe: bool = True
    can_continue: bool = True

    model_config = {"extra": "forbid"}


class CardAbHoldSetupBlockSnapshot(BaseModel):
    """Причина детерминированного блока ENTER setup (decision §14b).

    Пишется shop-runner (``process_ab_setup``) при пустом allowed-set /
    отсутствующем плане max CPO; читается bot UI для actionable-статуса PENDING.
    """

    kind: CardAbHoldSetupBlockKind
    detected_at: datetime = Field(default_factory=_now_utc)

    model_config = {"extra": "forbid"}


class CardAbHoldSignalRedisCache(
    AdvSettingRedisCache,
    RedisCacheBase,
    prefix="CardAbHoldSignal",
):
    """Ключ ``CardAbHoldSignal:{adv_id}`` — ENTER/EXIT cross-pod signal."""

    async def set_signal(self, snapshot: CardAbHoldSignalSnapshot) -> None:
        """Записать сигнал с TTL 15 минут."""
        await self.client.set(
            self._key,
            snapshot.model_dump_json(),
            ex=_SIGNAL_TTL_SEC,
        )

    async def get_signal(self) -> CardAbHoldSignalSnapshot | None:
        """Прочитать сигнал; None если нет / битый JSON."""
        raw = await self.client.get(self._key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            data: dict[str, Any] = json.loads(raw)
            at = data.get("requested_at")
            if at:
                dt = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                data["requested_at"] = dt
            return CardAbHoldSignalSnapshot.model_validate(data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    async def clear(self) -> None:
        """Удалить сигнал после обработки."""
        await self.client.delete(self._key)


class CardAbHoldLastAbortRedisCache(
    AdvSettingRedisCache,
    RedisCacheBase,
    prefix="CardAbHoldLastAbort",
):
    """Ключ ``CardAbHoldLastAbort:{adv_id}`` — UI poll «остановлено, можно продолжать»."""

    async def set_abort(self, snapshot: CardAbHoldLastAbortSnapshot) -> None:
        """Записать ack abort с TTL 1 час."""
        await self.client.set(
            self._key,
            snapshot.model_dump_json(),
            ex=_ABORT_TTL_SEC,
        )

    async def get_abort(self) -> CardAbHoldLastAbortSnapshot | None:
        """Прочитать last abort; None если нет / битый JSON."""
        raw = await self.client.get(self._key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            data: dict[str, Any] = json.loads(raw)
            at = data.get("stopped_at")
            if at:
                dt = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                data["stopped_at"] = dt
            return CardAbHoldLastAbortSnapshot.model_validate(data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None


class CardAbHoldSetupBlockRedisCache(
    AdvSettingRedisCache,
    RedisCacheBase,
    prefix="CardAbHoldSetupBlock",
):
    """Ключ ``CardAbHoldSetupBlock:{adv_id}`` — причина детерминированного блока setup.

    Writer = shop-runner ``process_ab_setup`` (set при пустом allowed-set /
    отсутствующем max CPO, clear при успешном ACTIVE); reader = bot UI poll.
    Даёт actionable-причину PENDING вместо generic «Подготовка…» (decision §14b)
    без новой PG-миграции (§14c: MVP recovery = reason + always-available EXIT).
    TTL 30 минут — переживает интервал между setup-тиками, но не залипает навсегда.
    """

    async def set_block(self, snapshot: CardAbHoldSetupBlockSnapshot) -> None:
        """Записать причину блока с TTL 30 минут."""
        await self.client.set(
            self._key,
            snapshot.model_dump_json(),
            ex=_SETUP_BLOCK_TTL_SEC,
        )

    async def get_block(self) -> CardAbHoldSetupBlockSnapshot | None:
        """Прочитать причину блока; None если нет / битый JSON / неизвестный kind."""
        raw = await self.client.get(self._key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            data: dict[str, Any] = json.loads(raw)
            at = data.get("detected_at")
            if at:
                dt = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                data["detected_at"] = dt
            return CardAbHoldSetupBlockSnapshot.model_validate(data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    async def clear(self) -> None:
        """Снять причину блока (успешный setup / EXIT)."""
        await self.client.delete(self._key)


class CardAbHoldCommonBidEnterResetRedisCache(
    AdvSettingRedisCache,
    RedisCacheBase,
    prefix="CardAbHoldCommonBidEnterReset",
):
    """Ключ ``CardAbHoldCommonBidEnterReset:{adv_id}`` — one-shot ENTER reset done.

    Decision §19 / tasks §27: после успешного owned reset-to-min маркер ``done``
    запрещает повторный reset mid-hold (Enable no-op / setup tick). EXIT MUST
    ``clear()``, чтобы новый ENTER снова сбросил common bid.
    """

    async def is_done(self) -> bool:
        """True, если ENTER reset для текущего hold-эпизода уже выполнен."""
        raw = await self.client.get(self._key)
        if not raw:
            return False
        if isinstance(raw, bytes):
            raw = raw.decode()
        return str(raw) == _COMMON_BID_ENTER_RESET_DONE

    async def mark_done(self) -> None:
        """Зафиксировать успешный (или no-op) ENTER common-bid reset."""
        _ = await self.client.set(
            self._key,
            _COMMON_BID_ENTER_RESET_DONE,
            ex=_COMMON_BID_ENTER_RESET_TTL_SEC,
        )

    async def clear(self) -> None:
        """Снять маркер на EXIT — следующий ENTER снова делает reset."""
        _ = await self.client.delete(self._key)


def setup_lock_redis_key(adv_id: int) -> str:
    """Ключ NX-lock для одного setup на кампанию."""
    return f"{SETUP_LOCK_KEY_PREFIX}:{int(adv_id)}"

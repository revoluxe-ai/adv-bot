"""Форматирование последнего V3-действия для блока «Обновл:» в меню РК."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.last_action_redis import (
    LastV3UpdaterActionRedisCache,
    LastV3UpdaterActionSnapshot,
)

MSK_TZ = timezone(timedelta(hours=3))
_TIME_FMT = "%H:%M:%S %d-%m-%Y"


def _to_msk(dt: datetime) -> datetime:
    """Привести aware/naive datetime к MSK (naive трактуем как UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MSK_TZ)


def format_snapshot_time_msk(updated_at: datetime) -> str:
    """Время снимка в московском поясе для UI."""
    return _to_msk(updated_at).strftime(_TIME_FMT)


def format_last_v3_action_str(snapshot: LastV3UpdaterActionSnapshot | None) -> str:
    """Строка для «посл. V3: …»; ``None`` → «Нет данных»."""
    if snapshot is None:
        return "Нет данных"
    time_str = format_snapshot_time_msk(snapshot.updated_at)
    kw_part = f" «{snapshot.keyword_text}»" if snapshot.keyword_text else ""
    mode_part = f"{snapshot.from_mode}→{snapshot.to_mode}"
    line = f"{snapshot.action.value}{kw_part} {mode_part} {time_str}"
    if snapshot.batch_extra_count > 0:
        line += f" (+{snapshot.batch_extra_count} ещё)"
    if snapshot.reason:
        line += f" ({snapshot.reason})"
    return line


async def load_last_v3_action_display(adv: AdvSetting) -> str:
    """Загрузить snapshot из Redis и отформатировать для меню."""
    cache = LastV3UpdaterActionRedisCache(adv)
    snapshot = await cache.get()
    return format_last_v3_action_str(snapshot)

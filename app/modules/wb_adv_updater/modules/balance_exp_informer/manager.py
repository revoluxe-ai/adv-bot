from __future__ import annotations

import asyncio
import logging
import math
import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.modules.wb_adv_updater.modules.balance_exp_informer.service import (
    BalanceReminderService,
)
from app.utils.db.session_maker import get_async_session_maker as session_factory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BalanceInformerConfig:
    send_hour_utc: int = 14
    window_end_hour_utc: int = 18
    fail_backoff_seconds: int = 60
    sleep_jitter_seconds: int = 10


CFG = BalanceInformerConfig()


def seconds_until_next_send_hour_utc(now: datetime, send_hour_utc: int) -> int:
    """
    Секунды до ближайшего {send_hour_utc}:00 UTC.
    Если сейчас раньше — до сегодня.
    Если сейчас >= — до завтра.
    """
    assert now.tzinfo is not None

    target_timezone = now.tzinfo
    target_today = datetime.combine(
        now.date(),
        time(send_hour_utc, 0),
        tzinfo=target_timezone,
    )
    target = target_today if now < target_today else target_today + timedelta(days=1)
    return max(0, math.ceil((target - now).total_seconds()))


def in_send_window_utc(now: datetime, send_hour_utc: int, window_end_hour_utc: int) -> bool:
    """
    Окно: [send_hour_utc, window_end_hour_utc)
    """
    return send_hour_utc <= now.hour < window_end_hour_utc


def _jitter(seconds: int) -> int:
    return random.randint(0, seconds) if seconds > 0 else 0


async def balance_expiration_informer_tick(
    service: BalanceReminderService,
    cfg: BalanceInformerConfig = CFG,
) -> None:
    """
    Один "тик" планировщика.
    Делает ровно одно:
      - либо спит до окна/следующего дня,
      - либо вызывает service.update() и затем спит.
    """
    now = datetime.now(ZoneInfo("Europe/Moscow"))

    if not in_send_window_utc(now, cfg.send_hour_utc, cfg.window_end_hour_utc):
        sleep_sec = seconds_until_next_send_hour_utc(now, cfg.send_hour_utc)
        await asyncio.sleep(sleep_sec + _jitter(cfg.sleep_jitter_seconds))
        return

    try:
        await service.update()
    except Exception as exc:
        logger.exception("Balance reminder service failed", exc_info=exc)
        await asyncio.sleep(cfg.fail_backoff_seconds)
        return

    now_after = datetime.now(ZoneInfo("Europe/Moscow"))
    sleep_sec = seconds_until_next_send_hour_utc(now_after, cfg.send_hour_utc)
    await asyncio.sleep(sleep_sec + _jitter(cfg.sleep_jitter_seconds))


async def balance_expiration_informer_update() -> None:
    service = BalanceReminderService(session_factory)

    while True:
        await balance_expiration_informer_tick(service)

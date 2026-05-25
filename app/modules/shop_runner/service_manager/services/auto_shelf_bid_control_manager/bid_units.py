"""Контракт единиц ставок Auto Shelf Bid Control.

Внутренний канон (PG, CH, Redis recommendations, setter, DTO ``*_minor``):
    **копейки** — как в WB API ``adv/v0/bids`` (200 ₽ → ``20000``).

Граница legacy min-bids (Redis ``min_bids`` / ``AdvMinNmidsBids``):
    кэш хранит **рубли** (legacy CPM после ``(min_cpm + 99) // 100`` из API).
    В control переводим в копейки через :func:`wb_min_cpm_rub_to_bid_minor`.

Telegram UI:
    ввод сумм ставок и шага — **в рублях**;
    отображение — :func:`format_bid_minor_for_telegram` (деление на 100);
    метки цикла — :func:`format_timestamp_for_telegram` (UTC в PG → МСК в чате).
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

KOPECKS_PER_RUB = 100
# Часовой пояс отображения меток цикла в Telegram (хранение в PG — UTC).
TELEGRAM_DISPLAY_TZ = "Europe/Moscow"
# Сколько последних тестовых точек ставки показывать в блоке «Покрытые ставки».
TELEGRAM_BID_POINTS_DISPLAY_LIMIT = 5

# WB API: ставка в копейках (200 ₽ → 20000). 500 ₽ → 50000.
DEFAULT_MAX_BID_MINOR = 50_000
# Минимальный шаг между тестовыми ставками: 1 ₽ → 100 копеек.
DEFAULT_MIN_BID_DISTANCE_MINOR = 100


def report_day_start_utc(tz_name: str = "Europe/Moscow") -> datetime:
    """Начало отчётного дня в UTC (для пассивной аналитики полок)."""
    tz = ZoneInfo(tz_name)
    local_start = datetime.now(tz).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return local_start.astimezone(timezone.utc)


def resolve_test_segment_start_utc(
    *,
    test_started_at: datetime | None,
    current_cycle_started_at: datetime | None,
    fallback_now: datetime | None = None,
) -> datetime:
    """Начало текущего test-сегмента в UTC (порог ``target_test_impressions``).

    Аналог ``main_started_at`` для main: показы до нового test/cycle reset не
    засчитываются в завершение фазы test.
    """
    if test_started_at is not None:
        return test_started_at
    if current_cycle_started_at is not None:
        return current_cycle_started_at
    return fallback_now or datetime.now(timezone.utc)


def rubles_to_bid_minor(rubles: int) -> int:
    """Перевести рубли из Telegram-ввода в внутренние копейки."""
    return int(rubles) * KOPECKS_PER_RUB


def wb_min_cpm_rub_to_bid_minor(cpm_rub: int) -> int:
    """Перевести min bid из Redis/AdvMinNmidsBids (рубли) в ``bid_minor`` (копейки)."""
    return rubles_to_bid_minor(int(cpm_rub))


def format_bid_minor_for_telegram(value: int | None, currency: str = "RUB") -> str:
    """Отформатировать ``bid_minor`` (копейки) для пользователя в Telegram."""
    if value is None:
        return "—"
    if currency == "RUB":
        rub = int(value) / KOPECKS_PER_RUB
        if rub == int(rub):
            return f"{int(rub)} ₽"
        return f"{rub:.2f} ₽"
    return str(int(value))


def truncate_datetime_to_seconds(value: datetime | None) -> datetime | None:
    """Обрезать ``datetime`` до секунд (без микросекунд) для UI и DTO."""
    if value is None:
        return None
    if value.microsecond == 0:
        return value
    return value.replace(microsecond=0)


def _parse_timestamp_for_display(value: str) -> datetime:
    """Разобрать метку из строки; naive трактуем как UTC (как в PG timestamptz)."""
    text = value.strip().replace("T", " ", 1)
    if "." in text:
        text = text.split(".", 1)[0]
    if "+" in text:
        text = text.split("+", 1)[0].strip()
    if text.endswith("Z"):
        text = text[:-1].strip()
    parsed = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    return parsed.replace(tzinfo=timezone.utc)


def format_timestamp_for_telegram(
    value: datetime | str | None,
    tz_name: str = TELEGRAM_DISPLAY_TZ,
) -> str:
    """Дата/время для Telegram: локальное время (по умолчанию МСК), без долей секунды."""
    if value is None:
        return "—"
    if isinstance(value, datetime):
        dt = truncate_datetime_to_seconds(value)
    else:
        text = str(value).strip()
        if not text:
            return "—"
        dt = _parse_timestamp_for_display(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(ZoneInfo(tz_name))
    suffix = " МСК" if tz_name == TELEGRAM_DISPLAY_TZ else ""
    return local.strftime("%Y-%m-%d %H:%M:%S") + suffix

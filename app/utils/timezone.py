import datetime
from zoneinfo import ZoneInfo


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def now_moscow() -> datetime.datetime:
    """Return current datetime in Moscow timezone."""
    return datetime.datetime.now(MOSCOW_TZ)


def today_moscow() -> datetime.date:
    """Return current date in Moscow timezone."""
    return now_moscow().date()


def utc_to_moscow(dt: datetime.datetime) -> datetime.datetime:
    """Convert aware datetime to Moscow timezone."""
    return dt.astimezone(MOSCOW_TZ)


def ensure_moscow(dt: datetime.datetime) -> datetime.datetime:
    """Attach Moscow timezone to naive datetimes or convert aware ones."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=MOSCOW_TZ)
    return dt.astimezone(MOSCOW_TZ)

from __future__ import annotations

from datetime import datetime, date

import pytz

from app.settings import settings


def billing_today() -> date:
    """Возвращает текущую дату по BILLING_TZ (Europe/Moscow по умолчанию)."""
    tz_name = getattr(settings, "BILLING_TZ", "Europe/Moscow")
    tz = pytz.timezone(tz_name)
    currently = datetime.now(tz)
    return currently.date()


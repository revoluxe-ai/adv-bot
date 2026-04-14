"""Снимок cooldown «выше цели при мин. ставке»: момент отключения и зафиксированные показы."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AboveTargetCooldownEntry:
    """last_disabled_at — начало текущего цикла; views_at_freeze — показы на момент фиксации."""

    last_disabled_at: datetime
    views_at_freeze: int

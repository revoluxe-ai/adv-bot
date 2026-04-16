"""Единое определение «активной» РК для выгрузки и импорта Excel."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models import AdvSetting


def is_active_adv(a: AdvSetting) -> bool:
    """Совпадает с сортировкой в списке кампаний: активная + бот включён."""
    return bool(a.active_status and a.bot_active)

"""Входы и факты аналитической агрегации.

Дневной факт кампании — последняя версия ``full_adv_wb_stat`` на ногу и день.
Пропуск дня не хранится как ноль: отсутствующая строка просто не входит в список.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.keyword_performance.domain.models import KeywordWindowRowV1
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv


@dataclass(frozen=True, slots=True)
class CampaignDailyFact:
    """Один физический день одной ноги из ``default_db.full_adv_wb_stat``."""

    adv_id: int
    stat_date: date
    views: int | None
    clicks: int | None
    spend_rub: float | None
    added_to_cart: int | None
    orders: int | None
    order_sum_rub: float | None


@dataclass(frozen=True, slots=True)
class AnalysisBuildRequest:
    """Всё, что нужно сервису, без обращения к БД или транспорту.

    ``campaign_source_complete_through`` пуст, пока источник сам не доказал
    полноту. Совпадение конца окна с границей пакета таким доказательством не является.
    """

    shop_id: str
    generated_at: str
    period: ExportPeriod
    scope: tuple[ExportScopeAdv, ...]
    campaign_facts: tuple[CampaignDailyFact, ...]
    keyword_windows: tuple[KeywordWindowRowV1, ...] = ()
    keyword_history_first: date | None = None
    keyword_history_last: date | None = None
    campaign_source_complete_through: date | None = None
    keyword_source_complete_through: date | None = None

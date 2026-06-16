"""История по дням для ключевых запросов WB.

Пакет содержит ClickHouse-менеджер и DTO для показа детальной дневной
статистики по одному ключевому запросу в клиентском боте.
"""

from .dto import KeywordDailyStat
from .keyword_daily_history_manager import KeywordDailyHistoryManager

__all__ = ["KeywordDailyHistoryManager", "KeywordDailyStat"]


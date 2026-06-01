"""Клики «полки» и «органика» за сегодня для полочного режима (``rec_system_mode``).

Используется в ``change_adv_strategy`` (``load_extras=True``) и в UI (орг/пол в статистике).
Без enrich ``traffic_clicks_dto`` остаётся None → сравнение organic/shelf в селекторе стратегии
пропускается, ``is_shelf_activation_allowed`` = False.
"""

from __future__ import annotations

from datetime import datetime

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
    TrafficClicksDTO,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager


def compute_shelf_clicks(auto_total_clicks: int, auto_keyword_clicks: int) -> int:
    """Клики полок/рекомендаций в авто-РК: все клики авто минус клики по ключевым фразам."""
    return max(0, auto_total_clicks - auto_keyword_clicks)


def compute_organic_clicks(funnel_clicks: int, all_campaign_clicks: int) -> int:
    """Органические переходы на карточку: клики воронки минус сумма кликов всех РК комплекса."""
    return max(0, funnel_clicks - all_campaign_clicks)


class TrafficClicksManager:
    async def enrich(self, complex_adv: ComplexAdv) -> None:
        """Заполняет ``complex_adv.traffic_clicks_dto`` за текущие сутки (ClickHouse + воронка).

        При выключенном ``rec_system_mode`` обнуляет DTO и выходит.
        """
        if not complex_adv.rec_system_promotion_mode_active:
            complex_adv.traffic_clicks_dto = None
            return

        # Один момент времени для всех запросов — иначе около полуночи даты могут разъехаться.
        now = datetime.now()

        # Все клики авто-кампании за сегодня (ключи + полки/рекомендации).
        auto_total_clicks = await full_wb_adv_stat.get_auto_total_clicks_today(
            complex_adv.adv_id, at=now
        )
        # Суммарные клики всех РК комплекса (авто + поиск, если есть).
        all_campaign_clicks_today = (
            await full_wb_adv_stat.get_stats_by_last_days(
                list(complex_adv.all_adv_ids),
                start_date=now,
                end_date=now,
            )
        ).clicks or 0
        # Клики именно по ключевым запросам в этой же авто-кампании за сегодня.
        auto_keyword_clicks, _auto_keyword_views = (
            await full_wb_adv_stat.get_keywords_clicks_and_views(
                [complex_adv.adv_id],
                start_date=now,
                end_date=now,
            )
        )
        # Карточные переходы из товарной воронки за сегодня.
        funnel_clicks = await common_stat_manager.get_today_funnel_clicks(
            complex_adv.nmids, at=now
        )

        # Полки/рекомендации = авто-клики минус клики по ключам.
        shelf_clicks = compute_shelf_clicks(auto_total_clicks, auto_keyword_clicks)
        # Органика: клики из воронки минус суммарные клики всех РК.
        organic_clicks = compute_organic_clicks(
            funnel_clicks,
            int(all_campaign_clicks_today),
        )
        complex_adv.traffic_clicks_dto = TrafficClicksDTO(
            organic_clicks=organic_clicks,
            shelf_clicks=shelf_clicks,
            keyword_clicks=auto_keyword_clicks,
        )


from __future__ import annotations

from datetime import datetime

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
    TrafficClicksDTO,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager


class TrafficClicksManager:
    async def enrich(self, complex_adv: ComplexAdv) -> None:
        if not complex_adv.rec_system_promotion_mode_active:
            complex_adv.traffic_clicks_dto = None
            return

        # Все клики авто-кампании за сегодня (ключи + полки/рекомендации).
        auto_total_clicks = await full_wb_adv_stat.get_auto_total_clicks_today(
            complex_adv.adv_id
        )
        # Клики именно по ключевым запросам в этой же авто-кампании за сегодня.
        keyword_search_clicks, _keyword_search_views = (
            await full_wb_adv_stat.get_keywords_clicks_and_views(
            [complex_adv.adv_id],
            start_date=datetime.now(),
            end_date=datetime.now(),
        )
        )
        # Карточные переходы из товарной воронки за сегодня.
        funnel_clicks = await common_stat_manager.get_today_funnel_clicks(
            complex_adv.nmids
        )

        # Полки/рекомендации = авто-клики минус клики по ключам.
        shelf_clicks = max(0, auto_total_clicks - keyword_search_clicks)
        # Органика по согласованной формуле:
        # воронка - авто-клики - клики по ключам.
        organic_clicks = max(
            0,
            funnel_clicks - auto_total_clicks - keyword_search_clicks,
        )
        complex_adv.traffic_clicks_dto = TrafficClicksDTO(
            organic_clicks=organic_clicks,
            shelf_clicks=shelf_clicks,
            keyword_clicks=keyword_search_clicks,
        )


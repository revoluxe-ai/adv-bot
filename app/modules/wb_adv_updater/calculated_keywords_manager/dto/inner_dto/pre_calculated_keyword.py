from __future__ import annotations

from pydantic import BaseModel

from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import KeywordSettingDTO
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import KeywordStat
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
)
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus

from .keyword_cpm_sources import KeywordCpmSources
from ...enum import KeywordRatingMode


class PreCalculatedKeyword(BaseModel):
    adv_id: int
    keyword_setting: KeywordSettingDTO
    cluster_stat: KeywordStat
    bidder_status: "BidderKeywordStatus"
    rating_mode: KeywordRatingMode
    cpm_sources: KeywordCpmSources | None = None

    @property
    def cpm(self) -> float:
        """CPM из каскада (set_bid → bid_log → stats). Если cpm_sources не задан
        (например в тестах вызывают __get_calculated_keywords без enrich), берём
        cluster_stat.cpm, чтобы рейтинг и orders_per_1000_rub считались.
        """
        if self.cpm_sources is not None:
            resolved = self.cpm_sources.resolved_cpm()
            if resolved is not None:
                return resolved
        return getattr(self.cluster_stat, "cpm", 0.0) or 0.0

    @property
    def ctr(self) -> float:
        return self.cluster_stat.ctr

    @property
    def conv_views_to_orders(self) -> float:
        """Конверсия показы→заказы (доля), из запроса."""
        return self.cluster_stat.conv_views_to_orders

    @property
    def orders_per_1000_rub(self) -> float:
        """Заказов на 1000 руб. (= conv × 1_000_000 / CPM). Чем больше — тем лучше."""
        result = calc_orders_per_1000_rub(self.conv_views_to_orders, self.cpm)
        if result is None:
            return 0.0
        return result

    @property
    def rating(self) -> float:
        """Метрика для сортировки/сравнения: по Mode — conv_views_to_orders или orders_per_1000_rub (чем больше, тем лучше)."""
        if self.rating_mode == KeywordRatingMode.BY_MAX_CONV:
            return self.conv_views_to_orders
        elif self.rating_mode == KeywordRatingMode.BY_MIN_CPO:
            return self.orders_per_1000_rub
        else:
            raise NotImplementedError(f"Unknown rating mode: {self.rating_mode}")

    @property
    def hard_status(self) -> int:
        return self.keyword_setting.hard_status

    @property
    def relevant(self) -> bool:
        return self.keyword_setting.relevant

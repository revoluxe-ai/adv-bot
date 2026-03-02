from datetime import datetime
from pydantic import BaseModel

from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import KeywordStat
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import KeywordSettingDTO
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)
from .inner_dto.keyword_cpm_sources import KeywordCpmSources
from .inner_dto.keyword_state import KeywordState
from .states import KeywordStatus, KeywordStatusReason

# Кешируем, поэтому юзаем Pydantic

class CalculatedKeyword(BaseModel):
    adv_id: int
    keyword_setting: KeywordSettingDTO
    cluster_stat: KeywordStat
    state: KeywordState
    # Рейтинг для сортировки (по Mode: conv_views_to_orders или orders_per_1000_rub). Заполняется менеджером из pre_kw.rating.
    rating: float
    target_pay_for_order: float | None
    above_rec_conversion: bool | None = None
    cpm_sources: KeywordCpmSources | None = None


    @property
    def cpc(self) -> float | None:
        if  not self.clicks:
            return None
        return self.spend / self.clicks


    @property
    def target_place(self) -> int | None:
        return self.keyword_setting.target_place

    @property
    def pay_for_order(self) -> float:
        """Себестоимость одного заказа (руб.), при текущем CPM. CPO = 1000 / orders_per_1000_rub."""
        return calc_pay_for_order(self.orders_per_1000_rub)


    @property
    def cpm(self) -> float:
        """CPM только из каскада (Redis set_bid → bid_log → stats). Без fallback на SQL."""
        if self.cpm_sources is not None:
            resolved = self.cpm_sources.resolved_cpm()
            if resolved is not None:
                return resolved
        return 0.0

    @property
    def cpm_set_bid(self) -> int | None:
        return self.cpm_sources.cpm_set_bid if self.cpm_sources else None

    @property
    def cpm_set_bid_date(self) -> datetime | None:
        return self.cpm_sources.cpm_set_bid_date if self.cpm_sources else None

    @property
    def cpm_from_bid_log(self) -> float | None:
        return self.cpm_sources.cpm_from_bid_log if self.cpm_sources else None

    @property
    def cpm_from_bid_log_date(self) -> datetime | None:
        return self.cpm_sources.cpm_from_bid_log_date if self.cpm_sources else None

    @property
    def cpm_from_stats(self) -> float | None:
        return self.cpm_sources.cpm_from_stats if self.cpm_sources else None

    @property
    def cpm_from_stats_date(self) -> datetime | None:
        return self.cpm_sources.cpm_from_stats_date if self.cpm_sources else None

    @property
    def add_to_cart(self) -> int:
        return self.cluster_stat.add_to_cart

    @property
    def orders(self)-> int:
        return self.cluster_stat.orders

    @property
    def reason(self) -> KeywordStatusReason:
        return self.state.reason

    @property
    def best_keyword_status(self) -> bool:
        return self.state.best_keyword_status

    @property
    def status(self) -> KeywordStatus:
        return self.state.status

    @property
    def spend(self) -> float:
        return self.cluster_stat.spend

    @property
    def ctr(self) -> float:
        return self.cluster_stat.ctr

    @property
    def clicks(self) -> int:
        return self.cluster_stat.clicks

    @property
    def text(self) -> str:
        return self.keyword_setting.text

    @property
    def orders_per_1000_rub(self) -> float:
        """Заказов на 1000 руб. рекламы (= conv × 1_000_000 / CPM). CPM из каскада."""
        return calc_orders_per_1000_rub(self.conv_views_to_orders, self.cpm)

    @property
    def rating_by_orders(self) -> float:
        """Обратная совместимость: заказов на 100₽ (= orders_per_1000_rub / 10)."""
        return self.orders_per_1000_rub / 10.0

    @property
    def conv_views_to_orders(self) -> float:
        """Конверсия показы→заказы (доля)."""
        return self.cluster_stat.conv_views_to_orders

    @property
    def views(self) -> int:
        return self.cluster_stat.views

    @property
    def keyword_setting_original_id(self) -> int:
        return self.keyword_setting.id

    @property
    def hard_status(self) -> int:
        return self.keyword_setting.hard_status

    # TODO: Обязательно сделать кнопку-отключение добавления только релевантных, и всем ее отключить по умолчанию
    @property
    def relevant(self) -> bool:
        return self.keyword_setting.relevant

    @property
    def position(self) -> float:
        position = self.cluster_stat.position
        position = max(round(position), 1)
        return position

    @property
    def timestamp(self) -> datetime:
        return self.cluster_stat.timestamp


    @property
    def total_views(self) -> int:
        return self.cluster_stat.total_views

    @property
    def total_orders(self) -> int:
        return self.cluster_stat.total_orders

    @property
    def predict_ctr(self) -> float | None:
        return self.keyword_setting.predict_ctr

    @property
    def added_clicks(self) -> int:
        return self.keyword_setting.added_clicks or 0



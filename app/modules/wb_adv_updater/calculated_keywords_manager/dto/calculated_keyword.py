from datetime import datetime
from pydantic import BaseModel

from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import KeywordStat
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import  KeywordSettingDTO
from .inner_dto.keyword_state import KeywordState
from .states import KeywordStatus, KeywordStatusReason

# Кешируем, поэтому юзаем Pydantic

class CalculatedKeyword(BaseModel):
    adv_id: int
    keyword_setting: KeywordSettingDTO
    cluster_stat: KeywordStat
    state: KeywordState
    target_pay_for_order: float | None


    # TODO: Переделать запрос расчета рейтинга

    @property
    def auto_max_bid_cpm(self) -> int | None:
        max_pay_for_all_views_for_order = self.target_pay_for_order
        if not max_pay_for_all_views_for_order:
           return None
        if self.rating_by_orders == 0:
            return None
        views_for_order = 1000/self.rating_by_orders
        pay_for_one_view = max_pay_for_all_views_for_order / views_for_order
        pay_for_1000_views = pay_for_one_view * 1000
        return int(pay_for_1000_views + 0.5)



    @property
    def pay_for_order_by_current_cpm(self) -> float:
        last_cpm = self.cpm
        pay_for_order = 1 / self.rating_by_orders * last_cpm / 1000
        return pay_for_order


    @property
    def cpm(self) -> float:
        return self.cluster_stat.cpm

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
    def cpc(self) -> float:
        return self.cluster_stat.cpc

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
    def rating_by_orders(self) -> float:
        return self.cluster_stat.final_rating

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
        return self.cluster_stat.position

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



from typing import Union, Optional

from aiogram.filters.callback_data import CallbackData


class ChoiceAdvPaginator(CallbackData, prefix="choice_adv_paginator"):
    wb_user_cabinet_original_id: int
    page: int


class Action:
    new = 'new'
    select = 'select'
    buy = 'buy'



class BudgetForCreatingAdv(CallbackData, prefix="budget"):
    type: str


class Shop(CallbackData, prefix="shop"):
    action: str
    wb_user_cabinet_original_id: int


class ShopNew(CallbackData, prefix="shop_new"):
    pass


class Adv(CallbackData, prefix="adv"):
    adv_original_id: int
    action: Optional[str] = None
    wb_user_cabinet_original_id: Optional[int] = None



class TurnBot(CallbackData, prefix="turn_bot"):
    action: str
    adv_original_id: Optional[int] = None
    wb_user_cabinet_original_id: int


class BotActive:
    action: bool


class Min_ctr(CallbackData, prefix="min_ctr"):
    action: str
    adv_original_id: int
    wb_user_cabinet_original_id: int


class AddNewToken(CallbackData, prefix="add_new_token"):
    wb_user_cabinet_original_id: int


class DeleteWbUserCabinet(CallbackData, prefix="delete_wb_user_cabinet"):
    wb_user_cabinet_original_id: int


class SettingKeywords(CallbackData, prefix="setting_keywords"):
    adv_original_id: int
    type: str
    page: int = 1
    reset_filter: bool = False


class SettingKeyword(CallbackData, prefix="setting_keyword"):
    keyword_setting_original_id: int


class ChangeKeywordHardStatus(CallbackData, prefix="change_keyword_hard_status"):
    new_hard_status: int
    keyword_setting_original_id: int


class CheckSubscribe(CallbackData, prefix="check_subscribe"):
    pass


class RefProgram(CallbackData, prefix="ref_program"):

    """select or new"""

    action: str


class OrderSubscribe(CallbackData, prefix="order_subscribe"):
    period_days: int
    price: int
    wb_cabinet_original_id: int


class Start(CallbackData, prefix="start"):
    pass


class ChangeMinCTR(CallbackData, prefix="change_min_ctr"):
    action: str
    adv_original_id: int


class ChangeMaxCPC(CallbackData, prefix="change_max_cpc"):
    action: str
    adv_original_id: int


class ChangeMinViewsForPredictCTR(CallbackData, prefix="change_min_views_for_predict_ctr"):
    pass


class AddBalance(CallbackData, prefix="add_balance"):
    wb_cabinet_original_id: int


class KeywordPositionHistory(CallbackData, prefix="keyword_position_history"):
    adv_original_id: int


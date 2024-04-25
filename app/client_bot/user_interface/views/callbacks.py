from aiogram.filters.callback_data import CallbackData
from typing import Union



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
    action: str
    adv_original_id: Union [int | None]
    wb_user_cabinet_original_id: int


class TurnAdv(CallbackData, prefix="turn_adv"):
    action: str
    adv_original_id: int
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

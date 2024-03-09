from aiogram.filters.callback_data import CallbackData
from enum import Enum
from typing import Union



class ChoiceAdvPaginator(CallbackData, prefix="choice_adv_paginator"):
    wb_user_cabinet_original_id: int
    page: int


class Action(str, Enum):
    new = 'new'
    select= 'select'



class BudgetForCreatingAdv(CallbackData, prefix="budget"):
    type: str


class Shop(CallbackData, prefix="shop"):
    action: str
    wb_user_cabinet_original_id: Union[int, None] = None


# class TimeZoneCallbackData(CallbackData, prefix="timezone"):
#     timezone: int


# class ChangeCabinetForCardsOrNot(CallbackData, prefix="change_cabinet"):
#     action: str
#     nmid: int
#     cabinet_id: int
#     card_id: int
class Adv(CallbackData, prefix="adv"):
    action: str
    adv_original_id: int
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


class AddNewToken(CallbackData, prefix="add_new_token"):
    wb_user_cabinet_original_id: int


class DeleteWbUserCabinet(CallbackData, prefix="delete_wb_user_cabinet"):
    wb_user_cabinet_original_id: int
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.db.associations import WBUserCabinet
from ...user_interface.views.callbacks import BudgetForCreatingAdv
from app.wildberries.models import  AdvSetting
import app
from ...user_interface.views import callbacks
from app.wildberries.data_classes.adv import Adv
from ...user_interface.views.callbacks import TurnAdv
from .callbacks import Action
from sqlalchemy import select
from session_maker import get_async_session_maker


sm = get_async_session_maker()


def get_shop_keyboard(all_shops: list[app.my_types.WBUserCabinet]):
    # Создаем список для строк кнопок
    keyboard_buttons = []

    for wb_user_cabinet in all_shops:
        shop_name = wb_user_cabinet.name
        wb_user_cabinet_original_id = wb_user_cabinet.id
        button = InlineKeyboardButton(text=shop_name, callback_data=callbacks \
                                      .Shop(action=Action.select,
                                            wb_user_cabinet_original_id=wb_user_cabinet_original_id).pack())
        # Добавляем кнопку в список строк кнопок
        keyboard_buttons.append([button])  # Каждая кнопка в своем списке, т.е. каждая в новой строке
    button = InlineKeyboardButton(text='Добавить магазин', callback_data=callbacks.Shop\
        (action=Action.new).pack())
    keyboard_buttons.append([button])
    # Создаем InlineKeyboardMarkup с переданным списком кнопок
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard


def get_budget_type_keyboard(balances):
    buttons = [
        [InlineKeyboardButton(text=f'Счет: {balances.balance} руб.', callback_data=BudgetForCreatingAdv(type='balance').pack())],
        [InlineKeyboardButton(text=f'Баланс: {balances.net} руб.', callback_data=BudgetForCreatingAdv(type='net').pack())],
        [InlineKeyboardButton(text=f'Бонусы: {balances.bonus} руб.', callback_data=BudgetForCreatingAdv(type='bonus').pack())]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return keyboard



#
#
# def get_timezone_keyboard():
#     # Инициализация клавиатуры без указания row_width
#
#     timezones = [
#         ('Калининград (UTC+2)', TimeZoneCallbackData(timezone=2).pack()),
#         ('Москва (UTC+3)', TimeZoneCallbackData(timezone=3).pack()),
#         ('Самара (UTC+4)', TimeZoneCallbackData(timezone=4).pack()),
#         ('Екатеринбург (UTC+5)', TimeZoneCallbackData(timezone=5).pack()),
#         ('Омск (UTC+6)',   TimeZoneCallbackData(timezone=6).pack()),
#         ('Красноярск (UTC+7)', TimeZoneCallbackData(timezone=7).pack()),
#         ('Иркутск (UTC+8)', TimeZoneCallbackData(timezone=8).pack()),
#         ('Якутск (UTC+9)', TimeZoneCallbackData(timezone=9).pack()),
#         ('Владивосток (UTC+10)', TimeZoneCallbackData(timezone=10).pack()),
#         ('Среднеколымск (UTC+11)', TimeZoneCallbackData(timezone=11).pack()),
#         ('Анадырь (UTC+12)', TimeZoneCallbackData(timezone=12).pack())
#     ]
#
#     buttons = []
#     for label, callback_data in timezones:
#         button = InlineKeyboardButton(text=label, callback_data=callback_data)
#         buttons.append([button])  # Добавление кнопки в клавиатуру
#     timezone_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
#     return timezone_keyboard


# def get_main_menu_keyboard():
#     keyboard = InlineKeyboardMarkup()
#     keyboard.add(InlineKeyboardButton(text='Тип бюджета', callback_data='add_adv'))
#     keyboard.add(InlineKeyboardButton(text='Добавить магазин', callback_data='add_shop'))
#     return keyboard

def get_adv_list_keyboard(advs: list[Adv]):
    buttons = []
    for adv in advs:
        button = InlineKeyboardButton(text=adv.name, callback_data=\
            callbacks.Adv(action='select', adv_original_id=adv.id).pack())
        buttons.append([button])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_adv_setting_keyboard(wb_user_cabinet: WBUserCabinet, adv_setting: AdvSetting):
    if adv_setting.bot_active:
        buttons = [
            [InlineKeyboardButton(text=f'Изменить минимальный CTR ({adv_setting.min_ctr})',
                                  callback_data=callbacks.Min_ctr(action='change',
                                         adv_original_id=adv_setting.id).pack())],
            [InlineKeyboardButton(text='Отключить бота', callback_data=TurnAdv(action='off',
             adv_original_id=adv_setting.id,
            wb_user_cabinet_original_id =wb_user_cabinet.id).pack())],

        ]
    else:
        buttons = [
            [InlineKeyboardButton(text='Включить бота', callback_data=TurnAdv(action='on',
               adv_original_id=adv_setting.id,
             wb_user_cabinet_original_id = wb_user_cabinet.id).pack())],
        ]

    wb_user_cabinet_original_id = wb_user_cabinet.id
    buttons.append([InlineKeyboardButton(text='Вернуться к списку кампаний',
                                         callback_data=\
                        callbacks.ChoiceAdvPaginator(wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                                                                                    page=1).pack())])


    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_advs_keyboard_with_paginator(wb_user_cabinet: WBUserCabinet, page: int, on_page: int):
    keyboard_buttons = []
    start_index = (page - 1) * on_page
    end_index = start_index + on_page
    wb_cabinet = wb_user_cabinet.wb_cabinet
    wb_user_cabinet_original_id = wb_user_cabinet.id
    # Добавляем кнопки для объявлений
    try:
         advs =  wb_cabinet.adv_settings
    except:
        pass
    for adv in advs[start_index:end_index]:
        button_text = adv.name
        callback_data = callbacks.Adv(action='select', adv_original_id=adv.id,
                                      wb_user_cabinet_original_id=wb_user_cabinet_original_id).pack()
        keyboard_buttons.append([InlineKeyboardButton(text=button_text,
                                                      callback_data=callback_data)])

    # Добавляем кнопки навигации
    if page > 1:
        prev_page = page - 1
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️",
                                                      callback_data=callbacks\
                 .ChoiceAdvPaginator(wb_user_cabinet_original_id = wb_user_cabinet_original_id
                 , page=prev_page).pack())])

    if len(advs) > end_index:
        next_page = page + 1
        keyboard_buttons.append([InlineKeyboardButton(text="➡️",
                                                      callback_data= callbacks
                                                      .ChoiceAdvPaginator(
                                                          wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                                                          page=next_page).pack())])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard



def add_app_token_or_delete_wb_user_cabinet(wb_user_cabinet:  app.my_types.WBUserCabinet):
    wb_user_cabinet_original_id = wb_user_cabinet.id
    buttons = [
        [InlineKeyboardButton(text='Добавить новый токен',
                              callback_data=callbacks.AddNewToken(wb_user_cabinet_original_id =
                                                                  wb_user_cabinet_original_id).pack())],
        [InlineKeyboardButton(text='Удалить магазин',
                              callback_data=callbacks.DeleteWbUserCabinet(wb_user_cabinet_original_id =
                                                                  wb_user_cabinet_original_id).pack())]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
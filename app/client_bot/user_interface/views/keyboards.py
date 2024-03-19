from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.modules.common_slaves.wildberries.models import WBUserCabinet, AdvSetting, KeywordSetting
from ...user_interface.views.callbacks import BudgetForCreatingAdv
import app
from ...user_interface.views import callbacks
from app.modules.common_slaves.wildberries.data_classes.adv import Adv
from ...user_interface.views.callbacks import TurnAdv
from .callbacks import Action
from app.utils.db.session_maker import get_async_session_maker
from ...utils import KeywordForKeyboard

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

    buttons = []
    buttons.append([InlineKeyboardButton(text='Контроль ключевых слов по кампании',
                              callback_data=callbacks.SettingKeywords(adv_original_id=adv_setting.id,
                                                                      type='by_adv').pack())])
    if adv_setting.bot_active:
        buttons.append(
        [InlineKeyboardButton(text='Отключить бота', callback_data=TurnAdv(action='off',
         adv_original_id=adv_setting.id,
        wb_user_cabinet_original_id =wb_user_cabinet.id).pack())])


    else:
        buttons.append(
            [InlineKeyboardButton(text='Включить бота',
                                  callback_data=TurnAdv(action='on',
                                   adv_original_id=adv_setting.id,
                                   wb_user_cabinet_original_id=wb_user_cabinet.id).pack())])

    wb_user_cabinet_original_id = wb_user_cabinet.id
    buttons.append([InlineKeyboardButton(text='Вернуться к списку кампаний',
                                         callback_data=\
                        callbacks.ChoiceAdvPaginator(wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                                                                                    page=1).pack())])


    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_advs_keyboard_with_paginator(wb_user_cabinet_original_id: int,
                                     adv_settings: list[AdvSetting],
                                     page: int, on_page: int):
    keyboard_buttons = []
    start_index = (page - 1) * on_page
    end_index = start_index + on_page
    for adv in adv_settings[start_index:end_index]:
        button_text = adv.name + ' (Бот включен)' if adv.bot_active else adv.name + ' (Бот отключен)'
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

    if len(adv_settings) > end_index:
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


def get_keywords_setting_keyboard(keywords: list[KeywordForKeyboard], adv_setting: AdvSetting,
                                  wb_user_cabinet_original_id: int,
                                   adv_choice_last_page,
                                  page=1):
    on_page = 5
    start_index = (page - 1) * on_page
    end_index = start_index + on_page

    bottoms = []
    for keyword in keywords[start_index:end_index]:
        clicks = keyword.statistic.clicks
        views = keyword.statistic.views
        ctr = keyword.statistic.ctr
        if keyword.keyword_settings.hard_status == 0:
            hard_status = 'ЧС'
        elif keyword.keyword_settings.hard_status == 1:
            hard_status = 'Авто'
        else:
            hard_status = 'БС'

        turn_on = '✅' if keyword.turn_on else '❌'
        text = f'{keyword.text} {turn_on}({hard_status}){clicks}/{views}/{round(ctr *100, 0)}% '


        inline_keyboard = [InlineKeyboardButton(text= text,
                                                callback_data=callbacks.SettingKeyword(
                                                keyword_setting_original_id = keyword.keyword_settings.id,
                                                ).pack())]
        bottoms.append(inline_keyboard)
    if page > 1:
        prev_page = page - 1
        bottoms.append([InlineKeyboardButton(text="⬅️",
                                             callback_data=callbacks.SettingKeywords(
                                                 adv_original_id=adv_setting.id,
                                                 type='by_adv',
                                                 page=prev_page).pack())])

    if len(keywords) > end_index:
        next_page = page + 1
        bottoms.append([InlineKeyboardButton(text="➡️",
                                             callback_data=callbacks.SettingKeywords(
                                                adv_original_id=adv_setting.id,
                                                type='by_adv',
                                                page=next_page).pack())])

    bottoms.append([InlineKeyboardButton(text='Вернуться к списку кампаний',
                                         callback_data=callbacks.ChoiceAdvPaginator(
                                             wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                                             page=adv_choice_last_page).pack())])
    keyboard = InlineKeyboardMarkup(inline_keyboard=bottoms)
    return keyboard



def get_keyword_setting_keyboard(keyword: KeywordSetting, adv_setting: AdvSetting, return_to: str = 'by_adv',):
    buttoms = []
    if keyword.hard_status in [0, 1]:
        buttom = [InlineKeyboardButton(text='В белый список',
                                       callback_data=callbacks.ChangeKeywordHardStatus(
                                           new_hard_status=2,
                                           keyword_setting_original_id=keyword.id).pack())]
        buttoms.append(buttom)

    if keyword.hard_status in [0, 2]:
        buttom = [InlineKeyboardButton(text='В авто',
                                       callback_data=callbacks.ChangeKeywordHardStatus(
                                           new_hard_status=1,
                                           keyword_setting_original_id=keyword.id).pack())]
        buttoms.append(buttom)

    if keyword.hard_status in [1, 2]:
        buttom = [InlineKeyboardButton(text='В черный список',
                                       callback_data=callbacks.ChangeKeywordHardStatus(
                                           new_hard_status=0,
                                           keyword_setting_original_id=keyword.id).pack())]
        buttoms.append(buttom)

    buttoms.append([InlineKeyboardButton(text='Вернуться к списку ключевых слов',
                                         callback_data=callbacks.SettingKeywords(
                                             adv_original_id=adv_setting.id,
                                             type=return_to).pack())])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttoms)
    return keyboard




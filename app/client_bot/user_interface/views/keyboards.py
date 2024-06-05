import asyncio
import datetime
from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.modules.common_slaves.wildberries.data_classes.adv import Adv
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.client_bot.const import BLACK_LIST, AUTO_MODE, WHITE_LIST, TURN_OFF
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker

from ...user_interface.views import callbacks
from ...user_interface.views.callbacks import BudgetForCreatingAdv, TurnAdv
from .callbacks import Action

if TYPE_CHECKING:
    from ...utils import KeywordForKeyboard

sm = get_async_session_maker


def get_shop_keyboard(all_shops: list[WBUserCabinet]):
    # Создаем список для строк кнопок
    keyboard_buttons = []

    for wb_user_cabinet in all_shops:
        shop_name = wb_user_cabinet.name
        wb_user_cabinet_original_id = wb_user_cabinet.id
        button = InlineKeyboardButton(
            text=shop_name,
            callback_data=callbacks.Shop(
                action=Action.select,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id).pack()
        )
        # Добавляем кнопку в список строк кнопок
        keyboard_buttons.append([button])  # Каждая кнопка в своем списке, т.е. каждая в новой строке
    button = InlineKeyboardButton(text='Добавить магазин', callback_data=callbacks.ShopNew().pack())

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
    loop = asyncio.get_event_loop()
    for adv in adv_settings[start_index:end_index]:
        check_last_24_hours = loop.run_until_complete(redis_manager.check_last_24_hours(adv.id))
        check_text = '✅' if check_last_24_hours else '❓'
        button_text = f'{check_text} {adv.name} (Бот включен)' if adv.bot_active else f'{adv.name} (Бот отключен)'
        button_text += f' Статус: {adv.active_status}'
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

    button = InlineKeyboardButton(
        text='Вернуться к меню магазина',
        callback_data=callbacks.Shop(
            action=Action.select,
            wb_user_cabinet_original_id=wb_user_cabinet_original_id).pack(),
    )

    keyboard_buttons.append([button])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)



def add_app_token_or_delete_wb_user_cabinet(wb_user_cabinet:  WBUserCabinet):
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


def get_keywords_setting_keyboard(keywords: list['KeywordForKeyboard'], adv_setting: AdvSetting,
                                  adv_choice_last_page,
                                  wb_user_cabinet_original_id: int,
                                   page):
    on_page = 12
    start_index = (page - 1) * on_page
    end_index = start_index + on_page

    bottoms = []
    for keyword in keywords[start_index:end_index]:
        clicks = keyword.statistic.clicks
        views = keyword.statistic.views
        ctr = keyword.statistic.ctr
        if keyword.keyword_settings.hard_status == BLACK_LIST:
            hard_status = 'Не рел.фраза'
        elif keyword.keyword_settings.hard_status == AUTO_MODE:
            hard_status = 'Авто'
        elif keyword.keyword_settings.hard_status == TURN_OFF:
            hard_status = 'Откл.'
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


def get_keyword_setting_keyboard(
    keyword: KeywordSetting,
    adv_setting: AdvSetting,
    auto_block_status,
    page,
    return_to: str = 'by_adv',
):
    buttons = []
    if keyword.hard_status in [BLACK_LIST, AUTO_MODE, TURN_OFF]:
        button = [InlineKeyboardButton(text='В белый список',
                                       callback_data=callbacks.ChangeKeywordHardStatus(
                                           new_hard_status=WHITE_LIST,
                                           keyword_setting_original_id=keyword.id).pack())]
        buttons.append(button)

    if auto_block_status and keyword.hard_status == AUTO_MODE:
        button = [InlineKeyboardButton(text='Тестировать дальше',
                                       callback_data=callbacks.ChangeKeywordHardStatus(
                                           new_hard_status=-AUTO_MODE,
                                           keyword_setting_original_id=keyword.id).pack())]

        buttons.append(button)

    if keyword.hard_status in [BLACK_LIST, WHITE_LIST, TURN_OFF]:
        button = [InlineKeyboardButton(text='В авто',
                                       callback_data=callbacks.ChangeKeywordHardStatus(
                                           new_hard_status=AUTO_MODE,
                                           keyword_setting_original_id=keyword.id).pack())]
        buttons.append(button)




    if keyword.hard_status in [AUTO_MODE, WHITE_LIST, BLACK_LIST]:

        bottom = [InlineKeyboardButton(text='Отключить (релевантная фраза)',
                                        callback_data=callbacks.ChangeKeywordHardStatus(
                                            new_hard_status=TURN_OFF,
                                            keyword_setting_original_id=keyword.id).pack())]
        buttons.append(bottom)


        button = [InlineKeyboardButton(text='В список не релевантных фраз',
                                       callback_data=callbacks.ChangeKeywordHardStatus(
                                           new_hard_status=BLACK_LIST,
                                           keyword_setting_original_id=keyword.id).pack())]
        buttons.append(button)

    if keyword.hard_status == TURN_OFF:
        button = [InlineKeyboardButton(text='В список не релевантных фраз',
                                       callback_data=callbacks.ChangeKeywordHardStatus(
                                           new_hard_status=BLACK_LIST,
                                           keyword_setting_original_id=keyword.id).pack())]
        buttons.append(button)


    buttons.append([InlineKeyboardButton(text='Вернуться к списку ключевых слов',
                                             callback_data=callbacks.SettingKeywords(
                                             adv_original_id=adv_setting.id,
                                             type=return_to,
                                             page=page,
                                             ).pack())])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_subscribe_keyboard():
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(text='Подписаться', url='https://t.me/auto_wb_master')
    builder.row(button)
    return builder.as_markup()


def get_ref_program_keyboard():
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(text='Создать новую реф.ссылку', callback_data = callbacks.RefProgram(
        action='new').pack())
    builder.row(button)
    button = InlineKeyboardButton(text='Существующие ссылки и их имена', callback_data= callbacks.RefProgram(
        action='select').pack())
    builder.row(button)
    return builder.as_markup()


def get_return_for_your_ref_links():
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(text = 'Назад', callback_data= callbacks.RefProgram(
        action='return').pack())

    builder.row(button)
    return builder.as_markup()


def get_shop_menu_keyboard(
    wb_user_cabinet:  WBUserCabinet,
    wb_cabinet_original_id: int,
    price_for_month: int,
    bonus_days: int,
):
    wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
    expiration_time: datetime.datetime = wb_cabinet.expiration_time
    demo: bool = wb_cabinet.demo
    now = datetime.datetime.now()

    builder = InlineKeyboardBuilder()

    if expiration_time > now:
        button = InlineKeyboardButton(
            text='Настройка рекламы',
            callback_data=callbacks.ChoiceAdvPaginator(
                wb_user_cabinet_original_id=wb_user_cabinet.id, page=1).pack(),
        )
        builder.row(button)
    if demo:
        button = InlineKeyboardButton(
            text='Продлить и получить бонус',
            callback_data=callbacks.OrderSubscribe(
                period_days=30 + bonus_days,
                price=price_for_month,
                wb_cabinet_original_id=wb_cabinet_original_id
            ).pack()
        )
        builder.row(button)
    else:
        button = InlineKeyboardButton(
            text='Продлить подписку',
            callback_data=callbacks.OrderSubscribe(
                period_days=30,
                price=price_for_month,
                wb_cabinet_original_id=wb_cabinet_original_id
            ).pack()
        )
        builder.row(button)

    button = InlineKeyboardButton(
        text='Вернуться к списку магазинов',
        callback_data=callbacks.Start().pack(),
    )
    builder.row(button)
    return builder.as_markup()


def get_payment_keyboard(price_for_month: int, period_days, bonus_days: int, wb_cabinet_original_id):
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(
        text='Продлить подписку',
        callback_data=callbacks.OrderSubscribe(
            period_days=period_days + bonus_days,
            price=price_for_month,
            wb_cabinet_original_id=wb_cabinet_original_id).pack(),
    )
    builder.row(button)

    button = InlineKeyboardButton(text='К списку магазинов', callback_data=callbacks.Start().pack())

    builder.row(button)

    return builder.as_markup()

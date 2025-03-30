from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import Action
from app.client_bot.user_interface.views.get_main_text import get_main_text
from app.modules.cabinet_bonus_manager.callbacks import AdminBonus
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.client_bot import const


class ShopChoice(TextWithKeyboard):
    parse_mode = ParseMode.HTML

    def __init__(self, bot: Bot, chat_id: int,
                 all_shops: list[WBUserCabinet]):
        super().__init__(bot, chat_id)
        self.__all_shops = all_shops
        self.user_telegram_id = chat_id


    @property
    def text(self) -> str:
        return get_main_text(self.user_telegram_id)

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return get_shop_keyboard(self.__all_shops, self.user_telegram_id)


def get_shop_keyboard(all_shops: list[WBUserCabinet], user_telegram_id) -> InlineKeyboardMarkup:
    # Создаем список для строк кнопок
    keyboard_buttons = []
    
    # Добавляем кнопку админ-панели в самый верх, если пользователь - администратор
    if user_telegram_id in const.ADMINS:
        admin_button = InlineKeyboardButton(
            text='Панель администратора', 
            callback_data=AdminBonus(action="menu").pack()
        )
        keyboard_buttons.append([admin_button])
    
    button = InlineKeyboardButton(text='Избранные кампании', callback_data=callbacks.ShowFavorites().pack())
    keyboard_buttons.append([button])

    for wb_user_cabinet in all_shops:
        shop_name = wb_user_cabinet.name
        wb_user_cabinet_original_id: int = wb_user_cabinet.id
        button = InlineKeyboardButton(text=shop_name, callback_data=callbacks \
                                      .Shop(action=Action.select,
                                            wb_user_cabinet_original_id=wb_user_cabinet_original_id).pack())
        # Добавляем кнопку в список строк кнопок
        keyboard_buttons.append([button])  # Каждая кнопка в своем списке, т.е. каждая в новой строке
    
    button = InlineKeyboardButton(text='Добавить магазин', callback_data=callbacks.ShopNew().pack())
    keyboard_buttons.append([button])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard

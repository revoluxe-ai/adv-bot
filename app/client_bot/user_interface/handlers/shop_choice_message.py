from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views import keyboards, callbacks
from app.client_bot.user_interface.views.callbacks import Action
from app.client_bot.user_interface.views.get_main_text import get_main_text
from app.modules.common_slaves.wildberries.models import WBUserCabinet


class ShopChoice(TextWithKeyboard):
    parse_mode = ParseMode.HTML

    def __init__(self, bot:Bot, chat_id: int,
                 all_shops: list[WBUserCabinet]):
        super().__init__(bot, chat_id)
        self.__all_shops = all_shops
        self.user_telegram_id = chat_id




    @property
    def text(self):
        return get_main_text(self.user_telegram_id)


    @property
    def keyboard(self):
        return get_shop_keyboard(self.__all_shops)






def get_shop_keyboard(all_shops: list[WBUserCabinet]):
    # Создаем список для строк кнопок
    keyboard_buttons = []
    button = InlineKeyboardButton(text='Избранные кампании', callback_data=callbacks.ShowFavorites().pack())
    keyboard_buttons.append([button])

    for wb_user_cabinet in all_shops:
        shop_name = wb_user_cabinet.name
        wb_user_cabinet_original_id = wb_user_cabinet.id
        button = InlineKeyboardButton(text=shop_name, callback_data=callbacks \
                                      .Shop(action=Action.select,
                                            wb_user_cabinet_original_id=wb_user_cabinet_original_id).pack())
        # Добавляем кнопку в список строк кнопок
        keyboard_buttons.append([button])  # Каждая кнопка в своем списке, т.е. каждая в новой строке
    button = InlineKeyboardButton(text='Добавить магазин', callback_data=callbacks.ShopNew().pack())

    keyboard_buttons.append([button])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard






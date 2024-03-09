from aiogram.types import FSInputFile
from typing import Union

from app.db.associations import WBUserCabinet
from ..message_templates.templates import (TextWithKeyboard,
                                                                        Text,
                                                                        TextWithKeyboardPagination)
from app.telegram_bot.redis_manager import LastMessage
from . import keyboards
from aiogram import Bot
from aiogram.types import Message
from app.wildberries.data_classes.adv import Adv as WbAdv
import logging
import app
from app.wildberries.models import AdvSetting, WBCabinet

logger = logging.getLogger(__name__)



class ShopChoice(TextWithKeyboard):
    def __init__(self, bot:Bot, last_message: Union[LastMessage, None, Message],
                 all_shops: list[app.my_types.WBUserCabinet]):
        chat_id = last_message.chat.id
        super().__init__(bot, last_message, chat_id)
        self.__all_shops = all_shops

    @property
    def text(self):
        return 'Выберете магазин (кабинет) или добавьте новый:'

    @property
    def keyboard(self):
        return keyboards.get_shop_keyboard(self.__all_shops)



class ShopNameGet(Text):
    def __init__(self, bot: Bot, last_message: Union[LastMessage, None, Message], chat_id: int):
        super().__init__(bot, last_message, chat_id)

    @property
    def text(self):
        return 'Введите название магазина (кабинета):'



class ShopApiGet(Text):
    text = 'Введите API ключ магазина (кабинета):'


    @property
    def image(self):
        photo_path = 'wb/keyword_async_ml_updater/bot/images/api_setting.png'
        photo = FSInputFile(photo_path)
        return photo


class ShopAddedSuccess(Text):

    def __init__(self, bot: Bot, last_message: Union[LastMessage, None, Message], chat_id: int, cabinet_name: str):
        super().__init__(bot, last_message, chat_id)
        self.__cabinet_name = cabinet_name

    @property
    def text(self):
        return f'Магазин {self.__cabinet_name} успешно добавлен!'





class GetApiForrbidenError(Text):
    text = ('Ключ API введен не верно или недостаточно прав для работы с рекламой.'
            ' Пожалуйста, создайте новый API-ключ и с нужными правами и пришлите его снова:')


class GetCardsApiError(Text):
    text = ('Ошибка настройки прав: нет доступа в контенту. Пожалуйста, создайте новый API-ключ с требуемыми правами и попробуйте снова.')


class AdvCompanyChoicing(TextWithKeyboardPagination):
    def __init__(self, bot: Bot, last_message: Union[LastMessage, None, Message],
                  chat_id: int, wb_user_cabinet: WBUserCabinet,
                 page: int = 1):
        super().__init__(bot, last_message, chat_id)
        self._wb_user_cabinet = wb_user_cabinet
        self._page = page

    @property
    def text(self):
        return 'Выберете рекламную кампанию:'

    @property
    def keyboard(self):
        return keyboards.get_advs_keyboard_with_paginator(self._wb_user_cabinet,
                                                          self._page,
                                                          self.on_page)


    @property
    def on_page(self):
        return 5


class ShopUpdateInfo(Text):


    @property
    def text(self):
        return f'Обновление данных для магазина, немного подождите...'



class AdvSettingMenu(TextWithKeyboard):
    def __init__(self, bot: Bot, last_message: Union[LastMessage, None, Message],
                 wb_user_cabinet: WBUserCabinet,
                 adv: AdvSetting,
                 chat_id: int):
        super().__init__(bot, last_message, chat_id)
        self.adv = adv
        self.wb_user_cabinet = wb_user_cabinet

    @property
    def text(self):
        return f'Кампания: {self.adv.name}'

    @property
    def keyboard(self):
        return keyboards.get_adv_setting_keyboard(self.wb_user_cabinet,  self.adv)


class CabinetExistsForUser(Text):
    text = 'Этот кабинет уже был добавлен вам ранее. Сейчас я предоставлю вам его...'


class NotValideToken(Text):
    text = 'Вы ввели что-то не то. Попробуйте снова:'


class ApiForrbidenError(Text):
    def __init__(self, bot: Bot, last_message: Union[LastMessage, None, Message],
                 chat_id: int, wb_user_cabinet: app.my_types.WBUserCabinet):
        super().__init__(bot, last_message, chat_id)
        self.__wb_user_cabinet = wb_user_cabinet


    text = ('Ошибка настройки прав: нет доступа в рекламе. Пожалуйста, '
            'создайте новый API-ключ с требуемыми правами и добавьте кабинет снова. '
            'Все ваши настройки будут сохранены')
    @property
    def keyword(self):
        return (keyboards.add_app_api_or_delete_user_wb_cabinet
                (self.__wb_user_cabinet_original_id))


class AddNewTokenGet(Text):
    def __init__(self, bot: Bot, last_message: Union[LastMessage, None, Message], chat_id: int,
                 wb_user_cabinet: app.my_types.WBUserCabinet):

        self.__wb_user_cabinet = wb_user_cabinet
        super().__init__(bot, last_message, chat_id)

    @property
    def text(self):
        return  f'Пришлите новый Api ключ дла магазина (кабинета) {self.__wb_user_cabinet.name}:'


class GetMinCtr(Text):
    def __init__(self, bot: Bot, last_message: Union[LastMessage, None, Message], chat_id: int,
                 adv: AdvSetting):
        self.__adv = adv
        super().__init__(bot, last_message, chat_id)

    @property
    def text(self):
        return f'Введите новое значение минимального CTR для кампании {self.__adv.name}:'


class CabinetExistsInSystem(Text):

    text = 'Этот кабинет уже существует в системе, мы его добавим вам...'


class WrongMinCTR:

    text = 'Минимальный CTR должен быть числом от 0 до 100. Попробуйте снова:'


class MinCTRChanged(Text):
    text = 'Минимальный CTR успешно изменен!'


class CabinetNameTooLong(Text):
    text = 'Название кабинета слишком длинное. Попробуйте снова(не более 50 символов):'
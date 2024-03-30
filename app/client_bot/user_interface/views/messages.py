from aiogram.types import FSInputFile

from app.modules.common_slaves.wildberries.models import (WBUserCabinet,
                                                          AdvSetting,
                                                          KeywordSetting)
from ..message_templates.templates import (TextWithKeyboard,
                                           Text,
                                           TextWithImage,
                                           TextWithKeyboardPagination,
                                           TextWithKeyboarAndImage)

from . import keyboards
from aiogram import Bot

import logging
import app
from ...utils import KeywordForKeyboard

logger = logging.getLogger(__name__)


class ShopChoice(TextWithKeyboard):
    def __init__(self, bot:Bot, chat_id: int,
                 all_shops: list[app.my_types.WBUserCabinet]):
        super().__init__(bot, chat_id)
        self.__all_shops = all_shops


    @property
    def text(self):
        return ('Вас приветствует самый продвинутый бот на рынке, созданный для управления '
                'рекламными кампаниями на Wildberries. \n'
                'Бот умеет автоматически блокировать не целевые запросы, а обновление'
                ' кампаний происходит в режиме реального времени\n\n'
                'Что это дает: \n'
                '1. Увеличение конверсии на 30-50% \n'
                '2. Снижение стоимости клика на 20-30% \n'
                '3. Возможность создавать множество кампаний и удобно ими управлять\n '
                'Как итог: с помощью этого бота вы получаете неоспоримое преимущество перед конкурентами!\n\n'
                
                'В настоящий момент бот проходит бета-тестирование, поэтому вы можете пользоваться его функционалом'
                'без ограничений совершенно бесплатно.\n\n'
                'Канал бота - @auto_wb_master\n'
                'Связь с разработчиком: @skyline360_1\n\n'
                
                'Внимание! Сейчас бот работает только с автоматическими рекламными кампаниями'
                'с включенным Бустом и отключенными показами в Карточках\n\n'
                 
                'Выберите магазин (кабинет) или добавьте новый:')

    @property
    def keyboard(self):
        return keyboards.get_shop_keyboard(self.__all_shops)



class ShopNameGet(Text):
    def __init__(self, bot: Bot, chat_id: int):
        super().__init__(bot,  chat_id)

    @property
    def text(self):
        return 'Введите название магазина (кабинета):'






class ShopAddedSuccess(Text):

    def __init__(self, bot: Bot, chat_id, cabinet_name: str):
        super().__init__(bot, chat_id)
        self.__cabinet_name = cabinet_name

    @property
    def text(self):
        return f'Магазин {self.__cabinet_name} успешно добавлен, идет обновление данных...'





class GetApiForrbidenError(Text):
    text = ('Ключ API введен не верно или недостаточно прав для работы с рекламой.'
            ' Пожалуйста, создайте новый API-ключ и с нужными правами и пришлите его снова:')


class GetCardsApiError(Text):
    text = ('Ошибка настройки прав: нет доступа в контенту. Пожалуйста, создайте новый API-ключ с требуемыми правами и попробуйте снова.')


class AdvCompanyChoicing(TextWithKeyboardPagination):
    def __init__(self, bot: Bot,
                  chat_id: int, wb_user_cabinet_original_id: int,
                 adv_settings: list[AdvSetting],
                 page: int = 1):
        super().__init__(bot, chat_id)
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._adv_settings = adv_settings
        self._page = page

    @property
    def text(self):
        return ('Выберите рекламную кампанию для настройки или проверки. \n'
                '✅ - кампания проверялась в течение последних 24 часов\n'
                 '❓ - кампания не проверялась в течение последних 24 часов\n')

    @property
    def keyboard(self):
        return keyboards.get_advs_keyboard_with_paginator(self._wb_user_cabinet_original_id,
                                                          self._adv_settings,
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
    def __init__(self, bot: Bot,
                 chat_id: int,
                 wb_user_cabinet: WBUserCabinet,
                 adv: AdvSetting):
        super().__init__(bot, chat_id)
        self.adv = adv
        self.wb_user_cabinet = wb_user_cabinet

    @property
    def text(self):
        return f'Кампания: {self.adv.name}'

    @property
    def keyboard(self):
        return keyboards.get_adv_setting_keyboard(self.wb_user_cabinet,  self.adv)


class CabinetNameExists(Text):
    text = 'Кабинет с таким именем уже существует, введите другое имя для кабинета:'


class CabinetExistsForUser(Text):
    text = "Этот кабинет уже был добавлен вам ранее. Сейчас я предоставлю вам его..."





class NotValideToken(Text):
    text = 'Вы ввели что-то не то. Попробуйте снова:'


class ApiForrbidenError(Text):
    def __init__(self, bot: Bot, chat_id, wb_user_cabinet: app.my_types.WBUserCabinet):
        super().__init__(bot, chat_id)
        self.__wb_user_cabinet = wb_user_cabinet


    text = ('Ошибка настройки прав: нет доступа в рекламе. Пожалуйста, '
            'создайте новый API-ключ с требуемыми правами и добавьте кабинет снова. '
            'Все ваши настройки будут сохранены')



class AddNewTokenGet(TextWithImage):
    def __init__(self, bot: Bot, chat_id,
                 cabinet_name: str):

        self.__cabinet_name  = cabinet_name
        super().__init__(bot, chat_id)

    @property
    def text(self):
        return  (f'Пришлите новый Api ключ дла магазина (кабинета) {self.__cabinet_name}.\n'
                 'Для работы бота нужны права Контент (анализ карточек для управления ключами) и Продвижение ('
                 'загрузка рекламной статистики и управление ключевыми словами)')



    @property
    def image(self):
        photo_path = 'app/client_bot/images/api_setting.png'
        photo = FSInputFile(photo_path)
        return photo



class GetMinCtr(Text):
    def __init__(self, bot: Bot,  chat_id: int,
                 adv: AdvSetting):
        self.__adv = adv
        super().__init__(bot, chat_id)

    @property
    def text(self):
        return f'Введите новое значение минимального CTR для кампании {self.__adv.name}:'


class CabinetExistsInSystem(Text):

    text = 'Этот кабинет уже существует в системе, мы его добавим вам...'


class WrongMinCTR(Text):

    text = 'Минимальный CTR должен быть числом от 0 до 100. Попробуйте снова:'


class MinCTRChanged(Text):
    text = 'Минимальный CTR успешно изменен!'


class CabinetNameTooLong(Text):
    text = 'Название кабинета слишком длинное. Попробуйте снова(не более 50 символов):'


class AdvKeywordsSetting(TextWithKeyboarAndImage):
    def __init__(self, bot: Bot, chat_id,
                 keywords: list[KeywordForKeyboard], adv_setting: AdvSetting, wb_user_cabinet_original_id,
                 adv_choice_last_page,
                 image: str, page):
        super().__init__(bot, chat_id)
        self._keywords = keywords
        self._adv_setting = adv_setting
        self._page = page
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._adv_choice_last_page = adv_choice_last_page
        self._image = image

    @property
    def text(self):
         if not self._keywords:
             return 'Ключевые слова еще не получены, зайдите позже'
         else:
            text =   (

                     'Название кампании: ' + str(self._adv_setting.name) + '\n'
                      'ID кампании: ' + str(self._adv_setting.adv_id) + '\n'                                                  
                     'Статистика и настройка ключевых слов \n'
                     'Расшифровка: \n'
                     '✅  - ключевое слово активно \n'
                     '❌  - ключевое слово не активно \n'
                     ' БС - ключевое слово в белом списке \n'
                     'ЧС   - ключевое слово в черном списке \n'
                     'Авто  - ключевое слово на автоуправлении \n'
                     'Информация перед ключевым словом: клики/показы/CTR \n')
            return text

    @property
    def image(self):
        return self._image

    @property
    def keyboard(self):
        return keyboards.get_keywords_setting_keyboard(self._keywords, self._adv_setting,
                                                       self._adv_choice_last_page,
                                                       self._wb_user_cabinet_original_id,
                                                       self._page)


class KeywordSettingMessage(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int,
                 keyword_setting: KeywordSetting, adv_setting: AdvSetting, last_page: int):
        super().__init__(bot, chat_id)
        self._keyword_setting = keyword_setting
        self._adv_setting = adv_setting
        self._page = last_page

    @property
    def text(self):
        return f'Статистика и настройка ключевого слова: {self._keyword_setting.text}'

    @property
    def keyboard(self):
        return keyboards.get_keyword_setting_keyboard(self._keyword_setting, self._adv_setting, self._page)


class GetNameOfNewAdvCompany(Text):
    text = 'Введите название новой рекламной кампании, максимум 128 символов:'


class TooLongNameOfNewAdvCompany(Text):
    text = 'Название кампании слишком длинное. Попробуйте снова, должно быть не более 128 символов:'


class GetNmidOfNewAdvCompany(Text):
    text = ('Какие товары добавить в кампанию? Вы можете указать несколько товаров'
            'В качестве разделителя можете использовать пробел, запятую, точку с запятой или точку.'
            'Указать можно артикулы WB или ваши артикулы. По возможности не создавайте РК более, '
            'чем на один товар:')


class NotFoundNmidOfNewAdvCompany(Text):
    def __init__(self, bot: Bot, chat_id: int, not_found_items: list[str]):
        self.__not_found_items = not_found_items
        super().__init__(bot, chat_id)

    @property
    def text(self):
        return f'Товары с идентификаторами {", ".join(self.__not_found_items)} не найдены. Попробуйте снова:'



import asyncio
import datetime
from aiogram.utils import deep_linking
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from app.modules.common_slaves.wildberries.models import (WBUserCabinet,
                                                          AdvSetting,
                                                          KeywordSetting, WBCabinet)
from app.utils.suffixes import get_day_suffix


from ..message_templates.templates import (TextWithKeyboard,
                                           Text,
                                           TextWithImage,
                                           TextWithKeyboardPagination,
                                           TextWithKeyboardAndImage)

from . import keyboards, db_manager
from aiogram import Bot

import logging
import app
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...utils import KeywordForKeyboard
from .import texts
logger = logging.getLogger(__name__)



_sm = get_async_session_maker()

class MainMenu(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id: int, user_original_id: int):
        super().__init__(bot, chat_id)
        self.__user_original_id = user_original_id


    @property
    def text(self):
        return texts.get_main_menu_text(self.__user_original_id)







class ShopChoice(TextWithKeyboard):
    def __init__(self, bot:Bot, chat_id: int,
                 all_shops: list[WBUserCabinet]):
        super().__init__(bot, chat_id)
        self.__all_shops = all_shops


    @property
    def text(self):
        return (
                
                'Бот разрабатывался и продолжает разрабатываться '
                'с целью сделать продвижение на Wildberries максимально эффективным.\n\n'
                
                'Для использования функционала бота вы должны быть подписаны на канал поддержки - @auto_wb_master\n\n'
                 
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
    
    async def __call__(self, state: FSMContext):

        await state.update_data(last_wb_user_cabinet_original_id=self._wb_user_cabinet_original_id)
        await state.update_data(last_wb_user_cabinet_page=self._page) #последняя страница выбора рк
        return await super().__call__()

    @staticmethod
    async def get_state_data(state: FSMContext)->(int, int):
        data = await state.get_data()
        last_wb_user_cabinet_original_id = data.get('last_wb_user_cabinet_original_id')
        last_wb_user_cabinet_page = data.get('last_wb_user_cabinet_page')
        return last_wb_user_cabinet_original_id, last_wb_user_cabinet_page


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
    def __init__(self, bot: Bot, chat_id, wb_user_cabinet: WBUserCabinet):
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

        self._image = 'app/client_bot/images/api_setting.png'

    @property
    def text(self):
        return  (f'Пришлите новый Api ключ дла магазина (кабинета) {self.__cabinet_name}.\n'
                 'Для работы бота нужны права Контент (анализ карточек для управления ключами) и Продвижение ('
                 'загрузка рекламной статистики и управление ключевыми словами)')


    @property
    def image(self):
        return self._image


    @image.setter
    def image(self, value):
        self._image = value



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


class AdvKeywordsSetting(TextWithKeyboardAndImage):
    def __init__(self, bot: Bot, chat_id,
                 keywords: list['KeywordForKeyboard'], adv_setting: AdvSetting, wb_user_cabinet_original_id,
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

    @image.setter
    def image(self, value):
        self._image = value

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


class LongTimeOperation(Text):
    text = 'Операция может занять некоторые время, пожалуйста, подождите...'



class NeedSubscribe(TextWithKeyboard):
    text = ('Для использования функций вы должны быть подписаны на канал службы поддержки')


    @property
    def keyboard(self):
        return keyboards.get_subscribe_keyboard()


class RefProgram(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id: int):
        self._user_telegram_id = chat_id
        super().__init__(bot, chat_id)

    async def __call__(self):
        ref_statistic = await db_manager.get_ref_statistic(self._user_telegram_id)
        self._ref_statistic = ref_statistic
        await super().__call__()

    @property
    def text(self):
        if not self._ref_statistic:
            return "У вас еще нет реферальных ссылок. Создайте новую ссылку по кнопке ниже: "

        # Заголовок таблицы и разделитель
        header = f"{'Имя реф.ссылки':<15} | {'Количество рефералов':>20} | {'Сумма платежей':>10}"
        divider = "-----------------------------------------------------------------------------"

        # Формирование строк таблицы
        rows = [f"{stat.name:<15}             |    {stat.referrals_count:>20}                 |  {stat.total_payments:>15}" for stat in self._ref_statistic]

        # Сборка итогового текста
        table = [header, divider] + rows
        return '\n'.join(table)


    keyboard = keyboards.get_ref_program_keyboard()


class RefLinkGetName(Text):
    text = 'Введите название для новой реферальной ссылки. Название будете видеть только вы:'


class RefLinkNameTooLong(Text):
    text = 'Название ссылки слишком длинное, должно быть не больше 30 символов. Попробуйте снова:'


class RefLinkNameAlreadyExists(Text):
    text = 'Такое название ссылки уже существует. Попробуйте снова:'


class RefLinkCreated(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id: int, ref_link: RefLink):
        self._ref_link = ref_link
        self._bot = bot
        super().__init__(bot, chat_id)


    async def __call__(self):
        self._link = await deep_linking.create_start_link(self._bot, str(self._ref_link.id))
        await super().__call__()

    @property
    def text(self):
        return (f'Ссылка {self._ref_link.name} успешно создана. \n\n' 
               f'Вот ссылка, по которой вы можете приглашать пользователей: '
                f'{self._link}')


    keyboard = keyboards.get_return_for_your_ref_links()



class RefProgramSelect(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id: int):
        self._user_telegram_id = chat_id
        super().__init__(bot, chat_id)



    async def __call__(self):
        ref_links = await db_manager.get_ref_names_and_links(self._user_telegram_id, self.bot)
        self._ref_links = ref_links
        await super().__call__()


    @property
    def text(self):
        text = 'Ваши реф.ссылки:\n\n'
        for ref in self._ref_links:
            text += f'{ref.name}: {ref.link}\n'
        return text



    keyboard = keyboards.get_return_for_your_ref_links()


class ShopMenu(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id: int, state: FSMContext, wb_user_cabinet_original_id: int):
       self._state = state
       self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
       self._price_for_month = 4900
       super().__init__(bot, chat_id)

    async def __call__(self):
        async with _sm() as session:
            stmt = select(WBUserCabinet)\
                 .options(joinedload(WBUserCabinet.wb_cabinet))\
                .filter(WBUserCabinet.id == self._wb_user_cabinet_original_id)
            result = await session.execute(stmt)
            self._wb_user_cabinet: WBUserCabinet = result.scalar_one()
            self._wb_cabinet: WBCabinet = self._wb_user_cabinet.wb_cabinet
        self._now = datetime.datetime.now()
        self._expiration_time: datetime.datetime = self._wb_cabinet.expiration_time
        self._expiration_time_str = self._expiration_time.strftime('%d-%m-%Y-%H:%M')
        self.days_left = (self._expiration_time - self._now).days + 1
        self.bonus_days = self.days_left * 2


        await super().__call__()

    @property
    def text(self):

        text = f'Магазин: {self._wb_user_cabinet.name}\n'


        if self._wb_cabinet.demo and self._expiration_time> self._now:
            text += ('Для этого магазина включен демо-режим. Вам доступны все опции и сервисы до '
                         f"""{self._expiration_time_str} \n"""
                     "После этого дальнейшее использование бота для данного магазина станет платным. \n"
                     f'Стоимость месячной подписки составляет {self._price_for_month} рублей для одного магазина.\n'
                     'После оплаты услуга считается оказанной, возврат средств не производится. '
                     'Если вы оплатите подписку до конца демо-периода, то мы компенсируем оставшееся'
                     f' время демо-периода в двойном размере ( итого + {get_day_suffix(self.bonus_days)}) ')
        elif not self._wb_cabinet.demo and self._expiration_time > self._now:
            text += (f'Тариф магазина оплачен до  {self._expiration_time_str}\n'
                     f'Стоимость месячной подписки составляет {self._price_for_month} рублей для одного магазина.\n'
                     'После оплаты услуга считается оказанной, возврат средств не производится. ')


        elif self._expiration_time < self._now:
            text += 'Тариф магазина не оплачен\n'

        return text

    @property
    def keyboard(self):
        return keyboards.get_shop_menu_keyboard(self._wb_user_cabinet,
                                                price_for_month=self._price_for_month, bonus_days=self.bonus_days)


class OrderSubscribe(Text):

    text = "Заказ на подписку получен, для оплаты свяжитесь с администратором бота @skyline360_1"



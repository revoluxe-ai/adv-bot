import datetime
import re

import aiogram
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import NoResultFound
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.models import (WBItemPosition, WBToken)
from app.modules.wb_adv_updater import data_manager
from aiogram.enums import ParseMode
from aiogram.utils import deep_linking
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker
from aiogram.fsm.context import FSMContext
from app.modules.common_slaves.wildberries.models import (WBUserCabinet,
                                                          AdvSetting,
                                                          KeywordSetting, WBCabinet)
from app.utils import redis_manager
from app.utils.suffixes import get_day_suffix
from .. import states
from ..message_templates.templates import (TextWithKeyboard,
                                           Text,
                                           TextWithImage,
                                           TextWithKeyboardPagination,
                                           TextWithKeyboardAndImage)

from . import keyboards, callbacks
from aiogram import Bot

import logging

from typing import TYPE_CHECKING, Optional

from ... import const

if TYPE_CHECKING:
    from ...utils import KeywordForKeyboard
from .import texts
logger = logging.getLogger(__name__)



_sm = get_async_session_maker

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
        return ("""
🤖 Я - специализированный бот для автоматизации АРК (автоматические рекламы) - базового и самого выгодного инструмента продвижения товаров на Wildberries.

Что я умею:
📈 Управлять ключевыми словами в автоматических рекламных кампаниях с помощью искусственного интеллекта

💰 Экономить до 90% рекламного бюджета на автоматические рекламные кампании

🚀 Увеличивать конверсию и снижать стоимость клика

🕒 Многократно экономить личное время и время менеджеров на чистку ключей в АРК

🔍 Автоматически подбирать фразы-спутники для вывода основных ключей в топ

📊 Продвигать товары с помощью АРК на полном автомате

Настройки:
⚙️ У меня достаточно настроек, чтобы тонко и под себя настроить управление АРК вплоть до полного отключения ИИ.

Начало работы:
🛒 Если у вас еще нет магазинов, то жмите "Добавить магазин" и следуйте инструкциям.

📋 Бот крайне прост в использовании: достаточно один раз его настроить, нажав несколько кнопок.
Каждый раздел снабжен подробными инструкциями и подсказками.

Дополнительные ресурсы:
🆕 Самая актуальная информация о боте на канале - https://t.me/auto_wb_master

👥 Группа поддержки и обсуждений бота - https://t.me/wbgram_disc

📩 Связь с админом: @skyline360_1
"""
        )

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

    @staticmethod
    async def get_state_data(state: FSMContext)->(int, int):
        data = await state.get_data()
        last_wb_user_cabinet_original_id = data.get('last_wb_user_cabinet_original_id')
        last_wb_user_cabinet_page = data.get('last_wb_user_cabinet_page')
        return last_wb_user_cabinet_original_id, last_wb_user_cabinet_page


    def __init__(self, bot: Bot,
                  state: FSMContext,
                  chat_id: int,
                  wb_user_cabinet_original_id: int,
                  page: int = 1):
        super().__init__(bot, chat_id)
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._page = page
        self._state = state



    async def __call__(self):
        await self._state.set_state(states.AdvCompanyCatalog.waiting_for_keywords_for_filter)
        async with _sm() as session:
            stmt = select(AdvSetting) \
                .join(AdvSetting.wb_cabinet) \
                .join(WBCabinet.wb_user_cabinets) \
                .where(WBUserCabinet.id == self._wb_user_cabinet_original_id) \
                .order_by(AdvSetting.bot_active.desc())
            result = await session.execute(stmt)
            adv_settings = result.scalars().all()
        adv_settings = await self._filter_advs(adv_settings)
        self._adv_settings = adv_settings
        stmt = select(WBCabinet.id)\
                .where(WBCabinet.wb_user_cabinets\
                       .any(WBUserCabinet == self._wb_user_cabinet_original_id))
        async with _sm() as session:
            result = await session.execute(stmt)
            wb_cabinet_original_id = result.scalar()
        await self._state.update_data(
            last_wb_cabinet_original_id=wb_cabinet_original_id,
            last_wb_user_cabinet_original_id=self._wb_user_cabinet_original_id,
            last_wb_user_cabinet_page=self._page
        )

        await super().__call__()


    async def _filter_advs(self, adv_settings: list[AdvSetting])->list[AdvSetting]:
        state_data = await self._state.get_data()
        keywords_filter: list[list[str]] = state_data.get('filter_advs')
        self._keywords_filter = keywords_filter
        if keywords_filter:
            clear_advs = []
            for adv in adv_settings:
                name = adv.name
                nmids = adv.nmids
                nmids = [str(nmid) for nmid in nmids]
                nmids = ' '.join(nmids)
                name = name + ' ' + nmids
                name = name.lower()
                name += str(adv.adv_id)
                for keyword_filter in keywords_filter:
                    keyword_filter = keyword_filter.strip().lower()
                    if keyword_filter in name:
                        clear_advs.append(adv)
            adv_settings = clear_advs
        return adv_settings



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
                                                          self.on_page,
                                                          self._keywords_filter)


    @property
    def on_page(self):
        return 20


class ShopUpdateInfo(Text):


    @property
    def text(self):
        return f'Обновление данных для магазина, немного подождите...'



class AdvSettingMenu(TextWithKeyboard):
    parse_mode = ParseMode.MARKDOWN

    def __init__(self, bot: Bot,
                 chat_id: int,
                 wb_user_cabinet: WBUserCabinet,
                 adv: AdvSetting):
        super().__init__(bot, chat_id)
        self.adv = adv
        self.wb_user_cabinet = wb_user_cabinet

    async def __call__(self):
        if self.adv.hard_min_ctr:
            self._min_ctr = round(self.adv.hard_min_ctr, 2)*100
        else:
            try:
                self._min_ctr = await data_manager.get_min_ctr(self.adv)
                if not self._min_ctr:
                    raise NoResultFound
                self._min_ctr = round(self._min_ctr*100, 1)
            except NoResultFound:
                self._min_ctr = 'Минимальный CTR не определен'

        try:
            self._mean_ctr = await data_manager.get_mean_ctr(self.adv)
            if not self._mean_ctr:
                raise NoResultFound
            self._mean_ctr = round(self._mean_ctr, 2) * 100
        except NoResultFound:
            self._mean_ctr = 'Средний CTR не определен'
        await super().__call__()


    @property
    def text(self):
        max_cpc = self.adv.max_cpc
        if not max_cpc:
            max_cpc_text = 'Максимальная стоимость клика не установлена'
        else:
            max_cpc_text = f'Максимальная стоимость клика: {max_cpc} р.'

        text = (
            f'📢 *Кампания:* {self.adv.name}\n'
            f'🆔 *ID кампании:* {self.adv.adv_id}\n'
            f'📌 *Статус:* {self.adv.active_status}\n'
            f'🎯 *Минимальный CTR для кампании:* {self._min_ctr} %\n'
            f'📈 *Средний CTR по активным ключам за весь период:* {self._mean_ctr} %\n'
            f'🔢 *Минимальное количество показов для прогноза CTR:* {self.adv.min_views_for_ml_predict}\n'
        )
        text += f'{max_cpc_text}'
        return text

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

        self._image = 'app/client_bot/images/static/api_setting.png'

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
    def __init__(
        self,
        bot: Bot,
        chat_id,
        keywords: list[CalculatedKeyword],
        adv_setting: AdvSetting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        image: str,
        page,
    ):
        super().__init__(bot, chat_id)
        self._keywords = keywords
        self._adv_setting = adv_setting
        self._page = page
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._adv_choice_last_page = adv_choice_last_page
        self._image = image
        self._filter: bool = False
        self._on_page = 24


    async def __call__(self, state: FSMContext, sort_mode = 'default'):
        self.sort_mode = sort_mode
        self._state = state
        data = await state.get_data()
        keywords_filter: list[str] = data.get('keywords_filter')
        clear_keywords = []
        if keywords_filter:
            self._filter = True
            for keyword in self._keywords:
                for keyword_filter in keywords_filter:
                    if '"' in keyword_filter or "'" in keyword_filter:
                        # Проверка на полное совпадение, если в фразе есть кавычки
                        keyword_filter = keyword_filter.replace('"', '').replace("'", '')
                        if keyword_filter == keyword.text:
                            if keyword not in clear_keywords:
                                clear_keywords.append(keyword)
                    else:
                        # Стандартная проверка на вхождение
                        if keyword_filter in keyword.text:
                            if keyword not in clear_keywords:
                                clear_keywords.append(keyword)

            self._keywords = clear_keywords
        self.min_ctr = await data_manager.get_min_ctr(self._adv_setting)
        hide_keywords_is_not_relevant = data.get('hide_keywords_is_not_relevant')
        self.hide_keywords_is_not_relevant = hide_keywords_is_not_relevant

        if hide_keywords_is_not_relevant:
            clear_keywords = []
            for keyword in self._keywords:
                if keyword.hard_status == 0:
                    continue
                clear_keywords.append(keyword)
            self._keywords = clear_keywords
        logger.debug("Начинаю отправку сообщения")

        filter_by_query = self._adv_setting.hide_small_query_keywords
        if filter_by_query:
            clear_keywords = []
            for keyword in self._keywords:
                if not isinstance(keyword.query, str) and keyword.query >= filter_by_query:
                     clear_keywords.append(keyword)
            self._keywords = clear_keywords



        await super().__call__()

    @property
    def text(self):
        total_page = len(self._keywords) // self._on_page

        text = (
                 'Название кампании: ' + str(self._adv_setting.name) + '\n'
                 f'Статус: {self._adv_setting.active_status}\n'
                 f"""Бот {'Включен' if self._adv_setting.bot_active else 'Выключен'}\n  """                                                      
                  'ID кампании: ' + str(self._adv_setting.adv_id) + '\n'                                                  
                 'Статистика и настройка ключевых слов \n'
                 f'Минимальный CRT для кампании: {round(self.min_ctr*100, 2)}%\n'
                 'Расшифровка: \n'
                 '✅  - ключевое слово активно \n'
                 '❌  - ключевое слово не активно \n'
                 ' БС - ключевое слово в белом списке \n'
                 'ЧС   - ключевое слово в черном списке \n'
                 'Авто  - ключевое слово на автоуправлении \n'                                                   
                 'Информация перед ключевым словом: клики/показы/CTR \n'
                 f'Cтраница: {self._page}/{total_page+1}\n'
        )
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
                                                       self._page,
                                                       self._filter,
                                                       self._on_page,
                                                       self.min_ctr,
                                                       self.hide_keywords_is_not_relevant,
                                                       sort_mode=self.sort_mode)


class KeywordSettingMessage(TextWithKeyboard):
    parse_mode = ParseMode.MARKDOWN

    def __init__(self, bot: Bot, chat_id: int,
                 keyword_setting_id,
                 last_page: int):
        super().__init__(bot, chat_id)
        self._keyword_original_id = keyword_setting_id
        self._page = last_page

    async def __call__(self):
        auto_block_status = await redis_manager.get_auto_block_status(self._keyword_original_id)
        self._auto_block_status = auto_block_status
        async with _sm() as session:
            stmt = select(KeywordSetting)\
                          .options(selectinload(KeywordSetting.adv_setting))\
                          .where(KeywordSetting.id == self._keyword_original_id)
            result = await session.execute(stmt)
            keyword_setting: KeywordSetting = result.scalars().one()
        adv_setting: AdvSetting = keyword_setting.adv_setting
        self._keyword_setting = keyword_setting
        self._adv_setting = adv_setting
        nmid = adv_setting.nmids[0]
        position: WBItemPosition = await redis_manager.get_keyword_position(keyword_setting.text, nmid)
        self.position = position
        if position:
            self.last_full_update = position.timestamp.strftime('%d-%m-%Y %H:%M')
        else:
            self.last_full_update = None

        async with get_clickhouse_client() as client:
            total_clicks, total_views, total_spend\
                = await data_manager.get_keyword_statistic_clickhouse(client,
                                                                      self._keyword_setting.text,
                                                                      self._adv_setting.adv_id)

        self.fact_ctr = round(total_clicks / total_views*100, 2) if total_views else 0

        self.spend = total_spend

        return await super().__call__()

    @property
    def text(self):
        keyword_text = self._keyword_setting.text
        keyword_text  = re.sub(r'([_*[\]()~>`#+\-=|{}.!])', r'\\\1', keyword_text)
        text = (f'🔑 *Статистика и настройка ключевого слова:* \n\n {keyword_text}\n\n'
                f'📊 *Фактический CTR:* {self.fact_ctr}%\n'
                f'💰 *Расход:* {round(self.spend, 2)} руб.\n')

        if self.position:
            text += (f'🏆 *Органическая позиция:* {self.position.base_position}\n'
                     f"""🚀 *Буст-позиция:* {self.position.promo_position if self.position.promo_position else "Нет"}\n"""
                     f"""💰 *Ставка на момент сбора данных:* {self.position.cpm if self.position.cpm else "Нет"}\n"""
                     f"""🕒 *Последнее обновление позиций:* {self.last_full_update if self.last_full_update else "Нет"}\n""")
        else:
            text += '📉 *Позиция на Wildberries:* не определена\n'

        return text

    @property
    def keyboard(self):
        return keyboards.get_keyword_setting_keyboard(self._keyword_setting,
                                                      self._adv_setting,
                                                      self._auto_block_status,
                                                      self._page)


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
        ref_statistic = await data_manager.get_ref_statistic(self._user_telegram_id)
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
        ref_links = await data_manager.get_ref_names_and_links(self._user_telegram_id, self.bot)
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
     parse_mode = ParseMode.MARKDOWN

     def __init__(self, bot: Bot, chat_id: int, state: FSMContext, wb_user_cabinet_original_id: int):
       self._state = state
       self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
       super().__init__(bot, chat_id)


     async def _is_active_adv(self):
        async with _sm() as session:
            stmt = select(AdvSetting)\
                .where(
                AdvSetting.wb_cabinet_id == self._wb_cabinet.id,
                AdvSetting.bot_active == True
            )
            result = await session.execute(stmt)
            advs = result.scalars().all()
        if advs:
            return True
        else:
            return False

     async def __call__(self):
        wb_user_cabinet_original_id = self._wb_user_cabinet_original_id
        await self._state.update_data(last_wb_user_cabinet_original_id=wb_user_cabinet_original_id)
        async with _sm() as session:
            stmt = select(WBUserCabinet)\
                .options(selectinload(WBUserCabinet.wb_cabinet),
                         selectinload(WBUserCabinet.user)\
                         .selectinload(User.wb_tokens)).where(
                WBUserCabinet.id == self._wb_user_cabinet_original_id)
            result = await session.execute(stmt)
            self._wb_user_cabinet: WBUserCabinet = result.scalar_one()
            self._wb_cabinet: WBCabinet = self._wb_user_cabinet.wb_cabinet
        self._now = datetime.datetime.now()
        self._expiration_time: datetime.datetime = self._wb_cabinet.expiration_time
        self._expiration_time_str = self._expiration_time.strftime('%d-%m-%Y-%H:%M')
        self.days_left = (self._expiration_time - self._now).days + 1
        self.bonus_days = self.days_left * 2
        await self._state.update_data(
            last_wb_user_cabinet_original_id=self._wb_user_cabinet.id,
            last_wb_cabinet_original_id=self._wb_cabinet.id
        )
        self.is_active_adv = await self._is_active_adv()
        if not (balance := self._wb_cabinet.balance):
            balance = 0
        if not (bonus := self._wb_cabinet.bonus):
            bonus = 0
        self._balance = balance
        self._bonus = bonus
        total_amount_for_day = 0
        async with _sm() as session:
            stmt = select(func.count(AdvSetting.id))\
                .where(AdvSetting.wb_cabinet_id == self._wb_cabinet.id,
                       AdvSetting.bot_active == True)
            result = await session.execute(stmt)
            count_active_advs = result.scalar()
            if count_active_advs:
                total_amount_for_day += count_active_advs * const.PRICE_FOR_ADV_FOR_DAY
            stmt = select(func.count(AdvSetting.id))\
            .where(AdvSetting.wb_cabinet_id == self._wb_cabinet.id,
                AdvSetting.parsing_active == True,)
            result = await session.execute(stmt)
            count_active_parsing = result.scalar()
            if count_active_parsing:
                total_amount_for_day += count_active_parsing * const.PARSING_PRICE
            stmt = select(func.count(AdvSetting.id)) \
                .where(AdvSetting.wb_cabinet_id == self._wb_cabinet.id,
                       AdvSetting.bidder_active == True, )
            result = await session.execute(stmt)
            count_auto_bidder = result.scalar()
            if count_auto_bidder:
                total_amount_for_day += count_auto_bidder * const.AUTO_BIDDER_PRICE

        self.count_active_advs = count_active_advs
        self.count_active_parsing = count_active_parsing
        self.count_auto_bidder = count_auto_bidder
        self.total_amount_for_day = total_amount_for_day
        user: User = self._wb_user_cabinet.user
        tokens: list[WBToken] = user.wb_tokens
        wb_cabinet: WBCabinet = self._wb_cabinet
        work_tokens = []
        for token in tokens:
            try:
                if token.shop_id == wb_cabinet.shop_id:
                    work_tokens.append(token)
            except NotValideToken:
                logger.debug(f'Токен {token} не валиден')
                continue

        shops_tokens = work_tokens
        shops_tokens.sort(key=lambda token:  token.expires, reverse=True)
        if user.user_telegram_id in [373435337]:
            expiration_time = datetime.datetime.now() + datetime.timedelta(days=30)
        else:
            expiration_time = shops_tokens[0].expires
        if expiration_time < datetime.datetime.now():
            self.bot.send_message(self.chat_id, 'Срок действия токена истек. Пожалуйста, обновите токен.\n'
                                                'Для этого добавьте магазин под другим именем с новым токеном')
            return
        self.expiration_time = expiration_time
        self.last_days_for_token = (expiration_time - datetime.datetime.now()).days
        await super().__call__()


     @property
     def text(self):
        balance = self._balance
        bonus = self._bonus
        count_active_advs = self.count_active_advs
        count_active_parsing = self.count_active_parsing
        count_auto_bidder = self.count_auto_bidder
        total_money = balance + bonus
        total_amount_for_day = self.total_amount_for_day
        if self.total_amount_for_day:
            last_for_days = int(total_money / self.total_amount_for_day)
        else:
            last_for_days = '∞'
        text = (
            f'📊 *Кампаний на автоуправлении*: {count_active_advs}\n'
            f'🔍 *Включен парсинг у кампаний*: {count_active_parsing}\n'
            f'🔧 *Включено автоуправление ставкой у кампаний*: {count_auto_bidder}\n'
            f'💸 *Расход в сутки*: {total_amount_for_day} рублей\n'
            f'⏳ *Срок действия токена*: {self.expiration_time}\n'
            f'*Истечет через* {get_day_suffix(self.last_days_for_token)}\n'

        )


        if isinstance(last_for_days, int):
            if last_for_days > 7:
                text += (f"""
💰 Денег хватит на {get_day_suffix(last_for_days)} работы бота. 💰
            """)
            elif last_for_days == 0:
                text += (f"""
⚠️ Денег на продление кампаний больше нет! ⚠️

💳 Срочно пополните баланс во избежание проблем с работой кампаний!
""")
            else:
                text += (f"""
🚨 Внимание!!! 🚨

💰 Денег хватит на {get_day_suffix(last_for_days)} работы бота.

🔔 Настоятельно рекомендую пополнить счет во избежание проблем с работой кампаний""")

        text += (
'===================================\n'
            f'🏬 Магазин: {self._wb_user_cabinet.name}\n'
            f'🆔 Shop ID: {self._wb_cabinet.shop_id}\n'
            f'💰 Баланс магазина: {balance} рублей\n'
            f'🎁 Бонусы: {self._bonus} рублей\n'
        )

        return text

     @property
     def keyboard(self):
        wb_user_cabinet = self._wb_user_cabinet
        wb_cabinet  = self._wb_cabinet
        is_active_adv = self.is_active_adv
        wb_cabinet_original_id = wb_cabinet.id
        is_active_adv: True
        wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
        builder = InlineKeyboardBuilder()

        button = InlineKeyboardButton(
        text = 'Автоматические рекламные кампании',
        callback_data = callbacks.ChoiceAdvPaginator(
            wb_user_cabinet_original_id=wb_user_cabinet.id, page=1).pack(),
        )
        builder.row(button)

        button = InlineKeyboardButton(
        text = 'Пополнить баланс',
        callback_data = callbacks.AddBalance(wb_cabinet_original_id=wb_cabinet_original_id).pack(),
        )

        builder.row(button)

        if is_active_adv:
            button = InlineKeyboardButton(
            text = 'Отключить все кампании',
            callback_data = callbacks.TurnBot(action='off_all',
                                              wb_user_cabinet_original_id=wb_user_cabinet.id).pack())
            builder.row(button)
        button = InlineKeyboardButton(text='Вернуться к списку магазинов',
        callback_data = callbacks.Start().pack())
        builder.row(button)
        return builder.as_markup()




class OrderSubscribe(Text):

    text = "В случае проблем с оплатой свяжитесь с администратором бота @skyline360_1"


class NoMainPhotos(TextWithKeyboard):
    parse_mode = None

    async def __call__(self, adv: AdvSetting):
        self.adv = adv
        await super().__call__()

    @property
    def keyboard(self):
        button = InlineKeyboardButton(
            text = 'Вернуться к списку магазинов',
            callback_data = callbacks.Start().pack()
        )
        builder = InlineKeyboardBuilder()
        builder.row(button)
        return builder.as_markup()



    @property
    def text(self):
        text = ('Я не смог загрузить карточки, участвующие в этой РК. Укажите артикул WB товара в названии кампании в личном кабинете - так я пойму какие товары участвуют в РК\n'
                'Данные кампании: \n'
                'Название кампании: ' + self.adv.name + '\n'
                f'ID кампании: {self.adv.adv_id}\n'                                        
                'Что конкретно нужно сделать:\n'
                '1. Зайдите в рекламный кабинет на WB - https://cmp.wildberries.ru/\n'
                '2. Найдите в кабинете эту кампанию\n'
                '3. Укажите артикул WB (цифровой артикул товара WB - 123456789)\n'
                '4. Подождите 20-30 минут, пока данные обновятся\n'
                'Если возникнут проблемы, то напишите разработчику бота @skyline360_1')
        return text



class ExpiredSubscription(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id: int, wb_cabinet_original_id: int):
            self._wb_cabinet_original_id = wb_cabinet_original_id
            super().__init__(bot, chat_id)

    async def __call__(self):
            async with _sm() as session:
                stmt = select(WBCabinet).where(WBCabinet.id == self._wb_cabinet_original_id)
                result = await session.execute(stmt)
                self._wb_cabinet = result.scalar()
            await super().__call__()

    @property
    def text(self):
           return (
            """
            Не достаточно средств для продолжения работы бота. Пополните баланс.
            """
        )

    @property
    def keyboard(self):
        return keyboards.get_payment_keyboard(
            wb_cabinet_original_id=self._wb_cabinet.id,
        )


class SettingMinCTR(TextWithKeyboard):
    def __init__(self, bot: Bot,  chat_id: int):
        super().__init__(bot, chat_id)
        self._min_ctr = None
        self._min_ctr_type = None
        self._adv = None


    async def __call__(self,  adv_original_id):
        async with _sm() as session:
            adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
            adv = adv.scalar()
        self._adv = adv
        if not adv.hard_min_ctr:
            self._min_ctr = await data_manager.get_min_ctr(adv)
            self._min_ctr_type = "auto"
        else:
            self._min_ctr = adv.hard_min_ctr
            self._min_ctr_type = 'direct'

        keywords: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv)
        keywords.sort(key=lambda x: x.predict_ctr, reverse=True)
        goods = []
        bads = []
        for kw in keywords:
            kw.real_ctr = kw.predict_ctr if kw.predict_ctr > kw.baes_ctr else kw.baes_ctr
            if kw.predict_ctr >= self._min_ctr or kw.baes_ctr >= self._min_ctr:
                goods.append(kw)
            else:
                bads.append(kw)

        goods = goods[-10:]
        bads = bads[:10]
        self._goods = goods
        self._bads = bads
        await super().__call__()


    @property
    def text(self):
        text = (f'Минимальный CTR для кампании {self._adv.name}'
                f' равен {round(self._min_ctr*100, 1)} %,'
                f"""тип минимального CTR: {"Задан в ручную"  if self._min_ctr_type == 'direct' else "Определен автоматически"}\n""")

        # keywords = self._goods + self._bads
        goods = self._goods
        bads = self._bads
        goods.sort(key=lambda x: x.real_ctr, reverse=True)
        bads.sort(key=lambda x: x.real_ctr, reverse=True)
        for good in goods:
            text += f'{good.text} - {round(good.real_ctr * 100, 1)}  % ✅\n'
        text += f'================== {round(self._min_ctr*100, 1)}\n'
        for bad in self._bads:
            predict_ctr = bad.predict_ctr
            baes_ctr = bad.baes_ctr
            ctr = predict_ctr if predict_ctr > baes_ctr else baes_ctr
            text += f'{bad.text} - {round(ctr*100, 1)}  % ❌\n'

        text += '\n\n'
        text += 'Введите новый CTR:'
        return text

    @property
    def keyboard(self):
        return keyboards.get_setting_min_ctr_keyboard(self._adv)


class MaxCPCSetting(TextWithKeyboard):

    async def __call__(self, adv_original_id):
        async with _sm() as session:
            adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
            adv = adv.scalar()
        self._adv = adv

        keywords: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv)
        keywords  = [kw for kw in keywords if kw.status == KeywordStatus.GOOD or kw.reason == KeywordStatus.MAX_CPC]
        keywords.sort(key=lambda x: x.cpc, reverse=True)
        if not self._adv.max_cpc:
            top_kw_list = []
            down_kw_list = keywords
        else:
            top_kw_list = []
            down_kw_list = []
            for keyword in keywords:
                if keyword.cpc > self._adv.max_cpc:
                    top_kw_list.append(keyword)
                else:
                    down_kw_list.append(keyword)
        self._top_kw_list = top_kw_list[-10:]
        self._down_kw_list = down_kw_list[:10]
        await super().__call__()


    @property
    def text(self):
        text = f"""Максимальная цена клика {'для кампании ' + self._adv.name + ' равна ' + str(round(self._adv.max_cpc, 2)) + ' р.'  if self._adv.max_cpc  else 'не задана'}\n"""
        for keyword in self._top_kw_list:
            text += f"""{keyword.text} - {round(keyword.cpc, 2)} р. ❌\n"""

        text += f'================== {round(self._adv.max_cpc, 2) if self._adv.max_cpc else ""}\n'
        print('============')
        for keyword in self._down_kw_list:
            text += f"""{keyword.text} - {round(keyword.cpc, 2)} р. ✅\n"""

        text += 'Введите новую максимальную цену клика для кампании:'
        return text

    @property
    def keyboard(self):
        return keyboards.get_setting_max_cpc_keyboard(self._adv)


class SettingMinViewsForPredictCTR(TextWithKeyboard):
        async def __call__(self, adv_original_id):
            async with _sm() as session:
                adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
                adv = adv.scalar()
            self._adv = adv
            await super().__call__()

        @property
        def text(self):
            return (f'Введите минимальное количество показов для прогноза CTR роботом для кампании {self._adv.name}.\n'
                    f'Текущее значение: {self._adv.min_views_for_ml_predict}.\n')


        @property
        def keyboard(self):
            return keyboards.get_setting_min_views_for_predict_ctr_keyboard(self._adv)


class NotItemsInAdvSetting(TextWithKeyboard):
    text = "Не смогли получить информацию о товарах в кампании через API. Вы можете указать артикул товара (цифровой артикул WB) в названии РК в кабинете Wildberries, либо ввести артикул прямо сейчас:"

    # keyword = keyboards.get_return_to_adv_setting_keyboard()

class IncorrectMinViewsForPredictCTR(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id, adv: AdvSetting):
        super().__init__(bot, chat_id)
        self._adv = adv


    text = 'Минимальное количество показов должно быть целым числом от 0 и больше. Попробуйте снова:'

    @property
    def keyboard(self):
        return keyboards.get_setting_min_views_for_predict_ctr_keyboard(self._adv)




class WaitingForAmount(Text):

    def __init__(self, bot: Bot, chat_id, master_sum: float):
        super().__init__(bot, chat_id)
        self.master_sum = master_sum



    @property
    def text(self):
        date_to = datetime.datetime.now() + datetime.timedelta(days=1)
        date_to = date_to.strftime('%d-%m-%Y')

        text = f"""
Прайс:
- Работа одной кампании, подключенной к боту: 35 р/сутки
- Парсинг активных ключей для одной кампании (включается отдельной кнопой): 15 р/сутки
- Биддер (управление ставками) - 25 р. в сутки за кампанию
        
🔥 Внимание! Только до 10-09-2024(завтра):

💰 Бонус 100 % от суммы пополнения!

Укажите сумму пополнения:"""

        return text


class BalanceUpdated(Text):
    def __init__(self, bot: Bot, chat_id, added_balance: float, bonus: float):
        super().__init__(bot, chat_id)
        self.__balance = added_balance
        self.__bonus = bonus
    @property
    def text(self):
        return f'Баланс успешно пополнен на {self.__balance} рублей + бонус {self.__bonus} рублей'


class Top10ByViewsKeywordsGraphic(TextWithKeyboardAndImage):
    async def __call__(self, adv_original_id: int):

            await super().__call__()

    @property
    def image(self):
        return self._image


    @image.setter
    def image(self, value):
        self._image = value

    text = None
    keyboard = None


class KeywordGraphicPart_1(TextWithImage):

    def __init__(self, bot, chat_id, image, adv_original_id):
        self._image = image
        self._adv_original_id = adv_original_id
        super().__init__(bot, chat_id)



    text = ''


    @property
    def image(self):
        return self._image


    @image.setter
    def image(self, value):
        self._image = value


class KeywordGraphicPart_2(TextWithKeyboardAndImage):
    def __init__(self, bot, chat_id, image, adv_original_id):
        self._image = image
        self._adv_original_id = adv_original_id
        super().__init__(bot, chat_id)

    text = ''

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    @property
    def keyboard(self):
        return keyboards.get_return_to_adv_setting_keyboard(self._adv_original_id)


class NotKeywordHistoryPositions(Text):
    text = 'Не удалось получить историю позиций ключевых слов для этой кампании'


class NotEnoughMoneyForParsing(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id, wb_cabinet_original_id):
        super().__init__(bot, chat_id)
        self._wb_cabinet_original_id = wb_cabinet_original_id



    text = """Не достаточный баланс для парсинга ключевых слов. Пополните баланс и попробуйте снова"""

    @property
    def keyboard(self):
        return keyboards.get_payment_keyboard(self._wb_cabinet_original_id)



class SubscribeOnMyNewChannel(Text):
    text = ("""
**Привет!** Я создатель этого бота. Меня часто спрашивают: могу ли я автоматизировать те или иные вещи для Wildberries или Ozon?
Отвечаю: _95% задач вы можете автоматизировать сами,_ используя ChatGPT, даже если вы полный ноль в программировании.
Для этого я открыл специальный канал, на котором расскажу как создавать крутые программы,
с помощью нейросетей за один день с самого нуля - [перейти на канал](https://t.me/selfscript)""" )

    parse_mode = ParseMode.MARKDOWN


class StatTelegramTranslation(Text):
    text = ('Привет! На связи разработчик данного бота, и когда я помогаю пользователям его настроить, '
            'то мне часто задают вопросы, напрямую к нему не относящиеся: как успешно продвигать товары, '
            'какую выбрать стратегию, как минимизировать расходы, повысить прибыль и т.д. \n Я не считаю себя '
            'супер-экспертом по маркетплейсам, но и свой бизнес запустить и раскрутить как-то смог. '
            'Поэтому сегодня в 15:00 по Москве я проведу трансляцию на канале поддержки бота @auto_wb_master, на '
            'которой поделюсь своим опытом и отвечу на самые частые вопросы. \n\n'
            'Сразу скажу, что я сторонник математического подхода к бизнесу, когда мы все считаем и проверяем заранее,'
            'а не делаем что-то наугад. Если вы разделяете такой подход, то прошу присоединиться к трансляции - @auto_wb_master_bot \n\n'
            'Все, до встречи на трансляции и удачи в вашем бизнесе!')


class WrongLinkMessage(Text):
    text = ('Пардон, ошибся во второй ссылке на канал, вот правильная: @auto_wb_master')


class TranslatinSoon(Text):
    text = ('Напоминаю: через 15 минут начнется трансляция на канале поддержки бота @auto_wb_master. ')


class Tranlation_15_00(Text):

    text = ('Ура! Починили возможность  добавления новых кампаний в бота  - /start \n\n'
            'Поэтому сегодня в 15:00 по Москве я проведу трансляцию на канале поддержки бота @auto_wb_master, на '
            'которой расскажу подробнее о том, как наш бот работает и как с его помощью экономить 70-80 % '
            'от рекламного бюджета при тех же результатах. Трансляция пройдет на канале поддержки бота @auto_wb_master\n'
            'До встречи!')


class Tranlation_14_45(Text):

    text = ('Решил напомнить: через 15 минут в трансляции на канале @auto_wb_master я расскажу о том, '
            'как наш бот работает и как с его помощью экономить 70-80 % от рекламного бюджета при тех же результатах.'
            ' Трансляция пройдет на канале поддержки бота @auto_wb_master\n'
            'Жду Вас!')


class BotPriceMessage(Text):
    text = ("""Приветствую, на связи разработчик данного бота.\n
Продвижение на маркетплейсах - это сложный процесс, и у каждого селлера возникают с этим проблемы в той или иной степени.
Наш бот отчасти решает эти проблемы, но нет предела совершенству, и нам нельзя стоять на месте - нужно двигаться дальше, делая его работу более качественной.
В рамках этого у нас план такой:
1. Мы сократим демо-период для новых магазинов до 2 дней (если добавить второй магазин - демка будет работать для него отдельно) - практика показывает, что этого времени для большинства достаточно чтобы оценить полезность бота для себя в том виде, в котором он есть сейчас + это сильно сократит нагрузку на сервер и навигация по боту станет быстрее.
2. Для обладателей платной подписки мы сделаем отдельную закрытую группу с целью совместного обсуждения и выработки плана развития бота, как в доработке текущего функционала, так и 
развития нового. Так мы сконцентрируемся на решении наиболее актуальных задач.
3. Сокращение демо-периода компенсируем резким снижением цены бота до 1000 р. в месяц за один магазин
4. Если вы хотите попасть в группу и принять активное участие в дальнейшей разработке и совершенствовании бота, то можете не дожидаться окончания демо-периода и заранее оплатить подписку. При этом, оставшиеся демо-дни буду компенсированы в двойном размере. \n\n

Если вы еще не успели оценить работу бота и его выгоду для вашего бизнеса, то жмите на /start и следуйте инструкциям \n

Канал поддержки бота - https://t.me/auto_wb_master
""")



class CallMe1(TextWithKeyboard):
    text = """
Вдогонку к предыдущему сообщению:
Если я не прочитал ваше сообщение, то значит очередь до вас еще не дошла - я специально не просматриваю и не отвечаю, чтобы никого случайно не пропустить.
Чтобы полноценно рассказать про использование бота для максимально эффективного продвижения на WB и ответить на ваши вопросы нужно в среднем 40-50 минут, поэтому обещанные 10 консультаций я смогу провести только в течении 2-3 дней.
Прошу набраться терпения - оно того стоит!
Если успели написать до момента отправки этого сообщения - то вы точно успели и не переживайте: дойду и до вас!
Если не успели: осталась буквально пара мест, так что скорее напишите мне,чтобы занять место и получить тест-драйв бота!    

"""

    keyboard = keyboards.get_call_me_keyboard()


class CallMe2(Text):
    text = """
Оборот или прибыль?

Привет! К сожалению, мест для личной консультации уже нет, и часть тех, кто оставил заявку, я не смогу проконсультировать. Но не переживайте: у большинства селлеров вопросы пересекаются, и я могу обобщать их и давать ответы прямо здесь, в боте.

Итак, поехали!

Когда я разрабатывал бота, то думал именно в контексте того, как бот должен влиять именно на прибыль. И то, что самый частый отзыв о боте заключается в экономии денег на рекламу и личного времени - так это так изначально и задумывалось.
Дело в том, что я вдоволь насмотрелся на бизнесы, которые делают заоблачные обороты, но если заглянуть в их бухгалтерию, то там дырка от бублика.
    """

class CallWithManager(TextWithKeyboard):


    text = ("""Мы с программистами провели исследование и вот что выяснилось:

1. Те, кто смогли подключиться к боту и самостоятельно в нем разобраться, 
повысили эффективность своих кампаний на 70 % по сравнению с кампаниями, которые к боту не подключены.\n
2. Тех, кого мы консультировали лично по работе с ботом, помогли в нем разобраться и объяснили на примере их товаров как использовать его максимально эффективно, увеличили эффективность
кампаний в пересчете на продажи в среднем в 2 раза.\n
\n
Как разработчик данного бота скажу, что потенциал увеличения продаж с помощью бота x4 - x5,
поэтому если у вас пока нет такого роста, значит вы все еще что-то делаете не так или не до
конца понимаете как работает бот и как работает Wildberries с его системой продвижения в топ.
Поэтому предлагаю следующую схему: свяжитесь со мной по кнопке ниже, 
мы с вами созвонимся в телеграмме, и я лично помогу вам настроить правильно 
бота и запустить эффективный процесс продвижения. \n
Вы получите сразу эффект: экономия бюджета на рекламу в 3-5 раз 
+ поймете как можно экономить несколько часов времени в день, которые обычно нужно тратить на настройку эффективной рекламы.\n\n

Не ждите когда у Wildberries все снова поменяются, используйте эффективный инструмент, пока он работает и дает результат! \n\n



""")


class Single_message0(TextWithKeyboard):

    text = """
Внимание: WB массово блокирует кабинеты!    

Извиняюсь, что беспокою столь рано, но у нас вопрос, не терпящий отлагательств.

Возможно, вы уже слышали, что Wildberries массово блокирует кабинеты селлеров, и, вероятно, ваш кабинет тоже под угрозой.
Дело в том, что многие рекламные биддеры используют ВНУТРЕННЕЕ API  WB, что ПРЯМО запрещено оффертой, в которой прописано,
что за использование внутреннего API кабинеты будут блокироваться. 
Сразу скажу, что наш бот автоматизации вывода товаров в топ использует только официальное API, которое никак не нарушает офферту WB, даже наоборот: маркетплейс прямо рекомендует использовать именно его.
Поэтому, если вы пользуетесь нашим ботом, то вам нечего бояться (К слову, наш бот вообще действует строго по правилам WB и его рекомендациям).
Однако, если вы используете другие биддеры, основанные на внутреннем API, то ваш кабинет в ближайшее время будет заблокирован.

Как этого избежать:

1. Прямо сейчас зайдите в кабинет WB и отключите все расширения, которые вы используете. Сделайте это прямо сейчас, иначе ваш кабинет 100 % заблокируют
2. Используйте только те средства автоматизации, которые используют специальный API WB согласно документации (https://openapi.wb.ru/)
3. Если у вас возникнут вопросы, то пишите мне, я вам помогу.
Берегите себя и свой кабинет!

    """


    keyboard = keyboards.get_call_me_keyboard0()


class Single_message1(TextWithKeyboardAndImage):

    text = """
Разъясняю по поводу блокировок:

Официальный API - это когда вы делаете API-ключ и используете его в сервисе, например, в нашем боте - это разрешено и поощряется Wildberries.
Внутреннее API - это когда вы используете внутренние методы, которые не предоставлены официально, например, через расширения в браузере - это запрещено оффертой WB и ведет к блокировке кабинета.    

Что делать:
1. Заходите в браузер и от греха по-дальше сносите все расширения, связанные с маркетплейсом. Потом будете разбираться что можно ставить - что нельзя. Сейчас главное - предотвратить блокировку.
2. Официальное API не трогайте - оно тут не при чем!

На долго ли это:
Пункт о блокировке за использование внутреннего API появился в офферте год назад где-то, но случаев блокировок не было.

Сейчас WB взялся за этот вопрос, значит уже не отстанет.

Если будут еще вопросы - не стесняйтесь, пишите мне. Это помогает понять проблемы моих клиентов и выкатить уже развернутое решение или ответ.     
    """

    image = 'app/client_bot/images/block_api.png'

    keyboard = keyboards.get_call_me_keyboard0()


class Single_message2(TextWithKeyboard):

    text = """
Провел 10 обещанных бесплатных консультаций по эффективному автоматизированному продвижению в поиске на WB с помощью нашего с вами бота.
Многие клиенты просят показать кейсы, но я не готов демонстрировать магазины клиентов без их согласия, да и доступов у меня к ним нет.

Поэтому хочу предложить такую схему:

Вы мне даете свой магазин для кейса, а я вам даю 2 недели использования бота бесплатно.

В первую очередь интересуют кейсы новых товаров в новых магазинов, чтобы показать какие результаты дает бот с нуля.

Если вам интересно - свяжитесь со мной по кнопке ниже, спасибо!
    
    """


    keyboard = keyboards.get_call_me_keyboard1()


class Single_message3(TextWithKeyboard):

    text = """
Во-первых, поздравляю с прошедшими праздниками!

Во-вторых, держите видео-запись консультации клиента по использованию нашего бота для продвижения на WB - https://t.me/auto_wb_master/97

Если вы тоже хотите получить консультацию по продвижению на WB с помощью нашего бота, то я готов провести ее под запись с дальнейшей выкладкой на канале.

Сразу хочу сказать, что в данном видео мы не раскрыли и 20 % возможностей бота, не смотря на 40-минутное видео, поэтому наверняка вопросы еще будут.

Сейчас в приоритете те, кто вообще еще не подключал бота - хотел бы проконсультировать под запись именно весь процесс от начала регистрации магазина в боте. Если ваш случай именно такой - буду рад помочь!

Бесплатное использование бота за кейс под запись еще актуально!

    
    """

    keyboard = keyboards.get_call_me_keyboard1()


class Single_message4(Text):
    text = """
    Для тех, кто только начинает бизнес на маркетплейсах, я выкладываю статьи на своем канале и делюсь своим опытом по старту с нуля.

В очередной статье рассказываю, почему наценка в товаре должна быть не меньше 500-600 % прибыли, иначе с большой вероятностью дело не взлетит - https://t.me/auto_wb_master/99
    """


class Single_message5(TextWithKeyboard):
    text = """
Привет! Последнюю неделю все, кому я помог внедрить бота в бизнес, оценили его работу на отлично. Поэтому пока приторможу внедрение новых функций и попробую помочь максимальному количеству людей внедрить то, что уже есть сейчас в бизнес на WB и получить прирост от x3-x5 к продажам.
На период внедрения вы можете пользоваться ботом бесплатно, если все устраивает - дальше цена 2 300 р. в месяц. 
Внедрять буду в порядке живой очереди, кнопка для связи ниже.


    """

    keyboard = keyboards.get_call_me_keyboard1()


class Single_message6(Text):

    text = """Написал подробную инструкцию по использованию бота для продвиженя товаров в топ на WB. 
Данный бот является самым эффективным инструментом для продвижения на WB и признан многими экспертами. 
Поэтому разобраться в его работе просто необходимо - https://telegra.ph/Instrukciya-prodvizheniyu-tovarov-na-Wildberries-po-klyuchevym-slovam-s-pomoshchyu-bota-wb-adv-master-bot-05-14"""


class Single_message7(TextWithKeyboard):
    text = """Добрый день! Внес изменение в инструкцию по продвижению товаров на WB с помощью бота.
    
Основные изменения:

1. Изменился порядок подключения кампаний к боту: он стал проще и теперь не нужно включать рекламу на WB для настройки бота. Теперь вы можете сначала подключить бота к АРК, сделать все настройки с ключами, а затем включать кампанию на WB. 
2. Появился новый раздел "Управление ставкой": из каких принципов нужно исходить при работе с ботом

Полный текст инструкции - https://telegra.ph/Instrukciya-prodvizheniyu-tovarov-na-Wildberries-po-klyuchevym-slovam-s-pomoshchyu-bota-wb-adv-master-bot-05-14

Заказать демо-доступ вы можете, связавшись с разработчиком бота, т.е. со мной, по ссылке ниже    
    """


    keyboard = keyboards.get_call_me_keyboard1()


class Single_message8(TextWithKeyboard):

    text = """Привет! Очень частый вопрос: может ли наш бот управлять рекламой «Поиск-каталог»?

Ответ:

У нас действительно были планы по подключению рекламы типа «Поиск-каталог» к боту, однако бот показал настолько выдающиеся результаты в продвижении товаров в топ, что мы все-таки решили отложить эту задачу, чтобы сконцентрироваться на том, что у бота уже получается очень хорошо - продвигать товары в топ.

Поэтому сейчас мы занимаемся совершенствованием пользовательского опыта вокруг его основной функции.

Если вас интересует продвижение в топ с минимальными затратами, то наш бот является наилучшим и единственным в своем роде инструментом из доступных.

Ни один сотрудник или сервис не сможет так эффективно накручивать показатель CTR товаров для повышения рейтинга карточки и роста позиций, при этом, вы можете отслеживать результаты в реальном времени.

Однако, для получения выдающихся результатов за минимальный срок нужно ВНИМАТЕЛЬНО изучить инструкцию по продвижению на WB — https://telegra.ph/Instrukciya-prodvizheniyu-tovarov-na-Wildberries-po-klyuchevym-slovam-s-pomoshchyu-bota-wb-adv-master-bot-05-14.

Стоимость использования бота составляет 2 300 рублей в месяц. Если вас интересует демо-доступ, то свяжитесь со мной по кнопке ниже.

"""


    keyboard  = keyboards.get_call_me_keyboard1()


class Single_message9(TextWithKeyboard):
    text = """
Привет! На VC появилась очень хорошая статья-инструкция по продвижению товаров на WB. В ней также упомянули нашего бота. Статья хорошая, объясняет нюансы продвижения в топ - https://vc.ru/trade/1182445-podrobnyy-gayd-po-prodvizheniyu-tovarov-v-top-wildberries   
    """

    keyboard = keyboards.get_call_me_keyboard1()

class Single_message10(Text):
    text = """
Добрый день! Несколько важных новостей:

1. В ближайшее время стоимость подписки бота будет временно увеличена до 5 500 рублей в месяц. Далее будем переходить на оплату за кампании с подпиской на год.

2. Выложил несколько записей типовых отзывов от клиентов бота: рост продаж, сокращение расходов на рекламу в 2-4 раза, экономия времени - 3-4 раза (ссылка на записи - https://t.me/auto_wb_master/129). Каждый пользователь бота должен получать такие результаты, если у Вас не выходит, то 100 % что-то не то делаете.

3. Теперь поддержка бота осуществляется через специальный чат в телеграмме - https://t.me/wbgram_disc. Все вопросы, связанные с работой бота, задавайте, пожалуйста, там. Личная поддержка теперь будет на вип-тарифе, о котором расскажу позже.     
    
    """
class Single_message11(Text):
    text = """
Внимание! Вышло очень важное обновление в боте, касаемо ручного управления ключевыми словами:
1. Кнопка "В черный" список переименован в "В список не релевантных фраз" - теперь это лучше отражает смысл данной кнопки
2. Появилась кнопка "Отключить (релевантная фраза) - сюда добавляем релеватные фразы, но которые нужно по тем или иным причинам отключить

В чем разница между этими кнопками:

Когда мы нажимаем в "Список не релевантных фраз" (бывший черный список), то мы даем команжу боту отключать аналогичные фразы, находящиеся в режиме Авто (режим по умолчанию).

Когда мы нажимаем "Отключить (релевантная фраза), то это тоже приводит к отключению слова, но боту поступает другая команда: включать другие аналогичные ключи.

Зачем это нужно:

Часто возникают ситуации, когда нужно отключить тот или иной запрос, не смотря на то, что он является релевантным, например, если ключ достиг целевой позиции и его больше не нужно продвигать.

Теперь вы можете просто отключать такие ключи, не давая команды боту блокировать аналогичные фразы. 

Пожалуйста, не добавляйте НЕ релевантные фразы в этот режим, иначе бот будет хуже реагировать на нецелевые запросы.

Сейчас функция находится в тесте, если возникнут проблемы - пишите в группу поддержки - https://t.me/wbgram_disc    
    
    
    """

class Single_message12(Text):

    text = """
Добрый день! Добавил функцию фильтрации фраз в боте для более удобной навигации.
Подробности - https://t.me/auto_wb_master/139    
    
    """
class Single_message13(Text):
    text = """
Добрый день! Добавил ручное управление CTR кампаний. Подробности - https://t.me/auto_wb_master/145?single    
    
    """


class Single_message14(Text):
    text = """"
Вышло важное обновление: теперь вы можете задавать максимальную стоимость клика, выше которой фразы будут автоматически отключаться.

Подробности на канале - https://t.me/auto_wb_master/150
    
    """


class Single_message15(Text):
    text = """
Добрый день! Работа с ботом стала еще эффективнее: теперь вы можете задавать количество показов, не достигнув которых бот не будет пытаться прогнозировать CTR и отключать фразу. Подробнее на канале бота - https://t.me/auto_wb_master/158    
    
    """


class Single_message20(Text):
    text = """
Ровно год назад, 1 июля 2023 года мне пришла идея сделать бота для автоматизации продвижения на WB.\n
Сейчас из интересной поделки бот превратился в серьезное профессиональное решение, которое используют селлеры с оборотом до миллиарда рублей в месяц! \n
В честь этого события я запускаю акцию: бонусы до 400 % на пополнение счетов магазинов бота!\n\n
Как это работает:\n
1. Для всех пополнений от 100 рублей начисляется бонус 200 % от суммы\n
2. Если сумма пополнения превышает мастер-сумму, то бонус составляет 400 % от суммы пополнения.\n
Например, если сейчас на старте акции вы пополните счет всего на 1000 рублей, то при наличии 1 кампании в магазине сможете использовать все функции бота в течении 3,5 месяцев, т.е. всего 285 рублей в месяц за кампанию.\n
Таким образом мой бот становиться не тольк самым лучшим, но и самым выгодным инструментом автоматизации рекламы на WB.\n
Предложение действует только до 5 числа этого месяца!\n
    
Вводите команду /start , выбирайте магазин или добавляйте новый, пополняйте счет и получайте бонусы!
    """


class Single_message21(Text):
    text = """
Добрый день! Выложил на канале свежий отзыв о работе бота: 4.5 млн. продаж с помощью бота, скрины и отзыв - https://t.me/auto_wb_master/199\n
Также напоминаю, что сегодня - предпоследний день акции, и у вас есть еще возможность получить бонус на услуги бота до 400 %. \n
Жмите /start , добавляйте магазин или выбирайте существующий и используйте акцию прямо сейчас ->  /start
    
    
    """


class Single_message22(Text):
     text  = """
     Добрый день! Напоминаю, что сегодня последний день супер-акции: до 400 % бонус за пополнение баланса!  Жмите старт /start, выбирайте нужные магазины или добавляйте  новый, пополняйте баланс магазина и получайте бонус 200 % при пополнении на любую сумму и 400 % при пополнении от мастер-суммы
     """


class Single_message23(Text):
    text = """
Добрый день! Выкладываю свежий отзыв на бота - https://t.me/auto_wb_master/204 \n
Также сообщаю, что по техническим причинам акция продляется до понедельника. \n
Жмите на /start , выбирайте магазин или добавляйте новый, пополняйте счет и получайте бонусы:\n
От 100 рублей - 200 % бонус\n
От мастер-суммы (на данный момент - 40 т.р.) - 400 % бонус\n 
Жмите - /start   
    """


class Single_message100(Text):
    text = """
    Начинаем подводить итоги конкурса "СуперМенеджер Недели"\n
    Куда присылать кейсы и другие подробности - https://t.me/auto_wb_master/222
       
    """


class Single_message101(Text):
    text = """
    🎉 Ура! Я записал свежее видео с практикой работы с ботом.\n
    🤖 Также рассказал о самых последних изменениях, улучшениях и доработках, а также проговорил текущую логику работы бота, так что смотреть обязательно не только новичкам, но и старожилам! 📈👥\n
🎥 Смотрим! 👀\n
   Видео на канале - https://t.me/auto_wb_master/227 \n\n
   Жмите /start , запускайте рекламу и забирайте топы продаж!
    
    
    """


class Single_message105(Text):
    text  = """
📢 Внимание, еще одно обновление бота - теперь им пользоваться стало еще удобнее! 📢

✨ Совершенству нет предела, поэтому вчера, по заветам пользователей, сделал несколько обновлений в боте, сам попробовал и мне кажется, что от предыдущего обновления теперь им пользоваться удобнее раза в два:

1️⃣ Как уже писалось ранее: теперь если факт CTR больше прогноза, то при принятии решения о включении или выключении фразы бот будет руководствоваться фактическим CTR.

🔍 Опытным путем установлено, что хоть это и дает на каких-то ключах сбой (ключи с высоким CTR, но без продаж), таких кейсов крайне мало, да и руками поправить их ничего не стоит.

🚀 Зато теперь с таким алгоритмом работа бота стала максимально плавной, перетекая из ИИ-алгоритмов до ручного контроля за ситуацией.

2️⃣ Сортировка и фильтрация АРК:
Теперь первыми показываются подключенные к боту кампании и их не нужно искать по задворкам.

🔎 А с умным поиском по тексту и артикулу выбор нужной кампании стал еще проще: достаточно вписать текст (работает многострочный ввод) и бот покажет только те кампании, название или артикул WB которых содержат этот текст.

📈 Например, многие помнят несколько цифр своих артикулов, теперь достаточно ввести эти несколько цифр и бот покажет все АРК, артикулы которых содержат эту числовую последовательность.

3️⃣ Показать активные ключи:

🔥 Теперь, чтобы бот показал только активные ключи, достаточно нажать одну кнопку, которую вы найдете на странице просмотра ключевых запросов.

🎯 Пробуйте, оценивайте, жмите /start

Новость на канале - https://t.me/auto_wb_master/233

Обсудить в чате - https://t.me/wbgram_disc
    """


class HelpCenterMainMenu(Text):
    @property
    def text(self):
        text = """
Самая свежая информация о боте - https://t.me/auto_wb_master
Обсуждение и поддержка - https://t.me/wbgram_disc
Связь с разработчиком - https://t.me/skyline360_1

Подробную информацию смотрите в разделах
        
"""
        return text


    @property
    def keyboard(self):
        builder = InlineKeyboardBuilder()

class WaitingForWhitePhrases(TextWithKeyboard):

    async def __call__(self, adv_setting_id):
        self.adv_setting_id = adv_setting_id
        await super().__call__()

    @property
    def text(self):
        return """
Отправьте мне список фраз (через перенос) которые вы хотите добавить в белый список (фразы для продвижения).  
Например:

платье женское
платье вечернее
платье летнее

Я автоматически добавлю эти ключи в белый список. Учитывается точное соответствие.

    """

    @property
    def keyboard(self):
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)




class WhitePhrasesAdded(TextWithKeyboard):
    async def __call__(self, adv_setting_id):
        self.adv_setting_id = adv_setting_id
        await super().__call__()

    text = "Фразы добавлены в белый список, можете ввести еще фразы или вернуться в настройки РК"
    @property
    def keyboard(self):
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)

class CPMSetting(TextWithKeyboard):
    async def __call__(self, adv_setting_id):
        async with _sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
            result = await session.execute(stmt)
            adv_setting = result.scalars().first()
        self.adv_setting = adv_setting
        await super().__call__()

    @property
    def text(self):
        text = f"""
Режим управления ставкой: {'Ручной'  if not self.adv_setting.bidder_active else 'Автоматический'}\n\n"""
        if self.adv_setting.bidder_active:
            text += f"""{'Целевое место место: ' + str(self.adv_setting.max_place) }\n
Максимальная ставка: {str(self.adv_setting.max_cpm)}\n"""
        return text

    @property
    def keyboard(self):
        builder = InlineKeyboardBuilder()

        if self.adv_setting.bidder_active:

            bottom = InlineKeyboardButton(text="Выключить автоматическое управление ставкой",
                                          callback_data=callbacks.CPMSettingMenu(
                                          action = "off_auto_cpm",
                                          adv_original_id = self.adv_setting.id).pack())
        else:
            bottom = InlineKeyboardButton(text="Включить автоматическое управление CPM",
                                      callback_data=callbacks.CPMSettingMenu(
                                          action="set_auto_cpm",
                                          adv_original_id=self.adv_setting.id).pack())

        builder.row(bottom)

        bottom = InlineKeyboardButton(text = 'Изменить ставку (Максимальную ставку)',
                                      callback_data = callbacks.CPMSettingMenu(
                                          action = 'set_manual_cpm',
                                          adv_original_id = self.adv_setting.id).pack())

        builder.row(bottom)


        if self.adv_setting.bidder_active:
            bottom = InlineKeyboardButton(text="Изменить целевую позицию",
                                          callback_data=callbacks.CPMSettingMenu(
                                          action = "set_max_position",
                                          adv_original_id = self.adv_setting.id).pack())
            builder.row(bottom)



        bottom = InlineKeyboardButton(text='К настройкам АРК',
                                         callback_data=callbacks.Adv(
                                                adv_original_id=self.adv_setting.id).pack())
        builder.row(bottom)


        return builder.as_markup()


class AutoCPMSettingGetMinPosition(Text):

    async def __call__(self, adv_setting_id: int):
        async with _sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
            result = await session.execute(stmt)
            adv_setting = result.scalars().first()
        self.adv_setting = adv_setting
        await super().__call__()

    @property
    def text(self):
        text = """
Введите позицию, которую вы хотите занимать в топе:
        """
        return text


class AutoCPMSettingGetMaxCPM(Text):
    text = """Укажите максимальную ставку:"""


class ManualCPMSetting(Text):
    text = """Укажите ставку (целое число от 100):"""


class WaitingForBlackPhrases(TextWithKeyboard):
    async def __call__(self, adv_setting_id):
        self.adv_setting_id = adv_setting_id
        black_phrases: Optional[list[str]]  = await redis_manager.get_black_phrases(adv_setting_id)
        self.black_phrases = black_phrases
        await super().__call__()

    @property
    def text(self):
        if self.black_phrases:
            blacklist = "\n".join(self.black_phrases)
            return f"""Текущий черный список:\n{blacklist}\n\nЧтобы обновить фразы, отправьте список еще раз. Список будет обновлен."""
        else:
            return ('Укажите через знак переноса фразы, которые вы хотите добавить в черный список (фразы для исключения из продвижения).'
            ' Если фраза указана без кавычек, то будут учитываться вхождения, если с кавычками - точное соответствие. Пример:\n\n'
            'платье женское\n'
            'платье вечернее\n'
            'платье летнее\n'
            '"женское летнее"\n'
        )

    @property
    def keyboard(self):
        builder = InlineKeyboardBuilder()

        if self.black_phrases:
            builder.row(InlineKeyboardButton(text="Сбросить черный список",
                                                callback_data=callbacks\
                                             .ResetBlackPhrases(adv_setting_id=self.adv_setting_id).pack()))

        builder.row(InlineKeyboardButton(text="Вернуться в настройки РК",
                                         callback_data=callbacks.Adv(adv_original_id=self.adv_setting_id).pack()))
        return builder.as_markup()


class Single_message102(TextWithImage):
    parse_mode='MarkdownV2'

    @property
    def text(self):
        return """
**💸Как продавцу на WB вывести карточку в ТОП и удержать позиции?**

[Получить пошаговое руководство \>\>](https://t.me/marpla_web_bot?start=link_5LpkvSXwOG)

➡️Вы получите эффективную **стратегию, по которой работают селлеры с доходом от 500к
**
**📅 5 сентября, Чт, 14:00 МСК**

**Что будет?**
\- Что изменилось за лето, и как подчинить алгоритмы ранжирования
\- Способы повысить конверсию, которые работают сейчас
\- Акции: убытки или возможность быстро заработать?
\- CTR, Склады и рейтинг: чего не договаривает WB?

**🎁Также вам будут доступны специальные сервисы\+биддер для управления рекламой БЕСПЛАТНО⚡️**

**Переходите в бота, чтобы уже в сентябре поднять выручку в 2\-3 раза, не увеличивая рекламный бюджет:** [@marpla_web_bot](https://t.me/marpla_web_bot?start=link_5LpkvSXwOG)   
    
    """

    image = 'app/client_bot/images/webinar.png'


class Single_message103(Text):


    @property
    def text(self):



        text = """
        📢 Хотите увеличить продажи на Wildberries? Давайте я вам помогу!

🔝 Ваши товары могут выделяться среди конкурентов уже завтра!

Я предлагаю вам решение, которое сэкономит ваше время и увеличит продажи через автоматизацию рекламы на Wildberries.

С помощью моего бота вы сможете легко запускать рекламные кампании, а я лично помогу вам на каждом этапе — от настройки до получения первых результатов.
Что вы получите? 🔥

    Полную автоматизацию рекламных кампаний — бот сам управляет процессом, вам не нужно тратить часы на ручные действия.
    Эффективное управление бюджетом — бот настраивает рекламу так, чтобы вы получали максимальные результаты при минимальных расходах.
    Простота в использовании — я подробно объясню, как всё работает, и помогу вам начать.
    Поддержка на каждом шаге — если возникнут вопросы, я всегда на связи.

🎁 И это не всё! Я дарю вам 1000 рублей на счёт для пробы бота. Вы сможете протестировать его возможности без рисков!
🚀 Хотите, чтобы я всё настроил и показал, как работает бот?

Пишите мне прямо сейчас, и я проведу вас через весь процесс настройки. Без лишних сложностей и головной боли!

@skyline360_1

Не упустите шанс, пока ваши конкуренты не заняли ваше место в топе!
        
        
        """



        return text


class Single_message104(Text):

    text = """
🔔 У вас на счету есть деньги, а бот простаивает? Пора действовать!

💰 Вы уже пополнили счёт, но ещё не используете наш бот для автоматизации рекламы на Wildberries?

Ваша возможность увеличить продажи ждёт! Бот готов к работе, и теперь он стал ещё мощнее благодаря новым функциям. Вложенные средства уже на счету — всё, что осталось, это запустить кампании и увидеть результаты!
Почему стоит активировать бота прямо сейчас?

- Ваш бюджет уже готов — не теряйте время, запускайте рекламу с минимальными усилиями.
- Новые возможности бота помогут вам настроить рекламу эффективнее, чем когда-либо.
- Лёгкий старт — я помогу вам на каждом этапе, от настройки до первой кампании.

💬 Напишите мне прямо сейчас, и я расскажу, как быстро и просто начать использовать бот для увеличения ваших продаж.

✉️ Связаться со мной: @skyline360_1

Деньги на счету — не дайте им простаивать, сделайте первый шаг к увеличению доходов на Wildberries!

Нажмите на /start  ⬇️    
    
    """


class Single_message106(Text):

        text = """
        🚀 СЕКРЕТНАЯ АКЦИЯ ТОЛЬКО ДЛЯ ПОЛЬЗОВАТЕЛЕЙ БОТА - 100% бонус при пополнении на любую сумму!

        🔥 За последнее время в нашем боте появилось много классных функций, которые сделают вашу рекламу на Wildberries ещё эффективнее!

        В честь этого мы объявляем ограниченную акцию:
        Пополните счёт до 18:00 10.09.2024 и получите 100% бонус на каждое пополнение! 💰
        Почему стоит действовать прямо сейчас?

        ♾ Удваивайте рекламный бюджет и используйте новые возможности бота на полную!
        ❗️Акция действует только до 18:00 вторника, так что не упустите шанс удвоить свои вложения.

        💬 Пишите мне, если у вас возникли вопросы или нужна помощь с настройкой:

        ✉️ @skyline360_1

        Успейте воспользоваться предложением и опробовать все новые функции бота!"""


class ItemIsOutOfIndex(Text):

    def __init__(self,bot,
            user_telegram_id,
            last_position: WBItemPosition,
            new_position: WBItemPosition):
        self.user_telegram_id = user_telegram_id
        self.last_position = last_position
        self.new_position = new_position
        super().__init__(bot, user_telegram_id)



    @property
    def text(self):
        return f"""
Ваш товар {self.last_position.nmid} выпал из индекса по ключевому слову {self.last_position.keyword_text}."""


class ItemIsInIndex(Text):

    def __init__(self,bot,
            user_telegram_id,
            last_position: WBItemPosition,
            new_position: WBItemPosition):
        self.user_telegram_id = user_telegram_id
        self.last_position = last_position
        self.new_position = new_position
        super().__init__(bot, user_telegram_id)


    @property
    def text(self):
        return f"""
Ваш товар {self.last_position.nmid} добавлен (вернулся) в индекс по ключевому слову {self.last_position.keyword_text}."""



class Single_message107(Text):
    text = """
    🚀 Как с помощью бота попасть в рекламные полки?

Не все знают, но у нас уже давно доступна эта функция! Чтобы ваши товары оказались на рекламных полках, нужно выполнить всего пару шагов:

1. Добавьте самые релевантные ключевые слова в белый список.
2. Установите минимальный CTR на 100.

И вуаля — ваши товары появятся на рекламных полках, привлекая больше покупателей! 🔥

Если вам нужна помощь с настройкой бота или у вас возникли вопросы, пишите мне, и я помогу настроить всё быстро и правильно.

📩  @skyline360_1
    
    """


class Single_message108(TextWithImage):
    text = """
🚀 Теперь в нашем боте есть поддержка кластеров! 🎯

Кластеры позволяют вам следить за ключевыми словами, чтобы они не блокировались. Это значит, что вам больше не нужно беспокоиться о том, что ключи могут выпасть из ротации или потерять эффективность — бот автоматически контролирует этот процесс.

✅ Ключи остаются активными, и вам больше не нужно тратить время на их проверку!

⚠️ Внимание: кластеры работают только при включенном парсинге ключевых слов. Убедитесь, что эта функция активирована для максимальной эффективности!

Если нужна помощь с настройкой кластеров или включением парсинга — пишите мне! Я помогу вам настроить всё быстро и без лишних сложностей.

📩 @skyline360_1    
    
    """

    image = 'images_for_sendings/108.jpg'



class Single_message109(Text):
    text = """
    Вы не запустили ещё ни одной рекламной кампании — самое время это исправить! 📈

Я помогу вам бесплатно настроить бота и запустить рекламу на Wildberries, чтобы ваши товары начали приносить прибыль уже сейчас.

Что даст вам бот?

🔹    Полная автоматизация рекламных кампаний — бот сам управляет процессом, освобождая ваше время.
🔹    Эффективное использование бюджета — вложенные средства будут работать с максимальной отдачей.
🔹    Моя поддержка на каждом этапе — помогу вам настроить всё с нуля, быстро и без сложностей.

🚀 Напишите мне прямо сейчас, и я помогу вам запустить первую рекламную кампанию, используя средства на вашем счёте!

📩 @skyline360_1
    
"""


class FilterByQuery(Text):
    text = """
    Введите минимальное число прогнозируемых показов для показа (0 - без фильтрации): 
    """


class Single_message110(TextWithKeyboard):


    text = """
Не получилось настроить бота или что-то пошло не так? Давайте я помогу! 🙌

Если вы уже пробовали использовать наш бот, но что-то не сработало или вы не до конца разобрались в настройках — это не проблема!

💡 Пишите мне, и я помогу вам бесплатно настроить бота, объясню все шаги и покажу, как эффективно запустить рекламу. Вы получите поддержку на каждом этапе, и вам не придётся разбираться во всём самостоятельно.
Что вам это даст?

    Личная помощь и настройка — я проведу вас через весь процесс.
    Ответы на все вопросы — объясню всё простыми словами.
    Полная готовность к запуску — вы сможете начать использовать бота с уверенностью.

🚀 Напишите мне прямо сейчас, и мы вместе запустим вашу рекламную кампанию без лишних сложностей!

📩 @skyline360_1    
    
    """


class Single_message111(TextWithKeyboard):
    async def  __call__(self, wb_user_cabinets: list[WBUserCabinet]):
        self._wb_user_cabinets = wb_user_cabinets
        await super().__call__()


    text = """
  ⏳ Последние сутки акции "Удвоение пополнений"!

❗️Мы снизили минимальный платёж до тысячи рублей!

Осталось всего 24 часа до завершения нашей акции, когда каждый ваш платёж удваивается. Это отличная возможность увеличить свой баланс, если вы планировали пополнить счёт.

💡 В чём суть?

🔸    На любую сумму пополнения вы получите 100% бонус.
🔸    Акция действует только до 18:00 вторника (завтра).
🔸    Если вы уже думали о пополнении — сейчас самое время, чтобы сделать это с дополнительной выгодой.

Акция подходит к концу, но вы ещё успеваете воспользоваться ей на полную. Всё решаете вы — никаких обязательств, только возможность получить больше. """

    @property
    def keyboard(self):
        return keyboards.get_payment_keyboard_for_shops(self._wb_user_cabinets)


class Single_message112(TextWithKeyboard):

    async def  __call__(self, wb_user_cabinets: list[WBUserCabinet]):
        self._wb_user_cabinets = wb_user_cabinets
        await super().__call__()

    text = """
 ⏳ До окончания акции "Удвоение пополнений" осталось всего несколько часов!

❗️ Акция завершается сегодня в 18:00, и у вас ещё есть возможность удвоить свой баланс! Напоминаем, что минимальный платёж — всего 1000 рублей.

💡 Что вы получаете?

🔸    100% бонус на каждое пополнение на любую сумму
🔸    Увеличенный баланс для будущих возможностей и успехов

Если вы планировали пополнить счёт — сегодня последний шанс получить двойную выгоду.   
    
    
    
    """



    @property
    def keyboard(self):
        return keyboards.get_payment_keyboard_for_shops(self._wb_user_cabinets)


class KeywordStatUpdated(Text):
    text = """Статистика из WB успешно загружена, подгружаю страницу"""


class MinusKeywordsUpdated(Text):
    text = "Минус-слова успешно обновлены, подгружаю страницу"






class Single_message113(TextWithKeyboard):

    async def  __call__(self, wb_user_cabinets: list[WBUserCabinet]):
        self._wb_user_cabinets = wb_user_cabinets
        await super().__call__()



    text = """
 ⏳ Остался всего 1 час до окончания акции "Удвоение пополнений"!

Акция завершится уже в 18:00, и это ваш последний шанс удвоить сумму пополнения.

🎯 Что важно помнить?

🔹    100% бонус на сумму пополнения от 1000 рублей.
🔹    Акция действует ещё 1 час — не упустите эту возможность!

Если планировали пополнить счёт — сделайте это сейчас и получите двойную выгоду! Время на исходе!"""

    @property
    def keyboard(self):
        return keyboards.get_payment_keyboard_for_shops(self._wb_user_cabinets)


class StrategySetting(TextWithKeyboard):

    async def __call__(self, adv_setting_id):
        async with _sm() as session:
            stmt = select(AdvSetting)\
            .where(AdvSetting.id == adv_setting_id)
            result = await session.execute(stmt)
            adv_setting = result.scalars().first()
            self.adv_setting = adv_setting
            await super().__call__()


    @property
    def text(self):
        text = f"""Настройка стратегии\n
        Текущая стратегия: {'Минимальный CTR' if not self.adv_setting.target_ctr_mode else 'Целевой CTR'}\n
        """
        if self.adv_setting.target_ctr_mode:
            text += f"""{'Агрессивный режим' if self.adv_setting.target_ctr_mode_strategy == 'forward' else 'Поддерживающий режим'}\n"""

        return text

    @property
    def keyboard(self):
        builder = InlineKeyboardBuilder()
        if self.adv_setting.target_ctr_mode is True:
             button = InlineKeyboardButton(text="Включить стратегию Минимальный CTR",
                                        callback_data=callbacks.StrategySetting(
                                            action="turn_on_min_ctr",
                                            adv_setting_original_id=self.adv_setting.id).pack())
             builder.row(button)
             if self.adv_setting.target_ctr_mode_strategy == 'keep':
                 button = InlineKeyboardButton(text="Включить Агрессивный Режим",
                                        callback_data=callbacks.StrategySetting(
                                            action="turn_on_forward_mode",
                                            adv_setting_original_id=self.adv_setting.id).pack())
                 builder.row(button)
             elif self.adv_setting.target_ctr_mode_strategy == 'forward':
                 button = InlineKeyboardButton(text="Включить Поддерживающий Режим",
                                        callback_data=callbacks.StrategySetting(
                                            action="turn_on_keep_mode",
                                            adv_setting_original_id=self.adv_setting.id).pack())
                 builder.row(button)

        else:
            button = InlineKeyboardButton(text="Включить стратегию Целевой CTR",
                                            callback_data=callbacks.StrategySetting(
                                            action="on_target_ctr",
                                            adv_setting_original_id=self.adv_setting.id).pack())
            builder.row(button)

        button = InlineKeyboardButton(text="Вернуться к настройкам кампании",
                                      callback_data=callbacks.Adv(adv_original_id=self.adv_setting.id).pack())
        builder.row(button)
        return builder.as_markup()


class Single_message115(TextWithImage):

    parse_mode='Markdown'

    text = """
    ⚡️Ваша выручка на WB взлетит в космос, если вы поймете это🚀

    ➡️На продаже сезонных товаров можно делать x2-x5, и для этого не нужно делать ничего сверхъестественного!

    👉Просто приходите [на живой эфир](https://t.me/start_nawb_bot?start=link_GO377LwN5k), где вы получите секреты «сезонки»-2024-2025

    Именно [эти алгоритмы](https://t.me/start_nawb_bot?start=link_GO377LwN5k) помогли селлерам сделать рекордную выручку на школьных товарах в августе🔥

    🎁Переходите в бота, жмите старт и сразу получите доступ к сервисам-помощникам: [@Sezonka_WB](https://t.me/start_nawb_bot?start=link_GO377LwN5k)"""

    image = './images_for_sendings/1.jpg'



class Single_message115(Text):

    text = """
Привет! 👋

Если у Вас возникли сложности с настройкой бота или что-то осталось непонятным — не волнуйся, такое бывает. Просто напишите мне, и я помогу разобраться и всё настроить правильно. Это бесплатно, так что можешь спокойно обращаться.

Если Вы уже писали, но я не ответил — не стесняйся напомнить о себе. Иногда сообщений приходит много, и я могу случайно пропустить или забыть. Пишите ещё раз, и я обязательно помогу.

📩 @skyline360_1
    
    """

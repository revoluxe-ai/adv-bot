import typing
from datetime import datetime
import re
from datetime import timedelta
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import NoResultFound
from app import utils
from app.modules.calculated_keywords_redis_cache_manager.redis_manager import RedisCalculatedKeywordsCacheManager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.models import WBItemPosition, WBBalancePayment
from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.modules.wb_adv_updater import data_manager
from aiogram.enums import ParseMode
from aiogram.utils import deep_linking
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from app.modules.common_advs_stat import CommonAdvsStatDataManager
from app.modules.wb_update_state_manager import KeywordStatUpdateState, AdvActiveKeywordUpdateStateManager
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker as sm
from aiogram.fsm.context import FSMContext
from app.modules.common_slaves.wildberries.models import (WBUserCabinet,
                                                          AdvSetting,
                                                          KeywordSetting, WBCabinet)
from app.utils import redis_manager
from app.utils.pricer.pricer import Pricer
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
from ...const import DEFAULT_BIDDER_STEP
from ...message_manager import LastMessage

if TYPE_CHECKING:
    from ...utils import KeywordForKeyboard
from .import texts
logger = logging.getLogger(__name__)



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
    text = ('Ошибка настройки прав: нет доступа в контенту.'
            ' Пожалуйста, создайте новый API-ключ с требуемыми правами и попробуйте снова.')


class AdvCompanyChoicing(TextWithKeyboardPagination):
    def __init__(self,
                 bot: Bot,
                 chat_id: int,
                 wb_user_cabinet_original_id: int,
                 adv_settings: list[AdvSetting],
                 state,
                 page: int = 1):
        self._state = state
        super().__init__(bot, chat_id)
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._adv_settings = adv_settings
        self._page = page  # Устанавливаем страницу из параметра
        self._keywords_filter = None  # Инициализируем фильтр ключевых слов

    @staticmethod
    async def _get_wb_cabinet(wb_cabinet_original_id: int):
        async with sm() as session:
            stmt = select(WBCabinet)\
                .where(WBCabinet.id == wb_cabinet_original_id)
            result = await session.execute(stmt)
            wb_cabinet = result.scalar()
            return wb_cabinet

    async def __call__(self) -> (LastMessage, str):
        await self._state.set_state(states.AdvCompanyCatalog.waiting_for_keywords_for_filter)
        # Сортируем кампании на активные и неактивные
        active_advs = []
        inactive_advs = []
        for adv in self._adv_settings:
            if adv.active_status and adv.bot_active:
                active_advs.append(adv)
            else:
                inactive_advs.append(adv)
        adv_settings = active_advs + inactive_advs
        adv_settings: list[AdvSetting] = await self._filter_advs(adv_settings)
        self._adv_settings = adv_settings
        stmt = (select(WBCabinet.id)
                .where(WBCabinet.wb_user_cabinets
                    .any(WBUserCabinet.id==int(self._wb_user_cabinet_original_id))))
        async with sm() as session:
            result = await session.execute(stmt)
            wb_cabinet_original_id = result.scalar()
        await self._state.update_data(
            last_wb_cabinet_original_id=wb_cabinet_original_id,
            last_wb_user_cabinet_original_id=self._wb_user_cabinet_original_id,
            last_wb_user_cabinet_page=self._page
        )
        # self._adv_settings = await data_manager.set_worst_promo_position(self._adv_settings)
        return await super().__call__()

    async def _filter_advs(self, adv_settings: list[AdvSetting]) -> list[AdvSetting]:
        state_data = await self._state.get_data()
        keywords_filter: list[str] | None = state_data.get('filter_advs')
        self._keywords_filter = keywords_filter
        if keywords_filter:
            clear_advs = []
            for adv in adv_settings:
                if not adv.bot_active and adv.active_status == adv.ActiveStatuses.DONE:
                    continue
                name = adv.name
                nmids = list(adv.nmids)
                nmids = [str(nmid) for nmid in nmids]
                nmids_str = ' '.join(nmids)
                name = name + ' ' + nmids_str
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
                '❓ - кампания не проверялась в течение последних 24 часов\n'
                '\n📊 Активные кампании отображаются первыми\n'
                '🔄 Неактивные кампании отображаются после активных')

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


class AdvSettingMenu(TextWithKeyboardAndImage):
    # parse_mode = ParseMode.HTML

    def __init__(self, bot: Bot,
                 chat_id: int,
                 wb_user_cabinet: WBUserCabinet,
                 adv: AdvSetting):
        super().__init__(bot, chat_id)
        self._bot = bot
        self._chat_id = chat_id
        self.adv = adv
        self.wb_user_cabinet = wb_user_cabinet

    async def __call__(self):
        try:
            self._min_ctr = await data_manager.get_min_ctr(self.adv)
            if not self._min_ctr:
                raise NoResultFound
        except NoResultFound:
            self._min_ctr = 'Минимальный CTR не определен'

        self.in_favorites_user: bool = await data_manager.is_adv_in_favorites(self.adv.id,
                                                                              self.wb_user_cabinet.user_id)

        full_stat_update_time = await self._get_last_full_stat_update(self.adv.adv_id)
        self.full_stat_update_time = full_stat_update_time if full_stat_update_time else 'Нет данных'

        try:
            nmids = self.adv.nmids
            images = await data_manager.get_main_photos(nmids[:1])
            image = images[0]
            self.image = image
        except:
            await NoMainPhotos(self._bot, self._chat_id)(self.adv)
            return

        last_update_keyword_stat: datetime = await self._get_last_update_keyword_stat(self.adv.adv_id)
        if last_update_keyword_stat:
            self.last_update_keyword_stat_str = last_update_keyword_stat.strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.last_update_keyword_stat_str = 'Нет данных'

        self.keywords_status_last_update_auto_adv = await self._get_last_keywords_status_update_timestamp(
            self.adv.adv_id)

        if not self.keywords_status_last_update_auto_adv:
            self.keywords_status_last_update_auto_adv = 'Нет данных'

        if (search_adv_id := self.adv.search_adv_id):
            self.keywords_status_last_update_search_adv = await self._get_last_keywords_status_update_timestamp(
                search_adv_id)
            if self.keywords_status_last_update_search_adv is None:
                self.keywords_status_last_update_search_adv = 'Нет данных'
        else:
            self.keywords_status_last_update_search_adv = 'Аукцион не подключен к РК'

        adv_stat: FullAdvStat \
            = await data_manager.get_full_adv_stat_for_adv_id_from_redis(adv_id=self.adv.adv_id)

        self.adv_stat = adv_stat

        # self.bid_update_time: datetime  = await redis_manager.get_last_bid_update(self.adv.adv_id)
        # self.bid_update_time = self.bid_update_time.timestamp()
        await super().__call__()

    @property
    def text(self):
        max_cpc = self.adv.max_cpc
        if not max_cpc:
            max_cpc_text = 'Максимальная стоимость клика не установлена'
        else:
            max_cpc_text = f'Максимальная стоимость клика: {max_cpc} р.'

        text = (
            f'📢 Кампания: {self.adv.name}\n'
            f'🆔 ID кампании: {self.adv.adv_id}\n'
            f'📌 Статус: {self.adv.active_status}\n'
            f'🎯 Минимальный CTR для кампании: {round(self._min_ctr*100, 2)} %\n'
            f'🔢 Минимальное количество показов для прогноза CTR: {self.adv.min_views_for_ml_predict}\n'
            f'Последнее обновление обобщенной статистики ключевых слов в базе: {self.last_update_keyword_stat_str}\n'
            f'Последнее обновление минус-слов в авто-кампании: {self.keywords_status_last_update_auto_adv}\n'
            f'Последнее обновление минус-слов в аукционе: {self.keywords_status_last_update_search_adv}\n'
            f'Последнее обновление полной статистики: {self.full_stat_update_time}\n'
            # f'Последнее обновление ставки: {self.bid_update_time}'
        )

        adv_stat = self.adv_stat

        if adv_stat:

            days_stat = adv_stat.days

            days_stat = sorted(days_stat, key=lambda x: x.date)

            stat_text = 'Статистика по дням:\n'
            stat_text += 'Дата | Заказы | Себестоимость заказа\n'
            stat_text += '--------------------------------\n'

            def reverse_date(date_str):
                parts = date_str.split('-')
                if len(parts) == 3:
                    return '-'.join(reversed(parts))
                else:
                    raise ValueError("Неправильный формат даты. Ожидается 'дата-месяц-год'.")

            for day_stat in days_stat[-5:]:
                date = day_stat.date
                date = reverse_date(date)
                date = date.replace('T03:00:00+03:00', '')
                spend = day_stat.sum
                orders = day_stat.orders
                if orders:
                    cost_per_order = spend / orders
                else:
                    cost_per_order = 0
                stat_text += f'{date} | {orders} | {round(cost_per_order, 0)} р.\n'

            text += stat_text
        text += f'{max_cpc_text}'

        return text

    @property
    def keyboard(self):
        return keyboards.get_adv_setting_keyboard(self.wb_user_cabinet,
                                                  self.adv,
                                                  self.in_favorites_user)

    @staticmethod
    def _get_last_update_keyword_stat(adv_id) -> datetime:
        last_update_keyword_stat_manager = KeywordStatUpdateState()
        last_update_keyword_stat_for_complex_adv = last_update_keyword_stat_manager.get_one(adv_id)
        return last_update_keyword_stat_for_complex_adv

    @staticmethod
    async def _get_last_keywords_status_update_timestamp(adv_id: int) -> datetime:
        last_update_keyword_status_manager = AdvActiveKeywordUpdateStateManager()
        timestamp = await last_update_keyword_status_manager.get_one(adv_id)
        return timestamp

    @staticmethod
    async def _get_last_full_stat_update(adv_id: int) -> datetime:
        last_full_stat_update = await data_manager.get_last_full_stat_update(adv_id)
        return last_full_stat_update


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

        self.__cabinet_name = cabinet_name
        super().__init__(bot, chat_id)

        self._image = 'app/client_bot/images/static/api_setting.png'

    @property
    def text(self):
        return (f'Пришлите новый Api ключ дла магазина (кабинета) {self.__cabinet_name}.\n'
                 'Для работы бота нужны права Контент,  Продвижение и Аналитика')

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
        image_mode='graphic'
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
        self.image_mode = image_mode

    async def __call__(self, state: FSMContext, sort_mode='by_adv') -> (LastMessage, str):
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
        
        # Получаем данные через CommonAdvsStatDataManager
        common_stat_data_manager = CommonAdvsStatDataManager()
        stat_data = await common_stat_data_manager.get_data(self._adv_setting,
                                                             self._keywords,
                                                             2)
        
        # Устанавливаем полученные данные
        self.min_ctr = stat_data.min_ctr
        self.auto_cpm = stat_data.auto_cpm
        self.auction_cpm = stat_data.auction_cpm
        self.total_spend = stat_data.total_spend
        self.addition_spend_in_adv = stat_data.addition_spend_in_adv
        self._all_orders_for_last_days = stat_data.all_orders_for_last_days
        self._mean_orders_for_days = stat_data.mean_orders_for_last_days
        self._mean_price_for_order = stat_data.mean_price_for_order
        self._spend_for_inner_adv_for_3_days = stat_data.spend_for_inner_advs
        self.full_adv_stat_for_last_days_for_auto_adv = stat_data.full_adv_stat_for_last_days_for_auto_adv
        self.full_adv_stat_for_last_days_for_auction = stat_data.full_adv_stat_for_last_days_for_auction
        self.common_stat = stat_data.common_stat
        if self._all_orders_for_last_days is not None:
            self._sum_spend = self._spend_for_inner_adv_for_3_days
        if self.image_mode == 'graphic':
            graphic = await self._graphic_injection()
            if not graphic:
                graphic = 'app/core/telegram/static_images/not_keywords_position_graphic.jpg'
            self._image = graphic
        await super().__call__()
        return

    @property
    def text(self) -> str:
        total_page = len(self._keywords) // self._on_page
        text = (
                'Название кампании: ' + str(self._adv_setting.name) + '\n'
                f'Статус: {self._adv_setting.active_status}\n'
                f"""Бот {'Включен' if self._adv_setting.bot_active else 'Выключен'}\n"""
                'ID кампании: ' + str(self._adv_setting.adv_id) + '\n'
                f'ID Аукциона: {self._adv_setting.search_adv_id}\n'
                f'Общая статистика за 3 дня:\n'
                f'Минимальный CRT для кампании: {self.min_ctr * 100:.2f}%\n'
                f'Страница: {self._page}/{total_page + 1}\n'
                f'Экспонента прог.CTR: {self._adv_setting.exponent_predict_ctr}\n'
                f'Общий расход на рекламу: {self.total_spend:.2f}\n'
                f'Расход на доп.трафик в Авто: {self.addition_spend_in_adv:.2f} р.\n'
                f'Общее число заказов: {self._all_orders_for_last_days}\n'
                f'Заказов из Авто: {self.full_adv_stat_for_last_days_for_auto_adv.orders}\n'
                f'Заказов из Аукцион: {self.full_adv_stat_for_last_days_for_auction.orders}\n'
                f"""Заказов из Органики: {self._all_orders_for_last_days
                    - self.full_adv_stat_for_last_days_for_auction.orders
                    - self.full_adv_stat_for_last_days_for_auto_adv.orders
                if self._all_orders_for_last_days else 0}"""
        )

        # Получаем целевые значения из настроек
        plan_for_sales_for_day = self._adv_setting.plan_for_sales_for_day
        plan_for_sales_for_day_str = str(round(plan_for_sales_for_day)) if plan_for_sales_for_day else "Не задано"

        target_price_for_order = self._adv_setting.target_price_for_order
        target_price_for_order_str = str(round(target_price_for_order)) if target_price_for_order else "Не задано"

        max_price_for_order = self._adv_setting.max_price_for_order
        max_price_for_order_str = str(round(max_price_for_order)) if max_price_for_order else "Не задано"

        order_cost = self._spend_for_inner_adv_for_3_days / self._all_orders_for_last_days\
            if self._all_orders_for_last_days else self._spend_for_inner_adv_for_3_days

        text += (
            f'\nВ среднем в день (срез за 3 дня):\n'
            f'Заказов: {self._mean_orders_for_days:.2f} (цель: {plan_for_sales_for_day_str})\n'
            f'Себестоимость: {round(order_cost, 2)} р.'
            f' (цель: {target_price_for_order_str}, макс: {max_price_for_order_str})\n'
        )

        text += f'\nСтавка из Авто: {self.auto_cpm} р. '
        text += f"""(Биддер для Авто: {' Включен' if self._adv_setting.bidder_for_auto else ' Выключен'})\n"""
        text += f"Ставка из Аукциона: {self.auction_cpm}\n"
        text += f"Целевая позиция: {self._adv_setting.max_place}\n"
        text += f"Максимальная ставка: {self._adv_setting.max_cpm}\n"
        return text

    @property
    def image(self) -> str:
        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    async def _graphic_injection(self):
        bot = self.bot
        user_telegram_id = self.chat_id
        adv_original_id = self._adv_setting.id
        result = (await utils.get_keyword_history_graphic(adv_original_id,
                                                          self._keywords))
        if not result:
            graphic = None
            legend = None
        else:
            graphic, legend = result
        if legend:
            await KeywordGraphicPart_1(bot, user_telegram_id, graphic, adv_original_id)()
            return legend
        return graphic

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
                                                       sort_mode=self.sort_mode,
                                                       image_mode=self.image_mode)

class KeywordSettingMessage(TextWithKeyboard):
    parse_mode = ParseMode.MARKDOWN

    def __init__(self, bot: Bot, chat_id: int,
                 keyword_setting_id,
                 last_page: int):
        super().__init__(bot, chat_id)
        self._keyword_original_id = keyword_setting_id
        self._page = last_page

    async def _get_calculated_keyword(self):
        redis_manager = RedisCalculatedKeywordsCacheManager()
        keyword = await redis_manager.get_calculated_keyword(self._adv_setting.adv_id,
                                                             self._keyword_setting.text)
        return keyword


    async def __call__(self) -> (LastMessage, str):
        auto_block_status = await redis_manager.get_auto_block_status(self._keyword_original_id)
        self._auto_block_status = auto_block_status
        async with sm(read_only=True) as session:
            stmt = select(KeywordSetting)\
                          .options(selectinload(KeywordSetting.adv_setting))\
                          .where(KeywordSetting.id == self._keyword_original_id)
            result = await session.execute(stmt)
            keyword_setting: KeywordSetting = result.scalars().one()
        adv_setting: AdvSetting = keyword_setting.adv_setting
        self._keyword_setting = keyword_setting
        self._adv_setting = adv_setting
        nmid = int(adv_setting.nmids[0])
        adv_id = int(self._adv_setting.adv_id)
        text = str(self._keyword_setting.text)
        position: WBItemPosition = await redis_manager.get_keyword_position(str(keyword_setting.text),
                                                                            nmid)
        self.position = position
        if position:
            self.last_full_update = position.timestamp.strftime('%d-%m-%Y %H:%M')
        else:
            self.last_full_update = None

        async with get_clickhouse_client() as client:
            total_clicks, total_views, total_spend\
                = await data_manager.get_keyword_statistic_clickhouse(client, text, adv_id)
        self.clicks = total_clicks
        self.views = total_views
        self.fact_ctr = total_clicks / total_views if total_views else 0

        self.original_predict_ctr =  await redis_manager.get_predict_ctr(adv_id, text)

        self.spend = total_spend
        self.calculated_keyword = await self._get_calculated_keyword()
        return await super().__call__()

    @property
    def text(self) -> str:
        keyword_text = self._keyword_setting.text
        keyword_text  = re.sub(r'([_*[\]()~>`#+\-=|{}.!])', r'\\\1', keyword_text)
        nmids = list(self._adv_setting.nmids)
        nmids = [str(nmid) for nmid in nmids]
        nmids_str = ', '.join(nmids)
        text = (f"""Артикул: {nmids_str}\n"""
                f'🔑 *Статистика и настройка ключевого слова:* \n\n {keyword_text}\n\n'
                f'📈 *Показы:* {self.views}\n'
                f'🖱 *Клики:* {self.clicks}\n'
                f'Прогнозируемый CTR: {self.original_predict_ctr*100 if self.original_predict_ctr else "Не просчитан"}%\n'
                f'📊 *Фактический CTR:* {self.fact_ctr*100}%\n'
                f'💰 *Расход:* {round(self.spend, 2)} руб.\n')
        if self.position:
            text += (f'🏆 *Органическая позиция:* {self.position.base_position}\n'
                     f"""🚀 *Буст-позиция:* {self.position.promo_position if self.position.promo_position else "Нет"}\n"""
                     f"""💰 *Ставка из выдачи WB :* {self.position.cpm if self.position.cpm else "Нет"}\n"""
                     f"""🕒 *Последнее обновление позиций:* {self.last_full_update if self.last_full_update else "Нет"}\n"""
                     f"""Тип кампании: {self.position.type_native if self.position.type_native else "Нет"}\n""")

        else:
            text += '📉 *Позиция на Wildberries:* не определена\n'

        return text

    @property
    def keyboard(self):
        return keyboards.get_keyword_setting_keyboard(self._keyword_setting,
                                                      self.calculated_keyword,
                                                      self._adv_setting,
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
    text = 'Для использования функций вы должны быть подписаны на канал службы поддержки'


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



class OrderSubscribe(Text):

    text = f"В случае проблем с оплатой свяжитесь по этому контакту -> {const.SUPPORT_LINK}"


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
                f'Если возникнут проблемы, то напишите сюда -> {const.SUPPORT_LINK}')
        return text



class ExpiredSubscription(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id: int, wb_cabinet_original_id: int):
            self._wb_cabinet_original_id = wb_cabinet_original_id
            super().__init__(bot, chat_id)

    async def __call__(self):
            async with sm() as session:
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
        async with sm() as session:
            adv = await session.execute(select(AdvSetting).where(AdvSetting.id == adv_original_id))
            adv: AdvSetting = adv.scalar()
        self._adv: AdvSetting = adv
        self._min_ctr = await data_manager.get_min_ctr(adv)
        if  adv.new_auto_min_ctr_mode:
            self._min_ctr_type = "auto"
        else:
            self._min_ctr_type = 'direct'

        keywords: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv)

        keywords_with_rating = [kw for kw in keywords if kw.rating_by_predict_ctr > 0]
        keywords_with_rating.sort(key=lambda x: x.rating_by_predict_ctr, reverse=True)
        keywords_without_rating = [kw for kw in keywords if kw.rating_by_predict_ctr == 0]
        keywords_with_rating.sort(key=lambda x: x.predict_ctr, reverse=True)
        keywords = keywords_with_rating + keywords_without_rating

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
                f"""тип минимального CTR: {"Задан в ручную"  if not self._adv.new_auto_min_ctr_mode
                    else "Определен автоматически"}\n""")

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
        async with sm() as session:
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
            async with sm() as session:
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


class IncorrectMinViewsForPredictCTR(TextWithKeyboard):

    def __init__(self, bot: Bot, chat_id, adv: AdvSetting):
        super().__init__(bot, chat_id)
        self._adv = adv


    text = 'Минимальное количество показов должно быть целым числом от 0 и больше. Попробуйте снова:'

    @property
    def keyboard(self):
        return keyboards.get_setting_min_views_for_predict_ctr_keyboard(self._adv)

class WaitingForAmount(Text):
    DISABLE_WEBPAGE_PREVIEW = True
    def __init__(self, bot: Bot, chat_id, master_sum: float, current_balance: float = None, current_bonus: float = None):
        super().__init__(bot, chat_id)
        self.master_sum = master_sum
        self._pricer = Pricer()
        self.current_balance = current_balance
        self.current_bonus = current_bonus

    @property
    def text(self):
        text = self._pricer.text
        # Добавляем информацию о текущем балансе, если она доступна
        if self.current_balance is not None:
            text = f"💰 Текущий баланс: {self.current_balance:.0f} руб.\n"
            
            if self.current_bonus is not None and self.current_bonus > 0:
                text += f"🎁 Текущие бонусы: {self.current_bonus:.0f} руб.\n"
            
            text += "\n" + self._pricer.text

        text += "\nУкажите сумму пополнения:"
        return text


class BalanceUpdated(Text):
    def __init__(self, bot: Bot, chat_id, added_balance: float, bonus: float):
        super().__init__(bot, chat_id)
        self.__balance = added_balance
        self.__bonus = bonus
        self._image = None



    @property
    def text(self):
        return f'Баланс успешно пополнен на {self.__balance} рублей + бонус {self.__bonus} рублей'


class Top10ByViewsKeywordsGraphic(TextWithKeyboardAndImage):

    def __init__(self, bot, chat_id):
        self._image = None
        super().__init__(bot, chat_id)


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
        async with sm() as session:
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

        button_text = "Выключить управление ставкой для Авто" if self.adv_setting.bidder_for_auto else "Включить управление ставкой для Авто"
        callback_action = "off_bidder_for_auto" if self.adv_setting.bidder_for_auto else "on_bidder_for_auto"

        bottom = InlineKeyboardButton(
            text=button_text,
            callback_data=callbacks.CPMSettingMenu(
                action=callback_action,
                adv_original_id=self.adv_setting.id
            ).pack()
        )

        builder.row(bottom)

        bottom = InlineKeyboardButton(text = 'Изменить ставку (Максимальную ставку)',
                                      callback_data = callbacks.CPMSettingMenu(
                                          action = 'set_manual_cpm',
                                          adv_original_id = self.adv_setting.id).pack())

        builder.row(bottom)
        step = self.adv_setting.bidder_step
        step = step if step else DEFAULT_BIDDER_STEP
        bottom = InlineKeyboardButton(text=f'Изменить шаг ставки ({step})',
                                        callback_data=callbacks.CPMSettingMenu(
                                            action='change_cpm_step',
                                            adv_original_id=self.adv_setting.id).pack())

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
        async with sm() as session:
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


class FilterByQuery(Text):
    text = """
    Введите минимальное число прогнозируемых показов для показа (0 - без фильтрации): 
    """


class KeywordStatUpdated(Text):
    text = """Статистика из WB успешно загружена, подгружаю страницу"""


class MinusKeywordsUpdated(Text):
    text = "Минус-слова успешно обновлены, подгружаю страницу"





class WhiteListReset(Text):
    text = "Белый список успешно сброшен"



class RelevantPhrasesAdded(TextWithKeyboard):

    def __init__(self, bot, user_telegram_id, adv_setting_id):
        self.adv_setting_id = adv_setting_id
        super().__init__(bot, user_telegram_id)

    text = "Фразы успешно добавлены в бот (авто) список"

    @property
    def keyboard(self):
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)


class WaitingForRelevantPhrases(Text):
    text = "Введите фразы, которые вы хотите добавить в кампанию в качестве релевантных фраз:"


class ShowFavoriteAdvs(TextWithKeyboard):
    text = '''Ваши избранные рекламные кампании:'''
    def __init__(self, bot, user_telegram_id):
        self.user_telegram_id = user_telegram_id
        super().__init__(bot, user_telegram_id)

    async def __call__(self):
        async with sm() as session:
            stmt = select(User)\
            .options(joinedload(User.favorites_advs))\
            .join(User.favorites_advs)\
            .where(User.user_telegram_id == self.user_telegram_id)
            result = await session.execute(stmt)
            user = result.scalars().first()
            self.user = user
            try:
                 advs: list[AdvSetting] = user.favorites_advs
            except:
                await self.bot.send_message(self.user_telegram_id, text="У вас нет избранных кампаний,"
                                                                        " добавить кампании в избранное вы сможете отдельно в каждом магазине"
                                                                        ". После этого сможете управлять всеми кампаниями ваших магазинов в одном месте.")
                return
        await super().__call__()

    @property
    def keyboard(self):
         keyboard = keyboards.get_advs_list(self.advs)
         return keyboard

async def process_cabinet_balance_topup(user_id: int, cabinet_id: int, amount: float):
    """Обработка запроса на пополнение баланса кабинета"""
    async with sm() as session:
        # Получаем пользователя для описания платежа
        user = await session.get(User, user_id)
        if not user:
            raise ValueError("Пользователь не найден")
            
        # Создаем запись о платеже
        payment = WBBalancePayment(
            wb_cabinet_id=cabinet_id,
            amount=amount,
            description=f"Пополнение баланса пользователем {user.username or user.user_telegram_id}",
            transaction_date_time=datetime.now()
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment

async def confirm_cabinet_balance_topup(payment_id: int, cabinet_id: int):
    """Подтверждение платежа и обновление баланса кабинета"""
    async with sm() as session:
        # Получаем платеж
        payment = await session.get(WBBalancePayment, payment_id)
        if not payment or payment.wb_cabinet_id != cabinet_id:
            raise ValueError("Платеж не найден или не соответствует кабинету")
        
        # Получаем кабинет
        cabinet = await session.get(WBCabinet, cabinet_id)
        if not cabinet:
            raise ValueError("Кабинет не найден")
        
        # Обновляем баланс кабинета
        cabinet.balance += payment.amount
        
        await session.commit()
        await session.refresh(payment)
        await session.refresh(cabinet)
        return payment, cabinet

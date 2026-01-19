# mypy: ignore-errors
# TODO: Глушу ошибки, их тут дофига, но надо разобраться потом
import logging
import re
from datetime import datetime
from operator import attrgetter
from typing import TYPE_CHECKING
from datetime import date as date_type
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    Message,
    InlineKeyboardMarkup,
)
from aiogram.utils import deep_linking
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dependency_injector.wiring import inject, Provide
from sqlalchemy import select

from app.client_bot import const, utils
from app.client_bot.const import DEFAULT_BIDDER_STEP
from app.client_bot.user_interface import states
from app.client_bot.user_interface.message_templates.templates import (
    Text,
    TextWithImage,
    TextWithKeyboard,
    TextWithKeyboardAndImage,
    TextWithKeyboardPagination,
)
from app.client_bot.user_interface.views import callbacks, keyboards
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBBalancePayment,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.models import PredictCTRMode
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat, DayStats
from app.modules.relevant_phrase_manager import RelevantPhraseManager
from app.modules.wb_adv_updater import data_manager, phrases_processor
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatusReason, KeywordStatus
from app.modules.wb_update_state_manager import (
    AdvActiveKeywordUpdateStateManager,
    KeywordStatUpdateState,
)
from app.shared.domains.wb.enums import (
    AdvType,
)
from app.utils import redis_manager
from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_cluster_bids_timestamp_manager import (
    RedisClusterBidsTimestampManager,
)
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# def reverse_date(date_str: str) -> str:
#     parts = date_str.split("-")
#     if len(parts) == 3:
#         return "-".join(reversed(parts))
#     else:
#         raise ValueError("Неправильный формат даты. Ожидается 'дата-месяц-год'.")


class ChangeShopDefaultMaxCPMMessage(Text):
    def __init__(self, bot: Bot, chat_id: int, current_max_cpm: int):
        super().__init__(bot, chat_id)
        self._current_max_cpm = current_max_cpm

    @property
    def text(self) -> str:
        return f"Введите новое дефолтное значение максимальной ставки (CPM). Текущее значение: {self._current_max_cpm}."


class ShopNameGet(Text):
    def __init__(self, bot: Bot, chat_id: int):
        super().__init__(bot, chat_id)

    @property
    def text(self) -> str:
        return "Введите название магазина (кабинета):"


class ShopAddedSuccess(Text):
    def __init__(self, bot: Bot, chat_id: int, cabinet_name: str) -> None:
        super().__init__(bot, chat_id)
        self.__cabinet_name = cabinet_name

    @property
    def text(self) -> str:
        return (
            f"Магазин {self.__cabinet_name} успешно добавлен, идет обновление данных..."
        )


class GetApiForrbidenError(Text):
    @property
    def text(self) -> str:
        return (
        "Ключ API введен не верно или недостаточно прав для работы с рекламой."
        " Пожалуйста, создайте новый API-ключ и с нужными правами и пришлите его снова:"
    )


class GetCardsApiError(Text):
    @property
    def text(self) -> str:
        return  (
        "Ошибка настройки прав: нет доступа в контенту."
        " Пожалуйста, создайте новый API-ключ с требуемыми правами и попробуйте снова."
    )


class AdvCompanyChoicing(TextWithKeyboardPagination):
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        wb_user_cabinet_original_id: int,
        adv_settings: list[AdvSetting],
        state: FSMContext,
        page: int = 1,
    ) -> None:
        self._state = state
        super().__init__(bot, chat_id)
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._adv_settings = adv_settings
        self._page = page  # Устанавливаем страницу из параметра
        self._keywords_filter: list[str] = []  # Инициализируем фильтр ключевых слов

    @staticmethod
    async def _get_wb_cabinet(wb_cabinet_original_id: int) -> WBCabinet | None:
        async with sm() as session:
            stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet_original_id)
            result = await session.execute(stmt)
            wb_cabinet = result.scalar()
            return wb_cabinet

    async def __call__(self) -> None:
        await self._state.set_state(
            states.AdvCompanyCatalog.waiting_for_keywords_for_filter
        )
        # Сортируем кампании на активные и неактивные
        active_advs: list[AdvSetting] = []
        inactive_advs: list[AdvSetting] = []
        for adv in self._adv_settings:
            if adv.active_status and adv.bot_active:
                active_advs.append(adv)
            else:
                inactive_advs.append(adv)
        adv_settings: list[AdvSetting] = active_advs + inactive_advs
        adv_settings_filtred: list[AdvSetting] = await self._filter_advs(adv_settings)
        self._adv_settings = adv_settings_filtred
        stmt = select(WBCabinet.id).where(
            WBCabinet.wb_user_cabinets.any(
                WBUserCabinet.id == int(self._wb_user_cabinet_original_id)
            )
        )
        async with sm() as session:
            result = await session.execute(stmt)
            wb_cabinet_original_id = result.scalar()
        await self._state.update_data(
            last_wb_cabinet_original_id=wb_cabinet_original_id,
            last_wb_user_cabinet_original_id=self._wb_user_cabinet_original_id,
            last_wb_user_cabinet_page=self._page,
        )
        # self._adv_settings = await data_manager.set_worst_promo_position(self._adv_settings)

        for adv in self._adv_settings:
            adv.check_last_24_hours = await redis_manager.check_last_24_hours(adv.id)

        return await super().__call__()

    async def _filter_advs(self, adv_settings: list[AdvSetting]) -> list[AdvSetting]:
        state_data = await self._state.get_data()
        keywords_filter: list[str] = state_data.get("filter_advs", [])
        self._keywords_filter = keywords_filter
        if keywords_filter:
            clear_advs: list[AdvSetting] = []
            for adv in adv_settings:
                if (
                    not adv.bot_active
                    and adv.active_status == adv.ActiveStatuses.DONE.value
                ):
                    continue
                name = adv.name
                nmids: list[int] = list(adv.nmids)
                nmids_str = " ".join([str(nmid) for nmid in nmids])
                name = name + " " + nmids_str
                name = name.lower()
                name += str(adv.adv_id)
                for keyword_filter in keywords_filter:
                    keyword_filter = keyword_filter.strip().lower()
                    if keyword_filter in name:
                        clear_advs.append(adv)
            adv_settings = clear_advs
        return adv_settings

    @property
    def text(self) -> str:
        return (
            "Выберите рекламную кампанию для настройки или проверки. \n"
            "✅ - кампания проверялась в течение последних 24 часов\n"
            "❓ - кампания не проверялась в течение последних 24 часов\n"
            "\n📊 Активные кампании отображаются первыми\n"
            "🔄 Неактивные кампании отображаются после активных"
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_advs_keyboard_with_paginator(
            self._wb_user_cabinet_original_id,
            self._adv_settings,
            self._page,
            self.on_page,
            self._keywords_filter,
        )

    @property
    def on_page(self) -> int:
        return 20


class ShopUpdateInfo(Text):
    @property
    def text(self) -> str:
        return "Обновление данных для магазина, немного подождите..."


class AdvSettingMenu(TextWithKeyboardAndImage):
    # parse_mode = ParseMode.HTML

    @inject
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        wb_user_cabinet: WBUserCabinet,
        adv: AdvSetting,
        redis_client: RedisClient = Provide["redis_client_wrapper"],
    ) -> None:
        super().__init__(bot, chat_id)
        self._bot = bot
        self._chat_id = chat_id
        self.adv = adv
        self.wb_user_cabinet = wb_user_cabinet
        self._redis_cluster_bids_timestamp_manager = RedisClusterBidsTimestampManager(
            redis_client
        )
        self._redis_common_stat_timestamp_manager = RedisCommonStatTimestampManager(
            redis_client
        )

    # TODO Дублирует аналогичную в app.client_bot.user_interface.views.messages.adv_keyword_messages.adv_keyword_messages.AdvKeywordsSetting._get_status_auction
    @staticmethod
    async def _get_status_auction(search_adv_id: int) -> str:
        if not search_adv_id:
            return "не подключен"
        stmt = select(AdvSetting.active_status).where(
            AdvSetting.adv_id == search_adv_id
        )
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            status = result.scalar_one_or_none()
            if not status:
                status = "РК не найдена"
            else:
                str(status)
            return status

    async def __call__(self) -> Message:
        auction_adv_id: int | None = self.adv.search_adv_id
        if auction_adv_id:
             self._status_auction = await self._get_status_auction(auction_adv_id)
        else:
            self._status_auction = "Не установлен"
        self._hard_min_ctr = self.adv.hard_min_ctr
        keywords = await utils.get_keywords_for_keyboard(self.adv)
        self._min_rating_by_orders: float | None = phrases_processor.get_min_rating_by_orders(keywords)

        self.in_favorites_user: bool = await data_manager.is_adv_in_favorites(
            self.adv.id, self.wb_user_cabinet.user_id
        )

        full_stat_update_time = await self._get_last_full_stat_update(self.adv.adv_id)
        if not full_stat_update_time:
            full_stat_update_time_str = "Нет данных"
        else:
            full_stat_update_time_str = full_stat_update_time.strftime(
                "%d.%m.%Y %H:%M:%S"
            )

        self.full_stat_update_time = full_stat_update_time_str

        nmids = self.adv.nmids
        images = await data_manager.get_main_photos(nmids[:1])
        image = images[0]
        self.image = image

        last_update_keyword_stat: datetime | None = (
            await self._get_last_update_keyword_stat(self.adv.adv_id)
        )
        if last_update_keyword_stat:
            self.last_update_keyword_stat_str = last_update_keyword_stat.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            self.last_update_keyword_stat_str = "Нет данных"

        last_update_common_stat: datetime | None = (
            await self._redis_common_stat_timestamp_manager.get(self.adv.adv_id)
        )
        if last_update_common_stat:
            self.last_update_common_stat_str = last_update_common_stat.strftime(
                "%d.%m.%Y %H:%M:%S"
            )
        else:
            self.last_update_common_stat_str = "Нет данных"

        self.keywords_status_last_update_auto_adv = (
            await self._get_last_keywords_status_update_timestamp(self.adv.adv_id)
        )

        if not self.keywords_status_last_update_auto_adv:
            self.keywords_status_last_update_auto_adv = "Нет данных"

        if search_adv_id := self.adv.search_adv_id:
            self.keywords_status_last_update_search_adv = (
                await self._get_last_keywords_status_update_timestamp(search_adv_id)
            )
            if self.keywords_status_last_update_search_adv is None:
                self.keywords_status_last_update_search_adv = "Нет данных"
        else:
            self.keywords_status_last_update_search_adv = "Аукцион не подключен к РК"

        adv_stat: FullAdvStat | None = (
            await data_manager.get_full_adv_stat_for_adv_id_from_redis(
                adv_id=self.adv.adv_id
            )
        )

        self.adv_stat: FullAdvStat | None = adv_stat

        from .last_auto_update_informer import LastAutoUpdateSettingInformer

        last_auto_setting_inform = LastAutoUpdateSettingInformer(self.adv)
        await last_auto_setting_inform.update_data()
        self._update_informer = last_auto_setting_inform
        self.last_cluster_bids_update = await self._redis_cluster_bids_timestamp_manager.get(self.adv) # noqa
        return await super().__call__()

    @property
    def text(self) -> str:
        max_cpc = self.adv.max_cpc
        if not max_cpc:
            max_cpc_text = "Максимальная стоимость клика не установлена"
        else:
            max_cpc_text = f"Максимальная стоимость клика: {max_cpc} р."

        # Determine predict CTR mode display text
        predict_ctr_mode = self.adv.predict_ctr_mode or PredictCTRMode.V1
        if predict_ctr_mode == PredictCTRMode.V1:
            predict_ctr_mode_text = "v1 (по ID кампании)"
        else:
            # TODO: Добавить отображение фото в ключах
            predict_ctr_mode_text = "v2 (по артикулам товара)"
        # TODO: Добавить когда была обновлена модель и когда обновлялся прогноз CTR
        text = (
            f"📢 Кампания: {self.adv.name}\n"
            f"🆔 ID кампании: {self.adv.adv_id}\n"
            f"📌 Статус Авто: {self.adv.active_status}\n"
            f"📌 Статус Аукциона: {self._status_auction}\n")
            # TODO: Попала ошибка в код, пытался сделать .2f строке
        if self._min_rating_by_orders is not None:
            text += f"🎯 Мин. Рейтинг по заказам для кампании: {round(self._min_rating_by_orders * 1000, 2)}\n"
        elif self._hard_min_ctr is not None:
            text += f"🎯 Мин. CTR: {round(self._hard_min_ctr, 2)}\n"
        else:
            text += f"Ограничители не заданы!"

        text += (
            f"🤖 Режим прогноза CTR: {predict_ctr_mode_text}\n"
            f"Посл. обнов. обобщенной статистики Ключей: {self.last_update_keyword_stat_str}\n"
            f"Посл. обнов. воронки: {self.last_update_common_stat_str}\n"
            f"Посл. обнов. полной рек.стат.: {self.full_stat_update_time}\n"
            f"Посл. обнов. минус-слов в авто: {self.keywords_status_last_update_auto_adv}\n"
            f"Посл. обнов. минус-слов в аук.: {self.keywords_status_last_update_search_adv}\n"
            f"Посл. обнов. ставок в кластерах: {self.last_cluster_bids_update.strftime('%d.%m.%Y %H:%M:%S') if self.last_cluster_bids_update else 'Нет данных'}\n"
            f"Посл. автом. добав. ключа в БС:"
            f" {self._update_informer.add_to_white_list_str}\n"
            f"Посл. автом. удал. ключа из БС:"
            f" {self._update_informer.delete_from_white_list_str}\n"
            f"Посл. авт. повыш. цел. позиции:"
            f" {self._update_informer.up_target_place_str}\n"
            f"Посл. авт. пониж. целевой позиции:"
            f" {self._update_informer.down_target_place_str}\n"
            f"Посл. доб верхнего ключа в БС:"
            f" {self._update_informer.update_top_key_str}\n"
        )

        adv_stat = self.adv_stat

        if adv_stat:
            days_stat: list[DayStats] = sorted(
                adv_stat.days, key=attrgetter("date")
            )
            stat_text = "Статистика по дням:\n"
            stat_text += "Дата | Заказы | Себестоимость заказа\n"
            stat_text += "--------------------------------\n"

            def reverse_date(date_: date_type) -> str:
                return date_.strftime("%d-%m-%Y")

            for day_stat in days_stat[-5:]:
                date_str = reverse_date(day_stat.date)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                spend = day_stat.sum
                orders = day_stat.orders
                if orders:
                    cost_per_order = spend / orders
                else:
                    cost_per_order = 0
                stat_text += f"{date_str} | {orders} | {round(cost_per_order, 0)} р.\n"

            text += stat_text
        text += f"{max_cpc_text}"

        return text

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_adv_setting_keyboard(
           self.wb_user_cabinet, self.adv, self.in_favorites_user
        )

    @staticmethod
    async def _get_last_update_keyword_stat(adv_id: int) -> datetime | None:
        last_update_keyword_stat_manager = KeywordStatUpdateState()
        last_update_keyword_stat_for_complex_adv = (
            await last_update_keyword_stat_manager.get_one(adv_id)
        )
        return last_update_keyword_stat_for_complex_adv

    @staticmethod
    async def _get_last_keywords_status_update_timestamp(
        adv_id: int,
    ) -> datetime | None:
        last_update_keyword_status_manager = AdvActiveKeywordUpdateStateManager()
        timestamp = await last_update_keyword_status_manager.get_one(adv_id)
        return timestamp

    @staticmethod
    async def _get_last_full_stat_update(adv_id: int) -> datetime | None:
        last_full_stat_update = await data_manager.get_last_full_stat_update(adv_id)
        return last_full_stat_update


class CabinetNameExists(Text):
    @property
    def text(self) -> str:
        return "Кабинет с таким именем уже существует, введите другое имя для кабинета:"

class CabinetExistsForUser(Text):
    @property
    def text(self) -> str:
        return "Этот кабинет уже был добавлен вам ранее. Сейчас я предоставлю вам его..."


class NotValideToken(Text):
    @property
    def text(self) -> str:
        return  "Вы ввели что-то не то. Попробуйте снова:"


class ApiForrbidenError(Text):
    def __init__(self, bot: Bot, chat_id: int, wb_user_cabinet: WBUserCabinet):
        super().__init__(bot, chat_id)
        self.__wb_user_cabinet = wb_user_cabinet

    @property
    def text(self) -> str:
        return (
        "Ошибка настройки прав: нет доступа в рекламе. Пожалуйста, "
        "создайте новый API-ключ с требуемыми правами и добавьте кабинет снова. "
        "Все ваши настройки будут сохранены"
    )


class AddNewTokenGet(TextWithImage):
    def __init__(self, bot: Bot, chat_id: int, cabinet_name: str):
        self.__cabinet_name = cabinet_name
        super().__init__(bot, chat_id)

        self._image = "app/client_bot/images/static/api_setting.png"

    @property
    def text(self) -> str:
        return (
            f"""Пришлите новый Api ключ дла магазина (кабинета) {self.__cabinet_name}.\n"""
            """Для работы бота нужны права Контент, Статистика,  Аналитика, Продвижение. Галочку 'Только для чтения'"""
            """ НЕ ставить!!!"""
        )

    @property
    def image(self) -> str:
        return self._image

    @image.setter
    def image(self, value: str) -> None:
        self._image = value


# TODO: Навести порядок с БД мастер-репликами


class GetMinCtr(Text):
    def __init__(self, bot: Bot, chat_id: int, adv: AdvSetting):
        self.__adv = adv
        super().__init__(bot, chat_id)

    @property
    def text(self) -> str:
        return (
            f"Введите новое значение минимального CTR для кампании {self.__adv.name}:"
        )


class CabinetExistsInSystem(Text):
    @property
    def text(self) -> str:
        return "Этот кабинет уже существует в системе, мы его добавим вам..."


class WrongMinCTR(Text):
    @property
    def text(self) -> str:
        return  "Минимальный CTR должен быть числом от 0 до 100. Попробуйте снова:"


class MinCTRChanged(Text):
    @property
    def text(self) -> str:
        return "Минимальный CTR успешно изменен!"


class CabinetNameTooLong(Text):
    @property
    def text(self) -> str:
        return "Название кабинета слишком длинное. Попробуйте снова(не более 50 символов):"

class KeywordSettingMessage(TextWithKeyboard):
    parse_mode = ParseMode.MARKDOWN

    def __init__(self, bot: Bot, chat_id: int, keyword_setting_id: int, last_page: int):
        super().__init__(bot, chat_id)
        self._keyword_original_id = keyword_setting_id
        self._page = last_page
        self._chat_id = chat_id

    @staticmethod
    async def _get_calculated_keyword(
        adv_id: int, text: str
    ) -> CalculatedKeyword | None:
        redis_manager_ = RedisCalculatedKeywordsCacheManager()
        keyword = await redis_manager_.get_calculated_keyword(adv_id, text)
        return keyword

    @staticmethod
    async def _get_keyword_text_and_adv_id(keyword_original_id: int,) -> tuple[KeywordSetting, AdvSetting]:
        # TODO: Поймали ошибку в рантайме
        stmt = select(KeywordSetting, AdvSetting)\
        .join(KeywordSetting.adv_setting)\
        .where(KeywordSetting.id == keyword_original_id)
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            result_row = result.first()
        if not result_row:
            raise ValueError('Не найдены данные о ключе')
        keyword: KeywordSetting = result_row[0]
        adv: AdvSetting = result_row[1]
        return keyword, adv


    @inject
    async def __call__(
        self,
        redis_manager_predict_ctr: PredictCTRRedisManager = Provide[
            PredictCTRManagerContainer.redis_manager
        ],
    ) -> None:
        keyword_setting, adv_setting = await self._get_keyword_text_and_adv_id(self._keyword_original_id)
        self._keyword_setting = keyword_setting
        keywords_redis_cache_manager = RedisCalculatedKeywordsCacheManager()
        keyword: CalculatedKeyword = await keywords_redis_cache_manager.get_calculated_keyword(adv_setting.adv_id,
                                                                                               keyword_setting.text)

        calculated_keyword = keyword
        self._calculated_keyword = calculated_keyword
        self._adv_setting = adv_setting
        self.position = calculated_keyword.position
        self.last_full_update = calculated_keyword.timestamp

        self.clicks = keyword.clicks
        self.views = keyword.views
        self.fact_ctr = keyword.ctr

        self.spend = keyword.spend
        return await super().__call__()

    @property
    def calculated_keyword(self) -> CalculatedKeyword:
        return self._calculated_keyword


    @staticmethod
    def get_str_rus_hard_status(int_hard_status: int) -> str:
        if int_hard_status == 0:
            return "Список не релевантных фраз"
        elif int_hard_status == 1:
            return "Авто"
        elif int_hard_status == 2:
            return "Белый список"
        elif int_hard_status == 3:
            return "Отключен"
        else:
            raise ValueError(f"Неизвестный хард-статус ключа: {int_hard_status}")

    @property
    def text(self) -> str:
        calculated_keyword = self.calculated_keyword
        keyword_text = self._keyword_setting.text
        keyword_text = re.sub(r"([_*[\]()~>`#+\-=|{}.!])", r"\\\1", keyword_text)  # type: ignore
        nmids = list(self._adv_setting.nmids)
        nmids = [str(nmid) for nmid in nmids]
        nmids_str = ", ".join(nmids)
        text = (
            f"📦 *Артикул:* {nmids_str}\n"
            f"⚙️ *Хард-статус:* {self.get_str_rus_hard_status(calculated_keyword.hard_status)}\n"
            f"🔄 *Текущий статус ключа:* {calculated_keyword.status}\n\n"
            f"🔑 *Ключевое слово и настройки:*\n{keyword_text}\n\n"
            f"📊 *Показы:* {self.views}\n"
            f"🖱 *Клики:* {self.clicks}\n"
            f"📈 *Фактический CTR:* {self.fact_ctr * 100:.2f}%\n"
            f"💰 *Расход:* {self.spend:.2f} ₽\n"
        )


        text += f"Рейтинг по заказам: {round(self._calculated_keyword.rating_by_orders * 1000, 2)}\n"

        pos = self.position
        if pos > 0:
            text += f"📈 *Позиция:* {round(pos, 2)}\n"
        else:
            text += "📈 *Позиция:* Нет на сайте\n"

        text += f"""🕒 *Последнее данных по ключу:* {self.calculated_keyword.timestamp.strftime('%d-%m-%Y')}\n"""
        return text

    @property
    def keyboard(self):
        return keyboards.get_keyword_setting_keyboard(
            self._keyword_setting,
            self.calculated_keyword,
            self._adv_setting,
            self._page,
        )


class GetNameOfNewAdvCompany(Text):
    @property
    def text(self) -> str:
        return "Введите название новой рекламной кампании, максимум 128 символов:"


class TooLongNameOfNewAdvCompany(Text):
    @property
    def text(self)-> str:
        return "Название кампании слишком длинное. Попробуйте снова, должно быть не более 128 символов:"


class GetNmidOfNewAdvCompany(Text):
    @property
    def text(self)-> str:
        return ("Какие товары добавить в кампанию? Вы можете указать несколько товаров"
        "В качестве разделителя можете использовать пробел, запятую, точку с запятой или точку."
        "Указать можно артикулы WB или ваши артикулы. По возможности не создавайте РК более, "
        "чем на один товар:")


class NotFoundNmidOfNewAdvCompany(Text):
    def __init__(self, bot: Bot, chat_id: int, not_found_items: list[str]):
        self.__not_found_items = not_found_items
        super().__init__(bot, chat_id)

    @property
    def text(self) -> str:
        return f"Товары с идентификаторами {', '.join(self.__not_found_items)} не найдены. Попробуйте снова:"


class LongTimeOperation(Text):
    @property
    def text(self)-> str:
        return "Операция может занять некоторые время, пожалуйста, подождите..."


class NeedSubscribe(TextWithKeyboard):
    @property
    def text(self) -> str:
        return "Для использования функций вы должны быть подписаны на канал службы поддержки"

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_subscribe_keyboard()


class RefLinkGetName(Text):
    @property
    def text(self) -> str:
        return "Введите название для новой реферальной ссылки. Название будете видеть только вы:"


class RefLinkNameTooLong(Text):
    @property
    def text(self) -> str:
        return "Название ссылки слишком длинное, должно быть не больше 30 символов. Попробуйте снова:"


class RefLinkNameAlreadyExists(Text):
    @property
    def text(self) -> str:
        return  "Такое название ссылки уже существует. Попробуйте снова:"


class RefLinkCreated(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, ref_link: RefLink):
        self._ref_link = ref_link
        self._bot = bot
        super().__init__(bot, chat_id)

    async def __call__(self) -> None:
        self._link = await deep_linking.create_start_link(
            self._bot, str(self._ref_link.id)
        )
        return await super().__call__()

    @property
    def text(self) -> str:
        return (
            f"Ссылка {self._ref_link.name} успешно создана. \n\n"
            f"Вот ссылка, по которой вы можете приглашать пользователей: "
            f"{self._link}"
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_return_for_your_ref_links()

class OrderSubscribe(Text):
    @property
    def text(self) -> str:
        return f"В случае проблем с оплатой свяжитесь по этому контакту -> {const.SUPPORT_LINK}"


class ExpiredSubscription(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, wb_cabinet_original_id: int):
        self._wb_cabinet_original_id = wb_cabinet_original_id
        super().__init__(bot, chat_id)

    async def __call__(self) -> None:
        async with sm() as session:
            stmt = select(WBCabinet).where(WBCabinet.id == self._wb_cabinet_original_id)
            result = await session.execute(stmt)
            self._wb_cabinet = result.scalar()
        return await super().__call__()

    @property
    def text(self) -> str:
        return """
            Не достаточно средств для продолжения работы бота. Пополните баланс.
            """

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        # Проверка на None для self._wb_cabinet перед доступом к .id
        cabinet_id = (
            self._wb_cabinet_original_id
        )  # Если wb_cabinet_original_id гарантированно int
        return keyboards.get_payment_keyboard(
            wb_cabinet_original_id=cabinet_id,
        )

class MaxCPCSetting(TextWithKeyboard):
    async def __call__(self, adv_original_id: int):
        async with sm() as session:
            result = await session.execute(
                select(AdvSetting).where(AdvSetting.id == adv_original_id)
            )
            adv: AdvSetting | None = result.scalar()
            if adv is None:
                raise ValueError('Не найдена РК в базе')

        self._adv: AdvSetting = adv

        keywords: list[CalculatedKeyword] = await utils.get_keywords_for_keyboard(adv)
        keywords   = [
            kw
            for kw in keywords
            if str(kw.status) == KeywordStatus.GOOD
            or kw.reason == KeywordStatusReason.MAX_CPC
        ]
        keywords: list[CalculatedKeyword] = [kw for kw in keywords if kw.cpc is not None]

        def safe_sort(kw: CalculatedKeyword) -> float:
            return kw.cpc if kw.cpc is not None else float('-inf')

        keywords.sort(key=safe_sort, reverse=True)
        if not self._adv.max_cpc:
            top_kw_list = []
            down_kw_list = keywords
        else:
            top_kw_list: list[CalculatedKeyword] = []
            down_kw_list: list[CalculatedKeyword] = []
            for keyword in keywords:
                cpc: float | None = keyword.cpc
                if cpc is None:
                    continue
                if cpc > self._adv.max_cpc:
                    top_kw_list.append(keyword)
                else:
                    down_kw_list.append(keyword)
        self._top_kw_list: list[CalculatedKeyword] = top_kw_list[-10:]
        self._down_kw_list = down_kw_list[:10]
        return await super().__call__()

    @property
    def text(self):
        text = f"""Максимальная цена клика {"для кампании " + self._adv.name + " равна " + str(round(self._adv.max_cpc, 2)) + " р." if self._adv.max_cpc else "не задана"}\n"""
        for keyword in self._top_kw_list:
            cpc = keyword.cpc
            if cpc is None:
                continue
            text += f"""{keyword.text} - {round(cpc, 2)} р. ❌\n"""

        text += f"================== {round(self._adv.max_cpc, 2) if self._adv.max_cpc else ''}\n"

        for keyword in self._down_kw_list:
            cpc = keyword.cpc
            if cpc is None:
                continue
            text += f"""{keyword.text} - {round(cpc, 2)} р. ✅\n"""

        text += "Введите новую максимальную цену клика для кампании:"
        return text

    @property
    def keyboard(self):
        return keyboards.get_setting_max_cpc_keyboard(self._adv)


class SettingMinViewsForPredictCTR(TextWithKeyboard):
    async def __call__(self, adv_original_id: int):
        async with sm() as session:
            result = await session.execute(
                select(AdvSetting).where(AdvSetting.id == adv_original_id)
            )
            adv: AdvSetting  = result.scalar()
        self._adv: AdvSetting = adv
        return await super().__call__()

    @property
    def text(self):
        return (
            f"Введите минимальное количество показов для прогноза CTR роботом для кампании {self._adv.name}.\n"
            f"Текущее значение: {self._adv.min_views_for_ml_predict}.\n"
        )

    @property
    def keyboard(self):
        return keyboards.get_setting_min_views_for_predict_ctr_keyboard(self._adv)


class IncorrectMinViewsForPredictCTR(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, adv: AdvSetting):
        super().__init__(bot, chat_id)
        self._adv = adv

    @property
    def text(self) -> str:
        return "Минимальное количество показов должно быть целым числом от 0 и больше. Попробуйте снова:"

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_setting_min_views_for_predict_ctr_keyboard(self._adv)


class NotKeywordHistoryPositions(Text):
    @property
    def text(self) -> str:
        return "Не удалось получить историю позиций ключевых слов для этой кампании"

class NotEnoughMoneyForParsing(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, wb_cabinet_original_id: int):
        super().__init__(bot, chat_id)
        self._wb_cabinet_original_id = wb_cabinet_original_id

    @property
    def text(self) -> str:
        return """Не достаточный баланс для парсинга ключевых слов. Пополните баланс и попробуйте снова"""

    @property
    def keyboard(self):
        return keyboards.get_payment_keyboard(self._wb_cabinet_original_id)


# class CallMe1(TextWithKeyboard):
#     text = """
# Вдогонку к предыдущему сообщению:
# Если я не прочитал ваше сообщение, то значит очередь до вас еще не дошла - я специально не просматриваю и не отвечаю, чтобы никого случайно не пропустить.
# Чтобы полноценно рассказать про использование бота для максимально эффективного продвижения на WB и ответить на ваши вопросы нужно в среднем 40-50 минут, поэтому обещанные 10 консультаций я смогу провести только в течении 2-3 дней.
# Прошу набраться терпения - оно того стоит!
# Если успели написать до момента отправки этого сообщения - то вы точно успели и не переживайте: дойду и до вас!
# Если не успели: осталась буквально пара мест, так что скорее напишите мне,чтобы занять место и получить тест-драйв бота!
#
# """
#     @property
#     def keyboard(self) -> InlineKeyboardMarkup:
#         return keyboards.get_call_me_keyboard()


class WaitingForWhitePhrases(TextWithKeyboard):
    async def __call__(self, adv_setting_id: int):
        self.adv_setting_id: int = adv_setting_id
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
    async def __call__(self, adv_setting_id: int):
        self.adv_setting_id: int = adv_setting_id
        await super().__call__()

    @property
    def text(self) -> str:
        return "Фразы добавлены в белый список, можете ввести еще фразы или вернуться в настройки РК"

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)


class CPMSetting(TextWithKeyboard):
    async def __call__(self, adv_setting_id: int) -> None:
        async with sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
            result = await session.execute(stmt)
            adv_setting = result.scalars().first()
        if adv_setting is None:
            raise RuntimeError(f"AdvSetting с id {adv_setting_id} не найден")
        self.adv_setting = adv_setting
        await super().__call__()

    @property
    def text(self):
        text = f"""
Режим управления ставкой: {"Ручной" if not self.adv_setting.bidder_active else "Автоматический"}\n\n"""
        if self.adv_setting.bidder_active:
            text += f"""{"Целевое место место: " + str(self.adv_setting.max_place)}\n
Максимальная ставка: {str(self.adv_setting.max_cpm)}\n"""
        return text

    @property
    def keyboard(self):
        builder = InlineKeyboardBuilder()

        if self.adv_setting.bidder_active:
            bottom = InlineKeyboardButton(
                text="Выключить автоматическое управление ставкой",
                callback_data=callbacks.CPMSettingMenu(
                    action="off_auto_cpm", adv_original_id=self.adv_setting.id
                ).pack(),
            )
        else:
            bottom = InlineKeyboardButton(
                text="Включить автоматическое управление CPM",
                callback_data=callbacks.CPMSettingMenu(
                    action="set_auto_cpm", adv_original_id=self.adv_setting.id
                ).pack(),
            )

        builder.row(bottom)

        button_text = (
            "Выключить управление ставкой для Авто"
            if self.adv_setting.bidder_for_auto
            else "Включить управление ставкой для Авто"
        )
        callback_action = (
            "off_bidder_for_auto"
            if self.adv_setting.bidder_for_auto
            else "on_bidder_for_auto"
        )

        bottom = InlineKeyboardButton(
            text=button_text,
            callback_data=callbacks.CPMSettingMenu(
                action=callback_action, adv_original_id=self.adv_setting.id
            ).pack(),
        )

        builder.row(bottom)


        bottom = InlineKeyboardButton(
            text="Изменить Максимальную ставку",
            callback_data=callbacks.CPMSettingMenu(
                action="set_manual_cpm", adv_original_id=self.adv_setting.id
            ).pack(),
        )

        _ = builder.row(bottom)

        step = self.adv_setting.bidder_step
        step = step if step else DEFAULT_BIDDER_STEP
        bottom = InlineKeyboardButton(
            text=f"Изменить шаг ставки ({step})",
            callback_data=callbacks.CPMSettingMenu(
                action="change_cpm_step", adv_original_id=self.adv_setting.id
            ).pack(),
        )

        builder.row(bottom)

        if self.adv_setting.bidder_active:
            bottom = InlineKeyboardButton(
                text="Изменить целевую позицию",
                callback_data=callbacks.CPMSettingMenu(
                    action="set_max_position", adv_original_id=self.adv_setting.id
                ).pack(),
            )
            builder.row(bottom)

        bottom = InlineKeyboardButton(
            text="К настройкам АРК",
            callback_data=callbacks.Adv(adv_original_id=self.adv_setting.id).pack(),
        )
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
    @property
    def text(self) -> str:
        return """Укажите максимальную ставку:"""


class ManualCPMSetting(Text):
    @property
    def text(self) -> str:
        return  """Укажите ставку (целое число от 100):"""


class WaitingForBlackPhrases(TextWithKeyboard):
    async def __call__(self, adv_setting_id: int):
        self.adv_setting_id: int = adv_setting_id
        async with sm() as session:
            adv: AdvSetting | None = await session.get(
                AdvSetting, self.adv_setting_id
            )  # Изменено
        if adv is None:
            raise ValueError(
                f"AdvSetting с id {self.adv_setting_id} не найден."
            )  # Изменено
        rel_manager = RelevantPhraseManager(adv)

        black_phrases: list[str] | None = await rel_manager.get_relevant_template_data()
        self.black_phrases = black_phrases
        return await super().__call__()

    @property
    def text(self) -> str:
        if self.black_phrases:
            blacklist = "\n".join(self.black_phrases)
            return f"""Текущий черный список:\n{blacklist}\n\nЧтобы обновить фразы, отправьте список еще раз. Список будет обновлен."""
        else:
            return (
                "Укажите через знак переноса фразы, которые вы хотите добавить в черный список (фразы для исключения из продвижения)."
                " Если фраза указана без кавычек, то будут учитываться вхождения, если с кавычками - точное соответствие. Пример:\n\n"
                "платье женское\n"
                "платье вечернее\n"
                "платье летнее\n"
                '"женское летнее"\n'
                "\nЕсли перед фразой стоит восклицательный знак (!), то вхождение одной из обозначенных фраз ОБЯЗАТЕЛЬНО, "
                "иначе фраза будет добавлена в не релевантные.\n"
            )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        if self.black_phrases:
            builder.row(
                InlineKeyboardButton(
                    text="Сбросить черный список",
                    callback_data=callbacks.ResetBlackPhrases(
                        adv_setting_id=self.adv_setting_id
                    ).pack(),
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="Вернуться в настройки РК",
                callback_data=callbacks.Adv(adv_original_id=self.adv_setting_id).pack(),
            )
        )
        return builder.as_markup()


class FilterByQuery(Text):

    @property
    def text(self) -> str:
        return """ Введите минимальное число прогнозируемых показов для показа (0 - без фильтрации):"""


class KeywordStatUpdated(Text):
    @property
    def text(self) -> str:
        return """Статистика из WB успешно загружена, подгружаю страницу"""


class MinusKeywordsUpdated(Text):
    @property
    def text(self) -> str:
        return "Минус-слова успешно обновлены, подгружаю страницу"


class WhiteListReset(Text):
    @property
    def text(self) -> str:
        return "Белый список успешно сброшен"


class RelevantPhrasesAdded(TextWithKeyboard):
    def __init__(
        self, bot: Bot, user_telegram_id: int, adv_setting_id: int
    ):  # Изменено
        self.adv_setting_id = adv_setting_id
        super().__init__(bot, user_telegram_id)

    @property
    def text(self) -> str:
        return "Фразы успешно добавлены в бот (авто) список"

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)


class WaitingForRelevantPhrases(Text):
    @property
    def text(self) -> str:
        return "Введите фразы, которые вы хотите добавить в кампанию в качестве релевантных фраз:"


async def process_cabinet_balance_topup(
    user_id: int, cabinet_id: int, amount: float
) -> WBBalancePayment:
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
            transaction_date_time=datetime.now(),
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment


async def confirm_cabinet_balance_topup(
    payment_id: int, cabinet_id: int
) -> tuple[WBBalancePayment, WBCabinet]:
    """Подтверждение платежа и обновление баланса кабинета"""
    async with sm() as session:
        # Получаем платеж
        payment: WBBalancePayment | None = await session.get(
            WBBalancePayment, payment_id
        )
        if not payment or payment.wb_cabinet_id != cabinet_id:
            raise ValueError("Платеж не найден или не соответствует кабинету")

        # Получаем кабинет
        cabinet: WBCabinet | None = await session.get(WBCabinet, cabinet_id)
        if not cabinet:
            raise ValueError("Кабинет не найден")

        # Обновляем баланс кабинета
        cabinet.balance += payment.amount

        await session.commit()
        await session.refresh(payment)
        await session.refresh(cabinet)
        return payment, cabinet

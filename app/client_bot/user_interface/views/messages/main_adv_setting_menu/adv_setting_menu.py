# mypy: ignore-errors
# TODO: Глушу ошибки, их тут дофига, но надо разобраться потом
import logging
from datetime import datetime
from operator import attrgetter
from typing import TYPE_CHECKING
from datetime import date as date_type
from aiogram import Bot
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
)
from dependency_injector.wiring import inject, Provide
from sqlalchemy import select

from app.client_bot import utils
from app.client_bot.user_interface.message_templates.templates import (
    TextWithKeyboardAndImage,
)
from . import keyboard
from app.core.redis_manager_v2.redis_client import RedisClient

from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.models import PredictCTRMode
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat, DayStats
from app.modules.wb_adv_updater import data_manager, phrases_processor
from app.modules.wb_update_state_manager import (
    AdvActiveKeywordUpdateStateManager,
    KeywordStatUpdateState,
)
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_cluster_bids_timestamp_manager import (
    RedisClusterBidsTimestampManager,
)
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_timestamp_manager import (
    RedisCommonBidTimestampManager,
)
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)
from ..last_auto_update_informer import LastAutoUpdateSettingInformer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AdvSettingMenu(TextWithKeyboardAndImage):
    """Главное меню настройки Комплексной Кампании"""

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
        self._redis_common_bid_timestamp_manager = RedisCommonBidTimestampManager(
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

        adv_id = self.adv.adv_id
        last_common_bid_update = (
            await self._redis_common_bid_timestamp_manager.get(adv_id)
        )
        if last_common_bid_update:
            self.last_common_bid_update_str = last_common_bid_update.strftime(
                "%H:%M:%S %d.%m.%Y"
            )
        else:
            self.last_common_bid_update_str = "Нет данных"

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
            f"Посл. обнов. общей ставки аукциона: {self.last_common_bid_update_str}\n"
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
        return keyboard.get_adv_setting_keyboard(
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

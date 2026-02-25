# mypy: ignore-errors
# TODO: Глушу ошибки, их тут дофига, но надо разобраться потом
import logging
from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
from operator import attrgetter
from typing import TYPE_CHECKING
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
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
    RedisCampaignActivityReasonManager,
    reason_code_to_display_text,
)
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
    get_auto_campaign_cost_activity_metrics,
)

from ..last_auto_update_informer import LastAutoUpdateSettingInformer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

MSK_TZ = timezone(timedelta(hours=3))


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
        self._redis_campaign_activity_reason_manager = (
            RedisCampaignActivityReasonManager(redis_client)
        )
        self._reason_auto = None
        self._reason_search = None
        self._is_campaign_active_by_cost: bool | None = None
        self._plan_set: bool = False
        self._spend_auto_today: float | None = None
        self._spend_search_today: float | None = None

    @staticmethod
    def _format_status_for_display(status: str | None) -> str:
        """Числовой код WB (4,9,11,7,8) или текст статуса → строка для отображения."""
        if not status:
            return "—"
        # Коды WB: 4=ready_for_start, 9=started, 11=pause, 7=done, 8=refused
        code_to_ru = {
            "4": "готова к старту",
            "9": "запущена",
            "11": "пауза",
            "7": "завершена",
            "8": "отклонена",
        }
        if status in code_to_ru:
            return code_to_ru[status]
        text_to_ru = {
            "ready_for_start": "готова к старту",
            "started": "запущена",
            "pause": "пауза",
            "done": "завершена",
            "refused": "отклонена",
        }
        return text_to_ru.get(status, status)

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
            return status

    async def __call__(self) -> Message:
        auction_adv_id: int | None = self.adv.search_adv_id
        if auction_adv_id:
             status_auction = await self._get_status_auction(auction_adv_id)
             status_auction = self._format_status_for_display(status_auction)
             self._status_auction = status_auction
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

        cost_metrics = await get_auto_campaign_cost_activity_metrics(
            self.adv,
        )
        self._target_cost = cost_metrics.target_cost
        self._avg_cost_additional = cost_metrics.avg_cost
        self._is_campaign_active_by_cost = cost_metrics.is_active
        self._plan_set = cost_metrics.plan_set

        self._reason_auto = await self._redis_campaign_activity_reason_manager.get(
            self.adv.adv_id, "auto"
        )
        if self.adv.search_adv_id:
            self._reason_search = await self._redis_campaign_activity_reason_manager.get(
                self.adv.search_adv_id, "search"
            )
        else:
            self._reason_search = None

        if getattr(self.adv, "auto_budget_watchdog_enabled", False):
            now_msk = datetime.now(MSK_TZ)
            start_of_day = datetime.combine(now_msk.date(), time.min, tzinfo=MSK_TZ)
            end_of_day = datetime.combine(now_msk.date(), time.max, tzinfo=MSK_TZ)
            try:
                self._spend_auto_today = await full_wb_adv_stat.get_spend_by_last_days(
                    [self.adv.adv_id], start_of_day, end_of_day
                )
            except Exception:
                logger.exception("Ошибка получения расхода Авто за день из ClickHouse")
                self._spend_auto_today = None
            if self.adv.search_adv_id:
                try:
                    self._spend_search_today = (
                        await full_wb_adv_stat.get_spend_by_last_days(
                            [self.adv.search_adv_id], start_of_day, end_of_day
                        )
                    )
                except Exception:
                    logger.exception(
                        "Ошибка получения расхода Аукциона за день из ClickHouse"
                    )
                    self._spend_search_today = None
            else:
                self._spend_search_today = 0.0

        return await super().__call__()

    @property
    def text(self) -> str:
        # Determine predict CTR mode display text
        predict_ctr_mode = self.adv.predict_ctr_mode or PredictCTRMode.V1
        if predict_ctr_mode == PredictCTRMode.V1:
            predict_ctr_mode_text = "v1 (по ID кампании)"
        else:
            # TODO: Добавить отображение фото в ключах
            predict_ctr_mode_text = "v2 (по артикулам товара)"
        # TODO: Добавить когда была обновлена модель и когда обновлялся прогноз CTR
        text = ""

        watchdog_enabled = getattr(self.adv, "auto_budget_watchdog_enabled", False)
        if not watchdog_enabled:
            text += "Авто-акт. РК: выкл\n"
        else:
            text += "Авто-акт. РК: включено\n"
            use_common = getattr(self.adv, "use_common_budget", False)
            if use_common:
                limit = self.adv.common_budget_daily_limit or 0
                spend = (self._spend_auto_today or 0) + (self._spend_search_today or 0)
                if self._spend_auto_today is None and self._spend_search_today is None:
                    text += "Общий бюджет: потрачено: нет данных\n"
                else:
                    remaining = max(0, limit - int(spend))
                    text += (
                        f"Общий бюджет: потрачено {int(round(spend))} р., "
                        f"осталось {remaining} р. (лимит {limit} р./сут)\n"
                    )
            else:
                auto_limit = self.adv.auto_budget_daily_limit or 0
                spend_auto = self._spend_auto_today or 0
                if self._spend_auto_today is None:
                    text += "Авто: потр: нет данных\n"
                else:
                    remaining_auto = max(0, auto_limit - int(spend_auto))
                    text += (
                        f"Авто: потрачено {int(round(spend_auto))} р., "
                        f"ост. {remaining_auto} р. (лим {auto_limit} р/с)\n"
                    )
                if self.adv.search_adv_id:
                    search_limit = self.adv.search_auto_budget_daily_limit or 0
                    spend_search = self._spend_search_today or 0
                    if self._spend_search_today is None:
                        text += "Аук: потр: нет данных\n"
                    else:
                        remaining_search = max(0, search_limit - int(spend_search))
                        text += (
                            f"Аук: потр {int(round(spend_search))} р., "
                            f"ост {remaining_search} р. (лим {search_limit} р/с)\n"
                        )
                else:
                    if self._spend_auto_today is not None:
                        text += "\n"

        if self.adv.rec_system_mode:
            if not self._plan_set:
                text += "❗ План не задан!\n"

            target_str = (
                f"{round(self._target_cost)} р."
                if self._target_cost is not None
                else "Не задано"
            )
            avg_str = (
                f"{round(self._avg_cost_additional)} р."
                if self._avg_cost_additional is not None
                else "Нет данных"
            )

            if self._target_cost is not None or self._avg_cost_additional is not None:
                text += f"План. себес. заказа: {target_str} (факт. рек.сис.: {avg_str})\n"

            if self._is_campaign_active_by_cost is False and self._avg_cost_additional is not None:
                suggested = round(self._avg_cost_additional * 1.1, 0)
                text += (
                    "⚠️ Рек. системы (полки) не раскр. "
                    f"Рек. макс.заказа >= {int(suggested)} р.\n"
                )

        management_enabled = bool(
            self.adv.bot_active
            and getattr(self.adv, "auto_budget_watchdog_enabled", False)
        )
        if management_enabled:
            reason_auto_str = (
                reason_code_to_display_text(self._reason_auto.reason_code.value)
                if self._reason_auto
                else "—"
            )
            reason_search_str = (
                reason_code_to_display_text(self._reason_search.reason_code.value)
                if self._reason_search
                else "—"
            )
        else:
            reason_auto_str = "Упр откл"
            reason_search_str = "Упр откл"

        reason_auction_display = (
            "Не подключен"
            if not self.adv.search_adv_id
            else reason_search_str
        )
        text += (
            f"📢 Камп: {self.adv.name}\n"
            f"🆔 ID камп: {self.adv.adv_id}\n"
            f"📌 Статус Авто: {self._format_status_for_display(self.adv.active_status)}\n"
            f"📌 Статус Аук: {self._status_auction}\n"
            f"Причина Авто: {reason_auto_str}\n"
            f"Причина Аук: {reason_auction_display}\n"
        )
            # TODO: Попала ошибка в код, пытался сделать .2f строке
        if self._min_rating_by_orders is not None:
            text += f"🎯 Мин. Рейтинг по зак.: {round(self._min_rating_by_orders * 1000, 2)}\n"
        elif self._hard_min_ctr is not None:
            text += f"🎯 Мин. CTR: {round(self._hard_min_ctr, 2)}\n"
        else:
            text += "Огран не заданы!"

        text += 'Посл.обнов:\n'

        text += (
            f"воронки: {self.last_update_common_stat_str}\n"
            f"рек.стат.: {self.full_stat_update_time}\n"
            f"минус в авто: {self.keywords_status_last_update_auto_adv}\n"
            f"минус в аук.: {self.keywords_status_last_update_search_adv}\n"
            f"ставок в кластерах: {self.last_cluster_bids_update.strftime('%d.%m.%Y %H:%M:%S') if self.last_cluster_bids_update else 'Нет данных'}\n"
            f"общей ставки аук: {self.last_common_bid_update_str}\n"
            f"добав ключа в БС:"
            f" {self._update_informer.add_to_white_list_str}\n"
            f"удал. ключа из БС:"
            f" {self._update_informer.delete_from_white_list_str}\n"
            f"повыш. цел. позиции:"
            f" {self._update_informer.up_target_place_str}\n"
            f"пониж. целевой позиции:"
            f" {self._update_informer.down_target_place_str}\n"
            f"доб верхнего ключа в БС:"
            f" {self._update_informer.update_top_key_str}\n"
        )

        adv_stat = self.adv_stat

        if adv_stat:
            days_stat: list[DayStats] = sorted(
                adv_stat.days, key=attrgetter("date")
            )
            stat_text = "Стат по дням:\n"
            stat_text += "Дата | Зак | Себес заказа\n"
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

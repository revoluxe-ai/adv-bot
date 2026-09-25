"""Главное меню настроек РК с кнопками для UI и управлением активностью."""

# mypy: ignore-errors
# TODO: Глушу ошибки, их тут дофига, но надо разобраться потом
import logging
from datetime import datetime, time, timedelta, timezone
from operator import attrgetter
from typing import TYPE_CHECKING, Mapping
from aiogram import Bot
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
)
from dependency_injector.wiring import inject, Provide
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import utils
from app.client_bot.cashback_snapshot import parse_cashback_snapshot
from app.client_bot.user_interface.message_templates.templates import (
    TextWithKeyboardAndImage,
)
from app.client_bot.ui_access import UiAccessMode, UiAccessResolver
from app.client_bot.ui_mode import UiModeService
from app.client_bot.user_interface.views.messages.strategy_display import (
    format_adv_strategy,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from . import keyboard
from app.core.redis_manager_v2.redis_client import RedisClient

from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBUserCabinet,
    WBCabinet,
)
from app.modules.auto_budget_manager.redis_auto_budget_last_success_manager import (
    RedisAutoBudgetLastSuccessManager,
)
from app.modules.auto_budget_manager.redis_auto_budget_topup_failed_manager import (
    RedisAutoBudgetTopupFailedManager,
)
from app.modules.auto_budget_manager.redis_shop_balance_snapshot_manager import (
    RedisShopBalanceSnapshotManager,
)
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
    CampaignActivityReason,
    RedisCampaignActivityReasonManager,
    reason_code_to_display_text,
)
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)
from app.modules.shop_runner.wb_statistic_manager.redis_cluster_stat_timestamp_manager import (
    RedisClusterStatTimestampManager,
)
from app.modules.shop_runner.service_manager.services.stats_freshness_manager import (
    StatsFreshnessManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
    TrafficClicksDTO,
)
from app.modules.shop_runner.service_manager.services.traffic_clicks_manager import (
    TrafficClicksManager,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state import (
    SalesStates,
    sales_state_short_label,
)
from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
    get_auto_campaign_cost_activity_metrics,
)
from app.shared.domains.wb.utils.promo_overlay import (
    attach_overlay_fields,
    fraction_from_cached_state,
    overlay_for_adv,
)
from app.modules.auto_budget_manager.redis_promo_state_manager import (
    RedisPromoStateManager,
)

from ..last_auto_update_informer import LastAutoUpdateSettingInformer
from ..last_v3_action_informer import load_last_v3_action_display

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

MSK_TZ = timezone(timedelta(hours=3))
SAFE_CAPTION_LIMIT = 900
# Prefer this many recent days in the campaign menu caption; rows may be dropped to fit.
DAILY_STATS_CAPTION_MAX_DAYS = 5


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
        stats_freshness_manager: StatsFreshnessManager | None = None,
    ) -> None:
        """Инициализировать меню с Redis- и ClickHouse-зависимостями.

        Args:
            bot: Telegram-бот для отрисовки меню.
            chat_id: Идентификатор чата пользователя.
            wb_user_cabinet: Кабинет WB, которому принадлежит кампания.
            adv: Настройки рекламной кампании.
            redis_client: Клиент Redis для кэшей меню.
            stats_freshness_manager: Необязательный менеджер свежести статистики;
                production использует стандартный ClickHouse reader, а тесты
                могут передать изолированный reader/manager.
        """
        super().__init__(bot, chat_id)
        self._bot = bot
        self._chat_id = chat_id
        self.adv = adv
        self.wb_user_cabinet = wb_user_cabinet
        self._stats_freshness_manager = (
            stats_freshness_manager or StatsFreshnessManager()
        )
        self._redis_cluster_bids_timestamp_manager = RedisClusterBidsTimestampManager(
            redis_client
        )
        self._redis_common_stat_timestamp_manager = RedisCommonStatTimestampManager(
            redis_client
        )
        self._redis_cluster_stat_timestamp_manager = RedisClusterStatTimestampManager(
            redis_client
        )
        self._redis_common_bid_timestamp_manager = RedisCommonBidTimestampManager(
            redis_client
        )
        self._redis_campaign_activity_reason_manager = (
            RedisCampaignActivityReasonManager(redis_client)
        )
        self._balance_snapshot_manager = RedisShopBalanceSnapshotManager(redis_client)
        self._topup_failed_manager = RedisAutoBudgetTopupFailedManager(redis_client)
        self._last_success_manager = RedisAutoBudgetLastSuccessManager(redis_client)
        self._redis_client = redis_client
        self._reason_auto = None
        self._reason_search = None
        self._shop_balance_snapshot: dict[str, int | str | None] | None = None
        self._topup_failed: dict[str, str] | None = None
        self._last_topup_success: dict[str, str] | None = None
        self._is_campaign_active_by_cost: bool | None = None
        self._cost_threshold_kind: str | None = None
        self._plan_set: bool = False
        self._plan_fact_ch_max_ts_str: str | None = None
        self._campaign_sales_state: SalesStates | None = None
        self._spend_auto_today: float | None = None
        self._spend_search_today: float | None = None
        # Расход за всю историю кампаний — для абсолютного лимита бюджета РК.
        self._spend_auto_total: float | None = None
        self._spend_search_total: float | None = None
        self._emergency_mode_active: bool = False
        self._emergency_mode_reason: str | None = None
        self._stats_fresh: bool = True
        self._stats_stale_reason: str | None = None
        self._traffic_clicks_dto: TrafficClicksDTO | None = None
        self._v3_last_action_str: str | None = None
        self._ui_access: UiAccessMode = UiAccessMode.FREE
        self._ui_access_resolver: UiAccessResolver | None = None
        if isinstance(redis_client, RedisClient): # pyright: ignore
            self._ui_access_resolver = UiAccessResolver(
                UiModeService(redis_client=redis_client)
            )

    @staticmethod
    def _format_status_for_display(status: str | None) -> str:
        """Числовой код WB (4,9,11,7,8) или текст статуса → строка для отображения."""
        if not status:
            return "—"
        # Коды WB: 4=ready_for_start, 9=started, 11=pause, 7=done, 8=refused
        code_to_ru = {
            "4": "гот к ст",
            "9": "зап",
            "11": "п",
            "7": "зав",
            "8": "отк",
        }
        if status in code_to_ru:
            return code_to_ru[status]
        text_to_ru = {
            "ready_for_start": "гот к ст",
            "started": "зап",
            "pause": "п",
            "done": "зав",
            "refused": "отк",
        }
        return text_to_ru.get(status, status)

    async def _resolve_cost_activity_complex_adv(self) -> ComplexAdv:
        """Собрать ComplexAdv с runtime promo overlay для cost-activity."""
        search_adv: AdvSetting | None = None
        if self.adv.search_adv_id is not None:
            async with sm(read_only=True) as session:
                result = await session.execute(
                    select(AdvSetting).where(
                        AdvSetting.adv_id == self.adv.search_adv_id
                    )
                )
                search_adv = result.scalar_one_or_none()
        complex_adv = ComplexAdv(self.adv, search_adv)
        shop_id: str | None = None
        async with sm(read_only=True) as session:
            result = await session.execute(
                select(WBCabinet.shop_id).where(WBCabinet.id == self.adv.wb_cabinet_id)
            )
            shop_id = result.scalar_one_or_none()
        promo_state = None
        if shop_id is not None:
            promo_state = await RedisPromoStateManager(self._redis_client).get(shop_id)
        fraction = fraction_from_cached_state(
            promo_state,
            self.adv.adv_id,
            getattr(self.adv, "search_adv_id", None),
        )
        overlay = overlay_for_adv(self.adv, fraction=fraction)
        attach_overlay_fields(self.adv, overlay, adv_id=self.adv.adv_id)
        complex_adv.promo_fraction = overlay.fraction
        complex_adv.promo_multiplier = overlay.multiplier
        complex_adv.effective_promo_plan = overlay
        return complex_adv

    # TODO Дублирует аналогичную в app.client_bot.user_interface.views.messages.adv_keyword_messages.adv_keyword_messages.AdvKeywordsSetting._get_status_auction
    @staticmethod
    async def _get_status_auction(search_adv_id: int) -> str:
        if not search_adv_id:
            return "не под"
        stmt = select(AdvSetting.active_status).where(
            AdvSetting.adv_id == search_adv_id
        )
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            status = result.scalar_one_or_none()
            if not status:
                status = "РК не най"
            return status

    async def __call__(self) -> Message:
        self._ui_access = await self._resolve_ui_access()
        auction_adv_id: int | None = self.adv.search_adv_id
        if auction_adv_id:
             status_auction = await self._get_status_auction(auction_adv_id)
             status_auction = self._format_status_for_display(status_auction)
             self._status_auction = status_auction
        else:
            self._status_auction = "Не уст"
        keywords = await utils.get_keywords_for_keyboard(self.adv)
        self._min_orders_per_1000_rub = phrases_processor.get_min_orders_per_1000_rub(keywords)
        self._min_conv_views_to_orders = phrases_processor.get_min_conv_views_to_orders(keywords)
        self._strategy = self.adv.strategy or Strategy.MIN_CPO

        self.in_favorites_user: bool = await data_manager.is_adv_in_favorites(
            self.adv.id, self.wb_user_cabinet.user_id
        )

        full_stat_update_time = await self._get_last_full_stat_update(self.adv.adv_id)
        if not full_stat_update_time:
            full_stat_update_time_str = "Н/д"
        else:
            full_stat_update_time_str = full_stat_update_time.strftime(
                "%d.%m.%Y %H:%M:%S"
            )

        self.full_stat_update_time = full_stat_update_time_str

        nmids = self.adv.nmids
        images = await data_manager.get_main_photos(nmids[:1])
        image = images[0] if images else "https://placehold.co/600x800/png?text=WB"
        self.image = image

        # last_update_keyword_stat: datetime | None = (
        #     await self._get_last_update_keyword_stat(self.adv.adv_id)
        # ) TODO: Разобраться что за данные, почему не используются
        adv_id = self.adv.adv_id
        last_update_common_stat: datetime | None = (
            await self._redis_common_stat_timestamp_manager.get(adv_id)
        )
        # Ключ в Redis — AdvSetting.id (как в manager.update_clusters_adv_stats_today)
        last_update_cluster_stat: datetime | None = (
            await self._redis_cluster_stat_timestamp_manager.get(self.adv.id)
        )
        # Детект аварии и свежести статы по ClickHouse (как в guard), а не по Redis
        (
            self._emergency_mode_active,
            self._emergency_mode_reason,
            self._stats_fresh,
            self._stats_stale_reason,
        ) = await self._resolve_emergency_mode_from_ch()
        if last_update_common_stat:
            self.last_update_common_stat_str = last_update_common_stat.strftime(
                "%d.%m.%Y %H:%M:%S"
            )
        else:
            self.last_update_common_stat_str = "Н/д"

        if last_update_cluster_stat:
            self.last_update_cluster_stat_str = last_update_cluster_stat.strftime(
                "%d.%m.%Y %H:%M:%S"
            )
        else:
            self.last_update_cluster_stat_str = "Н/д"

        self.keywords_status_last_update_auto_adv = (
            await self._get_last_keywords_status_update_timestamp(self.adv.adv_id)
        )

        if not self.keywords_status_last_update_auto_adv:
            self.keywords_status_last_update_auto_adv = "Н/д"

        if search_adv_id := self.adv.search_adv_id:
            self.keywords_status_last_update_search_adv = (
                await self._get_last_keywords_status_update_timestamp(search_adv_id)
            )
            if self.keywords_status_last_update_search_adv is None:
                self.keywords_status_last_update_search_adv = "Н/д"
        else:
            self.keywords_status_last_update_search_adv = "Аук не подк к РК"

        adv_stat: FullAdvStat | None = (
            await data_manager.get_full_adv_stat_for_adv_id_from_redis(
                adv_id=self.adv.adv_id
            )
        )

        self.adv_stat: FullAdvStat | None = adv_stat
        self._traffic_clicks_dto = await self._get_today_traffic_clicks_dto()

        search_adv_id = self.adv.search_adv_id
        last_common_bid_update = (
            await self._redis_common_bid_timestamp_manager.get(search_adv_id)
            if search_adv_id is not None
            else None
        )
        if last_common_bid_update:
            self.last_common_bid_update_str = last_common_bid_update.strftime(
                "%H:%M:%S %d.%m.%Y"
            )
        else:
            self.last_common_bid_update_str = "Н/д"

        last_auto_setting_inform = LastAutoUpdateSettingInformer(self.adv)
        await last_auto_setting_inform.update_data()
        self._update_informer = last_auto_setting_inform
        if self.adv.bot_active:
            self._v3_last_action_str = await load_last_v3_action_display(self.adv)
        else:
            self._v3_last_action_str = None
        self.last_cluster_bids_update = await self._redis_cluster_bids_timestamp_manager.get(self.adv) # noqa

        cost_activity_complex_adv = await self._resolve_cost_activity_complex_adv()
        cost_metrics = await get_auto_campaign_cost_activity_metrics(
            self.adv,
            complex_adv=cost_activity_complex_adv,
        )
        self._target_cost = cost_metrics.target_cost
        self._avg_cost_additional = cost_metrics.avg_cost
        self._is_campaign_active_by_cost = cost_metrics.is_active
        self._cost_threshold_kind = cost_metrics.cost_threshold_kind
        self._plan_set = cost_metrics.plan_set
        self._plan_fact_ch_max_ts_str = cost_metrics.plan_fact_ch_ts_msk
        self._campaign_sales_state = cost_metrics.campaign_sales_state

        self._reason_auto = await self._redis_campaign_activity_reason_manager.get(
            self.adv.adv_id, "auto"
        )
        if self.adv.search_adv_id:
            self._reason_search = await self._redis_campaign_activity_reason_manager.get(
                self.adv.search_adv_id, "search"
            )
        else:
            self._reason_search = None

        async with sm(read_only=True) as session:
            result = await session.execute(
                select(WBCabinet.shop_id).where(
                    WBCabinet.id == self.adv.wb_cabinet_id
                )
            )
            shop_id = result.scalar_one()
        self._shop_balance_snapshot = await self._balance_snapshot_manager.get(
            shop_id
        )
        self._topup_failed = await self._topup_failed_manager.get(self.adv.id)
        self._last_topup_success = await self._last_success_manager.get(self.adv.id)

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

            await self._load_total_spend()

        return await super().__call__()

    async def _load_total_spend(self) -> None:
        """Подтянуть расход за всю историю РК, если абсолютный лимит задан.

        Побочные эффекты: чтение ClickHouse ``full_adv_wb_stat``. При ошибке
        значение остаётся ``None`` — в меню показывается «н/д».
        """
        if not self._total_limit_active():
            return
        try:
            self._spend_auto_total = await full_wb_adv_stat.get_total_spend_by_advs(
                [self.adv.adv_id]
            )
        except Exception:
            logger.exception(
                "Ошибка получения суммарного расхода Авто из ClickHouse"
            )
            self._spend_auto_total = None
        if self.adv.search_adv_id:
            try:
                self._spend_search_total = (
                    await full_wb_adv_stat.get_total_spend_by_advs(
                        [self.adv.search_adv_id]
                    )
                )
            except Exception:
                logger.exception(
                    "Ошибка получения суммарного расхода Аукциона из ClickHouse"
                )
                self._spend_search_total = None
        else:
            self._spend_search_total = 0.0

    def _total_limit(self, attr_name: str) -> int:
        """Значение абсолютного лимита с ``AdvSetting``; ``0`` — лимита нет."""
        return getattr(self.adv, attr_name, 0) or 0

    def _total_limit_active(self) -> bool:
        """Задан ли хоть один абсолютный лимит (> 0) в текущем режиме бюджета."""
        if getattr(self.adv, "use_common_budget", False):
            return self._total_limit("common_budget_total_limit") > 0
        return (
            self._total_limit("auto_budget_total_limit") > 0
            or self._total_limit("search_auto_budget_total_limit") > 0
        )

    @staticmethod
    def _total_limit_line(label: str, spend: float | None, limit: int) -> str:
        """Строка «потрачено/лимит, остаток» для абсолютного лимита.

        При недоступной статистике сообщаем, что РК остановлена: гейт абсолютного
        лимита fail-closed и держит кампанию на паузе, пока расход неизвестен.
        """
        if limit <= 0:
            return ""
        if spend is None:
            return f"{label}: расх н/д, лим {limit} р. — РК на паузе\n"
        spend_rounded = int(round(spend))
        remaining = max(0, limit - spend_rounded)
        return f"{label}: {spend_rounded}/{limit} р., ост {remaining}\n"

    def _total_limit_block(self) -> str:
        """Блок абсолютных лимитов для меню РК по текущему режиму бюджета."""
        if not self._total_limit_active():
            return ""
        if getattr(self.adv, "use_common_budget", False):
            spend: float | None
            if self._spend_auto_total is None or self._spend_search_total is None:
                spend = None
            else:
                spend = self._spend_auto_total + self._spend_search_total
            return self._total_limit_line(
                "Об.абс", spend, self._total_limit("common_budget_total_limit")
            )
        block = self._total_limit_line(
            "Авто абс",
            self._spend_auto_total,
            self._total_limit("auto_budget_total_limit"),
        )
        if self.adv.search_adv_id:
            block += self._total_limit_line(
                "Аук абс",
                self._spend_search_total,
                self._total_limit("search_auto_budget_total_limit"),
            )
        return block

    async def _resolve_ui_access(self) -> UiAccessMode:
        """Resolve effective freemium access for campaign menu rendering."""
        if self._ui_access_resolver is None:
            return UiAccessMode.FREE
        return await self._ui_access_resolver.resolve_adv_ui_access(
            int(self.chat_id), self.adv
        )

    @property
    def text(self) -> str:
        # Determine predict CTR mode display text
        # TODO: Добавить когда была обновлена модель и когда обновлялся прогноз CTR
        text = ""
        if self._emergency_mode_active:
            text += (
                "🚨 АВ.РЕЖ, СТ > 6ч, РАСХ ОГРАН\n"
            )
            if self._emergency_mode_reason:
                text += f"{self._emergency_mode_reason}\n"
        elif self._stats_fresh:
            text += f"{self._fresh_reason_to_display()}\n"
        else:
            text += "Ст не све, авт приост\n"
            if self._stats_stale_reason:
                text += f"{self._stats_stale_reason}\n"
        text += "\n"
        text += (
            "Это меню рекламной кампании.\n"
            "Во free-режиме можно смотреть данные и выполнять ручные действия: "
            "ставки, целевые позиции, Excel.\n"
            "автоуправление рекламой и автоматическая оптимизация "
            "подключаются отдельно.\n\n"
        )

        watchdog_enabled = getattr(self.adv, "auto_budget_watchdog_enabled", False)
        if not watchdog_enabled:
            text += "Авто-акт: выкл\n"
            text += "Автопоп: выкл\n"
        else:
            text += "Авто-акт: вкл\n"
            use_common = getattr(self.adv, "use_common_budget", False)
            if use_common:
                limit = self.adv.common_budget_daily_limit or 0
                spend = (self._spend_auto_today or 0) + (self._spend_search_today or 0)
                if self._spend_auto_today is None or self._spend_search_today is None:
                    text += "Об.бюд потр: н/д\n"
                else:
                    spend_rounded = int(round(spend))
                    remaining = max(0, limit - spend_rounded)
                    text += (
                        f"Об.бюд: {spend_rounded}/{limit} р., ост {remaining}\n"
                    )
            else:
                auto_limit = self.adv.auto_budget_daily_limit or 0
                spend_auto = self._spend_auto_today or 0
                if self._spend_auto_today is None:
                    text += "Авто потр: н/д\n"
                else:
                    spend_auto_rounded = int(round(spend_auto))
                    remaining_auto = max(0, auto_limit - spend_auto_rounded)
                    text += (
                        f"Авто: {spend_auto_rounded}/{auto_limit} р., ост {remaining_auto}\n"
                    )
                if self.adv.search_adv_id:
                    search_limit = self.adv.search_auto_budget_daily_limit or 0
                    spend_search = self._spend_search_today or 0
                    if self._spend_search_today is None:
                        text += "Аук потр: н/д\n"
                    else:
                        spend_search_rounded = int(round(spend_search))
                        remaining_search = max(0, search_limit - spend_search_rounded)
                        text += (
                            f"Аук: {spend_search_rounded}/{search_limit} р., ост {remaining_search}\n"
                        )
                else:
                    if self._spend_auto_today is not None:
                        text += "\n"
            text += self._total_limit_block()

        # Предупреждение о неудачном пополнении (из Redis) — показываем всегда при наличии записи
        if self._topup_failed:
            failed_at: str = self._topup_failed.get("failed_at", "")
            try:
                dt = datetime.fromisoformat(
                    failed_at.replace("Z", "+00:00")
                ).astimezone(MSK_TZ)
                failed_at_str: str = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError):
                failed_at_str = failed_at or "—"
            text += (
                f"⚠ Поп.бюд не удался ({failed_at_str})\n"
            )

        # Остаток по балансу магазина (из Redis, обновляется при автопополнении)
        if self._shop_balance_snapshot:
            bal: int = int(self._shop_balance_snapshot.get("balance", 0) or 0)
            net: int = int(self._shop_balance_snapshot.get("net", 0) or 0)
            bonus: int = int(self._shop_balance_snapshot.get("bonus", 0) or 0)
            updated_at: str = str(self._shop_balance_snapshot.get("updated_at", ""))
            try:
                dt = datetime.fromisoformat(
                    str(updated_at).replace("Z", "+00:00")
                ).astimezone(MSK_TZ)
                updated_str: str = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError):
                updated_str = str(updated_at) if updated_at else "—"
            text += (
                f"Бал: осн {bal}, нет {net}, бон {bonus} (обн {updated_str})\n"
            )
            cashback_line = self._build_cashback_compact_line(
                self._shop_balance_snapshot
            )
            if cashback_line:
                text += cashback_line
        else:
            text += "Бал: н/д\n"

        # Последнее успешное пополнение
        at_val: str = (self._last_topup_success or {}).get("at", "")
        if self._last_topup_success and at_val:
            try:
                dt = datetime.fromisoformat(
                    at_val.replace("Z", "+00:00")
                ).astimezone(MSK_TZ)
                success_str: str = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError):
                success_str = at_val or "—"
            text += f"Поп посл: {success_str}\n"
        else:
            text += "Поп посл: н/д\n"

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
                ch_suffix = (
                    f" (пл-ф CH: {self._plan_fact_ch_max_ts_str} МСК)"
                    if self._plan_fact_ch_max_ts_str
                    else ""
                )
                text += f"Себес зак: план {target_str}, факт {avg_str}{ch_suffix}\n"
                if self._campaign_sales_state is not None:
                    text += (
                        f"Состояние: {sales_state_short_label(self._campaign_sales_state)}\n"
                    )

            if self._is_campaign_active_by_cost is False and self._avg_cost_additional is not None:
                suggested = round(self._avg_cost_additional * 1.1, 0)
                cost_label = (
                    "цель зак"
                    if self._cost_threshold_kind == "target"
                    else "макс.зак"
                )
                text += (
                    f"⚠ Рек.сис не раскр, {cost_label} >= {int(suggested)} р.\n"
                )
            if self._traffic_clicks_dto is not None:
                text += (
                    "Клики сегодн: "
                    f"орг {self._traffic_clicks_dto.organic_clicks}, "
                    f"полки {self._traffic_clicks_dto.shelf_clicks}, "
                    f"ключи {self._traffic_clicks_dto.keyword_clicks}\n"
                )

        management_enabled = bool(
            self.adv.bot_active
            and getattr(self.adv, "auto_budget_watchdog_enabled", False)
        )

        def _status_suffix(reason: CampaignActivityReason | None) -> str:
            if not management_enabled:
                return " (упр. отключено)"
            if reason is None:
                return " (н/д)"
            label = reason_code_to_display_text(str(reason.reason_code.value))
            dt = reason.updated_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_msk = dt.astimezone(MSK_TZ)
            ts = dt_msk.strftime("%d.%m.%Y %H:%M")
            return f" ({label}, {ts})"

        suffix_auto = _status_suffix(self._reason_auto)
        if not self.adv.search_adv_id:
            suffix_auction = " (не подк)"
        else:
            suffix_auction = _status_suffix(self._reason_search)

        id_auto = str(self.adv.adv_id) if self.adv.adv_id else "Не подкл"
        id_auction = str(self.adv.search_adv_id) if self.adv.search_adv_id else "Не подк"
        text += (
            f"📢 {self.adv.name}\n"
            f"ID А:{id_auto} У:{id_auction}\n"
            f"Авто: {self._format_status_for_display(self.adv.active_status)}{suffix_auto}\n"
            f"Аук: {self._status_auction}{suffix_auction}\n"
            f"🎯 {format_adv_strategy(self.adv.strategy)}\n"
        )
        mark_cpo = "▶ " if self._strategy == Strategy.MIN_CPO else "  "
        mark_conv = "▶ " if self._strategy == Strategy.MAX_CONV else "  "
        val_1000rub = (
            round(self._min_orders_per_1000_rub, 2)
            if self._min_orders_per_1000_rub is not None
            else "—"
        )
        val_1000views = (
            round(self._min_conv_views_to_orders * 1000, 2)
            if self._min_conv_views_to_orders is not None
            else "—"
        )
        text += f"{mark_cpo}Мин зак/1000р: {val_1000rub}\n"
        text += f"{mark_conv}Мин зак/1000п: {val_1000views}\n"

        text += "Обновл:\n"

        text += (
            f"ворон: {self.last_update_common_stat_str}\n"
            f"рекст: {self.full_stat_update_time}\n"
            f"класт: {self.last_update_cluster_stat_str}\n"
            f"минус авто: {self.keywords_status_last_update_auto_adv}\n"
            f"минус аук: {self.keywords_status_last_update_search_adv}\n"
            f"став класт: {self.last_cluster_bids_update.strftime('%d.%m.%Y %H:%M:%S') if self.last_cluster_bids_update else 'Н/д'}\n"
            f"общ.став аук: {self.last_common_bid_update_str}\n"
        )
        if self.adv.bot_active:
            text += f"посл. V3: {self._v3_last_action_str or 'Нет данных'}\n"
        else:
            text += (
                f"добавл в БС:"
                f" {self._update_informer.add_to_white_list_str}\n"
                f"удал из БС:"
                f" {self._update_informer.delete_from_white_list_str}\n"
            )
        text += (
            f"цел.поз +:"
            f" {self._update_informer.up_target_place_str}\n"
            f"цел.поз -:"
            f" {self._update_informer.down_target_place_str}\n"
            f"топ в БС:"
            f" {self._update_informer.update_top_key_str}\n"
        )

        adv_stat = self.adv_stat

        if adv_stat:
            days_stat: list[DayStats] = sorted(
                adv_stat.days, key=attrgetter("date")
            )
            text += AdvSettingMenu._build_caption_daily_stats_block(
                days_stat, len(text)
            )

        return self._shrink_for_caption(text)

    @staticmethod
    def _build_caption_daily_stats_block(
        days_stat_chrono: list[DayStats],
        prefix_char_len: int,
    ) -> str:
        """Block for «Стат дн»: up to ``DAILY_STATS_CAPTION_MAX_DAYS`` recent days.

        If ``prefix_char_len`` + block would exceed ``SAFE_CAPTION_LIMIT``, drops
        older days first (keeps most recent). When fewer days fit than are
        available in the window, the header notes «показано k из n дн.».
        """
        if not days_stat_chrono:
            return ""
        window = days_stat_chrono[-DAILY_STATS_CAPTION_MAX_DAYS:]
        n_window = len(window)

        def line_for_day(day_stat: DayStats) -> str:
            spend = day_stat.sum
            orders = day_stat.orders
            cost_per_order = spend / orders if orders else 0
            date_str = day_stat.date.strftime("%d-%m-%Y")
            return f"{date_str} | {orders} | {round(cost_per_order, 0)} р.\n"

        for k in range(n_window, 0, -1):
            subset = window[-k:]
            title = (
                f"Стат дн (показано {k} из {n_window} дн.):\n"
                if k < n_window
                else "Стат дн:\n"
            )
            stat_text = title + "Дата | Зак | Себес\n"
            for ds in subset:
                stat_text += line_for_day(ds)
            if prefix_char_len + len(stat_text) <= SAFE_CAPTION_LIMIT:
                return stat_text
        return ""

    @staticmethod
    def _shrink_for_caption(text: str) -> str:
        if len(text) <= SAFE_CAPTION_LIMIT:
            return text
        tail = "\n…[сокращено]"
        max_len = max(0, SAFE_CAPTION_LIMIT - len(tail))
        return text[:max_len] + tail

    @staticmethod
    def _build_cashback_compact_line(
        snapshot: Mapping[str, int | str | None],
    ) -> str | None:
        parsed = parse_cashback_snapshot(snapshot)
        if parsed is None:
            return None
        exp_part = ""
        if parsed.expiration_msk:
            exp_part = f", гор {parsed.expiration_msk.strftime('%d.%m')}"
        return f"КБ: {parsed.total}{parsed.percent_part}{exp_part}\n"

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboard.get_adv_setting_keyboard(
            self.wb_user_cabinet,
            self.adv,
            self.in_favorites_user,
            ui_access=self._ui_access,
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

    async def _resolve_emergency_mode_from_ch(
        self,
        session: AsyncSession | None = None,
    ) -> tuple[bool, str | None, bool, str | None]:
        """Детект аварии и свежести статы по данным ClickHouse (как StatsFreshnessGuard), не по Redis.
        Returns: (emergency_active, emergency_reason, stats_fresh, stats_stale_reason)."""
        search_adv: AdvSetting | None = None
        if getattr(self.adv, "search_adv_id", None):
            if session is None:
                async with sm(read_only=True) as read_session:
                    result = await read_session.execute(
                        select(AdvSetting).where(
                            AdvSetting.adv_id == self.adv.search_adv_id
                        )
                    )
            else:
                result = await session.execute(
                    select(AdvSetting).where(AdvSetting.adv_id == self.adv.search_adv_id)
                )
            search_adv = result.scalar_one_or_none()
        complex_adv = ComplexAdv(self.adv, search_adv)
        manager = getattr(self, "_stats_freshness_manager", None)
        if manager is None:
            manager = StatsFreshnessManager()
        state = await manager.evaluate(complex_adv)
        if state.is_stale_over_6h:
            return True, self._guard_reason_to_display(state.reason), False, None
        if not state.is_fresh:
            if state.reason:
                return False, None, False, self._stale_reason_to_display(state.reason)
            return False, None, False, self._stale_reason_fallback_to_display()
        return False, None, True, self._fresh_reason_to_display()

    @staticmethod
    def _stale_reason_to_display(reason: str) -> str:
        """Маппинг reason от guard (не авария) в текст: какая стата не свежая."""
        if "full_adv_stat_update" in reason:
            name = "Рекламная стата"
        elif "common_stat_update" in reason:
            name = "Общая стата"
        elif "cluster_stat_update" in reason:
            name = "Кластерная стата"
        else:
            name = "Стата"
        if "not yet collected" in reason:
            return f"{name} ещё не собрана"
        return f"{name} не свежая"

    @staticmethod
    def _guard_reason_to_display(reason: str | None) -> str:
        """Маппинг reason от guard в текст для пользователя."""
        if not reason:
            return "ст нет обн > 6 часов"
        if "full_adv_stat_update" in reason:
            name = "рек ст"
        elif "common_stat_update" in reason:
            name = "общ ст"
        elif "cluster_stat_update" in reason:
            name = "клас ст"
        else:
            name = "стата"
        # Call site only passes reason when is_stale_over_6h is True; guard sets that
        # only for "stale over 6h", never for "not yet collected".
        return f"{name}: нет обн>6ч"

    async def _get_today_traffic_clicks_dto(self) -> TrafficClicksDTO | None:
        if not self.adv.rec_system_mode:
            return None
        try:
            search_adv: AdvSetting | None = None
            if self.adv.search_adv_id:
                async with sm(read_only=True) as session:
                    result = await session.execute(
                        select(AdvSetting).where(
                            AdvSetting.adv_id == self.adv.search_adv_id
                        )
                    )
                    search_adv = result.scalar_one_or_none()
            complex_adv = ComplexAdv(
                adv_setting=self.adv,
                search_adv=search_adv,
            )
            manager = TrafficClicksManager()
            await manager.enrich(complex_adv)
            return complex_adv.traffic_clicks_dto
        except Exception:
            logger.exception(
                "Ошибка получения today traffic clicks для adv_id=%s", self.adv.adv_id
            )
            return None

    @staticmethod
    def _fresh_reason_to_display() -> str:
        return "стата свежая"

    @staticmethod
    def _stale_reason_fallback_to_display() -> str:
        return "стата не свежая"

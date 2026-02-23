"""Сервис управления активностью РК: бюджет, расписание, пауза/запуск.

Как это устроено (задумано):

- Ограничения показов по времени (расписание по часам/дням и период по датам)
  настраиваются пользователем в боте для любой кампании (кнопка «Ограничения
  показов по времени» в меню настроек РК).

- Применяются эти ограничения только здесь — в AutoAdvActiveControlService.
  Другие фоновые сервисы (бидер и т.д.) их не учитывают.

- В ensure_campaigns_active обрабатываются только кампании с включённым
  «Контролем активности кампании» (auto_budget_watchdog_enabled=True). Для них
  сервис подгружает настройки времени из БД и при «сейчас вне расписания»
  ставит РК на паузу (авто и/или поиск). Для кампаний без включённого контроля
  ограничения по времени из БД нигде не проверяются.

Итог: ограничения по времени — часть механизма «контроль активности»: пользователь
может заранее настроить расписание; оно начнёт действовать после включения
«Контроля активности кампании». Кнопка настроек времени показывается всем —
это задумано (настройка «на будущее»).
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Awaitable
from datetime import datetime, time, timedelta, timezone

from app.client_bot.user_interface.handlers.time_settings.logic import (
    allowed_now_from_db_state,
)
from app.client_bot.user_interface.handlers.time_settings.repository import (
    TimeSettingsDbState,
    TimeSettingsRepository,
)
from app.core.mp.wb.api.managers import WBModifier
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
    is_auto_campaign_active,
)
from app.utils.db.session_maker import get_async_session_maker as get_session_maker

logger = logging.getLogger(__name__)

MSK_TZ = timezone(timedelta(hours=3))
_time_settings_repo = TimeSettingsRepository()


class AutoAdvActiveControlService:
    """Управление активностью РК: пауза/запуск по бюджету и расписанию.

    Обрабатывает только кампании с bot_active и auto_budget_watchdog_enabled.
    Для них применяет лимиты бюджета и ограничения по времени (расписание/даты).
    """

    def __init__(
        self,
        wb_modifier: WBModifier,
        tasks_manager: TasksManager,
        plan_fact_reader: PlanFactReader | None = None,
    ) -> None:
        self._wb_modifier = wb_modifier
        self._tasks_manager = tasks_manager
        self._plan_fact_reader = plan_fact_reader or PlanFactReader() # просят тесты, потом все это исправить, техдолг

    async def ensure_campaigns_active(self, advs: Iterable[ComplexAdv]) -> None:
        """Привести активность РК в соответствие с бюджетом и расписанием.

        Обрабатываются только кампании с включённым «Контролем активности»
        (auto_budget_watchdog_enabled). Для них загружаются настройки времени
        из БД; при выходе за расписание/даты РК ставится на паузу. Ограничения
        по времени нигде больше не применяются — только в этом сервисе.
        """
        complex_advs = [
            adv
            for adv in advs
            if adv.bot_active
            and adv.auto_budget_watchdog_enabled  # управление активностью РК: бюджет, пополнение, расписание
        ]
        if not complex_advs:
            return None

        handlers: list[Callable[[], Awaitable[None]]] = []

        now_msk = datetime.now(MSK_TZ)
        start_of_day = datetime.combine(now_msk.date(), time.min, tzinfo=MSK_TZ)
        end_of_day = datetime.combine(now_msk.date(), time.max, tzinfo=MSK_TZ)

        unique_adv_ids = list({adv.adv_setting.id for adv in complex_advs})
        # Настройки времени применяются только для этих РК (с включённым контролем)
        time_settings_by_adv: dict[int, TimeSettingsDbState | None] = {}
        async with get_session_maker(read_only=True) as session:
            time_settings_by_adv = await _time_settings_repo.load_for_adv_ids(
                session, unique_adv_ids
            )

        for adv in complex_advs:
            db_state = time_settings_by_adv[adv.adv_setting.id]
            handlers.append(
                lambda complex_adv=adv, ds=db_state: self._auto_campaign_handler(
                    complex_adv, start_of_day, end_of_day, db_state=ds
                )
            )
            handlers.append(
                lambda complex_adv=adv, ds=db_state: self._search_campaign_handler(
                    complex_adv, start_of_day, end_of_day, db_state=ds
                )
            )

        if not handlers:
            return None

        max_workers = self._max_workers_for(len(handlers), cap=16)
        results = await run_tasks(
            handlers,
            max_workers=max_workers,
            tasks_manager=self._tasks_manager,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "Auto adv active control handler failed: %s", result
                )
        return None

    @staticmethod
    def _max_workers_for(handler_count: int, cap: int) -> int:
        return max(1, min(handler_count, cap))

    @staticmethod
    async def _get_spend_for_adv(
        adv_id: int | None,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        if adv_id is None:
            return 0.0
        return await full_wb_adv_stat.get_spend_by_last_days(
            [adv_id],
            start_date,
            end_date,
        )
    async def _auto_campaign_handler(
        self,
        adv: ComplexAdv,
        start_of_day: datetime,
        end_of_day: datetime,
        *,
        db_state: TimeSettingsDbState | None,
    ) -> None:
        auto_adv_id = adv.auto_adv_id
        auto_status = adv.auto_adv_active_status_str
        cost_log_suffix = " (common)" if adv.use_common_budget else ""

        # Расписание/даты из настроек времени; без настроек — показы разрешены
        time_allowed = (
            allowed_now_from_db_state(db_state) if db_state else True
        )
        if not time_allowed:
            if auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (time schedule) adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
            return None

        if adv.use_common_budget:
            common_limit = adv.common_budget_daily_limit or 0
            spend_auto = await self._get_spend_for_adv(
                auto_adv_id, start_of_day, end_of_day
            )
            spend_search = await self._get_spend_for_adv(
                adv.search_adv_id, start_of_day, end_of_day
            )
            combined_spend = spend_auto + spend_search
            if common_limit == 0 and auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (common limit 0) adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
                return None
            if 0 < common_limit <= combined_spend and auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (common spend %.2f >= limit %s) adv_id=%s shop_id=%s",
                    combined_spend,
                    common_limit,
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
                return None
            budget_ok = common_limit > 0 and combined_spend < common_limit
        else:
            auto_limit = adv.auto_budget_daily_limit or 0
            if auto_limit == 0 and auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
                return None
            spend_today = await self._get_spend_for_adv(
                auto_adv_id, start_of_day, end_of_day
            )
            if 0 < auto_limit <= spend_today and auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign because spend %.2f >= limit %s adv_id=%s shop_id=%s",
                    spend_today,
                    auto_limit,
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
                return None
            budget_ok = auto_limit > 0 and spend_today < auto_limit

        cost_activity = await is_auto_campaign_active(
            adv.adv_setting,
            plan_fact_reader=self._plan_fact_reader,
        )
        # TODO: Тут не понятно что делать, если cost_activity не доступно. Вообще, это ошибка какая-то, на всякий случай ничего не делаю
        if cost_activity is None:
            logger.info(
                "Auto watchdog: insufficient cost data%s adv_id=%s shop_id=%s",
                cost_log_suffix,
                auto_adv_id,
                adv.shop_id,
            )
            return None

        if (
            cost_activity is False
            and auto_status == WBAdvActiveStatus.STARTED
        ):
            logger.info(
                "Auto watchdog: pausing auto campaign%s due to failed cost rule adv_id=%s shop_id=%s",
                cost_log_suffix,
                auto_adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.pause_auto_campaign(adv)
            return None

        cost_rule_ok = cost_activity is True
        if (
            budget_ok
            and cost_rule_ok
            and auto_status in [WBAdvActiveStatus.PAUSE, WBAdvActiveStatus.READY_FOR_START]
        ):
            logger.info(
                "Auto budget watcher: starting auto campaign%s adv_id=%s shop_id=%s",
                cost_log_suffix,
                auto_adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.start_auto_campaign(adv)

    async def _search_campaign_handler(
        self,
        adv: ComplexAdv,
        start_of_day: datetime,
        end_of_day: datetime,
        *,
        db_state: TimeSettingsDbState | None,
    ) -> None:
        adv_id = adv.search_adv_id
        if adv_id is None:
            return None

        search_status = adv.search_adv_active_status_str

        # Расписание/даты из настроек времени; без настроек — показы разрешены
        time_allowed = (
            allowed_now_from_db_state(db_state) if db_state else True
        )
        if not time_allowed:
            if search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign (time schedule) adv_id=%s shop_id=%s",
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
            return None

        if adv.use_common_budget:
            common_limit = adv.common_budget_daily_limit or 0
            spend_auto = await self._get_spend_for_adv(
                adv.auto_adv_id, start_of_day, end_of_day
            )
            spend_search = await self._get_spend_for_adv(
                adv_id, start_of_day, end_of_day
            )
            combined_spend = spend_auto + spend_search
            if common_limit == 0 and search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign (common limit 0) adv_id=%s shop_id=%s",
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
                return None
            if 0 < common_limit <= combined_spend and search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign (common spend %.2f >= limit %s) adv_id=%s shop_id=%s",
                    combined_spend,
                    common_limit,
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
                return None
            if common_limit > 0 and combined_spend < common_limit and search_status in [
                WBAdvActiveStatus.PAUSE,
                WBAdvActiveStatus.READY_FOR_START,
            ]:
                logger.info(
                    "Auto budget watcher: starting auction campaign (common) adv_id=%s shop_id=%s",
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.start_auction_campaign(adv)
            return None

        spend_today = await self._get_spend_for_adv(adv_id, start_of_day, end_of_day)
        search_limit = adv.search_auto_budget_daily_limit or 0

        if 0 < search_limit <= spend_today:
            if search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign because spend %.2f >= limit %s adv_id=%s shop_id=%s",
                    spend_today,
                    search_limit,
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
            return

        if search_limit > 0 and search_status in [WBAdvActiveStatus.PAUSE, WBAdvActiveStatus.READY_FOR_START]:
            logger.info(
                "Auto budget watcher: starting auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.start_auction_campaign(adv)
        elif search_limit == 0 and search_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Auto budget watcher: pausing auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.pause_auction_campaign(adv)

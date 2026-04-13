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

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone

from app.modules import balance_manager

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
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
    AutoReasonCode,
    AuctionReasonCode,
    CampaignActivityCommand,
    CampaignActivityReason,
    RedisCampaignActivityReasonManager,
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
from app.shared.domains.wb.utils.balance_source import (
    balance_snapshot_from_response,
    cashback_summary_from_response,
)
from app.utils.db.session_maker import get_async_session_maker as get_session_maker

logger = logging.getLogger(__name__)

MSK_TZ = timezone(timedelta(hours=3))

_time_settings_repo = TimeSettingsRepository()


@dataclass
class WbWalletOkCache:
    """Per-``ensure_campaigns_active`` run: cache WB wallet positivity per cabinet.

    ``run_tasks`` runs handlers concurrently; without coordination, many coroutines
    could miss the cache between the membership check and ``get_campaign_balance``
    (there is an ``await`` in between). Per-cabinet locks plus double-checked
    loading ensure at most one WB wallet fetch per cabinet per run.
    """

    ok_by_cabinet: dict[int, bool] = field(default_factory=dict)
    _locks_by_cabinet: dict[int, asyncio.Lock] = field(default_factory=dict)
    _locks_meta: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def lock_for(self, wb_cabinet_id: int) -> asyncio.Lock:
        async with self._locks_meta:
            lock = self._locks_by_cabinet.get(wb_cabinet_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks_by_cabinet[wb_cabinet_id] = lock
            return lock


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
        redis_campaign_activity_reason_manager: RedisCampaignActivityReasonManager | None = None,
    ) -> None:
        self._wb_modifier = wb_modifier
        self._tasks_manager = tasks_manager
        self._plan_fact_reader = plan_fact_reader or PlanFactReader()  # просят тесты, потом все это исправить, техдолг
        self._reason_manager = redis_campaign_activity_reason_manager

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
        time_settings_by_adv: dict[int, TimeSettingsDbState | None]
        async with get_session_maker(read_only=True) as session:
            time_settings_by_adv = await _time_settings_repo.load_for_adv_ids(
                session, unique_adv_ids
            )

        wb_wallet_cache = WbWalletOkCache()
        for adv in complex_advs:
            db_state = time_settings_by_adv[adv.adv_setting.id]
            handlers.append(
                lambda complex_adv=adv, ds=db_state, cache=wb_wallet_cache: self._auto_campaign_handler(
                    complex_adv,
                    start_of_day,
                    end_of_day,
                    db_state=ds,
                    wb_wallet_cache=cache,
                )
            )
            handlers.append(
                lambda complex_adv=adv, ds=db_state, cache=wb_wallet_cache: self._search_campaign_handler(
                    complex_adv,
                    start_of_day,
                    end_of_day,
                    db_state=ds,
                    wb_wallet_cache=cache,
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

    async def _set_auto_reason(
        self,
        adv_id: int,
        command: CampaignActivityCommand,
        reason_code: AutoReasonCode,
    ) -> None:
        if self._reason_manager is not None:
            await self._reason_manager.set(
                adv_id,
                "auto",
                CampaignActivityReason(command=command, reason_code=reason_code),
            )

    async def _set_search_reason(
        self,
        adv_id: int,
        command: CampaignActivityCommand,
        reason_code: AuctionReasonCode,
    ) -> None:
        if self._reason_manager is not None:
            await self._reason_manager.set(
                adv_id,
                "search",
                CampaignActivityReason(command=command, reason_code=reason_code),
            )

    async def _cabinet_has_positive_balance(
        self,
        adv: ComplexAdv,
        wb_wallet_cache: WbWalletOkCache,
    ) -> bool:
        wb_cabinet_id = adv.adv_setting.wb_cabinet_id
        balance, bonus = await balance_manager.get_cabinet_balance_and_bonuses(
            wb_cabinet_id
        )
        total = float(balance) + float(bonus)
        if total > 0:
            return True

        cache = wb_wallet_cache.ok_by_cabinet
        if wb_cabinet_id in cache:
            return cache[wb_cabinet_id]

        lock = await wb_wallet_cache.lock_for(wb_cabinet_id)
        async with lock:
            if wb_cabinet_id in cache:
                return cache[wb_cabinet_id]

            ok_wb = False
            try:
                wb_resp = await self._wb_modifier.get_campaign_balance()
                if wb_resp:
                    snap = balance_snapshot_from_response(wb_resp)
                    cashback = cashback_summary_from_response(wb_resp)
                    wb_cashbacks_total = cashback.total
                    wb_wallet_sum = (
                        snap.balance + snap.net + snap.bonus + wb_cashbacks_total
                    )
                    ok_wb = wb_wallet_sum > 0
            except Exception:
                ok_wb = False

            cache[wb_cabinet_id] = ok_wb
            return ok_wb

    async def _auto_campaign_handler(
        self,
        adv: ComplexAdv,
        start_of_day: datetime,
        end_of_day: datetime,
        *,
        db_state: TimeSettingsDbState | None,
        wb_wallet_cache: WbWalletOkCache,
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
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.TIME_SCHEDULE,
            )
            return None

        if not await self._cabinet_has_positive_balance(adv, wb_wallet_cache):
            if auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (cabinet balance <= 0) adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.INSUFFICIENT_BALANCE,
            )
            return None

        # Авто-кампанию ведём только при включённом режиме продвижения полок (rec_system_mode).
        # rec_system_mode по умолчанию False — кампании без явного включения полок остаются на паузе
        # по дизайну продукта: логика контроля активности и стратегий завязана на полки (сначала
        # самые дешёвые места, затем конверсия). Это не баг, а намеренное ограничение.
        # Ранний выход только из этого обработчика; аукцион (поиск) обрабатывается отдельно
        # в _search_campaign_handler, который вызывается тем же ensure_campaigns_active.
        if not adv.rec_system_promotion_mode_active:
            if auto_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auto campaign (rec_system mode off) adv_id=%s shop_id=%s",
                    auto_adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auto_campaign(adv)
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.REC_SYSTEM_MODE_OFF,
            )
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
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.COMMON_LIMIT_0,
                )
                return None
            if common_limit == 0 and auto_status != WBAdvActiveStatus.STARTED:
                await self._set_auto_reason(
                       auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.COMMON_LIMIT_0,
                )
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
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.COMMON_SPEND_EXCEEDED,
                )
                return None
            if 0 < common_limit <= combined_spend and auto_status != WBAdvActiveStatus.STARTED:
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.COMMON_SPEND_EXCEEDED,
                )
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
                await self._set_auto_reason(
                    auto_adv_id, CampaignActivityCommand.PAUSE, AutoReasonCode.AUTO_LIMIT_0
                )
                return None
            if auto_limit == 0 and auto_status != WBAdvActiveStatus.STARTED:
                await self._set_auto_reason(
                    auto_adv_id, CampaignActivityCommand.PAUSE, AutoReasonCode.AUTO_LIMIT_0
                )
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
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.AUTO_SPEND_EXCEEDED,
                )
                return None
            if 0 < auto_limit <= spend_today and auto_status != WBAdvActiveStatus.STARTED:
                await self._set_auto_reason(
                    auto_adv_id,
                    CampaignActivityCommand.PAUSE,
                    AutoReasonCode.AUTO_SPEND_EXCEEDED,
                )
                return None
            budget_ok = auto_limit > 0 and spend_today < auto_limit

        cost_activity = await is_auto_campaign_active(
            adv.adv_setting,
            plan_fact_reader=self._plan_fact_reader,
        )
        # When cost_activity is None we do not change campaign state (do nothing).
        # Do not record PAUSE here — the campaign may still be running; recording PAUSE
        # would make the UI show "на паузе" and contradict the real WB status.
        if cost_activity is None:
            logger.info(
                "Auto watchdog: insufficient cost data%s adv_id=%s shop_id=%s",
                cost_log_suffix,
                auto_adv_id,
                adv.shop_id,
            )
            return None

        if cost_activity is False and auto_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Auto watchdog: pausing auto campaign%s due to failed cost rule adv_id=%s shop_id=%s",
                cost_log_suffix,
                auto_adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.pause_auto_campaign(adv)
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.COST_RULE_FAILED,
            )
            return None
        if cost_activity is False and auto_status != WBAdvActiveStatus.STARTED:
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.PAUSE,
                AutoReasonCode.COST_RULE_FAILED,
            )
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
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.STARTED,
                AutoReasonCode.BUDGET_OK_COST_OK,
            )
        elif budget_ok and cost_rule_ok and auto_status == WBAdvActiveStatus.STARTED:
            await self._set_auto_reason(
                auto_adv_id,
                CampaignActivityCommand.STARTED,
                AutoReasonCode.BUDGET_OK_COST_OK,
            )

    async def _search_campaign_handler(
        self,
        adv: ComplexAdv,
        start_of_day: datetime,
        end_of_day: datetime,
        *,
        db_state: TimeSettingsDbState | None,
        wb_wallet_cache: WbWalletOkCache,
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
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.TIME_SCHEDULE,
            )
            return None

        if not await self._cabinet_has_positive_balance(adv, wb_wallet_cache):
            if search_status == WBAdvActiveStatus.STARTED:
                logger.info(
                    "Auto budget watcher: pausing auction campaign (cabinet balance <= 0) adv_id=%s shop_id=%s",
                    adv_id,
                    adv.shop_id,
                )
                await self._wb_modifier.pause_auction_campaign(adv)
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.INSUFFICIENT_BALANCE,
            )
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
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.PAUSE,
                    AuctionReasonCode.COMMON_LIMIT_0,
                )
                return None
            if common_limit == 0 and search_status != WBAdvActiveStatus.STARTED:
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.PAUSE,
                    AuctionReasonCode.COMMON_LIMIT_0,
                )
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
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.PAUSE,
                    AuctionReasonCode.COMMON_SPEND_EXCEEDED,
                )
                return None
            if 0 < common_limit <= combined_spend and search_status != WBAdvActiveStatus.STARTED:
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.PAUSE,
                    AuctionReasonCode.COMMON_SPEND_EXCEEDED,
                )
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
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.STARTED,
                    AuctionReasonCode.COMMON_OK,
                )
            elif (
                common_limit > 0
                and combined_spend < common_limit
                and search_status == WBAdvActiveStatus.STARTED
            ):
                await self._set_search_reason(
                    adv_id,
                    CampaignActivityCommand.STARTED,
                    AuctionReasonCode.COMMON_OK,
                )
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
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.SEARCH_SPEND_EXCEEDED,
            )
            return

        if search_limit > 0 and search_status in [WBAdvActiveStatus.PAUSE, WBAdvActiveStatus.READY_FOR_START]:
            logger.info(
                "Auto budget watcher: starting auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.start_auction_campaign(adv)
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.STARTED,
                AuctionReasonCode.SEARCH_LIMIT_OK,
            )
        elif search_limit > 0 and search_status == WBAdvActiveStatus.STARTED:
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.STARTED,
                AuctionReasonCode.SEARCH_LIMIT_OK,
            )
        elif search_limit == 0 and search_status == WBAdvActiveStatus.STARTED:
            logger.info(
                "Auto budget watcher: pausing auction campaign adv_id=%s shop_id=%s",
                adv_id,
                adv.shop_id,
            )
            await self._wb_modifier.pause_auction_campaign(adv)
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.SEARCH_LIMIT_0,
            )
        elif search_limit == 0 and search_status != WBAdvActiveStatus.STARTED:
            await self._set_search_reason(
                adv_id,
                CampaignActivityCommand.PAUSE,
                AuctionReasonCode.SEARCH_LIMIT_0,
            )

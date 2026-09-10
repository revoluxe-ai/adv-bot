from __future__ import annotations
from zoneinfo import ZoneInfo
from app.modules.common_slaves.wildberries.models.wb_auto_budget_topup import WBAutoBudgetTopUp
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm
import asyncio
import datetime
from datetime import timedelta
import logging
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.types import (
    UNSET,
)
from app.core.redis_manager_v2.redis_client import RedisClient
from app.shared.domains.wb.enums import (
    AdvType,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.shared.domains.wb.exceptions import NotEnoughBalanceOnShopError
from app.shared.domains.wb.utils.balance_source import (
    TopUpBalanceDecision,
    balance_snapshot_from_response,
    cashback_packages_from_response,
    cashback_summary_from_response,
    select_topup_balance_decision,
)
from app.settings import settings

from app.modules.auto_budget_manager.redis_auto_budget_last_success_manager import (
    RedisAutoBudgetLastSuccessManager,
)
from app.modules.auto_budget_manager.redis_auto_budget_topup_failed_manager import (
    RedisAutoBudgetTopupFailedManager,
)
from app.modules.auto_budget_manager.redis_shop_balance_snapshot_manager import (
    RedisShopBalanceSnapshotManager,
)
from app.modules.auto_budget_manager.redis_promo_state_manager import (
    RedisPromoStateManager,
)
from app.modules.auto_budget_manager.promo_state_service import PromoStateService
from app.shared.domains.wb.utils.promo_accounting import parse_expiration

import typing

if typing.TYPE_CHECKING:
    from app.core.di.wb_manager_hub import WBManagerHub


logger = logging.getLogger(__name__)

MSK_TZ = datetime.timezone(timedelta(hours=3))


class AutoBudgetEnsureStatus(StrEnum):
    LOCK_BUSY = "lock_busy"
    LIMIT_DISABLED = "limit_disabled"
    LIMIT_REACHED = "limit_reached"
    BALANCE_SUFFICIENT = "balance_sufficient"
    ADV_NOT_READY = "adv_not_ready"
    TOPPED_UP = "topped_up"
    TOPUP_UNVERIFIED = "topup_unverified"
    TOPUP_FAILED = "topup_failed"
    ERROR = "error"
    NOT_NEW_ADV_STATS = 'not_new_adv_stats'
    BALANCE_NOT_GET = "balance_not_get"



@dataclass(slots=True)
class _CampaignConfig:
    adv_id: int
    limit: int


@dataclass(slots=True)
class AutoBudgetEnsureResult:
    status: AutoBudgetEnsureStatus
    campaign_type: AdvType
    adv_id: int | None
    spend_today: float
    planned_amount: int | None = None
    available_limit: float | None = None
    reason: str | None = None
    budget_total_before: int | None = None
    budget_total_after: int | None = None
    raw_budget_response: dict[str, Any] | None = None
    raw_deposit_response: dict[str, Any] | None = None
    topup_id: int | None = None


class AutoBudgetService:
    """Сервис автопополнения бюджетов кампаний."""

    def __init__(
        self,
        redis_client: RedisClient
    ) -> None:
        self._redis = redis_client
        self._balance_snapshot_manager = RedisShopBalanceSnapshotManager(redis_client)
        self._promo_state_manager = RedisPromoStateManager(redis_client)
        self._promo_state_service = PromoStateService(self._promo_state_manager)
        self._topup_failed_manager = RedisAutoBudgetTopupFailedManager(redis_client)
        self._last_success_manager = RedisAutoBudgetLastSuccessManager(redis_client)
        self._lock_ttl = settings.AUTO_BUDGET_LOCK_TTL_SEC
        self._topup_amount = settings.AUTO_BUDGET_TOPUP_AMOUNT
        self._min_balance = settings.AUTO_BUDGET_MIN_BALANCE
        self._max_single_ratio = max(
            0.0, float(settings.AUTO_BUDGET_MAX_SINGLE_TOPUP_RATIO)
        )
        self._verification_attempts = max(
            0, int(settings.AUTO_BUDGET_VERIFICATION_ATTEMPTS)
        )
        self._verification_delay = max(
            0.0, float(settings.AUTO_BUDGET_VERIFICATION_DELAY_SEC)
        )

    def _stale_stats_wb_total_threshold(self) -> int:
        """WB campaign total above which we keep the stale full-stats gate.

        When stats are stale, we only proceed (using possibly stale spend counters)
        if the live WB budget snapshot is below this threshold or missing. If
        ``AUTO_BUDGET_MIN_BALANCE`` is zero, use the top-up step so the gate is not
        disabled entirely.
        """
        if self._min_balance > 0:
            return self._min_balance
        return max(1, self._topup_amount)

    async def ensure_budget(
        self,
        adv: ComplexAdv,
        adv_setting_id: int,
        campaign_type: AdvType,
        wb_manager_hub: "WBManagerHub",
        *,
        force_after_start_rejection: bool = False,
    ) -> AutoBudgetEnsureResult | None:
        """Пополнить бюджет кампании по уже загруженному ``ComplexAdv``.

        Настройки берутся из ``adv.adv_setting`` в памяти; повторный SELECT AdvSetting
        в этом пути не выполняется.

        При отсутствии связи ``AdvSetting`` → ``WBCabinet`` lookup ``_get_wb_shop_id``
        бросает ``ValueError``; внешний обработчик ловит исключение и возвращает
        ``None`` (пополнение на этом тике пропускается, воркер не падает).
        """
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.emergency import (
            should_suppress_budget_and_activity_restart,
        )

        if should_suppress_budget_and_activity_restart(
            getattr(adv.adv_setting, "card_ab_hold_emergency_latch", False)
        ):
            # spec ab-hold-emergency-kill-switch: latch ACTIVE → no top-up
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.ADV_NOT_READY,
                campaign_type=campaign_type,
                adv_id=None,
                spend_today=0.0,
                reason="A/B Hold Emergency latch active — top-up suppressed",
            )

        lock_key = self._lock_key(adv_setting_id, campaign_type)
        acquired = await self._acquire_lock(lock_key)
        if not acquired:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LOCK_BUSY,
                campaign_type=campaign_type,
                adv_id=None,
                spend_today=0.0,
                reason="Auto-budget lock is busy",
            )
        try:
            result = await self._ensure_budget_locked(
                adv,
                adv_setting_id,
                campaign_type,
                wb_manager_hub,
                force_after_start_rejection=force_after_start_rejection,
            )

            return result
        except Exception: # noqa
            logger.exception("Failed to ensure budget lock")
            return None
        finally:
            await self._release_lock(lock_key)

    async def _ensure_budget_locked(
        self,
        complex_adv: ComplexAdv,
        adv_setting_id: int,
        campaign_type: AdvType,
        wb_manager_hub: "WBManagerHub",
        *,
        force_after_start_rejection: bool = False,
    ) -> AutoBudgetEnsureResult:
        """Пополнение бюджета одной кампании (search/auto) под Redis-lock.

        Перед пополнением пишет снапшот баланса в Redis по ``shop_id`` из
        ``_get_wb_shop_id``; без валидной связи с кабинетом метод не доходит
        до deposit (см. ``ensure_budget``).
        """

        adv_setting = complex_adv.adv_setting
        config = self.get_campaign_config(complex_adv, campaign_type)
        if config is None:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.ADV_NOT_READY,
                campaign_type=campaign_type,
                adv_id=None,
                spend_today=0.0,
                reason="Target campaign adv_id is missing",
            )

        limit = config.limit or 0
        if limit <= 0:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_DISABLED,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=0.0,
                reason="Auto-budget limit is not configured",
            )
        last_full_adv_stat_update: datetime.datetime | None = (
            await self._get_last_full_stat_update(config.adv_id)
        )
        now_msk = self._now_msk()
        stats_too_old = bool(
            last_full_adv_stat_update
            and now_msk
            > last_full_adv_stat_update
            + timedelta(seconds=settings.UPDATE_FULL_ADV_STAT_PERIOD)
        )
        cached_budget_info = None
        if stats_too_old and not force_after_start_rejection:
            cached_budget_info = await wb_manager_hub.wb_modifier.get_campaign_budget(
                config.adv_id
            )
            pre_total = cached_budget_info.total
            threshold = self._stale_stats_wb_total_threshold()
            need_topup_despite_stale_stats = (
                pre_total is None or pre_total < threshold
            )
            if not need_topup_despite_stale_stats:
                return AutoBudgetEnsureResult(
                    status=AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS,
                    campaign_type=campaign_type,
                    adv_id=config.adv_id,
                    spend_today=0.0,
                    budget_total_before=pre_total,
                    reason="Last Update Full Adv Stats too old",
                )

        date_msk = now_msk.date()
        spend_today = await self._calculate_spend_today(config.adv_id, now_msk)
        successful_topups, attempt_sum = await self._get_daily_topup_sums(
            adv_setting_id=complex_adv.original_adv_setting_id,
            campaign_type=campaign_type,
            date_msk=date_msk,
        )

        if successful_topups >= limit:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_REACHED,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=spend_today,
                available_limit=0,
                reason="Daily successful top-ups already reached limit",
            )

        if attempt_sum / 2 >= limit:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_REACHED,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=spend_today,
                available_limit=0,
                reason="Daily top-up attempts doubled exceed limit",
            )

        if spend_today >= limit:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_REACHED,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=spend_today,
                available_limit=0,
                reason="Daily spend limit exceeded",
            )

        budget_info = (
            cached_budget_info
            if cached_budget_info is not None
            else await wb_manager_hub.wb_modifier.get_campaign_budget(config.adv_id)
        )
        current_budget = budget_info.total
        if (
            current_budget is not None
            and current_budget >= self._min_balance > 0
        ):
            if not force_after_start_rejection:
                return AutoBudgetEnsureResult(
                    status=AutoBudgetEnsureStatus.BALANCE_SUFFICIENT,
                    campaign_type=campaign_type,
                    adv_id=config.adv_id,
                    spend_today=spend_today,
                    budget_total_before=current_budget,
                    available_limit=limit - spend_today,
                )

        # Следующее пополнение всегда происходит фиксированным шагом из настроек.
        # Предыдущая проверка гарантийно запрещает топап, если суммарно уже пополнили больше лимита,
        # поэтому здесь достаточно брать настроечную величину.
        planned_amount = self._compute_planned_amount()
        if planned_amount <= 0:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_REACHED,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=spend_today,
                available_limit=max(limit - spend_today, 0),
                reason="Computed planned amount is zero",
            )


        balance_response = await wb_manager_hub.wb_modifier.get_campaign_balance()
        if not balance_response:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.BALANCE_NOT_GET,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=spend_today,
                available_limit=limit - spend_today,
                reason="Balance response is None",
            )
        snapshot = balance_snapshot_from_response(balance_response)
        cashback_summary = cashback_summary_from_response(balance_response)



        async with sm(read_only=True) as session:
            shop_id: str = await self._get_wb_shop_id(session, adv_setting_id)
        await self._balance_snapshot_manager.set(
            shop_id,
            snapshot.balance,
            snapshot.net,
            snapshot.bonus,
            cashbacks_total=cashback_summary.total,
            cashbacks_earliest_expiration=cashback_summary.earliest_expiration_date,
            cashbacks_best_percent=cashback_summary.best_percent,
            cashbacks_packages=cashback_packages_from_response(balance_response),
        )
        try:
            balance_decision = select_topup_balance_decision(
                balance_response,
                topup_amount=planned_amount,
            )
            balance_type_source = balance_decision.balance_name
        except NotEnoughBalanceOnShopError:
            await self._topup_failed_manager.set(adv_setting.id)
            logger.warning(
                "Not enough balance on shop for auto budget top-up, adv_setting_id=%s, campaign_type=%s",
                adv_setting_id,
                campaign_type,
            )
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.TOPUP_FAILED,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=spend_today,
                available_limit=limit - spend_today,
                reason="Not enough balance on shop",
            )
        promo_amount, promo_percent, promo_expires_at, ordinary_amount = (
            self._allocation_fields_from_decision(balance_decision, planned_amount)
        )
        async with sm(read_only=False) as session:
            topup_log = await self._create_topup_entry(
                session=session,
                adv_setting_id=adv_setting.id,
                adv_id=config.adv_id,
                campaign_type=campaign_type,
                date_msk=date_msk,
                amount=planned_amount,
                balance_type=balance_type_source,
                budget_before=current_budget,
                request_payload={
                    "amount": planned_amount,
                    "balance_type": balance_type_source,
                    "campaign_type": campaign_type,
                    "cashback_sum": (
                        balance_decision.cashback.cashback_sum
                        if balance_decision.cashback
                        else None
                    ),
                    "cashback_percent": (
                        balance_decision.cashback.cashback_percent
                        if balance_decision.cashback
                        else None
                    ),
                },
                promo_amount=promo_amount,
                promo_percent=promo_percent,
                promo_expires_at=promo_expires_at,
                ordinary_amount=ordinary_amount,
            )

        try:
            deposit_result = await wb_manager_hub.wb_modifier.top_up_budget(
                adv_id=config.adv_id,
                amount=planned_amount,
                balance_type=balance_type_source,
                return_total=True,
                cashback_sum=(
                    balance_decision.cashback.cashback_sum
                    if balance_decision.cashback
                    else None
                ),
                cashback_percent=(
                    balance_decision.cashback.cashback_percent
                    if balance_decision.cashback
                    else None
                ),
            )
        except Exception as exc:  # pragma: no cover - network errors
            logger.error(
                "Auto budget top-up failed for adv_id=%s: %s",
                config.adv_id,
                exc,
                exc_info=True,
            )
            async with sm(read_only=False) as session:
                await self._mark_topup_entry(
                    session,
                    topup_log,
                    status="failed",
                    reason=str(exc),
                )
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.TOPUP_FAILED,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=spend_today,
                planned_amount=planned_amount,
                available_limit=limit - spend_today,
                reason=str(exc),
                budget_total_before=current_budget,
                raw_budget_response=budget_info.raw,
                topup_id=topup_log.id,
            )

        verification_total = await self._verify_budget(
            config.adv_id,
            expected_growth=(current_budget or 0) + planned_amount,
            wb_manager_hub=wb_manager_hub,
        )

        final_status = (
            "success"
            if verification_total is not None
            else "unverified"
        )
        async with sm(read_only=False) as session:
            await self._mark_topup_entry(
                session,
                topup_log,
                status=final_status,
                budget_after=verification_total,
                response_payload=deposit_result.raw if deposit_result else {},
                reason=None
                if verification_total is not None
                else "WB budget did not report expected growth",
            )

        result_status = (
            AutoBudgetEnsureStatus.TOPPED_UP
            if verification_total is not None
            else AutoBudgetEnsureStatus.TOPUP_UNVERIFIED
        )
        await self._last_success_manager.set(adv_setting.id)
        await self._topup_failed_manager.clear(adv_setting.id)

        return AutoBudgetEnsureResult(
            status=result_status,
            campaign_type=campaign_type,
            adv_id=config.adv_id,
            spend_today=spend_today,
            planned_amount=planned_amount,
            available_limit=limit - spend_today,
            budget_total_before=current_budget,
            budget_total_after=verification_total,
            raw_budget_response=budget_info.raw,
            raw_deposit_response=deposit_result.raw if deposit_result else None,
            topup_id=topup_log.id,
        )

    @staticmethod
    def get_campaign_config(
        complex_adv: ComplexAdv, campaign_type: AdvType
    ) -> _CampaignConfig | None:
        adv_setting = complex_adv.adv_setting
        overlay = getattr(complex_adv, "effective_promo_plan", None)

        if campaign_type == AdvType.AUTO:
            adv_id = adv_setting.adv_id
            limit = adv_setting.auto_budget_daily_limit or 0
            if overlay is not None and getattr(overlay, "active", False):
                limit = int(overlay.PromoAutoBudget)
        elif campaign_type == AdvType.SEARCH:
            adv_id = adv_setting.search_adv_id
            limit = adv_setting.search_auto_budget_daily_limit or 0
            if overlay is not None and getattr(overlay, "active", False):
                limit = int(overlay.PropoSearchBudget)
        else:
            raise ValueError(f"Unknown auto budget campaign type: {campaign_type}")
        if adv_id is None:
            return None
        return _CampaignConfig(
            adv_id=adv_id,
            limit=limit,
        )

    @staticmethod
    async def _calculate_spend_today(
        adv_id: int,
        now_msk: datetime.datetime,
    ) -> float:
        adv_ids: set[int] = {adv_id}
        start = datetime.datetime.combine(
            now_msk.date(), datetime.time.min, tzinfo=MSK_TZ
        )
        end = datetime.datetime.combine(
            now_msk.date(), datetime.time.max, tzinfo=MSK_TZ
        )
        stats = await full_wb_adv_stat.get_daily_stats_by_last_days(
            list(adv_ids), start, end
        )

        total_spend = 0.0
        for stat in stats or []:
            spend = getattr(stat, "spend", 0)
            if spend:
                total_spend += float(spend)
        return total_spend

    @staticmethod
    async def _get_daily_topup_sums(
        adv_setting_id: int,
        campaign_type: AdvType,
        date_msk: datetime.date,
    ) -> tuple[float, float]:
        filters = (
            WBAutoBudgetTopUp.adv_setting_id == adv_setting_id,
            WBAutoBudgetTopUp.campaign_type == campaign_type,
            WBAutoBudgetTopUp.date_msk == date_msk,
        )
        success_stmt = (
            select(func.coalesce(func.sum(WBAutoBudgetTopUp.amount), 0))
            .where(*filters, WBAutoBudgetTopUp.status == "success")
        )
        attempts_stmt = (
            select(func.coalesce(func.sum(WBAutoBudgetTopUp.amount), 0))
            .where(*filters)
        )
        async with sm(read_only=True) as session:
            success_result = await session.execute(success_stmt)
            attempts_result = await session.execute(attempts_stmt)
        success_total = success_result.scalar() or 0
        attempts_total = attempts_result.scalar() or 0
        return float(success_total), float(attempts_total)

    @staticmethod
    def _allocation_fields_from_decision(
        balance_decision: TopUpBalanceDecision,
        amount: int,
    ) -> tuple[int | None, int | None, datetime.datetime | None, int]:
        """Typed promo allocation metadata для журнала. Credit только при success."""
        cashback = getattr(balance_decision, "cashback", None)
        if cashback is None:
            return None, None, None, int(amount)
        promo_amount = int(getattr(cashback, "cashback_sum", 0) or 0)
        if promo_amount <= 0:
            return None, None, None, int(amount)
        promo_percent = int(getattr(cashback, "cashback_percent", 0) or 0)
        promo_expires_at = parse_expiration(
            getattr(cashback, "expiration_date", None)
        )
        ordinary_amount = max(0, int(amount) - promo_amount)
        return promo_amount, promo_percent, promo_expires_at, ordinary_amount

    async def refresh_promo_state(
        self,
        advs: list[ComplexAdv],
        wb_manager_hub: "WBManagerHub",
        shop_id: str | int,
    ) -> None:
        """Обновить derived promo-overlay из live WB и PG ledger в Redis.

        Вызывается watchdog после построения ``advs``. После записи snapshot
        тот же snapshot сразу применяется к уже созданным DTO, поэтому
        budget/activity paths используют новый overlay в текущем тике, а не
        ждут следующего запуска. При miss/stale runtime получает
        консервативное ``M=1``.

        Args:
            advs: DTO кампаний текущего watchdog-тика.
            wb_manager_hub: WB API facade для balance и UPD.
            shop_id: идентификатор кабинета, ключ Redis state.
        """
        try:
            await self._promo_state_service.refresh(
                shop_id=shop_id,
                advs=advs,
                wb_modifier=wb_manager_hub.wb_modifier,
            )
        except Exception:
            logger.warning(
                "promo state refresh failed shop_id=%s",
                shop_id,
                exc_info=True,
            )
        try:
            cached_state = await self._promo_state_manager.get(shop_id)
        except Exception:
            logger.warning(
                "promo state snapshot read failed shop_id=%s",
                shop_id,
                exc_info=True,
            )
            cached_state = None
        from app.shared.domains.wb.utils.promo_overlay import (
            apply_cached_state_to_complex_adv,
        )

        for complex_adv in advs:
            try:
                _ = apply_cached_state_to_complex_adv(complex_adv, cached_state)
            except Exception:
                logger.warning(
                    "promo state overlay apply failed shop_id=%s adv_id=%s",
                    shop_id,
                    getattr(complex_adv, "adv_id", None),
                    exc_info=True,
                )

    @staticmethod
    async def _create_topup_entry(
        session: AsyncSession,
        adv_setting_id: int,
        adv_id: int,
        campaign_type: AdvType,
        date_msk: datetime.date,
        amount: int,
        balance_type: str,
        budget_before: int | None,
        request_payload: dict[str, Any],
        promo_amount: int | None = None,
        promo_percent: int | None = None,
        promo_expires_at: datetime.datetime | None = None,
        ordinary_amount: int | None = None,
    ) -> WBAutoBudgetTopUp:
        entry = WBAutoBudgetTopUp(
            adv_setting_id=adv_setting_id,
            adv_id=adv_id,
            campaign_type=campaign_type,
            date_msk=date_msk,
            idempotency_key=uuid.uuid4().hex,
            amount=amount,
            promo_amount=promo_amount,
            promo_percent=promo_percent,
            promo_expires_at=promo_expires_at,
            ordinary_amount=ordinary_amount,
            balance_type=balance_type,
            budget_before=float(budget_before)
            if budget_before is not None
            else None,
            status="started",
            request_payload=request_payload,
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return entry

    @staticmethod
    async def _mark_topup_entry(
        session: AsyncSession,
        topup: WBAutoBudgetTopUp,
        *,
        status: str,
        reason: str | None = None,
        budget_after: int | float | None = None,
        response_payload: dict[str, Any] | None = None,
    ) -> None:
        stored_topup = await session.get(WBAutoBudgetTopUp, topup.id)
        if stored_topup is None:
            raise ValueError(f"WBAutoBudgetTopUp {topup.id} not found")
        stored_topup.status = status
        stored_topup.reason = reason
        stored_topup.budget_after = (
            float(budget_after) if budget_after is not None else budget_after
        )
        stored_topup.response_payload = response_payload
        await session.commit()

    async def _verify_budget(
        self,
        adv_id: int,
        expected_growth: int,
        wb_manager_hub: "WBManagerHub",
    ) -> int | None:
        attempts = max(self._verification_attempts, 0)
        if attempts == 0:
            return None
        for attempt in range(attempts):
            if attempt:
                await asyncio.sleep(self._verification_delay)
            info = await wb_manager_hub.wb_modifier.get_campaign_budget(adv_id)
            total = info.total
            if total is not None and total >= expected_growth:
                return total
        return None

    def _compute_planned_amount(
        self,
    ) -> int:
        # Возвращаем количество, строго соответствующее конфигу AUTO_BUDGET_TOPUP_AMOUNT.
        # Лимиты уже проверены выше (_ensure_budget_locked) по сумме успешных топапов,
        # а эта функция просто озвучивает, сколько добавить в очередной раз.
        return self._topup_amount

    @staticmethod
    def _normalize_balance_type(value: str | None) -> str:
        if not value:
            return "balance"
        normalized = value.strip().lower()
        return normalized or "balance"

    @staticmethod
    def _coerce_balance_value(value: int | object) -> int:
        if isinstance(value, int):
            return value
        if value == UNSET:
            return 0
        return 0

    async def _acquire_lock(self, key: str) -> bool:
        try:
            return bool(
                await self._redis.set(key=key, value="1", ex=self._lock_ttl, nx=True)
            )
        except Exception as exc:  # pragma: no cover - redis errors
            logger.error("Failed to acquire auto budget lock: %s", exc)
            return False

    async def _release_lock(self, key: str) -> None:
        try:
            _ = await self._redis.delete(key)
        except Exception as exc: # noqa
            logger.exception('Failed to acquire auto budget lock: %s', exc)

    @staticmethod
    def _lock_key(
        adv_setting_id: int, campaign_type: AdvType
    ) -> str:
        return f"auto_budget_lock:{adv_setting_id}:{campaign_type}"

    @staticmethod
    def _lock_key_common(adv_setting_id: int) -> str:
        return f"auto_budget_lock:{adv_setting_id}:common"

    @staticmethod
    async def _get_daily_topup_sums_common(
        adv_setting_id: int,
        date_msk: datetime.date,
    ) -> tuple[float, float]:
        """Sum successful and all topups for adv_setting_id on date (any campaign_type)."""
        filters = (
            WBAutoBudgetTopUp.adv_setting_id == adv_setting_id,
            WBAutoBudgetTopUp.date_msk == date_msk,
        )
        success_stmt = (
            select(func.coalesce(func.sum(WBAutoBudgetTopUp.amount), 0))
            .where(*filters, WBAutoBudgetTopUp.status == "success")
        )
        attempts_stmt = (
            select(func.coalesce(func.sum(WBAutoBudgetTopUp.amount), 0))
            .where(*filters)
        )
        async with sm(read_only=True) as session:
            success_result = await session.execute(success_stmt)
            attempts_result = await session.execute(attempts_stmt)
        success_total = success_result.scalar() or 0
        attempts_total = attempts_result.scalar() or 0
        return float(success_total), float(attempts_total)

    async def ensure_common_budget(
        self,
        adv: ComplexAdv,
        adv_setting_id: int,
        wb_manager_hub: "WBManagerHub",
        *,
        force_after_start_rejection: bool = False,
        start_failure_campaign: AdvType | None = None,
    ) -> AutoBudgetEnsureResult | None:
        """Пополнить общий бюджет по уже загруженному ``ComplexAdv`` (без reload AdvSetting).

        При отсутствии связи ``AdvSetting`` → ``WBCabinet`` lookup ``_get_wb_shop_id``
        бросает ``ValueError``; внешний обработчик ловит исключение и возвращает
        ``None`` (пополнение на этом тике пропускается, воркер не падает).
        """
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.emergency import (
            should_suppress_budget_and_activity_restart,
        )

        if should_suppress_budget_and_activity_restart(
            getattr(adv.adv_setting, "card_ab_hold_emergency_latch", False)
        ):
            # spec ab-hold-emergency-kill-switch: latch ACTIVE → no common top-up
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.ADV_NOT_READY,
                campaign_type=AdvType.AUTO,
                adv_id=None,
                spend_today=0.0,
                reason="A/B Hold Emergency latch active — common top-up suppressed",
            )

        lock_key = self._lock_key_common(adv_setting_id)
        acquired = await self._acquire_lock(lock_key)
        if not acquired:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LOCK_BUSY,
                campaign_type=AdvType.AUTO,
                adv_id=None,
                spend_today=0.0,
                reason="Auto-budget common lock is busy",
            )
        try:
            result = await self._ensure_common_budget_locked(
                adv,
                adv_setting_id,
                wb_manager_hub,
                force_after_start_rejection=force_after_start_rejection,
                start_failure_campaign=start_failure_campaign,
            )
            return result
        except Exception:  # noqa
            logger.exception("Failed to ensure common budget")
            return None
        finally:
            await self._release_lock(lock_key)

    async def _ensure_common_budget_locked(
        self,
        adv: ComplexAdv,
        adv_setting_id: int,
        wb_manager_hub: "WBManagerHub",
        *,
        force_after_start_rejection: bool = False,
        start_failure_campaign: AdvType | None = None,
    ) -> AutoBudgetEnsureResult:
        """Пополнение общего бюджета по уже загруженному ``ComplexAdv`` (без reload AdvSetting).

        Перед пополнением пишет снапшот баланса в Redis по ``shop_id`` из
        ``_get_wb_shop_id``; без валидной связи с кабинетом метод не доходит
        до deposit (см. ``ensure_common_budget``).
        """
        if not adv.use_common_budget:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.ADV_NOT_READY,
                campaign_type=AdvType.AUTO,
                adv_id=None,
                spend_today=0.0,
                reason="Common budget mode is disabled",
            )
        limit = adv.common_budget_daily_limit or 0
        adv_id_auto = adv.auto_adv_id
        adv_id_search = adv.search_adv_id
        if adv_id_search is None:
            logger.error('Нет adv_id search_adv')
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.ADV_NOT_READY,
                campaign_type=AdvType.AUTO,
                adv_id=None,
                spend_today=0.0,
                reason="Search campaign (search_adv_id) is not configured",
            )
        if limit <= 0:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_DISABLED,
                campaign_type=AdvType.AUTO,
                adv_id=adv_id_auto,
                spend_today=0.0,
                reason="Common budget limit is not configured",
            )
        now_msk = self._now_msk()
        period = timedelta(seconds=settings.UPDATE_FULL_ADV_STAT_PERIOD)
        last_auto = await self._get_last_full_stat_update(adv_id_auto)
        last_search = await self._get_last_full_stat_update(adv_id_search)
        if last_auto is not None and last_search is not None:
            stats_stale_common = (
                now_msk > last_auto + period or now_msk > last_search + period
            )
        elif last_auto is not None:
            stats_stale_common = now_msk > last_auto + period
        elif last_search is not None:
            stats_stale_common = now_msk > last_search + period
        else:
            stats_stale_common = True
        cached_info_auto = None
        cached_info_search = None
        if stats_stale_common:
            cached_info_auto = await wb_manager_hub.wb_modifier.get_campaign_budget(
                adv_id_auto
            )
            cached_info_search = await wb_manager_hub.wb_modifier.get_campaign_budget(
                adv_id_search
            )
            ba_pre = cached_info_auto.total or 0
            bs_pre = cached_info_search.total or 0
            threshold = self._stale_stats_wb_total_threshold()
            both_comfortable_on_wb = (
                ba_pre >= threshold and bs_pre >= threshold
            )
            if both_comfortable_on_wb and not force_after_start_rejection:
                return AutoBudgetEnsureResult(
                    status=AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS,
                    campaign_type=AdvType.AUTO,
                    adv_id=adv_id_auto,
                    spend_today=0.0,
                    budget_total_before=int(ba_pre + bs_pre),
                    reason="Last full adv stats too old",
                )
        date_msk = now_msk.date()
        spend_auto = await self._calculate_spend_today(adv_id_auto, now_msk)

        spend_search = await self._calculate_spend_today(adv_id_search, now_msk)
        spend_today = spend_auto + spend_search

        successful_topups, attempt_sum = await self._get_daily_topup_sums_common(
            adv_setting_id=adv_setting_id,
            date_msk=date_msk,
        )
        if successful_topups >= limit:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_REACHED,
                campaign_type=AdvType.AUTO,
                adv_id=adv_id_auto,
                spend_today=spend_today,
                available_limit=0,
                reason="Daily successful top-ups already reached limit",
            )
        if attempt_sum / 2 >= limit:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_REACHED,
                campaign_type=AdvType.AUTO,
                adv_id=adv_id_auto,
                spend_today=spend_today,
                available_limit=0,
                reason="Daily top-up attempts doubled exceed limit",
            )
        if spend_today >= limit:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_REACHED,
                campaign_type=AdvType.AUTO,
                adv_id=adv_id_auto,
                spend_today=spend_today,
                available_limit=0,
                reason="Daily spend limit exceeded",
            )

        info_auto = (
            cached_info_auto
            if cached_info_auto is not None
            else await wb_manager_hub.wb_modifier.get_campaign_budget(adv_id_auto)
        )
        budget_auto = info_auto.total
        info_search = (
            cached_info_search
            if cached_info_search is not None
            else await wb_manager_hub.wb_modifier.get_campaign_budget(adv_id_search)
        )
        budget_search = info_search.total
        b_auto = budget_auto or 0
        b_search = budget_search or 0
        combined_budget = b_auto + b_search
        threshold = self._stale_stats_wb_total_threshold()
        search_status_raw = getattr(adv, "search_adv_active_status_str", None)
        search_status = (
            search_status_raw.value
            if isinstance(search_status_raw, WBAdvActiveStatus)
            else search_status_raw
        )
        search_cold_start_needs_budget = (
            search_status
            in (
                WBAdvActiveStatus.PAUSE.value,
                WBAdvActiveStatus.READY_FOR_START.value,
            )
            and b_search < threshold
        )
        if (
            (last_auto is None or last_search is None)
            and not force_after_start_rejection
            and not search_cold_start_needs_budget
        ):
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS,
                campaign_type=AdvType.AUTO,
                adv_id=adv_id_auto,
                spend_today=spend_today,
                budget_total_before=int(combined_budget),
                reason="Missing full adv stats for one or both campaigns",
            )
        if (
            self._min_balance > 0
            and b_auto >= self._min_balance
            and b_search >= self._min_balance
        ):
            if not (
                force_after_start_rejection
                and start_failure_campaign is not None
            ):
                return AutoBudgetEnsureResult(
                    status=AutoBudgetEnsureStatus.BALANCE_SUFFICIENT,
                    campaign_type=AdvType.AUTO,
                    adv_id=adv_id_auto,
                    spend_today=spend_today,
                    budget_total_before=int(combined_budget),
                    available_limit=limit - spend_today,
                )
        planned_amount = self._compute_planned_amount()
        if planned_amount <= 0:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.LIMIT_REACHED,
                campaign_type=AdvType.AUTO,
                adv_id=adv_id_auto,
                spend_today=spend_today,
                available_limit=max(limit - spend_today, 0),
                reason="Computed planned amount is zero",
            )

        if (
            force_after_start_rejection
            and start_failure_campaign == AdvType.SEARCH
        ):
            target_adv_id = adv_id_search
            target_campaign_type = AdvType.SEARCH
        elif (
            force_after_start_rejection
            and start_failure_campaign == AdvType.AUTO
        ):
            target_adv_id = adv_id_auto
            target_campaign_type = AdvType.AUTO
        elif search_cold_start_needs_budget:
            target_adv_id = adv_id_search
            target_campaign_type = AdvType.SEARCH
        elif (budget_auto or 0) <= (budget_search or 0):
            target_adv_id = adv_id_auto
            target_campaign_type = AdvType.AUTO
        else:
            target_adv_id = adv_id_search
            target_campaign_type = AdvType.SEARCH
        current_budget = (
            budget_auto if target_campaign_type == AdvType.AUTO else budget_search
        )
        balance_response = await wb_manager_hub.wb_modifier.get_campaign_balance()
        if not balance_response:
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.BALANCE_NOT_GET,
                campaign_type=target_campaign_type,
                adv_id=target_adv_id,
                spend_today=spend_today,
                available_limit=limit - spend_today,
                reason="Balance response is None",
            )
        snapshot = balance_snapshot_from_response(balance_response)
        cashback_summary = cashback_summary_from_response(balance_response)
        async with sm(read_only=True) as session:
            shop_id = await self._get_wb_shop_id(
                session, adv.original_adv_setting_id
            )

        await self._balance_snapshot_manager.set(
            shop_id,
            snapshot.balance,
            snapshot.net,
            snapshot.bonus,
            cashbacks_total=cashback_summary.total,
            cashbacks_earliest_expiration=cashback_summary.earliest_expiration_date,
            cashbacks_best_percent=cashback_summary.best_percent,
            cashbacks_packages=cashback_packages_from_response(balance_response),
        )
        try:
            balance_decision = select_topup_balance_decision(
                balance_response,
                topup_amount=planned_amount,
            )
            balance_type_source = balance_decision.balance_name
        except NotEnoughBalanceOnShopError:
            await self._topup_failed_manager.set(adv.original_adv_setting_id)
            logger.warning(
                "Not enough balance on shop for common budget top-up, adv_setting_id=%s",
                adv_setting_id,
            )
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.TOPUP_FAILED,
                campaign_type=target_campaign_type,
                adv_id=target_adv_id,
                spend_today=spend_today,
                available_limit=limit - spend_today,
                reason="Not enough balance on shop",
            )
        promo_amount, promo_percent, promo_expires_at, ordinary_amount = (
            self._allocation_fields_from_decision(balance_decision, planned_amount)
        )
        async with sm(read_only=False) as session:
            topup_log = await self._create_topup_entry(
                session=session,
                adv_setting_id=adv.original_adv_setting_id,
                adv_id=target_adv_id,
                campaign_type=target_campaign_type,
                date_msk=date_msk,
                amount=planned_amount,
                balance_type=balance_type_source,
                budget_before=current_budget,
                request_payload={
                    "amount": planned_amount,
                    "balance_type": balance_type_source,
                    "campaign_type": target_campaign_type,
                    "common_budget": True,
                    "cashback_sum": (
                        balance_decision.cashback.cashback_sum
                        if balance_decision.cashback
                        else None
                    ),
                    "cashback_percent": (
                        balance_decision.cashback.cashback_percent
                        if balance_decision.cashback
                        else None
                    ),
                },
                promo_amount=promo_amount,
                promo_percent=promo_percent,
                promo_expires_at=promo_expires_at,
                ordinary_amount=ordinary_amount,
            )
        try:
            deposit_result = await wb_manager_hub.wb_modifier.top_up_budget(
                adv_id=target_adv_id,
                amount=planned_amount,
                balance_type=balance_type_source,
                return_total=True,
                cashback_sum=(
                    balance_decision.cashback.cashback_sum
                    if balance_decision.cashback
                    else None
                ),
                cashback_percent=(
                    balance_decision.cashback.cashback_percent
                    if balance_decision.cashback
                    else None
                ),
            )
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Auto budget common top-up failed for adv_id=%s: %s",
                target_adv_id,
                exc,
                exc_info=True,
            )
            async with sm(read_only=False) as session:
                await self._mark_topup_entry(
                    session,
                    topup_log,
                    status="failed",
                    reason=str(exc),
                )
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.TOPUP_FAILED,
                campaign_type=target_campaign_type,
                adv_id=target_adv_id,
                spend_today=spend_today,
                planned_amount=planned_amount,
                available_limit=limit - spend_today,
                reason=str(exc),
                budget_total_before=current_budget,
                topup_id=topup_log.id,
            )
        verification_total = await self._verify_budget(
            target_adv_id,
            (current_budget or 0) + planned_amount,
            wb_manager_hub=wb_manager_hub,
        )
        final_status = (
            "success"
            if verification_total is not None
            else "unverified"
        )
        async with sm(read_only=False) as session:
            await self._mark_topup_entry(
                session,
                topup_log,
                status=final_status,
                budget_after=verification_total,
                response_payload=deposit_result.raw if deposit_result else {},
                reason=None
                if verification_total is not None
                else "WB budget did not report expected growth",
            )
        result_status = (
            AutoBudgetEnsureStatus.TOPPED_UP
            if verification_total is not None
            else AutoBudgetEnsureStatus.TOPUP_UNVERIFIED
        )
        await self._last_success_manager.set(adv.original_adv_setting_id)
        await self._topup_failed_manager.clear(adv.original_adv_setting_id)
        return AutoBudgetEnsureResult(
            status=result_status,
            campaign_type=target_campaign_type,
            adv_id=target_adv_id,
            spend_today=spend_today,
            planned_amount=planned_amount,
            available_limit=limit - spend_today,
            budget_total_before=current_budget,
            budget_total_after=verification_total,
            raw_deposit_response=deposit_result.raw if deposit_result else None,
            topup_id=topup_log.id,
        )

    @staticmethod
    def _now_msk() -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc).astimezone(MSK_TZ)

    @staticmethod
    async def _get_last_full_stat_update(adv_id: int) -> datetime.datetime | None:
        dt = await data_manager.get_last_full_stat_update(adv_id)
        if dt is None:
            return None
        dt = dt.replace(tzinfo=ZoneInfo("Europe/Moscow"))
        return dt

    @staticmethod
    async def _get_wb_shop_id(session: AsyncSession, adv_setting_id: int) -> str:
        """Вернуть ``WBCabinet.shop_id`` для сегмента ключа Redis-снапшота баланса.

        Args:
            session: read-only сессия SQLAlchemy.
            adv_setting_id: PK ``AdvSetting.id`` (не ``adv_id`` WB).

        Returns:
            Строковый ``shop_id`` кабинета, связанного с настройкой РК.

        Raises:
            ValueError: если join ``AdvSetting`` → ``WBCabinet`` не нашёл кабинет.
                В штатном потоке watchdog каждая РК привязана к кабинету; при битых
                данных ensure_* на этом тике возвращает ``None`` (fail-fast вместо
                пополнения без снапшота баланса).
        """
        shop_id_get_query = (
            select(WBCabinet.shop_id)
            .join(WBCabinet.adv_settings)
            .where(AdvSetting.id == adv_setting_id)
        )
        result = await session.execute(shop_id_get_query)
        shop_id: str | None = result.scalar_one_or_none()
        if shop_id is None:
            raise ValueError(f"No WB cabinet found for adv_setting_id={adv_setting_id}")
        return shop_id

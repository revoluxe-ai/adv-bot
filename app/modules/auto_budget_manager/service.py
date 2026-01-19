from __future__ import annotations

import math
from zoneinfo import ZoneInfo

from app.modules.common_slaves.wildberries.models.wb_auto_budget_topup import WBAutoBudgetTopUp
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


from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.types import (
    UNSET,
)
from app.core.redis_manager_v2.redis_client import RedisClient
from app.shared.domains.wb.enums import (
    AdvType,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.shared.domains.wb.utils.balance_source import (
    select_balance_source_from_response,
)
from app.settings import settings

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
        self._lock_ttl = settings.AUTO_BUDGET_LOCK_TTL_SEC
        self._topup_amount = settings.AUTO_BUDGET_TOPUP_AMOUNT
        self._min_balance = settings.AUTO_BUDGET_MIN_BALANCE
        self._max_single_ratio = max(
            0.0, float(settings.AUTO_BUDGET_MAX_SINGLE_TOPUP_RATIO)
        )
        self._min_remaining_limit = max(
            0, int(settings.AUTO_BUDGET_MIN_REMAINING_LIMIT)
        )
        self._verification_attempts = max(
            0, int(settings.AUTO_BUDGET_VERIFICATION_ATTEMPTS)
        )
        self._verification_delay = max(
            0.0, float(settings.AUTO_BUDGET_VERIFICATION_DELAY_SEC)
        )

    @staticmethod
    async def set_daily_limit(
        adv_setting_id: int,
        limit: int,
        balance_type: str | None,
        campaign_type: AdvType,
    ) -> None:
        async with sm(read_only=False) as session:
            adv_setting = await session.get(AdvSetting, adv_setting_id)
            if adv_setting is None:
                raise ValueError(f"AdvSetting {adv_setting_id} not found")
            normalized_balance = balance_type.strip() if balance_type else None
            if campaign_type == AdvType.AUTO:
                adv_setting.auto_budget_daily_limit = max(limit, 0)
                adv_setting.auto_budget_balance_type = normalized_balance
            else:
                adv_setting.search_auto_budget_daily_limit = max(limit, 0)
                adv_setting.search_auto_budget_balance_type = normalized_balance
            await session.commit()

    async def ensure_budget(
        self,
        adv_setting_id: int,
        campaign_type: AdvType,
        wb_manager_hub: "WBManagerHub",
    ) -> AutoBudgetEnsureResult | None:
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
                adv_setting_id, campaign_type, wb_manager_hub
            )

            return result
        except Exception: # noqa
            logger.exception("Failed to ensure budget lock")
            return None
        finally:
            await self._release_lock(lock_key)

    async def _ensure_budget_locked(
        self,
        adv_setting_id: int,
        campaign_type: AdvType,
        wb_manager_hub: "WBManagerHub",
    ) -> AutoBudgetEnsureResult:

        async with sm(read_only=True) as session:
            adv_setting = await session.get(AdvSetting, adv_setting_id)
        config = self.get_campaign_config(adv_setting, campaign_type)
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
        last_full_adv_stat_update: datetime.datetime | None =  await self._get_last_full_stat_update(config.adv_id)
        now_msk = self._now_msk()

        if (last_full_adv_stat_update
                and now_msk > last_full_adv_stat_update
                + timedelta(seconds=settings.UPDATE_FULL_ADV_STAT_PERIOD)):
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.NOT_NEW_ADV_STATS,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=0.0,
                reason="Last Update Full Adv Stats too old",
            )

        date_msk = now_msk.date()
        spend_today = await self._calculate_spend_today(config.adv_id, now_msk)
        successful_topups, attempt_sum = await self._get_daily_topup_sums(
            adv_setting_id=adv_setting.id,
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

        budget_info = await wb_manager_hub.wb_modifier.get_campaign_budget(
            config.adv_id
        )
        current_budget = budget_info.total
        if (
            current_budget is not None
            and current_budget >= self._min_balance > 0
        ):
            return AutoBudgetEnsureResult(
                status=AutoBudgetEnsureStatus.BALANCE_SUFFICIENT,
                campaign_type=campaign_type,
                adv_id=config.adv_id,
                spend_today=spend_today,
                budget_total_before=current_budget,
                available_limit=limit - spend_today,
            )

        remaining_successful_limit = max(limit - successful_topups, 0)
        planned_amount = self._compute_planned_amount(
            limit=limit,
            spend_today=spend_today,
            remaining_topup_amount=remaining_successful_limit,
        )
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
        _, balance_type_source = select_balance_source_from_response(
            balance_response)
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
                },
            )

        try:
            deposit_result = await wb_manager_hub.wb_modifier.top_up_budget(
                adv_id=config.adv_id,
                amount=planned_amount,
                balance_type=balance_type_source,
                return_total=True,
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
        adv_setting: AdvSetting, campaign_type: AdvType
    ) -> _CampaignConfig | None:
        if campaign_type == AdvType.AUTO:
            adv_id = adv_setting.adv_id
            limit = adv_setting.auto_budget_daily_limit or 0
        elif campaign_type == AdvType.SEARCH:
            adv_id = adv_setting.search_adv_id
            limit = adv_setting.search_auto_budget_daily_limit or 0
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
    ) -> WBAutoBudgetTopUp:
        entry = WBAutoBudgetTopUp(
            adv_setting_id=adv_setting_id,
            adv_id=adv_id,
            campaign_type=campaign_type,
            date_msk=date_msk,
            idempotency_key=uuid.uuid4().hex,
            amount=amount,
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
        limit: int,
        spend_today: float,
        remaining_topup_amount: float,
    ) -> int:
        available = max(limit - spend_today, 0)
        if self._min_remaining_limit > 0 and available < self._min_remaining_limit:
            return 0
        if available <= 0 or remaining_topup_amount <= 0:
            return 0
        topup_increment = max(int(self._topup_amount), 1)
        deficit = max(available, topup_increment)
        multiplier = math.ceil(deficit / topup_increment)
        planned = multiplier * topup_increment
        return planned

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
            await self._redis.delete(key)
        except Exception as exc: # noqa
            logger.exception('Failed to acquire auto budget lock: %s', exc)

    @staticmethod
    def _lock_key(
        adv_setting_id: int, campaign_type: AdvType
    ) -> str:
        return f"auto_budget_lock:{adv_setting_id}:{campaign_type}"

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

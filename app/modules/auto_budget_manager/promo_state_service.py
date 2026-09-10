"""Refresh common-pool + campaign promo remaining and cache derived overlay."""

from __future__ import annotations

import datetime
import logging
from decimal import Decimal
from typing import Any, Iterable, Mapping

from app.modules.auto_budget_manager.promo_ledger import (
    PROMO_LOOKBACK_DAYS,
    ingest_promo_upd_items,
    load_campaign_ledgers,
    load_oldest_live_allocation_at,
)
from app.modules.auto_budget_manager.redis_promo_state_manager import (
    CachedCampaignPromoState,
    RedisPromoStateManager,
)
from app.settings import settings
from app.shared.domains.wb.utils.promo_accounting import resolve_promo_availability
from app.shared.domains.wb.utils.promo_plan_multiplier import (
    PROMO_AUTO_BUDGET_LABEL,
    PROMO_MAX_CPO_LABEL,
    PROMO_TARGET_BUDGET_LABEL,
    PROMO_TARGET_CPO_LABEL,
    PROPO_SEARCH_BUDGET_LABEL,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

# Единое окно с приходом/расходом ledger (см. promo_ledger.PROMO_LOOKBACK_DAYS).
_UPD_LOOKBACK_DAYS = PROMO_LOOKBACK_DAYS

# Максимальная длина одного WB GET /adv/v1/upd (интервал inclusive, календарные дни).
UPD_API_MAX_WINDOW_DAYS = 30


def _resolve_upd_from_date(
    *,
    now: datetime.datetime,
    last_successful_ingest_at: datetime.datetime | None,
    oldest_live_allocation_at: datetime.datetime | None = None,
) -> datetime.date:
    """Вернуть начало incremental UPD-запроса с безопасным календарным overlap.

    API WB принимает границы только в днях. Поэтому после успешного ingest
    повторно читается день watermark: так не теряются строки, появившиеся или
    исправленные WB позднее в тот же день. Первый запрос после Redis miss
    берёт минимум recovery-interval ``PROMO_LOOKBACK_DAYS`` и, если есть
    старый живой allocation, расширяется до его даты.
    """
    fallback = now.date() - datetime.timedelta(days=_UPD_LOOKBACK_DAYS)
    if last_successful_ingest_at is None:
        resolved = fallback
    else:
        if last_successful_ingest_at.tzinfo is None:
            last_successful_ingest_at = last_successful_ingest_at.replace(
                tzinfo=datetime.timezone.utc
            )
        resolved = max(fallback, min(last_successful_ingest_at.date(), now.date()))
    if oldest_live_allocation_at is not None:
        if oldest_live_allocation_at.tzinfo is None:
            oldest_live_allocation_at = oldest_live_allocation_at.replace(
                tzinfo=datetime.timezone.utc
            )
        resolved = min(resolved, oldest_live_allocation_at.date())
    return min(resolved, now.date())


def _iter_upd_date_ranges(
    *,
    from_date: datetime.date,
    to_date: datetime.date,
) -> Iterable[tuple[datetime.date, datetime.date]]:
    """Разбить UPD-backfill на непересекающиеся API-окна ≤ ``UPD_API_MAX_WINDOW_DAYS``.

    Recovery-горизонт ``PROMO_LOOKBACK_DAYS`` задаётся в ``_resolve_upd_from_date``;
    здесь только chunking под лимит WB «не больше месяца» на один запрос.
    """
    if from_date > to_date:
        return
    window_days = max(1, UPD_API_MAX_WINDOW_DAYS)
    current = from_date
    while current <= to_date:
        window_end = min(
            current + datetime.timedelta(days=window_days - 1),
            to_date,
        )
        yield current, window_end
        current = window_end + datetime.timedelta(days=1)


def _advert_ids_from_settings(advs: Iterable[Any]) -> list[int]:
    ids: set[int] = set()
    for adv in advs:
        setting = getattr(adv, "adv_setting", adv)
        auto_id = getattr(setting, "adv_id", None)
        search_id = getattr(setting, "search_adv_id", None)
        if auto_id:
            ids.add(int(auto_id))
        if search_id:
            ids.add(int(search_id))
    return sorted(ids)


def log_effective_promo_entities(
    *,
    adv_id: int,
    overlay: Any,
) -> None:
    """Логировать Owner labels пяти effective entities буквально."""
    logger.info(
        "RaisePlanOnPromobonuses overlay adv_id=%s active=%s f=%s M=%s "
        "%s=%s %s=%s %s=%s %s=%s %s=%s",
        adv_id,
        getattr(overlay, "active", False),
        getattr(overlay, "fraction", Decimal("0")),
        getattr(overlay, "multiplier", Decimal("1")),
        PROMO_MAX_CPO_LABEL,
        getattr(overlay, "PromoMaxCPO", None),
        PROMO_TARGET_CPO_LABEL,
        getattr(overlay, "PromoTargetCPO", None),
        PROMO_AUTO_BUDGET_LABEL,
        getattr(overlay, "PromoAutoBudget", None),
        PROPO_SEARCH_BUDGET_LABEL,
        getattr(overlay, "PropoSearchBudget", None),
        PROMO_TARGET_BUDGET_LABEL,
        getattr(overlay, "promo_target_budget", None),
    )


class PromoStateService:
    """Read-only WB refresh + PG ledger → Redis derived promo state.

    Сбой ``get_campaign_balance`` (исключение или ``None`` / непригодный
    payload) публикует snapshot с ``overlay_trusted=False``. Это сохраняет
    ingest watermarks для следующей попытки, но overlay readers переходят
    в консервативный ``M=1``.
    """

    def __init__(self, redis_manager: RedisPromoStateManager) -> None:
        self._redis = redis_manager

    async def refresh(
        self,
        *,
        shop_id: str | int,
        advs: Iterable[Any],
        wb_modifier: Any,
        campaign_budget_by_adv_id: Mapping[int, int | None] | None = None,
    ) -> None:
        """Обновить spend journal и derived cache. Без production mutations.

        Args:
            shop_id: идентификатор магазина для Redis derived cache.
            advs: кампании магазина (берём adv_id / search_adv_id).
            wb_modifier: WB client с get_campaign_balance / get_costs_history.
            campaign_budget_by_adv_id: опциональные бюджеты для ledger.

        Если ``get_campaign_balance`` падает или возвращает ``None`` /
        непригодный payload, snapshot всё равно записывается с
        ``overlay_trusted=False``: предыдущий snapshot не остаётся
        доверенным, а watermarks UPD не теряются. Успешный non-None объект
        (в том числе пустой cashback) — не сбой fetch: snapshot пишется как
        обычно.
        """
        advert_ids = _advert_ids_from_settings(advs)
        now = datetime.datetime.now(datetime.timezone.utc)
        topup_amount = int(getattr(settings, "AUTO_BUDGET_TOPUP_AMOUNT", 1000) or 1000)
        try:
            previous_state = await self._redis.get(shop_id)
        except Exception:
            logger.warning(
                "promo state: cannot read UPD ingest watermark shop_id=%s",
                shop_id,
                exc_info=True,
            )
            previous_state = None
        upd_ingested_at = (
            previous_state.upd_ingested_at if previous_state is not None else None
        )
        upd_coverage_from = (
            previous_state.upd_coverage_from if previous_state is not None else None
        )
        oldest_live_allocation_at: datetime.datetime | None = None
        coverage_lookup_ok = True
        pool_response = None
        pool_fetch_ok = False
        try:
            pool_response = await wb_modifier.get_campaign_balance()
            pool_fetch_ok = pool_response is not None
        except Exception:
            logger.warning(
                "promo state: get_campaign_balance failed shop_id=%s",
                shop_id,
                exc_info=True,
            )
        if upd_coverage_from is None and advert_ids:
            try:
                async with sm(read_only=True) as session:
                    oldest_live_allocation_at = (
                        await load_oldest_live_allocation_at(
                            session,
                            advert_ids,
                            now=now,
                        )
                    )
            except Exception:
                logger.warning(
                    "promo state: cannot determine historical UPD coverage "
                    "shop_id=%s",
                    shop_id,
                    exc_info=True,
                )
                coverage_lookup_ok = False
        upd_ingest_ok = False
        try:
            # WB не даёт live per-campaign promo balance: списания кэшбэка берём
            # из УПД (paymentType Keshbek/Кэшбэк) и пишем в WBCampaignPromoSpend.
            to_date = now.date()
            from_date = _resolve_upd_from_date(
                now=now,
                last_successful_ingest_at=upd_ingested_at,
                oldest_live_allocation_at=(
                    None
                    if upd_coverage_from is not None
                    else oldest_live_allocation_at
                ),
            )
            for window_from, window_to in _iter_upd_date_ranges(
                from_date=from_date,
                to_date=to_date,
            ):
                try:
                    items = await wb_modifier.get_costs_history(
                        from_date=window_from,
                        to_date=window_to,
                    )
                except Exception:
                    logger.warning(
                        "promo state: UPD_FETCH_FAILED shop_id=%s "
                        "from=%s to=%s",
                        shop_id,
                        window_from,
                        window_to,
                        exc_info=True,
                    )
                    raise
                try:
                    async with sm(read_only=False) as session:
                        _ = await ingest_promo_upd_items(session, items or [])
                except Exception:
                    logger.warning(
                        "promo state: UPD_PG_INGEST_FAILED shop_id=%s "
                        "from=%s to=%s",
                        shop_id,
                        window_from,
                        window_to,
                        exc_info=True,
                    )
                    raise
            # Обновляем watermark только после успешного request и PG ingest.
            upd_ingested_at = now
            if upd_coverage_from is None and coverage_lookup_ok:
                upd_coverage_from = datetime.datetime.combine(
                    from_date,
                    datetime.time.min,
                    tzinfo=datetime.timezone.utc,
                )
            upd_ingest_ok = True
        except Exception:
            # Детали уже в UPD_FETCH_FAILED / UPD_PG_INGEST_FAILED выше.
            pass
        ledgers: dict[int, Any] = {}
        ledger_load_ok = True
        if advert_ids:
            try:
                async with sm(read_only=True) as session:
                    ledgers = await load_campaign_ledgers(
                        session,
                        advert_ids,
                        now=now,
                        campaign_budget_by_adv_id=dict(
                            campaign_budget_by_adv_id or {}
                        ),
                    )
            except Exception:
                ledger_load_ok = False
                logger.warning(
                    "promo state: campaign ledger load failed shop_id=%s",
                    shop_id,
                    exc_info=True,
                )
        overlay_trusted = (
            pool_fetch_ok
            and upd_ingest_ok
            and coverage_lookup_ok
            and ledger_load_ok
        )
        campaigns: dict[int, CachedCampaignPromoState] = {}
        shop_pool_usable = False
        shop_pool_amount = 0
        shop_pool_fraction = Decimal("0")
        for adv_id in advert_ids:
            availability = resolve_promo_availability(
                pool_response=pool_response,
                topup_amount=topup_amount,
                campaign_ledger=ledgers.get(adv_id),
                now=now,
            )
            if availability.pool_usable:
                shop_pool_usable = True
                shop_pool_amount = availability.pool_amount
                shop_pool_fraction = availability.pool_fraction
            expires_at = None
            if availability.campaign_expires_at is not None:
                expires_at = availability.campaign_expires_at.isoformat()
            campaigns[adv_id] = CachedCampaignPromoState(
                remaining=availability.campaign_remaining,
                fraction=availability.campaign_fraction,
                expires_at=expires_at,
                usable=availability.usable,
                effective_fraction=availability.fraction,
                pool_usable=availability.pool_usable,
                campaign_usable=availability.campaign_usable,
            )
        await self._redis.set(
            shop_id,
            topup_amount=topup_amount,
            pool_usable=shop_pool_usable,
            pool_amount=shop_pool_amount,
            pool_fraction=shop_pool_fraction,
            campaigns=campaigns,
            upd_ingested_at=upd_ingested_at,
            upd_coverage_from=upd_coverage_from,
            overlay_trusted=overlay_trusted,
        )
        logger.info(
            "promo state refreshed shop_id=%s campaigns=%s pool_usable=%s "
            "pool_amount=%s overlay_trusted=%s pool_fetch_ok=%s upd_ingest_ok=%s",
            shop_id,
            len(campaigns),
            shop_pool_usable,
            shop_pool_amount,
            overlay_trusted,
            pool_fetch_ok,
            upd_ingest_ok,
        )

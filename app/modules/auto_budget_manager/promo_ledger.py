"""Загрузка allocation/spend и ingest UPD для promo remaining."""

from __future__ import annotations

import datetime
from collections import defaultdict
from typing import Any, Iterable, cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.types import (
    UNSET,
)
from app.modules.common_slaves.wildberries.models.wb_auto_budget_topup import (
    WBAutoBudgetTopUp,
)
from app.modules.common_slaves.wildberries.models.wb_campaign_promo_spend import (
    WBCampaignPromoSpend,
)
from app.shared.domains.wb.utils.promo_accounting import (
    CampaignPromoLedger,
    PromoAllocationTranche,
    PromoSpendRow,
    campaign_ledger_from_rows,
    is_expired,
    is_promo_payment_type,
    parse_expiration,
    spend_fingerprint,
)

# Окно UPD ingest (PromoStateService._UPD_LOOKBACK_DAYS). Ledger leftover-usable
# не режет этим cutoff: живой leftover старше 90d должен оставаться usable.
# Приход и расход на load выровнены (оба без cutoff), иначе allocation без
# spend завышает remaining. Ingest lookback этим не расширяется.
PROMO_LOOKBACK_DAYS = 90


def _unset_to_none(value: Any) -> Any:
    if value is UNSET:
        return None
    return value


def parse_upd_time(value: Any) -> datetime.datetime | None:
    """Разобрать updTime WB в aware datetime."""
    raw = _unset_to_none(value)
    if raw is None:
        return None
    if isinstance(raw, datetime.datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=datetime.timezone.utc)
        return raw
    return parse_expiration(str(raw))


async def load_success_tranches(
    session: AsyncSession,
    advert_ids: Iterable[int],
    *,
    cutoff: datetime.datetime | None = None,
) -> list[PromoAllocationTranche]:
    """Verified allocations: status=success и promo_amount > 0.

    ``cutoff`` — опциональная нижняя граница ``created_at``. Leftover-usable
    путь (``load_campaign_ledgers``) cutoff не передаёт: живой leftover старше
    ingest-окна должен оставаться в ledger. Если cutoff задан, его нужно
    применять и к spend, иначе remaining завышается.
    """
    ids = list({int(adv_id) for adv_id in advert_ids})
    if not ids:
        return []
    conditions: list[ColumnElement[bool]] = [
        WBAutoBudgetTopUp.adv_id.in_(ids),
        WBAutoBudgetTopUp.status == "success",
        WBAutoBudgetTopUp.promo_amount.is_not(None),
        WBAutoBudgetTopUp.promo_amount > 0,
    ]
    if cutoff is not None:
        conditions.append(WBAutoBudgetTopUp.created_at >= cutoff)
    stmt = select(WBAutoBudgetTopUp).where(*conditions)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    tranches: list[PromoAllocationTranche] = []
    for row in rows:
        promo_amount = int(row.promo_amount or 0)
        if promo_amount <= 0:
            continue
        created = row.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=datetime.timezone.utc)
        tranches.append(
            PromoAllocationTranche(
                topup_id=int(row.id),
                advert_id=int(row.adv_id),
                promo_amount=promo_amount,
                amount=int(row.amount),
                expires_at=row.promo_expires_at,
                created_at=created,
                budget_after=row.budget_after,
            )
        )
    return tranches


async def load_oldest_live_allocation_at(
    session: AsyncSession,
    advert_ids: Iterable[int],
    *,
    now: datetime.datetime,
) -> datetime.datetime | None:
    """Найти самую раннюю ещё живую promo allocation.

    Она задаёт нижнюю границу исторического UPD-backfill: если spend может
    уменьшить этот транш, его нельзя считать покрытым только 90-дневным
    recovery-окном. Истёкшие транши не требуют backfill для текущего overlay.

    Args:
        session: PG-сессия для журнала успешных пополнений.
        advert_ids: auto/search ``advert_id`` кампаний магазина.
        now: момент проверки expiry.

    Returns:
        UTC ``created_at`` самого раннего non-expired success-транша или
        ``None``, если живых траншей нет.
    """
    tranches = await load_success_tranches(session, advert_ids)
    live_created_at = [
        tranche.created_at
        for tranche in tranches
        if not is_expired(tranche.expires_at, now=now)
    ]
    return min(live_created_at) if live_created_at else None


async def load_spend_rows(
    session: AsyncSession,
    advert_ids: Iterable[int],
    *,
    cutoff: datetime.datetime | None = None,
) -> list[PromoSpendRow]:
    """Persisted UPD cashback rows.

    ``cutoff`` — опциональная нижняя граница ``upd_time``. Leftover-usable
    путь cutoff не передаёт (окно с приходом выровнено). Строки без
    ``upd_time`` сохраняем: расход всегда уменьшает remaining (безопасная
    сторона), терять его нельзя.
    """
    ids = list({int(adv_id) for adv_id in advert_ids})
    if not ids:
        return []
    conditions: list[ColumnElement[bool]] = [WBCampaignPromoSpend.advert_id.in_(ids)]
    if cutoff is not None:
        conditions.append(
            (WBCampaignPromoSpend.upd_time.is_(None))
            | (WBCampaignPromoSpend.upd_time >= cutoff)
        )
    stmt = select(WBCampaignPromoSpend).where(*conditions)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        PromoSpendRow(
            fingerprint=row.fingerprint,
            advert_id=int(row.advert_id),
            upd_sum=int(row.upd_sum),
            upd_time=row.upd_time,
        )
        for row in rows
    ]


async def load_campaign_ledgers(
    session: AsyncSession,
    advert_ids: Iterable[int],
    *,
    now: datetime.datetime,
    campaign_budget_by_adv_id: dict[int, int | None] | None = None,
) -> dict[int, CampaignPromoLedger]:
    """Ledger по каждому advert_id.

    Leftover-usable: non-expired success-tranche с remaining>0 не режется
    окном ``PROMO_LOOKBACK_DAYS``. Приход и расход читаются из PG без cutoff,
    чтобы окна оставались выровнены (не завышать remaining allocation без
    spend). ``now`` нужен FEFO/expiry в ``campaign_ledger_from_rows``.
    UPD ingest lookback не меняется.
    """
    ids = list({int(adv_id) for adv_id in advert_ids})
    tranches = await load_success_tranches(session, ids)
    spends = await load_spend_rows(session, ids)
    by_adv_tranches: dict[int, list[PromoAllocationTranche]] = defaultdict(list)
    by_adv_spend: dict[int, list[PromoSpendRow]] = defaultdict(list)
    for tranche in tranches:
        by_adv_tranches[tranche.advert_id].append(tranche)
    for spend in spends:
        by_adv_spend[spend.advert_id].append(spend)
    budgets = campaign_budget_by_adv_id or {}
    ledgers: dict[int, CampaignPromoLedger] = {}
    for adv_id in ids:
        ledgers[adv_id] = campaign_ledger_from_rows(
            adv_id,
            by_adv_tranches.get(adv_id, []),
            by_adv_spend.get(adv_id, []),
            now=now,
            campaign_budget_total=budgets.get(adv_id),
        )
    return ledgers


def _item_field(item: object, attr: str, *keys: str) -> object | None:
    """Прочитать поле UPD из attrs-модели или dict."""
    if isinstance(item, dict):
        mapping = cast(dict[str, object], item)
        for key in keys:
            if key in mapping:
                return mapping[key]
        return None
    return _unset_to_none(getattr(item, attr, None))


def iter_promo_upd_items(items: Iterable[object]) -> list[dict[str, object]]:
    """Отфильтровать UPD items с promo paymentType.

    Если WB не прислал ``updNum``, одинаковые строки всё ещё могут быть
    разными списаниями. Поэтому для повторяющихся одинаковых payload-ов
    добавляется стабильный индекс внутри batch; первый элемент сохраняет
    legacy fingerprint для совместимости с уже записанным PG.
    """
    parsed: list[dict[str, object]] = []
    for item in items:
        payment_type = _item_field(item, "payment_type", "paymentType", "payment_type")
        if not is_promo_payment_type(payment_type):
            continue
        advert_id = _item_field(item, "advert_id", "advertId", "advert_id")
        if advert_id is None:
            continue
        upd_sum = _item_field(item, "upd_sum", "updSum", "upd_sum")
        if upd_sum is None:
            continue
        upd_num = _item_field(item, "upd_num", "updNum", "upd_num")
        upd_time = _item_field(item, "upd_time", "updTime", "upd_time")
        parsed.append(
            {
                "advert_id": int(str(advert_id)),
                "upd_num": int(str(upd_num)) if upd_num is not None else None,
                "upd_time": str(upd_time) if upd_time is not None else None,
                "upd_sum": int(str(upd_sum)),
                "payment_type": str(payment_type),
            }
        )
    duplicate_indexes: dict[str, int] = defaultdict(int)
    for row in parsed:
        if row["upd_num"] is not None:
            continue
        identity = "|".join(
            (
                str(row["advert_id"]),
                str(row["upd_time"] or ""),
                str(row["upd_sum"]),
                str(row["payment_type"]),
            )
        )
        row["_missing_upd_index"] = duplicate_indexes[identity]
        duplicate_indexes[identity] += 1
    return parsed


async def ingest_promo_upd_items(
    session: AsyncSession,
    items: Iterable[object],
) -> int:
    """Idempotent insert promo UPD rows. Returns number of attempted rows."""
    rows = iter_promo_upd_items(items)
    if not rows:
        return 0
    payloads: list[dict[str, object]] = []
    for row in rows:
        advert_id = int(str(row["advert_id"]))
        upd_sum = int(str(row["upd_sum"]))
        payment_type = str(row["payment_type"])
        upd_num_raw = row["upd_num"]
        upd_num = int(str(upd_num_raw)) if upd_num_raw is not None else None
        upd_time_raw = row["upd_time"]
        upd_time = str(upd_time_raw) if upd_time_raw is not None else None
        duplicate_index_raw = row.get("_missing_upd_index")
        duplicate_index = (
            int(str(duplicate_index_raw))
            if duplicate_index_raw is not None
            else None
        )
        fingerprint = spend_fingerprint(
            advert_id=advert_id,
            upd_num=upd_num,
            upd_time=upd_time,
            upd_sum=upd_sum,
            payment_type=payment_type,
            duplicate_index=duplicate_index,
        )
        payloads.append(
            {
                "advert_id": advert_id,
                "upd_num": upd_num,
                "upd_time": parse_upd_time(upd_time),
                "upd_sum": upd_sum,
                "payment_type": payment_type,
                "fingerprint": fingerprint,
            }
        )
    stmt = pg_insert(WBCampaignPromoSpend).values(payloads)
    stmt = stmt.on_conflict_do_nothing(index_elements=["fingerprint"])
    await session.execute(stmt)
    await session.commit()
    return len(payloads)

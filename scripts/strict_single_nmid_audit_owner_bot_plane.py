"""Owner-bot Job access plane для strict single-NMID read-only audit.

Адаптер реализует ``OwnerBotReadOnlyPlane`` поверх существующего access plane
(``get_access_for_wb_cabinet``, ``WBManagerHubFactory``, generated Reports и
Promotion adapters). Новый raw HTTP-клиент не создаётся; mutation write
поверхности блокируются ``mutation_guard``.
"""

from __future__ import annotations

import asyncio
import re
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, cast

from scripts.strict_single_nmid_audit import (
    CONFIRMED,
    GAP,
    AuditIdentity,
    AuditPeriod,
    Evidence,
    SpendEvidence,
    StrictAuditError,
    evidence,
)
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op


def _read_int(row: dict[str, Any], *names: str) -> int:
    """Вернуть первое положительное целое из WB/PG aliases."""
    for name in names:
        value = row.get(name)
        if value in (None, ""):
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    return 0


def _read_number(row: dict[str, Any], *names: str) -> float | None:
    """Вернуть первое числовое поле или ``None``."""
    for name in names:
        value = row.get(name)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _parse_nmids(raw: Any) -> set[int]:
    """Разобрать nmids из PG ``advsetting.nmids`` без расширения scope."""
    return {int(match) for match in re.findall(r"\d+", str(raw or ""))}


def _parse_day(value: Any) -> date | None:
    """Нормализовать ISO date/datetime к календарному дню."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)
    try:
        if "T" in text or " " in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return date.fromisoformat(text[:10])
    except (TypeError, ValueError):
        return None


def _row_day(row: dict[str, Any]) -> date | None:
    """Извлечь календарный день supplier row."""
    for key in ("date", "lastChangeDate", "orderDate"):
        parsed = _parse_day(row.get(key))
        if parsed is not None:
            return parsed
    return None


def _is_cancel(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel", "")).lower() in {"true", "1", "t"}


def _orders_attestation(period: AuditPeriod, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Честная period attestation по фактическим датам supplier orders."""
    days = sorted({day.isoformat() for day in (_row_day(row) for row in rows) if day})
    covered_start = days[0] if days else None
    covered_end = days[-1] if days else None
    return {
        "family": "ORDERS_OR_SALES_REPORTS_READ",
        "endpoint": "GET /api/v1/supplier/orders",
        "period_attestation": {
            **period.as_dict(),
            "covered_start": covered_start,
            "covered_end": covered_end,
            "row_count": len(rows),
            "exact_window_confirmed": (
                covered_start == period.start.isoformat()
                and covered_end == period.end.isoformat()
            ),
        },
    }


async def _load_pg_rows(shop_id: str, cabinet: int) -> list[dict[str, Any]]:
    """Загрузить advsetting через explicit PURE_READ PostgreSQL session."""
    assert_read_only_op("strict_single_nmid_audit_pg_select")
    from sqlalchemy import text
    from app.utils.db.session_maker import get_async_session_maker

    async with get_async_session_maker(read_only=True) as session:
        identity = (
            await session.execute(
                text("SELECT id, shop_id FROM public.wbcabinet WHERE id = :cabinet"),
                {"cabinet": cabinet},
            )
        ).mappings().all()
        if not identity:
            raise StrictAuditError(f"PG identity missing for cabinet={cabinet}")
        actual_shop = str(identity[0]["shop_id"])
        if actual_shop != shop_id:
            raise StrictAuditError(
                f"PG shop_id mismatch: expected={shop_id} got={actual_shop}"
            )
        rows = (
            await session.execute(
                text(
                    """
                    SELECT a.id, a.adv_id, a._search_adv_id, a.name, a.nmids,
                           a.type, a.active_status, a.bot_active,
                           a.automatic_version, a.strategy,
                           a.target_price_for_order, a.max_price_for_order,
                           a.auto_budget_daily_limit,
                           a.search_auto_budget_daily_limit,
                           a.use_common_budget, a.common_budget_daily_limit
                    FROM public.advsetting a
                    WHERE a.wb_cabinet_id = :cabinet
                    """
                ),
                {"cabinet": cabinet},
            )
        ).mappings().all()
    return [dict(row) for row in rows]


async def _load_wb_bundle(
    shop_id: str,
    period: AuditPeriod,
    extra_campaign_ids: Iterable[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Собрать campaigns, fullstats и supplier orders через existing WB stack."""
    assert_read_only_op("get_supplier_orders")
    assert_read_only_op("get_supplier_sales")
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.chunked import (
        run_chunked_single_range,
    )
    from app.modules.common_slaves.wildberries.super_cabinet_manager import (
        get_access_for_wb_cabinet,
    )
    from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
    from scripts.wb_api_readonly_ops.collect.orders_sales import collect_orders_sales
    from scripts.wb_api_readonly_ops.collect.raw_store import RawStore

    _ = await get_access_for_wb_cabinet(shop_id)
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()  # type: ignore[attr-defined]
        )
        hub = factory.get_wb_manager_hub(shop_id)
        promotion = hub.wb_data_manager.promotion_manager
        campaign_ids_raw = await promotion._client.promotion_count_adapter.get_cabinet_adv_ids()
        campaign_ids = sorted(
            {
                int(value)
                for value in campaign_ids_raw or []
                if str(value).isdigit()
            }
            | {int(value) for value in extra_campaign_ids if int(value) > 0}
        )
        campaigns: list[dict[str, Any]] = []
        for offset in range(0, len(campaign_ids), 100):
            payload = await promotion.get_adverts_v2_by_ids(
                campaign_ids[offset : offset + 100]
            )
            if isinstance(payload, list):
                campaigns.extend(cast(list[dict[str, Any]], payload))
        fullstats: list[dict[str, Any]] = []
        if campaign_ids:
            adapter = promotion._client.fullstats_adapter

            async def fetcher(
                ids: list[int], begin: date, end: date
            ) -> list[dict[str, Any]]:
                assert_read_only_op("get_fullstats")
                raw = await adapter.get_fullstats(ids, begin, end)
                return cast(list[dict[str, Any]], raw or [])

            fullstats = [
                dict(item)
                for item in await run_chunked_single_range(
                    campaign_ids,
                    period.start,
                    period.end,
                    fetcher=fetcher,
                )
            ]
        budget = ApiCallBudget(max_seconds=900.0, max_api_calls=50)
        with tempfile.TemporaryDirectory(prefix="strict-nmid-audit-") as tmp:
            store = RawStore(Path(tmp))
            order_rows, _sales_rows = await collect_orders_sales(
                hub.wb_data_manager,
                store=store,
                budget=budget,
                orders_date_from=period.start.isoformat(),
            )
        orders = [dict(row) for row in order_rows]
        return campaigns, fullstats, orders


@dataclass
class _Bundle:
    """Кэш read-only фактов на один audit identity/period."""

    pg_rows: list[dict[str, Any]]
    campaigns: list[dict[str, Any]]
    fullstats: list[dict[str, Any]]
    orders: list[dict[str, Any]]
    memberships: dict[int, set[int]] = field(default_factory=dict)


class OwnerBotStrictSingleNmidReadOnlyPlane:
    """Job-runtime plane: existing Owner-bot readers без duplicate HTTP."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, int, str, str], _Bundle] = {}

    def _bundle(self, identity: AuditIdentity, period: AuditPeriod) -> _Bundle:
        key = (
            identity.shop_id,
            identity.cabinet,
            period.start.isoformat(),
            period.end.isoformat(),
        )
        if key in self._cache:
            return self._cache[key]

        async def _load_all() -> _Bundle:
            pg_rows = await _load_pg_rows(identity.shop_id, identity.cabinet)
            pg_campaign_ids = [
                campaign_id
                for row in pg_rows
                for campaign_id in (
                    _read_int(row, "adv_id"),
                    _read_int(row, "_search_adv_id"),
                )
                if campaign_id
            ]
            campaigns, fullstats, orders = await _load_wb_bundle(
                identity.shop_id, period, pg_campaign_ids
            )
            memberships: dict[int, set[int]] = defaultdict(set)
            for row in pg_rows:
                for field in ("adv_id", "_search_adv_id"):
                    campaign_id = _read_int(row, field)
                    if campaign_id:
                        memberships[campaign_id].update(_parse_nmids(row.get("nmids")))
            for campaign in campaigns:
                campaign_id = _read_int(campaign, "advertId", "advert_id", "id")
                if campaign_id and campaign_id not in memberships:
                    auto = campaign.get("autoParams") or {}
                    nms = auto.get("nms") if isinstance(auto, dict) else None
                    if isinstance(nms, list):
                        memberships[campaign_id].update(
                            {
                                parsed
                                for item in nms
                                if isinstance(item, dict)
                                for parsed in (_read_int(item, "nm", "nmId", "nmID"),)
                                if parsed
                            }
                        )
            return _Bundle(
                pg_rows=pg_rows,
                campaigns=campaigns,
                fullstats=fullstats,
                orders=orders,
                memberships=dict(memberships),
            )

        bundle = asyncio.run(_load_all())
        self._cache[key] = bundle
        return bundle

    def read_current_contour(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Прочитать current contour из PG/WB без A1 fallback."""
        bundle = self._bundle(identity, period)
        rows = [
            row
            for row in bundle.pg_rows
            if identity.nmid in _parse_nmids(row.get("nmids"))
        ]
        if not rows:
            yield evidence(
                identity,
                "current_contour",
                "nmid_offer",
                None,
                source="owner-bot-pg-advsetting",
                provenance={"reason": "no advsetting row for exact nmid"},
                period=period,
                present=False,
            )
            return
        row = rows[0]
        mapping: list[tuple[str, Any]] = [
            ("nmid_offer", {"nmid": identity.nmid, "size_id": identity.size_id}),
            ("adv_setting", {"adv_id": _read_int(row, "adv_id") or None}),
            (
                "auto",
                {"adv_id": _read_int(row, "adv_id") or None, "type": row.get("type")},
            ),
            (
                "search",
                {"search_adv_id": _read_int(row, "_search_adv_id") or None},
            ),
            (
                "other_ids",
                {
                    "adv_id": _read_int(row, "adv_id") or None,
                    "search_adv_id": _read_int(row, "_search_adv_id") or None,
                },
            ),
            ("wb_statuses", {"active_status": row.get("active_status")}),
            ("bot_settings", {"bot_active": row.get("bot_active")}),
            (
                "cpo",
                {
                    "target_price_for_order": row.get("target_price_for_order"),
                    "max_price_for_order": row.get("max_price_for_order"),
                },
            ),
            (
                "limits",
                {
                    "auto_budget_daily_limit": row.get("auto_budget_daily_limit"),
                    "search_auto_budget_daily_limit": row.get(
                        "search_auto_budget_daily_limit"
                    ),
                    "common_budget_daily_limit": row.get("common_budget_daily_limit"),
                },
            ),
        ]
        for field_name, value in mapping:
            yield evidence(
                identity,
                "current_contour",
                field_name,
                value,
                source="owner-bot-pg-advsetting",
                provenance={"source": "public.advsetting", "read_only": True},
                period=period,
            )

    def read_orders(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Orders/units/GMV через ORDERS_OR_SALES_REPORTS_READ identity."""
        bundle = self._bundle(identity, period)
        scoped = [
            row
            for row in bundle.orders
            if _read_int(row, "nmId", "nmID", "nm_id") == identity.nmid
            and (day := _row_day(row)) is not None
            and period.start <= day <= period.end
            and not _is_cancel(row)
        ]
        attestation = _orders_attestation(period, scoped)
        orders_count = len(scoped)
        units = sum(_read_int(row, "quantity", "qty") or 1 for row in scoped)
        gmv = sum(_read_number(row, "finishedPrice", "priceWithDisc") or 0.0 for row in scoped)
        for field_name, value in (
            ("orders", orders_count),
            ("units", units),
            ("gmv", round(gmv, 2)),
        ):
            yield evidence(
                identity,
                "orders",
                field_name,
                value,
                source="statistics-reports",
                provenance=attestation,
                period=period,
            )

    def read_attribution(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Direct/associated counts только при explicit fullstats membership."""
        bundle = self._bundle(identity, period)
        direct = associated = 0
        for item in bundle.fullstats:
            adv_id = _read_int(item, "advertId", "advert_id", "id")
            if not adv_id:
                continue
            membership = bundle.memberships.get(adv_id, set())
            if not membership:
                continue
            days = item.get("days")
            if not isinstance(days, list):
                continue
            for day in days:
                if not isinstance(day, dict):
                    continue
                parsed = _parse_day(day.get("date"))
                if parsed is None or not period.start <= parsed <= period.end:
                    continue
                apps = day.get("apps")
                if not isinstance(apps, list):
                    continue
                for app in apps:
                    nms = app.get("nms") if isinstance(app, dict) else None
                    if not isinstance(nms, list):
                        continue
                    for nm in nms:
                        if not isinstance(nm, dict):
                            continue
                        ordered = _read_int(nm, "nmId", "nmID", "nm_id", "id")
                        if ordered != identity.nmid:
                            continue
                        orders = _read_int(nm, "orders")
                        if ordered in membership:
                            direct += orders
                        else:
                            associated += orders
        if direct == 0 and associated == 0:
            yield evidence(
                identity,
                "attribution",
                "direct",
                None,
                source="owner-bot-promotion-fullstats",
                provenance={"reason": "no authoritative attribution rows"},
                period=period,
                complete=False,
                attribution_class="direct",
            )
            yield evidence(
                identity,
                "attribution",
                "associated",
                None,
                source="owner-bot-promotion-fullstats",
                provenance={"reason": "no authoritative attribution rows"},
                period=period,
                complete=False,
                attribution_class="associated",
            )
            return
        yield evidence(
            identity,
            "attribution",
            "direct",
            direct,
            source="owner-bot-promotion-fullstats",
            provenance={"membership": "explicit"},
            period=period,
            attribution_class="direct",
        )
        yield evidence(
            identity,
            "attribution",
            "associated",
            associated,
            source="owner-bot-promotion-fullstats",
            provenance={"membership": "explicit"},
            period=period,
            attribution_class="associated",
        )

    def read_topology(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Topology только при explicit campaign membership для nmid."""
        bundle = self._bundle(identity, period)
        memberships = {
            adv_id: sorted(nmids)
            for adv_id, nmids in bundle.memberships.items()
            if identity.nmid in nmids
        }
        if not memberships:
            yield evidence(
                identity,
                "topology",
                "topology",
                None,
                source="owner-bot-membership",
                provenance={"reason": "authoritative topology not evidenced"},
                period=period,
                complete=False,
            )
            return
        yield evidence(
            identity,
            "topology",
            "topology",
            memberships,
            source="owner-bot-membership",
            provenance={"membership_map": memberships},
            period=period,
        )

    def read_stock(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Stock views без unsupported inference — explicit unsupported."""
        del identity, period
        return []

    def read_physical_spend(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[SpendEvidence]:
        """Physical spend из promotion fullstats campaign-day rows."""
        bundle = self._bundle(identity, period)
        total = Decimal("0")
        overlap_keys: set[str] = set()
        for item in bundle.fullstats:
            adv_id = _read_int(item, "advertId", "advert_id", "id")
            if not adv_id or identity.nmid not in bundle.memberships.get(adv_id, set()):
                continue
            days = item.get("days")
            if not isinstance(days, list):
                continue
            for day in days:
                if not isinstance(day, dict):
                    continue
                parsed = _parse_day(day.get("date"))
                if parsed is None or not period.start <= parsed <= period.end:
                    continue
                spend = _read_number(day, "sum", "spend") or 0.0
                if spend <= 0:
                    continue
                overlap_key = f"physical:{adv_id}:{parsed.isoformat()}"
                if overlap_key in overlap_keys:
                    continue
                overlap_keys.add(overlap_key)
                total += Decimal(str(spend))
        if total <= 0:
            yield SpendEvidence(
                amount=None,
                source="owner-bot-promotion-fullstats",
                overlap_key=None,
                identity=identity,
                period=period,
                provenance={"reason": "no physical spend in window"},
                status=GAP,
            )
            return
        yield SpendEvidence(
            amount=total,
            source="owner-bot-promotion-fullstats",
            overlap_key="physical:canonical",
            identity=identity,
            period=period,
            provenance={"overlap_keys": sorted(overlap_keys)},
            status=CONFIRMED,
        )


def build_owner_bot_read_only_plane() -> OwnerBotStrictSingleNmidReadOnlyPlane:
    """Создать Job-runtime plane без side effects."""
    return OwnerBotStrictSingleNmidReadOnlyPlane()

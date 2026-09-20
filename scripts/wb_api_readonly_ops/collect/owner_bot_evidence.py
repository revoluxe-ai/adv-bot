"""Shared Owner-bot Job-scoped read-only evidence loading.

Единый async lifecycle и WB/PG primitives для collectors (strict single-NMID,
A1-aligned paths). Не создаёт parallel HTTP; mutation guard обязателен.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, cast

from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op


@dataclass(frozen=True)
class EvidenceReaderFailure(Exception):
    """Typed failure для collector GAP provenance (не infrastructure BLOCKED)."""

    section: str
    source: str
    phase: str
    error_class: str
    message: str

    def __str__(self) -> str:
        return (
            f"{self.error_class} source={self.source} phase={self.phase}: "
            f"{self.message}"
        )


@dataclass
class OwnerBotEvidenceBundle:
    """Кэш read-only фактов на один audit identity/period."""

    pg_rows: list[dict[str, Any]]
    campaigns: list[dict[str, Any]]
    fullstats: list[dict[str, Any]]
    orders: list[dict[str, Any]]
    memberships: dict[int, set[int]] = field(default_factory=dict)


class JobScopedEvidenceRuntime:
    """Один asyncio loop на Job execution + deterministic cleanup."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def run(self, coro: Any) -> Any:
        """Выполнить coroutine на Job-owned loop без ``asyncio.run()``."""
        asyncio.set_event_loop(self._loop)
        return self._loop.run_until_complete(coro)

    def close(self) -> None:
        """Закрыть loop и dispose module-level async SQLAlchemy engines."""
        if self._loop.is_closed():
            return
        try:
            from app.utils.db.session_maker import read_only_engine, read_write_engine

            async def _dispose() -> None:
                await read_only_engine.dispose()
                await read_write_engine.dispose()

            self.run(_dispose())
        except Exception:
            pass
        finally:
            self._loop.close()


async def load_pg_advsetting_rows(shop_id: str, cabinet: int) -> list[dict[str, Any]]:
    """Загрузить wbcabinet identity + advsetting через read-only SQLAlchemy session.

    Session выполняется на текущем event loop Job runtime (не nested asyncio.run).
    """
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
            raise EvidenceReaderFailure(
                section="current_contour",
                source="owner-bot-pg-wbcabinet",
                phase="pg_identity",
                error_class="StrictAuditError",
                message=f"PG identity missing for cabinet={cabinet}",
            )
        actual_shop = str(identity[0]["shop_id"])
        if actual_shop != shop_id:
            raise EvidenceReaderFailure(
                section="identity",
                source="owner-bot-pg-wbcabinet",
                phase="pg_identity",
                error_class="StrictAuditError",
                message=f"PG shop_id mismatch: expected={shop_id} got={actual_shop}",
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


def _parse_nmids(raw: Any) -> set[int]:
    import re

    return {int(match) for match in re.findall(r"\d+", str(raw or ""))}


def _read_int(row: dict[str, Any], *names: str) -> int:
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


def _build_memberships(
    pg_rows: list[dict[str, Any]],
    campaigns: list[dict[str, Any]],
) -> dict[int, set[int]]:
    memberships: dict[int, set[int]] = defaultdict(set)
    for row in pg_rows:
        for adv_field in ("adv_id", "_search_adv_id"):
            campaign_id = _read_int(row, adv_field)
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
    return dict(memberships)


async def load_wb_evidence_bundle(
    shop_id: str,
    period_start: date,
    period_end: date,
    extra_campaign_ids: Iterable[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Campaigns, fullstats (supported adapter API), orders через shared collect."""
    import tempfile

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
                for item in payload:
                    normalized = jsonable(item)
                    if isinstance(normalized, dict):
                        campaigns.append(cast(dict[str, Any], normalized))
        fullstats: list[dict[str, Any]] = []
        if campaign_ids:
            adapter = promotion._client.fullstats_adapter

            async def fetcher(
                chunk: list[int], begin: date, end: date
            ) -> list[Any]:
                assert_read_only_op("fullstats_request_chunk")
                return await adapter._request_chunk(chunk, begin, end)

            raw_items = await run_chunked_single_range(
                campaign_ids,
                period_start,
                period_end,
                fetcher=fetcher,
            )
            for item in raw_items:
                if hasattr(item, "to_dict"):
                    normalized = jsonable(item.to_dict())
                else:
                    normalized = jsonable(item)
                if isinstance(normalized, dict):
                    fullstats.append(cast(dict[str, Any], normalized))
        budget = ApiCallBudget(max_seconds=900.0, max_api_calls=50)
        with tempfile.TemporaryDirectory(prefix="owner-bot-evidence-") as tmp:
            store = RawStore(Path(tmp))
            order_rows, _sales_rows = await collect_orders_sales(
                hub.wb_data_manager,
                store=store,
                budget=budget,
                orders_date_from=period_start.isoformat(),
            )
        orders = [
            cast(dict[str, Any], normalized)
            for row in order_rows
            for normalized in (jsonable(row),)
            if isinstance(normalized, dict)
        ]
        return campaigns, fullstats, orders


async def load_owner_bot_evidence_bundle(
    shop_id: str,
    cabinet: int,
    period_start: date,
    period_end: date,
) -> OwnerBotEvidenceBundle:
    """PG + WB shared load для одного identity/window."""
    try:
        pg_rows = await load_pg_advsetting_rows(shop_id, cabinet)
    except EvidenceReaderFailure:
        raise
    except Exception as exc:
        raise EvidenceReaderFailure(
            section="current_contour",
            source="owner-bot-pg-advsetting",
            phase="pg_load",
            error_class=type(exc).__name__,
            message=str(exc),
        ) from exc
    pg_campaign_ids = [
        campaign_id
        for row in pg_rows
        for campaign_id in (
            _read_int(row, "adv_id"),
            _read_int(row, "_search_adv_id"),
        )
        if campaign_id
    ]
    try:
        campaigns, fullstats, orders = await load_wb_evidence_bundle(
            shop_id,
            period_start,
            period_end,
            pg_campaign_ids,
        )
    except Exception as exc:
        raise EvidenceReaderFailure(
            section="orders",
            source="owner-bot-wb-evidence",
            phase="wb_load",
            error_class=type(exc).__name__,
            message=str(exc),
        ) from exc
    memberships = _build_memberships(pg_rows, campaigns)
    return OwnerBotEvidenceBundle(
        pg_rows=pg_rows,
        campaigns=campaigns,
        fullstats=fullstats,
        orders=orders,
        memberships=memberships,
    )

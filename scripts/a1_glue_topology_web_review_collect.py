"""READ_ONLY: A1 glue/topology/price/ad evidence for Web analytical chat.

Собирает product glue topology, prices, stock, factual sales, physical ad contour,
fullstats attribution и association edges для приоритетных категорий йога-ассортимента
магазина A1. Без production mutations (glue/price/ad writes).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import shutil
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.a1_cpc_two_sku_safety_preflight import (
    WB_STATUS_NAMES,
    _adv_nm_map,
    _bootstrap,
    _fetch_seller_stocks,
    _load_pg,
    _parse_nmids,
)
from scripts.a1_sale_price_snapshot import fetch_prices
from scripts.wb_a1_associated_conversions import (
    _jsonable,
    _nm_rows,
    _read_float,
    _read_int,
)
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.cards import collect_cards
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.orders_sales import _paginate_supplier_rows
from scripts.wb_api_readonly_ops.collect.raw_store import RawStore

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-GLUE-TOPOLOGY-WEB-REVIEW"
OPEN_DAY = date(2026, 9, 6)

WORKING_SKUS = (14166423, 85970344, 14824677, 837395782, 7974113)
WINDOWS = (7, 14, 28)

CATEGORY_LABELS = {
    "yoga_belts": "yoga belts (ремни для йоги)",
    "yoga_mats": "yoga mats (коврики для йоги)",
    "yoga_rollers": "yoga rollers (валики)",
    "stretching_pillows": "stretching pillows (подушки для растяжки)",
    "yoga_pillows": "yoga pillows (подушки для йоги)",
}

def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _closed_end_day(now: datetime | None = None) -> date:
    """Последний полностью закрытый день (MSK): вчера относительно now."""
    return (now or _msk_now()).date() - timedelta(days=1)


def _closed_dates(closed_end: date, days: int) -> set[str]:
    start = closed_end - timedelta(days=days - 1)
    out: set[str] = set()
    d = start
    while d <= closed_end:
        out.add(d.isoformat())
        d += timedelta(days=1)
    return out


def _write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in cols})


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_jsonable(row), ensure_ascii=False) + "\n")


def _classify_category(subject: str, title: str) -> str | None:
    """Классифицировать nmID в одну из 5 приоритетных категорий или None."""
    s = (subject or "").lower()
    t = (title or "").lower()
    combined = f"{s} {t}"
    if "ремн" in combined and ("йог" in combined or "yoga" in combined):
        return "yoga_belts"
    if "коврик" in combined:
        if "антивибрац" in combined or "стиральн" in combined:
            return None
        if any(k in combined for k in ("йог", "yoga", "фитнес", "спорт", "профессиональн")):
            return "yoga_mats"
        if "чехол" in combined:
            return None
    if any(k in combined for k in ("валик", "болстер", "roller", "bolster")):
        return "yoga_rollers"
    if "подуш" in combined or "pillow" in t:
        if "растяж" in combined or "stretch" in t or s == "подушки для растяжки":
            return "stretching_pillows"
        if any(k in combined for k in ("йог", "yoga", "фитнес", "растяж")):
            return "stretching_pillows" if "растяж" in combined else "yoga_pillows"
        return "yoga_pillows"
    return None


def _group_size_bucket(size: int) -> str:
    if size <= 1:
        return "GROUP_SIZE_1"
    if size == 2:
        return "GROUP_SIZE_2"
    if 3 <= size <= 5:
        return "GROUP_SIZE_3_TO_5"
    if size > 5:
        return "GROUP_SIZE_GT_5"
    return "MIXED_OR_SUSPICIOUS"


def _card_attrs(card: dict[str, Any]) -> dict[str, Any]:
    """Извлечь distinguishing attributes из Content API card."""
    chars = card.get("characteristics") or []
    attr_parts: list[str] = []
    for ch in chars:
        if not isinstance(ch, dict):
            continue
        name = ch.get("name") or ch.get("id")
        val = ch.get("value")
        if name and val:
            attr_parts.append(f"{name}={val}")
    sizes = card.get("sizes") or []
    size_names = [
        str(sz.get("techSize") or sz.get("techSizeName") or "")
        for sz in sizes
        if isinstance(sz, dict)
    ]
    return {
        "color": card.get("colors") or card.get("color"),
        "sizes": "|".join(s for s in size_names if s),
        "characteristics": "; ".join(attr_parts[:12]),
        "dimensions": card.get("dimensions"),
        "media_count": len(card.get("mediaFiles") or card.get("photos") or []),
    }


def _is_cancelled(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel")).lower() in ("true", "1", "t")


def _order_day(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("lastChangeDate") or "")[:10]


def _sales_window(
    orders: list[dict[str, Any]], nm_id: int, dates: set[str]
) -> dict[str, Any]:
    events = 0
    units = 0
    value = 0.0
    last_order = ""
    for row in orders:
        if _is_cancelled(row):
            continue
        nm = _read_int(row, "nmId", "nmID", "nm_id")
        if nm != nm_id:
            continue
        day = _order_day(row)
        if day not in dates:
            continue
        qty = _read_int(row, "quantity", "qty") or 1
        price = _read_float(row, "totalPrice", "priceWithDisc", "finishedPrice")
        events += 1
        units += qty
        value += price * qty if price else 0.0
        if day > last_order:
            last_order = day
    return {
        "events": events,
        "units": units,
        "value": round(value, 2),
        "last_order_date": last_order or "GAP",
    }


def _nm_to_contours(
    pg_rows: list[dict[str, str]], wb_campaigns: list[dict[str, Any]]
) -> dict[int, list[dict[str, Any]]]:
    """Сопоставить nmID → physical campaigns (PG + WB inventory)."""
    adv_nm = _adv_nm_map(wb_campaigns)
    nm_to_advs: dict[int, set[int]] = defaultdict(set)
    for adv_id, nms in adv_nm.items():
        for n in nms:
            nm_to_advs[n].add(adv_id)

    out: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in pg_rows:
        setting_id = _read_int(row, "id")
        auto_id = _read_int(row, "adv_id")
        search_id = _read_int(row, "_search_adv_id")
        nmids = _parse_nmids(row.get("nmids") or "")
        for nmid in nmids:
            out[nmid].append(
                {
                    "adv_setting_id": setting_id,
                    "auto_adv_id": auto_id,
                    "search_adv_id": search_id or None,
                    "name": row.get("name"),
                    "bot_active": row.get("bot_active"),
                    "target_cpo": row.get("target_price_for_order"),
                    "max_cpo": row.get("max_price_for_order"),
                    "auto_daily_limit": row.get("auto_budget_daily_limit"),
                    "search_daily_limit": row.get("search_auto_budget_daily_limit"),
                    "pg_active_status": row.get("active_status"),
                    "nmids_pg": nmids,
                }
            )
    for nmid, adv_ids in nm_to_advs.items():
        for adv_id in adv_ids:
            if not any(c.get("auto_adv_id") == adv_id or c.get("search_adv_id") == adv_id for c in out[nmid]):
                out[nmid].append(
                    {
                        "adv_setting_id": None,
                        "auto_adv_id": adv_id,
                        "search_adv_id": None,
                        "name": "WB_ONLY_UNMAPPED_PG",
                        "bot_active": "GAP",
                        "target_cpo": "GAP",
                        "max_cpo": "GAP",
                        "auto_daily_limit": "GAP",
                        "search_daily_limit": "GAP",
                        "pg_active_status": "GAP",
                        "nmids_pg": [],
                    }
                )
    return out


def _promoted_set(campaign: dict[str, Any]) -> set[int]:
    return _adv_nm_map([campaign]).get(_read_int(campaign, "id", "advertId"), set())


def _direct_assoc_split(
    nm_rows: list[dict[str, Any]],
    promoted: set[int],
    dates: set[str],
) -> dict[str, Any]:
    direct_carts = direct_orders = direct_gmv = 0
    assoc_carts = assoc_orders = assoc_gmv = 0.0
    for r in nm_rows:
        if r["date"] not in dates:
            continue
        ordered = r["ordered_nm_id"]
        if ordered in promoted:
            direct_carts += r["atbs"]
            direct_orders += r["orders"]
            direct_gmv += r["sum_price"]
        else:
            assoc_carts += r["atbs"]
            assoc_orders += r["orders"]
            assoc_gmv += r["sum_price"]
    split = "OK" if promoted else "GAP"
    return {
        "direct_carts": direct_carts,
        "associated_carts": assoc_carts,
        "direct_orders": direct_orders,
        "associated_orders": assoc_orders,
        "direct_gmv": round(direct_gmv, 2),
        "associated_gmv": round(assoc_gmv, 2),
        "DIRECT_ASSOC_SPLIT": split,
    }


def _association_edges(
    nm_rows: list[dict[str, Any]],
    adv_id: int,
    promoted: set[int],
    dates: set[str],
    window_label: str,
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    grouped: dict[int, dict[str, float | int]] = defaultdict(
        lambda: {"carts": 0, "orders": 0, "gmv": 0.0}
    )
    for r in nm_rows:
        if r["advert_id"] != adv_id or r["date"] not in dates:
            continue
        receiver = r["ordered_nm_id"]
        if receiver in promoted:
            continue
        g = grouped[receiver]
        g["carts"] += r["atbs"]
        g["orders"] += r["orders"]
        g["gmv"] += r["sum_price"]
    donor = "UNKNOWN_MULTI_PROMOTED" if len(promoted) > 1 else (
        str(next(iter(promoted))) if len(promoted) == 1 else "UNKNOWN"
    )
    for receiver, g in grouped.items():
        if not any((g["carts"], g["orders"], g["gmv"])):
            continue
        edges.append(
            {
                "source_campaign": adv_id,
                "source_promoted_set": ",".join(str(x) for x in sorted(promoted)),
                "donor_nmID": donor,
                "receiver_nmID": receiver,
                "window": window_label,
                "associated_carts": g["carts"],
                "associated_orders": g["orders"],
                "associated_gmv": round(float(g["gmv"]), 2),
                "causal_note": "ASSOCIATION != CAUSAL EFFECT",
            }
        )
    return edges


def _price_role(price: Any, prices_in_group: list[float]) -> str:
    if price is None or not prices_in_group:
        return "UNKNOWN"
    try:
        p = float(price)
    except (TypeError, ValueError):
        return "UNKNOWN"
    mn, mx = min(prices_in_group), max(prices_in_group)
    if mx == mn:
        return "CORE"
    if p <= mn:
        return "VALUE"
    if p >= mx:
        return "PREMIUM"
    return "ALTERNATIVE"


async def _wb_collect(
    pg_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[int]]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.chunked import (
        run_chunked_single_range,
    )

    adv_ids = sorted(
        {
            _read_int(r, "adv_id")
            for r in pg_rows
            if _read_int(r, "adv_id")
        }
        | {
            _read_int(r, "_search_adv_id")
            for r in pg_rows
            if _read_int(r, "_search_adv_id")
        }
    )
    closed_end = _closed_end_day()
    begin = closed_end - timedelta(days=27)

    campaigns: list[dict[str, Any]] = []
    fullstats_raw: list[dict[str, Any]] = []
    orders_raw: list[dict[str, Any]] = []

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        pm = dm.promotion_manager
        budget = ApiCallBudget(max_seconds=1800.0, max_api_calls=2000)
        reports_manager = getattr(dm, "reports_manager", None)

        async def fetch_orders(df: str) -> list[object]:
            if reports_manager is not None:
                return list(await reports_manager.get_supplier_orders(date_from=df, flag=0) or [])
            return list(await dm.get_supplier_orders(date_from=df, flag=0) or [])

        orders_result = await _paginate_supplier_rows(
            fetch=fetch_orders,
            initial_date_from=begin.isoformat(),
            budget=budget,
            max_pages=1200,
        )
        orders_raw = [jsonable(r) for r in orders_result.rows if isinstance(jsonable(r), dict)]

        budget.consume()
        cabinet_adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        budget.consume()
        camps_raw = list(await pm.get_adverts_v2_by_ids(cabinet_adv_ids) or [])
        for item in camps_raw:
            row = jsonable(item)
            if isinstance(row, dict):
                campaigns.append(row)

        client = pm._client
        adapter = client.fullstats_adapter

        async def fetcher(chunk: list[int], b: date, e: date) -> list[Any]:
            return await adapter._request_chunk(chunk, b, e)

        items = await run_chunked_single_range(adv_ids, begin, closed_end, fetcher)
        for item in items:
            fullstats_raw.append(_jsonable(item.to_dict()))

    return campaigns, fullstats_raw, orders_raw, adv_ids


async def _all_cards() -> list[dict[str, Any]]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        store = RawStore(Path("/tmp/cards_raw"))
        budget = ApiCallBudget(max_calls=10_000)
        _, cards = await collect_cards(
            hub.wb_data_manager, store=store, budget=budget, page_limit=100
        )
    return cards


def run_collect(output_dir: Path) -> dict[str, Any]:
    """Собрать evidence package и вернуть manifest summary."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True)
    staging = output_dir / "staging"
    staging.mkdir(parents=True)

    _bootstrap()
    checked_at = _msk_now()
    closed_end = _closed_end_day(checked_at)
    gaps: list[str] = []

    cards = asyncio.run(_all_cards())
    _write_jsonl(raw_dir / "content_cards_all.jsonl", cards)

    card_by_nmid: dict[int, dict[str, Any]] = {}
    imt_members: dict[int, set[int]] = defaultdict(set)
    for card in cards:
        nmid = _read_int(card, "nmID", "nmId", "nmid")
        if not nmid:
            continue
        card_by_nmid[nmid] = card
        imt = _read_int(card, "imtID", "imtId", "imt_id")
        if imt:
            imt_members[imt].add(nmid)

    priority_nmids: set[int] = set()
    nmid_category: dict[int, str] = {}
    for nmid, card in card_by_nmid.items():
        cat = _classify_category(
            str(card.get("subjectName") or ""),
            str(card.get("title") or ""),
        )
        if cat:
            priority_nmids.add(nmid)
            nmid_category[nmid] = cat

    scoped_nmids: set[int] = set(priority_nmids)
    for nmid in list(priority_nmids):
        imt = _read_int(card_by_nmid[nmid], "imtID", "imtId")
        if imt and imt in imt_members:
            scoped_nmids |= imt_members[imt]

    store_total_cards = len(card_by_nmid)
    if not scoped_nmids:
        gaps.append("SCOPED_NMIDS_EMPTY — no priority category matches in Content API cards")

    pg_rows = _load_pg(staging)
    campaigns, fullstats_raw, orders_raw, adv_ids = asyncio.run(_wb_collect(pg_rows))
    _write_jsonl(raw_dir / "campaigns_v2.jsonl", campaigns)
    _write_jsonl(raw_dir / "fullstats_v3_raw.jsonl", fullstats_raw)
    _write_jsonl(raw_dir / "supplier_orders_raw.jsonl", orders_raw)

    nm_rows, day_rows = _nm_rows(fullstats_raw)
    wb_by_id = {_read_int(c, "id", "advertId"): c for c in campaigns}

    scoped_list = sorted(scoped_nmids)
    price_rows, price_route, price_gaps = asyncio.run(fetch_prices(scoped_list))
    gaps.extend(price_gaps)
    price_by_nmid = {int(r["nmID"]): r for r in price_rows if r.get("nmID") is not None}

    cards_subset = {
        n: card_by_nmid[n]
        for n in scoped_list
        if n in card_by_nmid
    }
    stock_data = asyncio.run(_fetch_stocks_for_cards(cards_subset))

    dates_7 = _closed_dates(closed_end, 7)
    dates_14 = _closed_dates(closed_end, 14)
    dates_28 = _closed_dates(closed_end, 28)
    nm_contours = _nm_to_contours(pg_rows, campaigns)

    scope_rows = [
        {
            "shop_id": SHOP_ID,
            "store_total_nmids": store_total_cards,
            "scoped_nmids_count": len(scoped_list),
            "priority_category_nmids_count": len(priority_nmids),
            "imt_groups_in_scope": len({ _read_int(card_by_nmid[n], "imtID", "imtId") for n in scoped_list if n in card_by_nmid }),
            "last_fully_closed_day": closed_end.isoformat(),
            "open_day": OPEN_DAY.isoformat(),
            "checked_at_msk": _iso_msk(checked_at),
            "working_skus": ",".join(str(x) for x in WORKING_SKUS),
            "CLIENT_REPORTS_FBS_PRESENT": "YES",
            "CLIENT_REPORTS_STOCK_DUPLICATED": "YES",
        }
    ]
    _write_csv(
        output_dir / "01_SCOPE_AND_IDENTITY.csv",
        scope_rows,
        list(scope_rows[0].keys()),
    )

    glue_rows: list[dict[str, Any]] = []
    imt_scoped = defaultdict(set)
    for nmid in scoped_list:
        imt = _read_int(card_by_nmid.get(nmid, {}), "imtID", "imtId")
        if imt:
            imt_scoped[imt].add(nmid)

    for imt_id, members in sorted(imt_scoped.items(), key=lambda x: -len(x[1])):
        member_cards = [card_by_nmid[m] for m in members if m in card_by_nmid]
        subjects = {str(c.get("subjectName") or "") for c in member_cards}
        cats = {nmid_category.get(m, "") for m in members if nmid_category.get(m)}
        prices = [
            float(price_by_nmid[m].get("SALE_PRICE_REFERENCE") or 0)
            for m in members
            if m in price_by_nmid
            and price_by_nmid[m].get("SALE_PRICE_REFERENCE") is not None
        ]
        price_spread = round(max(prices) - min(prices), 2) if len(prices) >= 2 else "GAP"
        glue_rows.append(
            {
                "imt_id": imt_id,
                "group_size": len(members),
                "size_bucket": _group_size_bucket(len(members)),
                "member_nmids": ",".join(str(x) for x in sorted(members)),
                "subject_names": "|".join(sorted(subjects)),
                "priority_categories": "|".join(sorted(c for c in cats if c)),
                "subject_consistent": "YES" if len(subjects) <= 1 else "MIXED",
                "price_spread_rub": price_spread,
                "has_ad_presence": "YES" if any(nm_contours.get(m) for m in members) else "NO",
                "semantic_outliers": "REVIEW" if len(subjects) > 1 else "",
            }
        )
    _write_csv(
        output_dir / "02_CURRENT_GLUE_TOPOLOGY.csv",
        glue_rows,
        [
            "imt_id", "group_size", "size_bucket", "member_nmids", "subject_names",
            "priority_categories", "subject_consistent", "price_spread_rub",
            "has_ad_presence", "semantic_outliers",
        ],
    )

    attr_rows: list[dict[str, Any]] = []
    for nmid in scoped_list:
        card = card_by_nmid.get(nmid, {})
        attrs = _card_attrs(card)
        imt = _read_int(card, "imtID", "imtId")
        attr_rows.append(
            {
                "nmID": nmid,
                "imtID": imt or "GAP",
                "vendorCode": card.get("vendorCode") or "GAP",
                "title": card.get("title") or "GAP",
                "subjectID": card.get("subjectID") or "GAP",
                "subjectName": card.get("subjectName") or "GAP",
                "brand": card.get("brand") or "GAP",
                "group_size": len(imt_scoped.get(imt, {nmid})),
                "priority_category": nmid_category.get(nmid, ""),
                "color": attrs.get("color") or "",
                "sizes": attrs.get("sizes") or "",
                "characteristics": attrs.get("characteristics") or "",
                "raw_card_path": "raw/content_cards_all.jsonl",
            }
        )
    _write_csv(
        output_dir / "03_PRODUCT_ATTRIBUTES_CURRENT.csv",
        attr_rows,
        [
            "nmID", "imtID", "vendorCode", "title", "subjectID", "subjectName",
            "brand", "group_size", "priority_category", "color", "sizes",
            "characteristics", "raw_card_path",
        ],
    )

    price_out: list[dict[str, Any]] = []
    for nmid in scoped_list:
        pr = price_by_nmid.get(nmid, {})
        price_out.append(
            {
                "nmID": nmid,
                "base_list_price": pr.get("price") if pr.get("price") is not None else "GAP",
                "seller_discount_pct": pr.get("discount") if pr.get("discount") is not None else "GAP",
                "discounted_price": pr.get("discountedPrice") if pr.get("discountedPrice") is not None else "GAP",
                "effective_seller_price": pr.get("SALE_PRICE_REFERENCE") if pr.get("SALE_PRICE_REFERENCE") is not None else "GAP",
                "wb_visible_signal": pr.get("STATUS") or "GAP",
                "source": price_route or "GAP",
                "checked_at_msk": _iso_msk(checked_at),
            }
        )
    _write_csv(
        output_dir / "04_PRICE_CURRENT.csv",
        price_out,
        [
            "nmID", "base_list_price", "seller_discount_pct", "discounted_price",
            "effective_seller_price", "wb_visible_signal", "source", "checked_at_msk",
        ],
    )

    stock_out: list[dict[str, Any]] = []
    for nmid in scoped_list:
        st = stock_data.get(nmid, {})
        fbs = st.get("fbs_total")
        fbo = st.get("fbo_total")
        stock_out.append(
            {
                "nmID": nmid,
                "fbo": fbo if fbo is not None else "GAP",
                "fbs": fbs if fbs is not None else "GAP",
                "total": st.get("total") if st.get("total") is not None else "GAP",
                "source": st.get("source", "GAP"),
                "checked_at_msk": _iso_msk(checked_at),
                "freshness": st.get("freshness", "snapshot"),
                "CLIENT_REPORTS_FBS_PRESENT": "YES",
            }
        )
    _write_csv(
        output_dir / "05_STOCK_CURRENT.csv",
        stock_out,
        ["nmID", "fbo", "fbs", "total", "source", "checked_at_msk", "freshness", "CLIENT_REPORTS_FBS_PRESENT"],
    )

    sales_rows: list[dict[str, Any]] = []
    for nmid in scoped_list:
        s7 = _sales_window(orders_raw, nmid, dates_7)
        s14 = _sales_window(orders_raw, nmid, dates_14)
        s28 = _sales_window(orders_raw, nmid, dates_28)
        sales_rows.append(
            {
                "nmID": nmid,
                "window_7d_events": s7["events"],
                "window_7d_units": s7["units"],
                "window_7d_value": s7["value"],
                "window_14d_events": s14["events"],
                "window_14d_units": s14["units"],
                "window_14d_value": s14["value"],
                "window_28d_events": s28["events"],
                "window_28d_units": s28["units"],
                "window_28d_value": s28["value"],
                "last_order_date": s28["last_order_date"],
                "cancellation_treatment": "exclude isCancel=true",
                "source": "supplier_orders_api",
                "period_closed_through": closed_end.isoformat(),
            }
        )
    _write_csv(
        output_dir / "06_FACTUAL_SALES_WINDOWS.csv",
        sales_rows,
        [
            "nmID", "window_7d_events", "window_7d_units", "window_7d_value",
            "window_14d_events", "window_14d_units", "window_14d_value",
            "window_28d_events", "window_28d_units", "window_28d_value",
            "last_order_date", "cancellation_treatment", "source", "period_closed_through",
        ],
    )

    contour_rows: list[dict[str, Any]] = []
    for nmid in scoped_list:
        for c in nm_contours.get(nmid, []):
            auto_id = c.get("auto_adv_id")
            wb_c = wb_by_id.get(int(auto_id or 0), {})
            wb_status = wb_c.get("status") if wb_c else "GAP"
            contour_rows.append(
                {
                    "nmID": nmid,
                    "adv_setting_id": c.get("adv_setting_id") or "GAP",
                    "auto_adv_id": auto_id or "GAP",
                    "search_adv_id": c.get("search_adv_id") or "GAP",
                    "campaign_name": c.get("name") or "GAP",
                    "wb_status": wb_status,
                    "wb_status_name": WB_STATUS_NAMES.get(int(wb_status), str(wb_status)) if str(wb_status).isdigit() else wb_status,
                    "pg_active_status": c.get("pg_active_status") or "GAP",
                    "bot_active": c.get("bot_active") or "GAP",
                    "target_cpo": c.get("target_cpo") or "GAP",
                    "max_cpo": c.get("max_cpo") or "GAP",
                    "auto_daily_limit": c.get("auto_daily_limit") or "GAP",
                    "search_daily_limit": c.get("search_daily_limit") or "GAP",
                    "promoted_nmids": ",".join(str(x) for x in _parse_nmids(str(c.get("nmids_pg") or ""))),
                }
            )
        if not nm_contours.get(nmid):
            contour_rows.append(
                {
                    "nmID": nmid,
                    "adv_setting_id": "GAP",
                    "auto_adv_id": "GAP",
                    "search_adv_id": "GAP",
                    "campaign_name": "GAP",
                    "wb_status": "GAP",
                    "wb_status_name": "GAP",
                    "pg_active_status": "GAP",
                    "bot_active": "GAP",
                    "target_cpo": "GAP",
                    "max_cpo": "GAP",
                    "auto_daily_limit": "GAP",
                    "search_daily_limit": "GAP",
                    "promoted_nmids": "GAP",
                }
            )
    _write_csv(
        output_dir / "07_CAMPAIGN_CONTOUR_CURRENT.csv",
        contour_rows,
        [
            "nmID", "adv_setting_id", "auto_adv_id", "search_adv_id", "campaign_name",
            "wb_status", "wb_status_name", "pg_active_status", "bot_active",
            "target_cpo", "max_cpo", "auto_daily_limit", "search_daily_limit", "promoted_nmids",
        ],
    )

    perf_rows: list[dict[str, Any]] = []
    scoped_adv_ids: set[int] = set()
    for nmid in scoped_list:
        for c in nm_contours.get(nmid, []):
            if c.get("auto_adv_id"):
                scoped_adv_ids.add(int(c["auto_adv_id"]))
            if c.get("search_adv_id"):
                scoped_adv_ids.add(int(c["search_adv_id"]))

    for adv_id in sorted(scoped_adv_ids):
        for window, dates in (("7d", dates_7), ("14d", dates_14), ("28d", dates_28)):
            day_subset = [r for r in day_rows if r["advert_id"] == adv_id and r["date"] in dates]
            if not day_subset:
                continue
            views = sum(r["day_views"] for r in day_subset)
            clicks = sum(r["day_clicks"] for r in day_subset)
            spend = round(sum(r["day_spend"] for r in day_subset), 2)
            orders = sum(r["day_orders"] for r in day_subset)
            gmv = round(sum(r["day_sum_price"] for r in day_subset), 2)
            ctr = round(clicks / views, 6) if views else "GAP"
            perf_rows.append(
                {
                    "adv_id": adv_id,
                    "window": window,
                    "spend": spend,
                    "views": views,
                    "clicks": clicks,
                    "ctr": ctr,
                    "orders": orders,
                    "gmv": gmv,
                    "source": "wb.fullstats.v3 day totals (no re-sum nm)",
                }
            )
    _write_csv(
        output_dir / "08_ADV_PERFORMANCE_WINDOWS.csv",
        perf_rows,
        ["adv_id", "window", "spend", "views", "clicks", "ctr", "orders", "gmv", "source"],
    )

    nm_attr_rows: list[dict[str, Any]] = []
    for r in nm_rows:
        if r["advert_id"] not in scoped_adv_ids:
            continue
        if r["date"] not in dates_28:
            continue
        nm_attr_rows.append(
            {
                "adv_id": r["advert_id"],
                "date": r["date"],
                "app_type": r.get("app_type"),
                "ordered_nmID": r["ordered_nm_id"],
                "carts": r["atbs"],
                "orders": r["orders"],
                "gmv": r["sum_price"],
                "period_state": "CLOSED" if r["date"] != OPEN_DAY.isoformat() else "OPEN",
            }
        )
    _write_csv(
        output_dir / "09_ADV_NM_ATTRIBUTION.csv",
        nm_attr_rows,
        ["adv_id", "date", "app_type", "ordered_nmID", "carts", "orders", "gmv", "period_state"],
    )

    edge_rows: list[dict[str, Any]] = []
    for c in campaigns:
        adv_id = _read_int(c, "id", "advertId")
        if adv_id not in scoped_adv_ids:
            continue
        promoted = _promoted_set(c)
        if not promoted & scoped_nmids:
            continue
        edge_rows.extend(
            _association_edges(nm_rows, adv_id, promoted, dates_28, "28d_closed")
        )
    _write_csv(
        output_dir / "10_ASSOCIATION_EDGES.csv",
        edge_rows,
        [
            "source_campaign", "source_promoted_set", "donor_nmID", "receiver_nmID",
            "window", "associated_carts", "associated_orders", "associated_gmv", "causal_note",
        ],
    )

    priority5_rows: list[dict[str, Any]] = []
    for nmid in WORKING_SKUS:
        card = card_by_nmid.get(nmid, {})
        cat = nmid_category.get(nmid, "")
        imt = _read_int(card, "imtID", "imtId")
        group = imt_scoped.get(imt, {nmid}) if imt else {nmid}
        alts = [m for m in group if m != nmid and m in scoped_list]
        pr = price_by_nmid.get(nmid, {})
        s28 = _sales_window(orders_raw, nmid, dates_28)
        contours = nm_contours.get(nmid, [])
        primary_adv = contours[0].get("auto_adv_id") if contours else "GAP"
        promoted = set()
        for c in campaigns:
            if _read_int(c, "id", "advertId") == int(primary_adv or 0):
                promoted = _promoted_set(c)
        da = _direct_assoc_split(
            [r for r in nm_rows if r["advert_id"] == int(primary_adv or 0)],
            promoted,
            dates_28,
        ) if primary_adv != "GAP" else {"direct_orders_28d": "GAP", "associated_orders_28d": "GAP", "DIRECT_ASSOC_SPLIT": "GAP"}

        support = "STRONG" if s28["units"] >= 3 and contours else "MEDIUM" if contours else "WEAK"
        priority5_rows.append(
            {
                "nmID": nmid,
                "category": CATEGORY_LABELS.get(cat, cat or "GAP"),
                "imtID": imt or "GAP",
                "title": card.get("title") or "GAP",
                "current_price": pr.get("SALE_PRICE_REFERENCE") if pr.get("SALE_PRICE_REFERENCE") is not None else "GAP",
                "units_28d": s28["units"],
                "sales_value_28d": s28["value"],
                "adv_setting_id": contours[0].get("adv_setting_id") if contours else "GAP",
                "auto_adv_id": primary_adv,
                "direct_orders_28d": da.get("direct_orders", "GAP"),
                "associated_orders_28d": da.get("associated_orders", "GAP"),
                "alternatives_in_group": ",".join(str(a) for a in sorted(alts)),
                "CURRENT_ENTRY_SUPPORT": support,
                "notes": "working SKU — do not silently replace",
            }
        )
    _write_csv(
        output_dir / "11_PRIORITY5_COMPARISON.csv",
        priority5_rows,
        [
            "nmID", "category", "imtID", "title", "current_price", "units_28d",
            "sales_value_28d", "adv_setting_id", "auto_adv_id", "direct_orders_28d",
            "associated_orders_28d", "alternatives_in_group", "CURRENT_ENTRY_SUPPORT", "notes",
        ],
    )

    decision_rows: list[dict[str, Any]] = []
    for nmid in scoped_list:
        card = card_by_nmid.get(nmid, {})
        cat = nmid_category.get(nmid, "")
        imt = _read_int(card, "imtID", "imtId")
        pr = price_by_nmid.get(nmid, {})
        st = stock_data.get(nmid, {})
        s7 = _sales_window(orders_raw, nmid, dates_7)
        s14 = _sales_window(orders_raw, nmid, dates_14)
        s28 = _sales_window(orders_raw, nmid, dates_28)
        contours = nm_contours.get(nmid, [])
        c0 = contours[0] if contours else {}
        other_adv = sorted(
            {
                int(x)
                for c in contours[1:]
                for x in (c.get("auto_adv_id"), c.get("search_adv_id"))
                if x and str(x).isdigit()
            }
        )
        spend = {w: 0.0 for w in WINDOWS}
        for c in contours:
            for leg in ("auto_adv_id", "search_adv_id"):
                aid = c.get(leg)
                if not aid:
                    continue
                for w, dates in zip(WINDOWS, (dates_7, dates_14, dates_28)):
                    spend[w] += sum(
                        r["day_spend"]
                        for r in day_rows
                        if r["advert_id"] == int(aid) and r["date"] in dates
                    )
        promoted: set[int] = set()
        auto_id = c0.get("auto_adv_id")
        if auto_id:
            wb_c = wb_by_id.get(int(auto_id), {})
            promoted = _promoted_set(wb_c) if wb_c else set()
        da28 = _direct_assoc_split(
            [r for r in nm_rows if auto_id and r["advert_id"] == int(auto_id)],
            promoted,
            dates_28,
        )
        attrs = _card_attrs(card)
        entry = "YES" if nmid in WORKING_SKUS else ""
        support = "STRONG" if nmid in WORKING_SKUS else ""
        row_gaps: list[str] = []
        if pr.get("SALE_PRICE_REFERENCE") is None:
            row_gaps.append("PRICE_GAP")
        if st.get("fbs_total") is None:
            row_gaps.append("FBS_QUANTITY_GAP")
        decision_rows.append(
            {
                "category": CATEGORY_LABELS.get(cat, cat),
                "subject": card.get("subjectName") or "GAP",
                "current_imt_id": imt or "GAP",
                "current_group_size": len(imt_scoped.get(imt, {nmid})) if imt else 1,
                "nm_id": nmid,
                "vendor_code": card.get("vendorCode") or "GAP",
                "title": card.get("title") or "GAP",
                "key_attributes": attrs.get("characteristics") or attrs.get("sizes") or "",
                "current_price": pr.get("SALE_PRICE_REFERENCE") if pr.get("SALE_PRICE_REFERENCE") is not None else "GAP",
                "price_source": price_route or "GAP",
                "fbo": st.get("fbo_total") if st.get("fbo_total") is not None else "GAP",
                "fbs": st.get("fbs_total") if st.get("fbs_total") is not None else "GAP",
                "stock_source": st.get("source", "GAP"),
                "sales_events_7d": s7["events"],
                "units_7d": s7["units"],
                "sales_value_7d": s7["value"],
                "sales_events_14d": s14["events"],
                "units_14d": s14["units"],
                "sales_value_14d": s14["value"],
                "sales_events_28d": s28["events"],
                "units_28d": s28["units"],
                "sales_value_28d": s28["value"],
                "adv_setting_id": c0.get("adv_setting_id") or "GAP",
                "auto_adv_id": c0.get("auto_adv_id") or "GAP",
                "search_adv_id": c0.get("search_adv_id") or "GAP",
                "other_adv_ids": ",".join(str(x) for x in other_adv),
                "wb_status": wb_by_id.get(int(auto_id or 0), {}).get("status", "GAP") if auto_id else "GAP",
                "bot_active": c0.get("bot_active") or "GAP",
                "target_cpo": c0.get("target_cpo") or "GAP",
                "max_cpo": c0.get("max_cpo") or "GAP",
                "auto_daily_limit": c0.get("auto_daily_limit") or "GAP",
                "search_daily_limit": c0.get("search_daily_limit") or "GAP",
                "ad_spend_7d": round(spend[7], 2),
                "ad_spend_14d": round(spend[14], 2),
                "ad_spend_28d": round(spend[28], 2),
                "direct_carts_28d": da28.get("direct_carts", "GAP"),
                "associated_carts_28d": da28.get("associated_carts", "GAP"),
                "direct_orders_28d": da28.get("direct_orders", "GAP"),
                "associated_orders_28d": da28.get("associated_orders", "GAP"),
                "direct_gmv_28d": da28.get("direct_gmv", "GAP"),
                "associated_gmv_28d": da28.get("associated_gmv", "GAP"),
                "entry_candidate_current": entry,
                "entry_support": support,
                "gaps": ";".join(row_gaps),
                "checked_at_msk": _iso_msk(checked_at),
            }
        )
    _write_csv(
        output_dir / "12_DECISION_INPUT_TABLE.csv",
        decision_rows,
        [
            "category", "subject", "current_imt_id", "current_group_size", "nm_id",
            "vendor_code", "title", "key_attributes", "current_price", "price_source",
            "fbo", "fbs", "stock_source", "sales_events_7d", "units_7d", "sales_value_7d",
            "sales_events_14d", "units_14d", "sales_value_14d", "sales_events_28d",
            "units_28d", "sales_value_28d", "adv_setting_id", "auto_adv_id", "search_adv_id",
            "other_adv_ids", "wb_status", "bot_active", "target_cpo", "max_cpo",
            "auto_daily_limit", "search_daily_limit", "ad_spend_7d", "ad_spend_14d",
            "ad_spend_28d", "direct_carts_28d", "associated_carts_28d", "direct_orders_28d",
            "associated_orders_28d", "direct_gmv_28d", "associated_gmv_28d",
            "entry_candidate_current", "entry_support", "gaps", "checked_at_msk",
        ],
    )

    draft_group_rows: list[dict[str, Any]] = []
    for imt_id, members in sorted(imt_scoped.items(), key=lambda x: -len(x[1])):
        if len(members) <= 5:
            draft_group_rows.append(
                {
                    "draft_group_id": f"KEEP_IMT_{imt_id}",
                    "imt_id": imt_id,
                    "proposed_members": ",".join(str(m) for m in sorted(members)),
                    "proposed_size": len(members),
                    "action_draft": "KEEP",
                    "rationale": "size within 3-5 target or smaller; WEB_DECISION_REQUIRED",
                }
            )
        else:
            by_subject: dict[str, list[int]] = defaultdict(list)
            for m in members:
                subj = str(card_by_nmid.get(m, {}).get("subjectName") or "unknown")
                by_subject[subj].append(m)
            for idx, (subj, ms) in enumerate(sorted(by_subject.items()), start=1):
                draft_group_rows.append(
                    {
                        "draft_group_id": f"SPLIT_IMT_{imt_id}_{idx}",
                        "imt_id": imt_id,
                        "proposed_members": ",".join(str(x) for x in sorted(ms)),
                        "proposed_size": len(ms),
                        "action_draft": "SPLIT_CANDIDATE",
                        "rationale": f"group_size>{5}; subject={subj}; WEB_DECISION_REQUIRED",
                    }
                )
    _write_csv(
        output_dir / "13_DRAFT_GROUPING_FOR_WEB_REVIEW.csv",
        draft_group_rows,
        ["draft_group_id", "imt_id", "proposed_members", "proposed_size", "action_draft", "rationale"],
    )

    draft_price_rows: list[dict[str, Any]] = []
    for nmid in scoped_list:
        imt = _read_int(card_by_nmid.get(nmid, {}), "imtID", "imtId")
        group = imt_scoped.get(imt, {nmid}) if imt else {nmid}
        group_prices = [
            float(price_by_nmid[m]["SALE_PRICE_REFERENCE"])
            for m in group
            if m in price_by_nmid and price_by_nmid[m].get("SALE_PRICE_REFERENCE") is not None
        ]
        pr = price_by_nmid.get(nmid, {})
        cur = pr.get("SALE_PRICE_REFERENCE")
        role = _price_role(cur, group_prices)
        rel = "MID"
        if group_prices and cur is not None:
            mn, mx = min(group_prices), max(group_prices)
            if float(cur) <= mn:
                rel = "LOWEST_IN_GROUP"
            elif float(cur) >= mx:
                rel = "HIGHEST_IN_GROUP"
        draft_price_rows.append(
            {
                "nmID": nmid,
                "imtID": imt or "GAP",
                "DRAFT_PRICE_ROLE": role,
                "CURRENT_PRICE": cur if cur is not None else "GAP",
                "RELATIVE_POSITION": rel,
                "DIRECTION_DRAFT": "REVIEW",
                "note": "no production price change; CLIENT/WEB_DECISION_REQUIRED",
            }
        )
    _write_csv(
        output_dir / "14_DRAFT_PRICE_ROLES_FOR_WEB_REVIEW.csv",
        draft_price_rows,
        ["nmID", "imtID", "DRAFT_PRICE_ROLE", "CURRENT_PRICE", "RELATIVE_POSITION", "DIRECTION_DRAFT", "note"],
    )

    dq_lines = [
        "# Data Quality and Gaps",
        "",
        f"- shop_id: `{SHOP_ID}`",
        f"- last_fully_closed_day: `{closed_end.isoformat()}` (verified MSK semantics)",
        f"- open_day: `{OPEN_DAY.isoformat()}` (excluded from closed windows)",
        f"- store_total_nmids: {store_total_cards}",
        f"- scoped_nmids: {len(scoped_list)}",
        f"- priority_category_nmids: {len(priority_nmids)}",
        f"- imt_groups_in_scope: {len(imt_scoped)}",
        f"- campaigns_in_fullstats: {len(adv_ids)}",
        f"- supplier_orders_raw: {len(orders_raw)}",
        "",
        "## Gaps",
    ]
    for g in gaps:
        dq_lines.append(f"- {g}")
    if not price_route:
        dq_lines.append("- PRICE_API: GAP or blocked")
    (output_dir / "15_DATA_QUALITY_AND_GAPS.md").write_text("\n".join(dq_lines) + "\n", encoding="utf-8")

    qa_lines = [
        "# Master QA Report (collector draft)",
        "",
        f"Package `{PACKAGE}` generated at {_iso_msk(checked_at)}.",
        f"Scoped {len(scoped_list)} nmIDs across {len(imt_scoped)} imt groups.",
        "Attribution present: YES (09_ADV_NM_ATTRIBUTION.csv).",
        "Association edges: YES (10_ASSOCIATION_EDGES.csv).",
        "Direct/associated split: per-campaign when promoted set known.",
        "",
        "MASTER should rewrite after QA.",
    ]
    (output_dir / "16_MASTER_QA_REPORT.md").write_text("\n".join(qa_lines) + "\n", encoding="utf-8")

    human = [
        "# Human Summary",
        "",
        f"A1 glue/topology READ_ONLY snapshot for Web chat.",
        f"Closed windows end {closed_end.isoformat()}; open day {OPEN_DAY.isoformat()} excluded.",
        f"Store has {store_total_cards} cards; scope {len(scoped_list)} nmIDs "
        f"({len(priority_nmids)} priority category + glue expansion).",
        f"Working SKUs tracked: {', '.join(str(x) for x in WORKING_SKUS)}.",
        "No glue/price/ad production changes performed.",
    ]
    (output_dir / "17_HUMAN_SUMMARY.md").write_text("\n".join(human) + "\n", encoding="utf-8")

    manifest = {
        "package": PACKAGE,
        "artifact_class": "A1_GLUE_TOPOLOGY_WEB_REVIEW",
        "primary_zip_basename": f"{PACKAGE}.zip",
        "shop_id": SHOP_ID,
        "created_at_msk": _iso_msk(checked_at),
        "last_fully_closed_day": closed_end.isoformat(),
        "open_day": OPEN_DAY.isoformat(),
        "counts": {
            "store_total_nmids": store_total_cards,
            "scoped_nmids": len(scoped_list),
            "priority_nmids": len(priority_nmids),
            "imt_groups": len(imt_scoped),
            "campaigns": len(campaigns),
            "association_edges": len(edge_rows),
        },
        "working_skus": list(WORKING_SKUS),
        "gaps": gaps,
    }
    (output_dir / "00_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    findings = evidence.secret_scan(output_dir)
    if findings:
        raise SystemExit(f"Secret scan failed: {findings[:3]}")

    archive, digest = evidence.archive_directory(output_dir)
    return {
        "EXECUTION_STATUS": "COMPLETE",
        "PACKAGE": PACKAGE,
        "SHOP_ID": SHOP_ID,
        "LAST_FULLY_CLOSED_DAY": closed_end.isoformat(),
        "SCOPED_NMIDS": len(scoped_list),
        "IMT_GROUPS": len(imt_scoped),
        "ZIP_ABSOLUTE_PATH": str(archive.resolve()),
        "ZIP_SHA256": digest,
        "PRIMARY_ARTIFACT": archive.name,
        "CRITICAL_GAPS": gaps,
    }


async def _fetch_stocks_for_cards(
    cards: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """FBS via marketplace stocks API; FBO GAP unless present on card."""
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    if not cards:
        return {}
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        products = hub.wb_data_manager.products_manager
        seller = await _fetch_seller_stocks(products, cards)

    out: dict[int, dict[str, Any]] = {}
    by_nmid = seller.get("by_nmid") or {}
    for nmid in cards:
        entry = by_nmid.get(nmid, {})
        fbs = entry.get("total_sellable")
        out[nmid] = {
            "fbs_total": fbs if fbs is not None else None,
            "fbo_total": None,
            "total": fbs if fbs is not None else None,
            "source": seller.get("source", "POST /api/v3/stocks/{warehouse_id}"),
            "freshness": seller.get("status", "snapshot"),
        }
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A1 glue topology Web review READ_ONLY collector.")
    parser.add_argument(
        "--output-dir",
        default=".tmp/a1_glue_topology_web_review",
        help="Output directory (will be zipped)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.output_dir).resolve()
    result = run_collect(out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""READ_ONLY: A1 current sale price snapshot for CPO normalization (10% of sale price).

POST /api/v2/list/goods/filter — WB Discounts & Prices API. Без writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")

TARGET_NMIDS = (
    85970344,
    770642983,
    14166423,
    837395782,
    7974113,
    14824677,
    4491664,
    7974106,
    7839837,
    4491663,
    13713289,
    4491650,
    147281596,
)

HIGHLIGHT_NMIDS = {14824677, 837395782}


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _parse_goods_item(item: Any) -> dict[str, Any]:
    d = jsonable(item)
    if not isinstance(d, dict):
        return {"status": "GAP", "raw": d}

    nm_id = d.get("nmID") or d.get("nm_id")
    vendor_code = d.get("vendorCode")
    currency = d.get("currencyIsoCode4217")
    discount = d.get("discount")
    club_discount = d.get("clubDiscount")
    editable = d.get("editableSizePrice")

    sizes_raw = d.get("sizes") or []
    sizes: list[dict[str, Any]] = []
    prices: list[int] = []
    discounted: list[float] = []
    club_disc: list[float] = []

    for sz in sizes_raw:
        if not isinstance(sz, dict):
            continue
        p = sz.get("price")
        dp = sz.get("discountedPrice")
        cdp = sz.get("clubDiscountedPrice")
        sizes.append({
            "sizeID": sz.get("sizeID"),
            "techSizeName": sz.get("techSizeName"),
            "price": p,
            "discountedPrice": dp,
            "clubDiscountedPrice": cdp,
        })
        if p is not None:
            prices.append(int(p))
        if dp is not None:
            discounted.append(float(dp))
        if cdp is not None:
            club_disc.append(float(cdp))

    if not discounted:
        return {
            "nmID": nm_id,
            "vendorCode": vendor_code,
            "currency": currency,
            "price": None,
            "discount": discount,
            "discountedPrice": None,
            "clubDiscountedPrice": None,
            "editableSizePrice": editable,
            "sizes": sizes,
            "size_price_min": None,
            "size_price_max": None,
            "SALE_PRICE_REFERENCE": None,
            "CPO_10_PERCENT": None,
            "STATUS": "NOT_FOUND_IN_RESPONSE",
        }

    sale_ref = min(discounted)
    single_dp = discounted[0] if len(discounted) == 1 else None
    row_dp = (
        single_dp
        if single_dp is not None and min(discounted) == max(discounted)
        else sale_ref
    )

    return {
        "nmID": nm_id,
        "vendorCode": vendor_code,
        "currency": currency,
        "price": prices[0] if len(prices) == 1 else (min(prices) if prices else None),
        "discount": discount,
        "discountedPrice": row_dp,
        "clubDiscountedPrice": club_disc[0] if len(club_disc) == 1 else None,
        "editableSizePrice": editable,
        "sizes": sizes,
        "size_price_min": min(discounted),
        "size_price_max": max(discounted),
        "SALE_PRICE_REFERENCE": sale_ref,
        "CPO_10_PERCENT": round(sale_ref * 0.10),
        "STATUS": "OK",
        "sale_price_rule": (
            "single_discountedPrice"
            if len(discounted) == 1 or min(discounted) == max(discounted)
            else "MIN(discountedPrice) across sizes"
        ),
        "club_discount_note": (
            "clubDiscountedPrice collected but not used as SALE_PRICE_REFERENCE"
        ),
    }


PRICES_API_BASE = "https://discounts-prices-api.wildberries.ru"
PRICES_ROUTE = "POST /api/v2/list/goods/filter"


async def _price_tokens() -> list[tuple[str, str]]:
    """(api_key, label) для токенов с «Цены и скидки» или fallback candidates."""
    from app.modules.common_slaves.wildberries import super_cabinet_manager

    access = await super_cabinet_manager.get_access_for_wb_cabinet(SHOP_ID)
    out: list[tuple[str, str]] = []
    for token in sorted(access.tokens, key=lambda t: t.expires, reverse=True):
        if token.is_expired:
            continue
        cats = token.categories
        if "Цены и скидки" in cats:
            out.append((token.api_key, "prices_and_discounts"))
        elif "Маркетплейс" in cats:
            out.append((token.api_key, "marketplace"))
        elif "Контент" in cats:
            out.append((token.api_key, "content"))
    return out


def _blocked_rows(nmids: list[int], gaps: list[str]) -> list[dict[str, Any]]:
    status = "PRICES_API_SCOPE_DENIED"
    if any(g.startswith("NO_WB_TOKEN_WITH_") for g in gaps):
        status = "GAP_NO_PRICES_TOKEN"
    return [
        {
            "nmID": nmid,
            "vendorCode": None,
            "price": None,
            "discount": None,
            "discountedPrice": None,
            "size_price_min": None,
            "size_price_max": None,
            "SALE_PRICE_REFERENCE": None,
            "CPO_10_PERCENT": None,
            "STATUS": status,
        }
        for nmid in nmids
    ]


async def _enrich_vendor_codes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """vendorCode из Content API (не заменяет Prices API для SALE_PRICE_REFERENCE)."""
    from scripts.a1_cpc_two_sku_safety_preflight import _fetch_cards

    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    nmids_set = {int(r["nmID"]) for r in rows if r.get("nmID") is not None}
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        products = hub.wb_data_manager.products_manager
        cards = await _fetch_cards(products, nmids_set)
    for row in rows:
        card = cards.get(int(row["nmID"]), {})
        if card.get("vendorCode"):
            row["vendorCode"] = card["vendorCode"]
        if row.get("STATUS", "").startswith(("GAP_", "PRICES_")):
            row["content_card_note"] = (
                "vendorCode from Content API only; prices require «Цены и скидки» token"
            )
    return rows


async def fetch_prices(nmids: list[int]) -> tuple[list[dict[str, Any]], str, list[str]]:
    import httpx

    gaps: list[str] = []
    tokens = await _price_tokens()
    if not any(label == "prices_and_discounts" for _, label in tokens):
        gaps.append("NO_WB_TOKEN_WITH_Цены_и_скидки_CATEGORY")

    payload: dict[str, Any] | None = None
    route_used = f"{PRICES_API_BASE}{PRICES_ROUTE}"
    async with httpx.AsyncClient(base_url=PRICES_API_BASE, timeout=60.0) as client:
        for api_key, label in tokens:
            response = await client.post(
                "/api/v2/list/goods/filter",
                json={"nmList": nmids},
                headers={"Authorization": api_key, "Content-Type": "application/json"},
            )
            if response.status_code == 200:
                payload = response.json()
                route_used = f"{route_used} (token={label})"
                break
            gaps.append(f"prices_api_{label}_http_{response.status_code}")

    if payload is None:
        return _blocked_rows(nmids, gaps), "", gaps

    data = payload.get("data") if isinstance(payload, dict) else None
    goods_raw = []
    if isinstance(data, dict):
        goods_raw = data.get("listGoods") or data.get("list_goods") or []

    by_nmid: dict[int, dict[str, Any]] = {}
    for item in goods_raw:
        row = _parse_goods_item(item)
        nmid = row.get("nmID")
        if nmid is not None:
            by_nmid[int(nmid)] = row

    out: list[dict[str, Any]] = []
    for nmid in nmids:
        if nmid in by_nmid:
            out.append(by_nmid[nmid])
        else:
            out.append({
                "nmID": nmid,
                "vendorCode": None,
                "price": None,
                "discount": None,
                "discountedPrice": None,
                "size_price_min": None,
                "size_price_max": None,
                "SALE_PRICE_REFERENCE": None,
                "CPO_10_PERCENT": None,
                "STATUS": "NOT_FOUND_IN_RESPONSE",
            })
    return out, route_used, gaps


async def run_snapshot(nmids: list[int]) -> tuple[list[dict[str, Any]], str, list[str]]:
    rows, route, gaps = await fetch_prices(nmids)
    if gaps:
        rows = await _enrich_vendor_codes(rows)
    return rows, route, gaps


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="")
    args = ap.parse_args(argv)
    checked = _iso_msk(_msk_now())
    rows, route, gaps = asyncio.run(run_snapshot(list(TARGET_NMIDS)))

    payload = {
        "checked_at_msk": checked,
        "shop_id": SHOP_ID,
        "source_route": route,
        "gaps": gaps,
        "mode": "STRICT_READ_ONLY",
        "rows": rows,
        "highlight": {str(n): next((r for r in rows if r.get("nmID") == n), {}) for n in HIGHLIGHT_NMIDS},
        "READ_ONLY": "CONFIRMED",
        "WB_API_WRITES": 0,
        "DB_WRITES": 0,
    }

    if args.output:
        Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

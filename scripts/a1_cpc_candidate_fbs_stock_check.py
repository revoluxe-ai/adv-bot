"""READ_ONLY: A1 FBS stock check for CPC candidates via Marketplace API.

GET /api/v3/warehouses + POST /api/v3/stocks/{warehouseId} per seller warehouse.
chrtIds — через Content API (cards). Суммирование FBS по chrtId/nmID; FBO — константы.
Без writes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _read_int
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-CPC-CANDIDATE-FBS-STOCK-CHECK"

TARGET_NMIDS = (837395782, 180148471, 206697189, 288483603, 14824677, 180145507)

FBO_KNOWN: dict[int, int] = {
    837395782: 33,
    180148471: 4,
    206697189: 0,
    288483603: 0,
    14824677: 0,
    180145507: 0,
}

# WB analytics pseudo-warehouse — never use for FBS stocks endpoint
EXCLUDED_WAREHOUSE_IDS = {-999999}


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


async def _fetch_chrt_ids(products: Any, nmids: set[int]) -> dict[int, list[int]]:
    from app.core.mp.wb.api.generated.products.v1.content_products_client.models import (
        PostContentV2GetCardsListBody,
        PostContentV2GetCardsListBodySettings,
        PostContentV2GetCardsListBodySettingsCursor,
        PostContentV2GetCardsListBodySettingsFilter,
        PostContentV2GetCardsListBodySettingsSort,
    )
    from app.core.mp.wb.api.generated.products.v1.content_products_client.types import UNSET

    out: dict[int, list[int]] = {}
    sort = PostContentV2GetCardsListBodySettingsSort(ascending=True)
    for nmid in nmids:
        filter_ = PostContentV2GetCardsListBodySettingsFilter(with_photo=-1, text_search=str(nmid))
        cursor = PostContentV2GetCardsListBodySettingsCursor(limit=20)
        settings = PostContentV2GetCardsListBodySettings(filter_=filter_, cursor=cursor, sort=sort)
        body = PostContentV2GetCardsListBody(settings=settings)
        response = await products.get_cards_list(body=body)
        chrt_ids: list[int] = []
        if response is None:
            out[nmid] = chrt_ids
            continue
        cards_raw = response.cards
        page = list(cards_raw) if cards_raw is not UNSET and cards_raw else []
        for card in page:
            d = jsonable(card)
            if not isinstance(d, dict):
                continue
            card_nmid = _read_int(d, "nmID", "nmId", "nmid")
            if card_nmid != nmid:
                continue
            for sz in d.get("sizes") or []:
                if isinstance(sz, dict):
                    cid = _read_int(sz, "chrtID", "chrtId")
                    if cid:
                        chrt_ids.append(cid)
        out[nmid] = sorted(set(chrt_ids))
    return out


MARKETPLACE_BASE_URL = "https://marketplace-api.wildberries.ru"


async def _resolve_marketplace_auth(
    access: Any,
) -> tuple[str | None, list[dict[str, Any]]]:
    """Подобрать токен для marketplace-api probe GET /api/v3/warehouses."""
    probe_errors: list[dict[str, Any]] = []
    tokens = [t for t in access.tokens if not t.is_expired]
    if not tokens:
        return None, [{
            "endpoint": "token_lookup",
            "warehouseId": None,
            "http_status": None,
            "response_body": "GAP: no non-expired personal tokens",
        }]

    def _token_rank(token: Any) -> tuple[int, float]:
        cats = token.categories or set()
        score = 0
        if "Маркетплейс" in cats:
            score += 100
        if "Контент" in cats:
            score += 20
        if "Цены и скидки" in cats:
            score += 10
        if token.read_only:
            score += 5
        return score, token.expires.timestamp()

    for token in sorted(tokens, key=_token_rank, reverse=True):
        status, raw_text, _ = await _marketplace_request(
            token.api_key, "GET", "/api/v3/warehouses",
        )
        if status == 200:
            return token.api_key, probe_errors
        probe_errors.append({
            "endpoint": "GET /api/v3/warehouses",
            "warehouseId": None,
            "http_status": status,
            "response_body": raw_text,
            "api_host": MARKETPLACE_BASE_URL,
            "token_categories": sorted(token.categories),
            "token_read_only": token.read_only,
        })
    return None, probe_errors


async def _marketplace_request(
    token: str,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> tuple[int, str, Any]:
    import httpx

    async with httpx.AsyncClient(
        base_url=MARKETPLACE_BASE_URL,
        timeout=httpx.Timeout(30.0),
        headers={"Authorization": token, "Content-Type": "application/json"},
    ) as client:
        response = await client.request(method, path, json=json_body)
        try:
            body: Any = response.json()
        except Exception:  # noqa: BLE001
            body = response.text
        return response.status_code, response.text[:4000], body


async def _get_seller_warehouses(token: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """GET /api/v3/warehouses на marketplace-api (READ_ONLY)."""
    errors: list[dict[str, Any]] = []
    status, raw_text, raw = await _marketplace_request(token, "GET", "/api/v3/warehouses")
    if status != 200:
        errors.append({
            "endpoint": "GET /api/v3/warehouses",
            "warehouseId": None,
            "http_status": status,
            "response_body": raw_text,
            "api_host": MARKETPLACE_BASE_URL,
        })
        return [], errors

    warehouses: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            wh = jsonable(item) if not isinstance(item, dict) else item
            if not isinstance(wh, dict):
                continue
            wh_id = _read_int(wh, "id", "warehouseId")
            if wh_id in EXCLUDED_WAREHOUSE_IDS or wh_id <= 0:
                continue
            delivery = wh.get("deliveryType") or wh.get("delivery_type")
            warehouses.append({
                "warehouseId": wh_id,
                "name": wh.get("name"),
                "officeId": wh.get("officeId") or wh.get("office_id"),
                "deliveryType": delivery,
                "FBS_marker": delivery == 1 or delivery == "1",
                "cargoType": wh.get("cargoType") or wh.get("cargo_type"),
                "isDeleting": wh.get("isDeleting") or wh.get("is_deleting"),
                "isProcessing": wh.get("isProcessing") or wh.get("is_processing"),
            })
    return warehouses, errors


async def _post_warehouse_stocks(
    token: str,
    warehouse_id: int,
    chrt_ids: list[int],
) -> dict[str, Any]:
    """POST /api/v3/stocks/{warehouseId} на marketplace-api (READ_ONLY)."""
    status, raw_text, payload = await _marketplace_request(
        token, "POST", f"/api/v3/stocks/{warehouse_id}", json_body={"chrtIds": chrt_ids},
    )
    result: dict[str, Any] = {
        "warehouseId": warehouse_id,
        "http_status": status,
        "endpoint": f"POST /api/v3/stocks/{warehouse_id}",
        "api_host": MARKETPLACE_BASE_URL,
    }
    if status != 200:
        result["error"] = True
        result["response_body"] = raw_text
        return result

    stocks: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        items = payload.get("stocks") or payload.get("data") or []
        if isinstance(items, list):
            stocks = [x if isinstance(x, dict) else jsonable(x) for x in items]
    elif isinstance(payload, list):
        stocks = [x if isinstance(x, dict) else jsonable(x) for x in payload]

    result["stocks"] = stocks
    return result


async def run_check() -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis

    checked = _msk_now()
    app_config = AppConfig.create()
    rc = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=rc.host, port=rc.port, db=rc.db, password=rc.password, decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx = HttpxClientHandler()
    await httpx.init()
    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        access = await get_access_for_wb_cabinet(SHOP_ID)
        if access is None:
            return {
                "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "SELLER_WAREHOUSES": [],
                "WAREHOUSE_ERRORS": [{
                    "endpoint": "token_lookup",
                    "warehouseId": None,
                    "http_status": None,
                    "response_body": "GAP: cabinet access not found",
                }],
                "SKU_STOCK": [],
                "NO_WRITES": "CONFIRMED",
            }
        hub = WBManagerHubFactory(httpx_client_handler=httpx, redis_client_wrapper=redis_wrap).get_wb_manager_hub(SHOP_ID)
        products = hub.wb_data_manager.products_manager
        chrt_by_nmid = await _fetch_chrt_ids(products, set(TARGET_NMIDS))
        mp_token, token_probe_errors = await _resolve_marketplace_auth(access)
        if not mp_token:
            return {
                "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "SELLER_WAREHOUSES": [],
                "WAREHOUSE_ERRORS": token_probe_errors,
                "SKU_STOCK": [
                    {
                        "NMID": n,
                        "CHRT_IDS": chrt_by_nmid.get(n, []),
                        "FBS_STOCK_TOTAL": "GAP",
                        "FBS_STOCK_BY_WAREHOUSE": [],
                        "FBO_STOCK_KNOWN": FBO_KNOWN.get(n, 0),
                        "TOTAL_SELLABLE_KNOWN": f"FBO={FBO_KNOWN.get(n, 0)}; FBS=GAP",
                    }
                    for n in TARGET_NMIDS
                ],
                "NO_WRITES": "CONFIRMED",
            }

        chrt_to_nmid = {cid: n for n, ids in chrt_by_nmid.items() for cid in ids}
        all_chrt = sorted(chrt_to_nmid)

        warehouses, wh_errors = await _get_seller_warehouses(mp_token)
        warehouses_lookup_failed = bool(wh_errors)

        warehouse_errors: list[dict[str, Any]] = list(wh_errors)
        by_chrt: dict[int, int] = defaultdict(int)
        by_nmid_wh: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        by_nmid_total: dict[int, int] = defaultdict(int)
        post_errors = 0

        for wh in warehouses:
            wh_id = int(wh["warehouseId"])
            if not all_chrt:
                continue
            resp = await _post_warehouse_stocks(mp_token, wh_id, all_chrt)
            if resp.get("error"):
                post_errors += 1
                warehouse_errors.append({
                    "warehouseId": wh_id,
                    "http_status": resp.get("http_status"),
                    "response_body": resp.get("response_body"),
                    "endpoint": resp.get("endpoint"),
                    "api_host": resp.get("api_host"),
                })
                continue
            for item in resp.get("stocks") or []:
                if not isinstance(item, dict):
                    continue
                chrt = _read_int(item, "chrtId", "chrt_id", "chrtID")
                amt = _read_int(item, "amount", "quantity", "stock") or 0
                if not chrt:
                    continue
                by_chrt[chrt] += amt
                nmid = chrt_to_nmid.get(chrt)
                if nmid:
                    by_nmid_wh[nmid][wh_id] += amt
                    by_nmid_total[nmid] += amt

        sku_rows: list[dict[str, Any]] = []
        for nmid in TARGET_NMIDS:
            fbo = FBO_KNOWN.get(nmid, 0)
            if warehouses_lookup_failed:
                fbs_val: Any = "GAP"
            else:
                fbs_val = by_nmid_total.get(nmid, 0)
            wh_breakdown = [
                {
                    "warehouseId": wid,
                    "warehouse_name": next(
                        (w.get("name") for w in warehouses if w.get("warehouseId") == wid), None
                    ),
                    "amount": amt,
                }
                for wid, amt in sorted(by_nmid_wh.get(nmid, {}).items())
            ]
            total_sellable: Any
            if fbs_val == "GAP":
                total_sellable = f"FBO={fbo}; FBS=GAP"
            else:
                total_sellable = fbo + int(fbs_val)
            row: dict[str, Any] = {
                "NMID": nmid,
                "CHRT_IDS": chrt_by_nmid.get(nmid, []),
                "FBS_STOCK_BY_CHRT_ID": {
                    str(cid): by_chrt[cid]
                    for cid in chrt_by_nmid.get(nmid, [])
                    if cid in by_chrt
                } if fbs_val != "GAP" else {},
                "FBS_STOCK_TOTAL": fbs_val,
                "FBS_STOCK_BY_WAREHOUSE": wh_breakdown if fbs_val != "GAP" else [],
                "FBO_STOCK_KNOWN": fbo,
                "TOTAL_SELLABLE_KNOWN": total_sellable,
            }
            if post_errors and fbs_val != "GAP":
                row["FBS_STOCK_PARTIAL"] = True
            sku_rows.append(row)

        return {
            "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "SELLER_WAREHOUSES": warehouses,
            "WAREHOUSE_ERRORS": warehouse_errors,
            "SKU_STOCK": sku_rows,
            "NO_WRITES": "CONFIRMED",
        }
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_cpc_candidate_fbs_stock")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    payload = asyncio.run(run_check())
    pkg = root / PACKAGE
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / f"{PACKAGE}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
    )
    summary = {
        "CHECKED_AT_MSK": payload["CHECKED_AT_MSK"],
        "SELLER_WAREHOUSES": payload["SELLER_WAREHOUSES"],
        "WAREHOUSE_ERRORS": payload["WAREHOUSE_ERRORS"],
        "SKU_STOCK": [
            {
                "NMID": r["NMID"],
                "CHRT_IDS": r["CHRT_IDS"],
                "FBS_STOCK_TOTAL": r["FBS_STOCK_TOTAL"],
                "FBS_STOCK_BY_WAREHOUSE": r["FBS_STOCK_BY_WAREHOUSE"],
                "FBO_STOCK_KNOWN": r["FBO_STOCK_KNOWN"],
                "TOTAL_SELLABLE_KNOWN": r["TOTAL_SELLABLE_KNOWN"],
            }
            for r in payload["SKU_STOCK"]
        ],
        "NO_WRITES": payload["NO_WRITES"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

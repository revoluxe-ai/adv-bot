"""READ_ONLY: A1 full FBS stock snapshot — marketplace warehouses + content assortment.

Собирает полный FBS stock по всем seller warehouses и chrtId ассортимента.
Опционально FBO через Analytics wb-warehouses. Без writes.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _read_int
from scripts.wb_api_readonly_ops.collect.cards import collect_cards
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-FULL-FBS-STOCK-SNAPSHOT"

CPC_CANDIDATE_NMIDS = (837395782, 180148471, 206697189, 288483603, 14824677, 180145507)

MARKETPLACE_BASE_URL = "https://marketplace-api.wildberries.ru"
FBO_ENDPOINT = "POST /api/analytics/v1/stocks-report/wb-warehouses"
CHRT_BATCH_SIZE = 1000
MAX_RETRIES = 3
RETRY_STATUSES = {429, 502, 503, 504}
EXCLUDED_WAREHOUSE_IDS = {-999999}


class StockStatus(StrEnum):
    CONFIRMED_ZERO = "CONFIRMED_ZERO"
    POSITIVE_STOCK = "POSITIVE_STOCK"
    API_GAP = "API_GAP"
    CHRTID_NOT_RETURNED = "CHRTID_NOT_RETURNED"


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _chunks(items: list[int], size: int) -> list[list[int]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


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
        timeout=httpx.Timeout(60.0),
        headers={"Authorization": token, "Content-Type": "application/json"},
    ) as client:
        response = await client.request(method, path, json=json_body)
        try:
            body: Any = response.json()
        except Exception:  # noqa: BLE001
            body = response.text
        return response.status_code, response.text[:4000], body


async def _marketplace_request_with_retry(
    token: str,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> tuple[int, str, Any, int]:
    """HTTP-запрос с retry для transient errors; возвращает retry_count."""
    retries = 0
    last: tuple[int, str, Any] = (0, "", None)
    for attempt in range(MAX_RETRIES + 1):
        status, raw_text, body = await _marketplace_request(
            token, method, path, json_body=json_body,
        )
        last = (status, raw_text, body)
        if status not in RETRY_STATUSES or attempt >= MAX_RETRIES:
            return status, raw_text, body, retries
        retries += 1
        await asyncio.sleep(1.5 * (2**attempt))
    return last[0], last[1], last[2], retries


async def _resolve_marketplace_token(access: Any) -> tuple[str | None, list[dict[str, Any]]]:
    """Токен с категорией Маркетплейс; probe GET /api/v3/warehouses для каждого кандидата."""
    probe_errors: list[dict[str, Any]] = []
    tokens = [t for t in access.tokens if not t.is_expired]
    if not tokens:
        return None, [{
            "endpoint": "token_lookup",
            "http_status": None,
            "response_body": "GAP: no non-expired tokens in cabinet",
        }]

    mp_tokens = [t for t in tokens if "Маркетплейс" in (t.categories or set())]
    others = [t for t in tokens if t not in mp_tokens]
    candidates = mp_tokens + others

    token_inventory = [
        {
            "token_index": idx,
            "categories": sorted(t.categories),
            "read_only": t.read_only,
            "has_marketplace": "Маркетплейс" in (t.categories or set()),
        }
        for idx, t in enumerate(tokens)
    ]
    probe_errors.append({
        "endpoint": "token_inventory",
        "tokens_total": len(tokens),
        "marketplace_tokens_total": len(mp_tokens),
        "inventory": token_inventory,
    })

    for token in candidates:
        status, raw_text, _ = await _marketplace_request(
            token.api_key, "GET", "/api/v3/warehouses",
        )
        if status == 200:
            return token.api_key, probe_errors
        probe_errors.append({
            "endpoint": "GET /api/v3/warehouses",
            "http_status": status,
            "response_body": raw_text,
            "api_host": MARKETPLACE_BASE_URL,
            "token_categories": sorted(token.categories),
            "token_read_only": token.read_only,
            "has_marketplace_category": "Маркетплейс" in (token.categories or set()),
        })
    return None, probe_errors


def _parse_warehouses(raw: Any) -> list[dict[str, Any]]:
    warehouses: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return warehouses
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
            "raw": {k: v for k, v in wh.items() if k not in ("raw",)},
        })
    return warehouses


def _build_identity_map(cards: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    """Собрать identity map и sku_meta по nmID."""
    rows: list[dict[str, Any]] = []
    sku_meta: dict[int, dict[str, Any]] = {}
    for card in cards:
        nmid = _read_int(card, "nmID", "nmId", "nmid")
        if not nmid:
            continue
        vendor = card.get("vendorCode")
        subject = card.get("subjectName")
        subject_id = card.get("subjectID") or card.get("subjectId")
        sku_meta[nmid] = {
            "nmID": nmid,
            "vendorCode": vendor,
            "subjectName": subject,
            "subjectID": subject_id,
            "brand": card.get("brand"),
            "title": card.get("title"),
        }
        for sz in card.get("sizes") or []:
            if not isinstance(sz, dict):
                continue
            chrt = _read_int(sz, "chrtID", "chrtId")
            if not chrt:
                continue
            rows.append({
                "nmID": nmid,
                "vendorCode": vendor,
                "subjectName": subject,
                "subjectID": subject_id,
                "chrtId": chrt,
                "techSize": sz.get("techSize"),
                "wbSize": sz.get("wbSize"),
                "skus": "|".join(str(s) for s in (sz.get("skus") or [])),
            })
    return rows, sku_meta


def _parse_stock_items(payload: Any) -> list[dict[str, Any]]:
    stocks: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        items = payload.get("stocks") or payload.get("data") or []
        if isinstance(items, list):
            stocks = [x if isinstance(x, dict) else jsonable(x) for x in items]
    elif isinstance(payload, list):
        stocks = [x if isinstance(x, dict) else jsonable(x) for x in payload]
    return [s for s in stocks if isinstance(s, dict)]


@dataclass
class CollectState:
    """Состояние сбора FBS для coverage/retry tracking."""

    raw_records: list[dict[str, Any]] = field(default_factory=list)
    api_errors: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    batches_total: int = 0
    batches_ok: int = 0
    batches_failed: int = 0
    chrt_wh_status: dict[tuple[int, int, int], StockStatus] = field(default_factory=dict)
    chrt_wh_amount: dict[tuple[int, int, int], int] = field(default_factory=dict)


async def _collect_fbs_stocks(
    token: str,
    warehouses: list[dict[str, Any]],
    chrt_ids: list[int],
    chrt_to_nmid: dict[int, int],
) -> CollectState:
    """POST /api/v3/stocks/{warehouseId} батчами по chrtIds."""
    state = CollectState()
    wh_names = {int(w["warehouseId"]): w.get("name") for w in warehouses}

    for wh in warehouses:
        wh_id = int(wh["warehouseId"])
        for batch_idx, batch in enumerate(_chunks(chrt_ids, CHRT_BATCH_SIZE)):
            state.batches_total += 1
            status, raw_text, payload, retries = await _marketplace_request_with_retry(
                token,
                "POST",
                f"/api/v3/stocks/{wh_id}",
                json_body={"chrtIds": batch},
            )
            state.retry_count += retries
            record = {
                "warehouseId": wh_id,
                "warehouseName": wh_names.get(wh_id),
                "batch_index": batch_idx,
                "batch_size": len(batch),
                "chrtIds_requested": batch,
                "http_status": status,
                "endpoint": f"POST /api/v3/stocks/{wh_id}",
                "api_host": MARKETPLACE_BASE_URL,
            }
            if status != 200:
                state.batches_failed += 1
                record["response_body"] = raw_text
                record["error"] = True
                state.raw_records.append(record)
                state.api_errors.append({
                    "warehouseId": wh_id,
                    "batch_index": batch_idx,
                    "http_status": status,
                    "response_body": raw_text,
                    "endpoint": record["endpoint"],
                })
                for cid in batch:
                    state.chrt_wh_status[(cid, wh_id, chrt_to_nmid.get(cid, 0))] = StockStatus.API_GAP
                continue

            state.batches_ok += 1
            items = _parse_stock_items(payload)
            returned_chrts: set[int] = set()
            for item in items:
                chrt = _read_int(item, "chrtId", "chrt_id", "chrtID")
                if not chrt:
                    continue
                returned_chrts.add(chrt)
                amt = _read_int(item, "amount", "quantity", "stock") or 0
                nmid = chrt_to_nmid.get(chrt, 0)
                st = StockStatus.POSITIVE_STOCK if amt > 0 else StockStatus.CONFIRMED_ZERO
                key = (chrt, wh_id, nmid)
                state.chrt_wh_status[key] = st
                state.chrt_wh_amount[key] = amt
                record.setdefault("stocks", []).append({
                    "chrtId": chrt,
                    "nmID": nmid,
                    "amount": amt,
                    "status": st.value,
                })
            for cid in batch:
                key = (cid, wh_id, chrt_to_nmid.get(cid, 0))
                if key not in state.chrt_wh_status:
                    state.chrt_wh_status[key] = StockStatus.CHRTID_NOT_RETURNED
            state.raw_records.append(record)
            await asyncio.sleep(0.35)

    return state


async def _fetch_fbo_all(
    analytics_adapter: Any,
    nmids: list[int],
) -> tuple[dict[int, int], dict[str, Any]]:
    """FBO через Analytics wb-warehouses (READ_ONLY)."""
    meta: dict[str, Any] = {
        "endpoint": FBO_ENDPOINT,
        "collected": False,
        "nmids_requested": len(nmids),
    }
    if not nmids:
        meta["status"] = "skipped_empty_assortment"
        return {}, meta

    try:
        client = await analytics_adapter.auth_client_handler.get_proxy_client(analytics_adapter)
        body = {"nmIds": nmids, "limit": 250000, "offset": 0}
        http = client.get_async_httpx_client()
        response = await http.request(
            method="post",
            url="/api/analytics/v1/stocks-report/wb-warehouses",
            json=body,
            headers={"Content-Type": "application/json"},
        )
        meta["http_status"] = response.status_code
        if response.status_code != 200:
            meta["status"] = "FBO_GAP"
            meta["error_body"] = response.text[:2000]
            return {}, meta

        payload = response.json()
        rows: list[dict[str, Any]] = []
        if isinstance(payload, dict):
            data = payload.get("data") or payload.get("stocks") or payload.get("items")
            if isinstance(data, list):
                rows = [jsonable(x) if not isinstance(x, dict) else x for x in data]
            elif isinstance(payload.get("data"), dict):
                inner = payload["data"].get("items") or payload["data"].get("stocks")
                if isinstance(inner, list):
                    rows = [jsonable(x) if not isinstance(x, dict) else x for x in inner]
        elif isinstance(payload, list):
            rows = [jsonable(x) if not isinstance(x, dict) else x for x in payload]

        fbo_by_nmid: dict[int, int] = defaultdict(int)
        for row in rows:
            if not isinstance(row, dict):
                continue
            nmid = _read_int(row, "nmId", "nm_id", "nmid")
            qty = _read_int(row, "quantity", "amount", "stock") or 0
            if nmid:
                fbo_by_nmid[nmid] += qty
        meta["collected"] = True
        meta["status"] = "OK"
        meta["row_count"] = len(rows)
        meta["nmids_with_fbo_rows"] = len(fbo_by_nmid)
        return dict(fbo_by_nmid), meta
    except Exception as exc:  # noqa: BLE001
        meta["status"] = "FBO_GAP"
        meta["error"] = str(exc)[:500]
        return {}, meta


def _aggregate(
    state: CollectState,
    identity_rows: list[dict[str, Any]],
    sku_meta: dict[int, dict[str, Any]],
    warehouses: list[dict[str, Any]],
    fbo_by_nmid: dict[int, int],
    fbo_meta: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """CHRT-level, SKU×warehouse, SKU-total агрегаты."""
    wh_names = {int(w["warehouseId"]): w.get("name") for w in warehouses}

    chrt_level: list[dict[str, Any]] = []
    for (chrt, wh_id, nmid), st in sorted(state.chrt_wh_status.items()):
        amt = state.chrt_wh_amount.get((chrt, wh_id, nmid))
        chrt_level.append({
            "nmID": nmid,
            "chrtId": chrt,
            "warehouseId": wh_id,
            "warehouseName": wh_names.get(wh_id),
            "amount": amt if st != StockStatus.API_GAP else None,
            "stock_status": st.value,
        })

    sku_wh: dict[tuple[int, int], int] = defaultdict(int)
    for (chrt, wh_id, nmid), st in state.chrt_wh_status.items():
        if st in (StockStatus.CONFIRMED_ZERO, StockStatus.POSITIVE_STOCK):
            sku_wh[(nmid, wh_id)] += state.chrt_wh_amount.get((chrt, wh_id, nmid), 0)

    by_wh: list[dict[str, Any]] = []
    for (nmid, wh_id), total in sorted(sku_wh.items()):
        by_wh.append({
            "nmID": nmid,
            "vendorCode": sku_meta.get(nmid, {}).get("vendorCode"),
            "warehouseId": wh_id,
            "warehouseName": wh_names.get(wh_id),
            "FBS_STOCK": total,
        })

    nmids = sorted({r["nmID"] for r in identity_rows})
    sku_totals: list[dict[str, Any]] = []
    for nmid in nmids:
        wh_stock = {wh_id: amt for (n, wh_id), amt in sku_wh.items() if n == nmid}
        fbs_total = sum(wh_stock.values())
        wh_with_stock = sum(1 for v in wh_stock.values() if v > 0)
        meta = sku_meta.get(nmid, {})
        fbo = fbo_by_nmid.get(nmid) if fbo_meta.get("collected") else None
        row: dict[str, Any] = {
            "nmID": nmid,
            "vendorCode": meta.get("vendorCode"),
            "subjectName": meta.get("subjectName"),
            "subjectID": meta.get("subjectID"),
            "FBS_STOCK_TOTAL": fbs_total,
            "number_of_warehouses_with_stock": wh_with_stock,
            "stock_distribution": wh_stock,
        }
        if fbo_meta.get("collected"):
            row["FBO_STOCK"] = fbo or 0
            row["FBS_STOCK"] = fbs_total
            row["TOTAL_SELLABLE_KNOWN"] = (fbo or 0) + fbs_total
        else:
            row["FBO_STOCK"] = "currently_not_collected"
            row["TOTAL_SELLABLE_KNOWN"] = f"FBS={fbs_total}; FBO=currently_not_collected"
        sku_totals.append(row)

    return chrt_level, by_wh, sku_totals


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in fieldnames})


def _coverage_stats(
    state: CollectState,
    chrt_ids: list[int],
    warehouses: list[dict[str, Any]],
) -> dict[str, Any]:
    expected = len(chrt_ids) * len(warehouses)
    ok_statuses = {StockStatus.CONFIRMED_ZERO, StockStatus.POSITIVE_STOCK, StockStatus.CHRTID_NOT_RETURNED}
    covered = sum(1 for st in state.chrt_wh_status.values() if st in ok_statuses)
    gaps = sum(1 for st in state.chrt_wh_status.values() if st == StockStatus.API_GAP)
    return {
        "expected_chrt_warehouse_pairs": expected,
        "covered_pairs": covered,
        "api_gap_pairs": gaps,
        "coverage_pct": round(100.0 * covered / expected, 2) if expected else 0.0,
        "batches_total": state.batches_total,
        "batches_ok": state.batches_ok,
        "batches_failed": state.batches_failed,
        "retry_count": state.retry_count,
    }


async def run_snapshot(output_dir: Path) -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis

    started = _msk_now()
    pkg = output_dir / PACKAGE
    pkg.mkdir(parents=True, exist_ok=True)

    app_config = AppConfig.create()
    rc = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=rc.host, port=rc.port, db=rc.db, password=rc.password, decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx_handler = HttpxClientHandler()
    await httpx_handler.init()

    try:
        access = await get_access_for_wb_cabinet(SHOP_ID)
        if access is None:
            fail = {
                "CHECKED_AT_MSK": started.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "MARKETPLACE_SCOPE": "FAIL",
                "errors": [{"response_body": "cabinet access not found"}],
                "NO_WRITES": "CONFIRMED",
            }
            (pkg / "summary.json").write_text(json.dumps(fail, ensure_ascii=False, indent=2), encoding="utf-8")
            return fail

        mp_token, probe_errors = await _resolve_marketplace_token(access)
        if not mp_token:
            fail = {
                "CHECKED_AT_MSK": started.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "COLLECTION_STARTED_AT_MSK": started.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "MARKETPLACE_SCOPE": "FAIL",
                "WAREHOUSE_ERRORS": probe_errors,
                "NO_WRITES": "CONFIRMED",
            }
            (pkg / "summary.json").write_text(json.dumps(fail, ensure_ascii=False, indent=2), encoding="utf-8")
            (pkg / "collect_report.json").write_text(
                json.dumps({"scope_check": probe_errors, "stopped": True}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return fail

        status, raw_text, wh_raw, _ = await _marketplace_request_with_retry(
            mp_token, "GET", "/api/v3/warehouses",
        )
        if status != 200:
            fail = {
                "CHECKED_AT_MSK": started.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "MARKETPLACE_SCOPE": "FAIL",
                "WAREHOUSE_ERRORS": [{
                    "endpoint": "GET /api/v3/warehouses",
                    "http_status": status,
                    "response_body": raw_text,
                    "api_host": MARKETPLACE_BASE_URL,
                }],
                "NO_WRITES": "CONFIRMED",
            }
            (pkg / "summary.json").write_text(json.dumps(fail, ensure_ascii=False, indent=2), encoding="utf-8")
            return fail

        warehouses = _parse_warehouses(wh_raw)
        hub = WBManagerHubFactory(
            httpx_client_handler=httpx_handler, redis_client_wrapper=redis_wrap,
        ).get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager

        budget = ApiCallBudget(max_seconds=3600.0, max_api_calls=50_000)
        from scripts.wb_api_readonly_ops.collect.raw_store import RawStore

        store = RawStore(output_dir / "_raw_cards")
        _, cards = await collect_cards(dm, store=store, budget=budget, page_limit=100)

        identity_rows, sku_meta = _build_identity_map(cards)
        chrt_to_nmid: dict[int, int] = {r["chrtId"]: r["nmID"] for r in identity_rows}
        chrt_ids = sorted(chrt_to_nmid)

        fbo_by_nmid: dict[int, int] = {}
        fbo_meta: dict[str, Any] = {"status": "FBO_GAP"}
        try:
            analytics_client = dm._analytics_manager._AnalyticsManager__wb_api_client
            analytics = analytics_client.sales_funnel_adapter
            nmids_all = sorted({r["nmID"] for r in identity_rows})
            fbo_by_nmid, fbo_meta = await _fetch_fbo_all(analytics, nmids_all)
        except Exception as exc:  # noqa: BLE001
            fbo_meta = {"status": "FBO_GAP", "error": str(exc)[:500]}

        state = await _collect_fbs_stocks(mp_token, warehouses, chrt_ids, chrt_to_nmid)
        chrt_level, by_wh, sku_totals = _aggregate(
            state, identity_rows, sku_meta, warehouses, fbo_by_nmid, fbo_meta,
        )
        coverage = _coverage_stats(state, chrt_ids, warehouses)
        finished = _msk_now()

        nmids_positive = sum(1 for r in sku_totals if (r.get("FBS_STOCK_TOTAL") or 0) > 0)
        nmids_zero = sum(1 for r in sku_totals if (r.get("FBS_STOCK_TOTAL") or 0) == 0)
        total_fbs_units = sum(int(r.get("FBS_STOCK_TOTAL") or 0) for r in sku_totals)

        cpc_matrix = []
        sku_by_nmid = {r["nmID"]: r for r in sku_totals}
        for nmid in CPC_CANDIDATE_NMIDS:
            row = sku_by_nmid.get(nmid)
            cpc_matrix.append({
                "nmID": nmid,
                "vendorCode": (sku_meta.get(nmid) or {}).get("vendorCode"),
                "FBS_STOCK_TOTAL": row.get("FBS_STOCK_TOTAL") if row else "NOT_IN_ASSORTMENT",
                "FBO_STOCK": row.get("FBO_STOCK") if row else "NOT_IN_ASSORTMENT",
                "TOTAL_SELLABLE_KNOWN": row.get("TOTAL_SELLABLE_KNOWN") if row else "NOT_IN_ASSORTMENT",
                "stock_distribution": row.get("stock_distribution") if row else {},
            })

        _write_csv(
            pkg / "identity_map.csv",
            identity_rows,
            ["nmID", "vendorCode", "subjectName", "subjectID", "chrtId", "techSize", "wbSize", "skus"],
        )
        _write_csv(
            pkg / "fbs_stock_full.csv",
            chrt_level,
            ["nmID", "chrtId", "warehouseId", "warehouseName", "amount", "stock_status"],
        )
        _write_csv(
            pkg / "fbs_stock_by_warehouse.csv",
            by_wh,
            ["nmID", "vendorCode", "warehouseId", "warehouseName", "FBS_STOCK"],
        )

        with (pkg / "fbs_stock_raw.jsonl").open("w", encoding="utf-8") as f:
            for rec in state.raw_records:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

        data_gaps = [e for e in state.api_errors]
        if not fbo_meta.get("collected"):
            data_gaps.append({"type": "FBO", **fbo_meta})

        operational_signal = "SUITABLE"
        if coverage["coverage_pct"] < 95:
            operational_signal = "PARTIAL_COVERAGE"
        if state.batches_failed > 0:
            operational_signal = "PARTIAL_COVERAGE"
        if coverage["coverage_pct"] < 50:
            operational_signal = "NOT_SUITABLE_FOR_LAUNCH"

        summary = {
            "CHECKED_AT_MSK": finished.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "COLLECTION_STARTED_AT_MSK": started.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "COLLECTION_FINISHED_AT_MSK": finished.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "MARKETPLACE_SCOPE": "PASS",
            "source_endpoints": {
                "fbs_warehouses": "GET https://marketplace-api.wildberries.ru/api/v3/warehouses",
                "fbs_stocks": "POST https://marketplace-api.wildberries.ru/api/v3/stocks/{warehouseId}",
                "assortment": "POST /content/v2/get/cards/list",
                "fbo": FBO_ENDPOINT if fbo_meta.get("collected") else "not_collected",
            },
            "assortment_nmids_total": len({r["nmID"] for r in identity_rows}),
            "assortment_chrtids_total": len(chrt_ids),
            "warehouses_total": len(warehouses),
            "nmids_with_positive_fbs": nmids_positive,
            "nmids_with_zero_fbs": nmids_zero,
            "total_fbs_units": total_fbs_units,
            "coverage_pct": coverage["coverage_pct"],
            "coverage_detail": coverage,
            "errors_gaps": data_gaps,
            "CPC_CANDIDATE_STOCK_MATRIX": cpc_matrix,
            "operational_launch_signal": operational_signal,
            "reliability_note": (
                "FBS stock = API-reported seller warehouse stock at collection time; "
                "not verified physical warehouse count."
            ),
            "NO_WRITES": "CONFIRMED",
        }

        collect_report = {
            "CHECKED_AT_MSK": summary["CHECKED_AT_MSK"],
            "collection_window": {
                "started": summary["COLLECTION_STARTED_AT_MSK"],
                "finished": summary["COLLECTION_FINISHED_AT_MSK"],
            },
            "SELLER_WAREHOUSES": warehouses,
            "assortment_cards": len(cards),
            "identity_rows": len(identity_rows),
            "warehouse_coverage": coverage,
            "api_errors": state.api_errors,
            "retry_count": state.retry_count,
            "fbo_collection": fbo_meta,
            "response_limitations": {
                "chrt_batch_size": CHRT_BATCH_SIZE,
                "max_retries_per_batch": MAX_RETRIES,
                "retry_statuses": sorted(RETRY_STATUSES),
            },
            "operational_launch_signal": operational_signal,
        }

        (pkg / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
        )
        (pkg / "collect_report.json").write_text(
            json.dumps(collect_report, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
        )

        sku_totals_path = pkg / "sku_totals.json"
        sku_totals_path.write_text(
            json.dumps(sku_totals, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
        )

        return {
            **summary,
            "ABSOLUTE_ARTIFACT_PATH": str(pkg.resolve()),
            "DATA_GAPS": data_gaps,
        }
    finally:
        await httpx_handler.shutdown()
        await redis_raw.aclose()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A1 full FBS stock snapshot (READ_ONLY)")
    ap.add_argument("--output-dir", default=".tmp/a1_full_fbs_stock")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()

    payload = asyncio.run(run_snapshot(root))
    chat_summary = {
        "CHECKED_AT_MSK": payload.get("CHECKED_AT_MSK"),
        "MARKETPLACE_SCOPE": payload.get("MARKETPLACE_SCOPE"),
        "WAREHOUSES_TOTAL": payload.get("warehouses_total"),
        "ASSORTMENT_NMIDS_TOTAL": payload.get("assortment_nmids_total"),
        "NMIDS_WITH_POSITIVE_FBS": payload.get("nmids_with_positive_fbs"),
        "TOTAL_FBS_UNITS": payload.get("total_fbs_units"),
        "COVERAGE": payload.get("coverage_pct"),
        "CPC_CANDIDATE_STOCK_MATRIX": payload.get("CPC_CANDIDATE_STOCK_MATRIX"),
        "DATA_GAPS": payload.get("DATA_GAPS") or payload.get("errors_gaps") or payload.get("WAREHOUSE_ERRORS"),
        "ABSOLUTE_ARTIFACT_PATH": payload.get("ABSOLUTE_ARTIFACT_PATH"),
        "NO_WRITES": payload.get("NO_WRITES", "CONFIRMED"),
    }
    print(json.dumps(chat_summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

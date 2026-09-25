"""READ_ONLY: A1 CPC target stock check via WB Analytics wb-warehouses.

POST /api/analytics/v1/stocks-report/wb-warehouses для nmID 837395782 и 180148471.
Также корректирует WB status semantics (9=active, 11=paused) для adv 34210859.
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
PACKAGE = "A1-CPC-TARGET-STOCK-CHECK"

TARGET_NMIDS = (837395782, 180148471)
ADV_34210859 = 34210859

WB_STATUS_SEMANTICS = {
    9: "ACTIVE",
    11: "PAUSED",
    7: "COMPLETED",
    8: "DECLINED",
    4: "READY_TO_LAUNCH",
}

ENDPOINT = "POST /api/analytics/v1/stocks-report/wb-warehouses"
FRESHNESS_NOTE = "WB docs: data updated every 30 minutes"


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _aggregate_stock(rows: list[dict[str, Any]], nmid: int) -> dict[str, Any]:
  """Агрегировать FBO stock по nmID из сырых строк WB."""
  sku_rows = [r for r in rows if _read_int(r, "nmId", "nm_id", "nmid") == nmid]
  by_wh: dict[int, dict[str, Any]] = {}
  total_qty = 0
  total_in_way_to = 0
  total_in_way_from = 0
  raw_rows: list[dict[str, Any]] = []

  for r in sku_rows:
    wh_id = _read_int(r, "warehouseId", "warehouse_id")
    qty = _read_int(r, "quantity", "amount", "stock") or 0
    in_to = _read_int(r, "inWayToClient", "in_way_to_client") or 0
    in_from = _read_int(r, "inWayFromClient", "in_way_from_client") or 0
    total_qty += qty
    total_in_way_to += in_to
    total_in_way_from += in_from
    raw_rows.append(dict(r))
    bucket = by_wh.setdefault(
      wh_id,
      {
        "warehouse_id": wh_id,
        "warehouse_name": r.get("warehouseName") or r.get("warehouse_name"),
        "region_name": r.get("regionName") or r.get("region_name"),
        "quantity": 0,
        "inWayToClient": 0,
        "inWayFromClient": 0,
        "rows": [],
      },
    )
    bucket["quantity"] += qty
    bucket["inWayToClient"] += in_to
    bucket["inWayFromClient"] += in_from
    bucket["rows"].append(r)

  return {
    "nmID": nmid,
    "source": ENDPOINT,
    "total_wb_stock_quantity": total_qty,
    "total_inWayToClient": total_in_way_to,
    "total_inWayFromClient": total_in_way_from,
    "stock_by_warehouse": sorted(by_wh.values(), key=lambda x: -int(x.get("quantity") or 0)),
    "raw_row_count": len(raw_rows),
    "raw_rows": raw_rows,
  }


async def _fetch_wb_warehouses_stock(adapter: Any, nmids: list[int]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  """Вызов POST /api/analytics/v1/stocks-report/wb-warehouses (READ_ONLY)."""
  checked = _msk_now()
  client = await adapter.auth_client_handler.get_proxy_client(adapter)
  body = {"nmIds": nmids, "limit": 250000, "offset": 0}
  http = client.get_async_httpx_client()
  response = await http.request(
    method="post",
    url="/api/analytics/v1/stocks-report/wb-warehouses",
    json=body,
    headers={"Content-Type": "application/json"},
  )
  meta = {
    "endpoint": ENDPOINT,
    "http_status": response.status_code,
    "checked_at_msk": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
    "request_body": body,
    "freshness": FRESHNESS_NOTE,
    "response_headers_date": response.headers.get("date"),
  }
  if response.status_code != 200:
    meta["error_body"] = response.text[:2000]
    return [], meta

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

  normalized: list[dict[str, Any]] = []
  for row in rows:
    if isinstance(row, dict):
      normalized.append(row)
  meta["raw_response_top_keys"] = list(payload.keys()) if isinstance(payload, dict) else ["list"]
  meta["row_count"] = len(normalized)
  return normalized, meta


async def _fetch_adv_34210859(pm: Any) -> dict[str, Any]:
  camps = list(await pm.get_adverts_v2_by_ids([ADV_34210859]) or [])
  if not camps:
    return {"adv_id": ADV_34210859, "status": "NOT_FOUND"}
  c = jsonable(camps[0])
  if not isinstance(c, dict):
    return {"adv_id": ADV_34210859, "status": "PARSE_ERROR"}
  wb_status = _read_int(c, "status")
  settings = c.get("settings") if isinstance(c.get("settings"), dict) else {}
  budget = None
  try:
    b = await pm.get_campaign_budget(ADV_34210859)
    bd = jsonable(b)
    budget = bd if isinstance(bd, dict) else {"total": getattr(b, "total", None)}
  except Exception as exc:  # noqa: BLE001
    budget = {"error": str(exc)[:300]}

  semantic = WB_STATUS_SEMANTICS.get(wb_status, f"UNKNOWN_{wb_status}")
  return {
    "adv_id": ADV_34210859,
    "wb_status_code": wb_status,
    "WB_STATUS": semantic,
    "34210859_WB_STATUS": "PAUSED" if wb_status == 11 else semantic,
    "payment_type": settings.get("payment_type") or settings.get("paymentType"),
    "placements": settings.get("placements"),
    "nm_settings": c.get("nm_settings") or c.get("nmSettings"),
    "budget": budget,
    "status_semantics_note": "Corrected: WB status 9=ACTIVE, 11=PAUSED (prior preflight mislabeled 11 as active)",
  }


def _safety_verdicts(stock837: dict[str, Any], stock180: dict[str, Any], adv342: dict[str, Any]) -> dict[str, str]:
  qty837 = stock837.get("total_wb_stock_quantity")
  qty180 = stock180.get("total_wb_stock_quantity")
  paused = adv342.get("wb_status_code") == 11

  v837 = "CONDITIONAL"
  if not paused:
    v837 = "NO"
  elif qty837 is not None and qty837 <= 0:
    v837 = "CONDITIONAL"
  elif paused and (qty837 is None or qty837 > 0):
    v837 = "YES"

  v180 = "YES"
  if qty180 is not None and qty180 <= 0:
    v180 = "CONDITIONAL"

  return {
    "837395782_CPC_SAFETY_AFTER_CORRECTION": v837,
    "180148471_CPC_SAFETY": v180,
  }


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
    hub = WBManagerHubFactory(httpx_client_handler=httpx, redis_client_wrapper=redis_wrap).get_wb_manager_hub(SHOP_ID)
    dm = hub.wb_data_manager
    pm = dm.promotion_manager
    analytics_client = dm._analytics_manager._AnalyticsManager__wb_api_client
    analytics = analytics_client.sales_funnel_adapter

    rows, api_meta = await _fetch_wb_warehouses_stock(analytics, list(TARGET_NMIDS))
    stock837 = _aggregate_stock(rows, 837395782)
    stock180 = _aggregate_stock(rows, 180148471)
    stock837["api_meta"] = api_meta
    stock180["api_meta"] = api_meta

    adv342 = await _fetch_adv_34210859(pm)
    safety = _safety_verdicts(stock837, stock180, adv342)

    return {
      "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
      "STOCK_837395782": stock837,
      "STOCK_180148471": stock180,
      "34210859_WB_STATUS": adv342.get("34210859_WB_STATUS") or adv342.get("WB_STATUS"),
      "34210859_DETAIL": adv342,
      **safety,
      "WB_STATUS_SEMANTICS_CORRECTION": WB_STATUS_SEMANTICS,
      "NO_WRITES": "CONFIRMED",
    }
  finally:
    await httpx.shutdown()
    await redis_raw.aclose()


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--output-dir", default=".tmp/a1_cpc_target_stock_check")
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
    k: payload[k]
    for k in (
      "CHECKED_AT_MSK", "STOCK_837395782", "STOCK_180148471",
      "34210859_WB_STATUS", "837395782_CPC_SAFETY_AFTER_CORRECTION",
      "180148471_CPC_SAFETY", "NO_WRITES",
    )
  }
  summary["STOCK_837395782"] = {
    "total_wb_stock_quantity": payload["STOCK_837395782"].get("total_wb_stock_quantity"),
    "warehouse_count": len(payload["STOCK_837395782"].get("stock_by_warehouse", [])),
    "freshness": payload["STOCK_837395782"].get("api_meta", {}).get("freshness"),
  }
  summary["STOCK_180148471"] = {
    "total_wb_stock_quantity": payload["STOCK_180148471"].get("total_wb_stock_quantity"),
    "warehouse_count": len(payload["STOCK_180148471"].get("stock_by_warehouse", [])),
    "freshness": payload["STOCK_180148471"].get("api_meta", {}).get("freshness"),
  }
  print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
  return 0


if __name__ == "__main__":
  sys.exit(main())

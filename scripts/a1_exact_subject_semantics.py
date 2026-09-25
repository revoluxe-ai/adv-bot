"""READ_ONLY: comparative semantic evidence для exact-subject SKU (subjectID=4069).

Targeted PG campaign map + fullstats prefilter + normquery/keywords/minus/bids.
Без full-cabinet keyword export.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _nm_rows, _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-EXACT-SUBJECT-SEMANTICS"

EXACT_NMIDS = [837342085, 837391003, 837395782, 837407440, 837407441, 994300104]
TARGET_SUBJECT_ID = 4069
TARGET_SUBJECT_NAME = "Подушки для растяжки"

PERIOD_FROM = date(2026, 8, 5)
PERIOD_TO = date(2026, 9, 1)

SEMANTICS_FIELDS = [
    "nmid",
    "adv_id",
    "date",
    "query_text",
    "normalized_query",
    "cluster",
    "views",
    "clicks",
    "spend",
    "carts",
    "orders",
    "bid",
    "negative_state",
    "whitelist_state",
    "source",
]

INDEX_FIELDS = [
    "query_or_cluster",
    "nmids_count",
    "nmids",
    "campaigns_count",
    "total_views",
    "total_clicks",
    "total_spend",
    "total_orders",
    "sources",
]

HARD_STATUS_LABEL = {
    0: "blacklist",
    1: "in_test",
    2: "whitelist",
    3: "turned_off",
    4: "fixed_phrase",
}


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap() -> None:
    from scripts import ch_a1_evidence as evidence

    u, p = os.environ.get("POSTGRES_USER"), os.environ.get("POSTGRES_PASSWORD")
    if u and p:
        evidence._PG_CREDENTIALS = u, p
    h = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get("POSTGRES_REPLICA_HOST")
    if h:
        evidence.PG_EXTERNAL_HOST = h
    pt = os.environ.get("POSTGRES_PORT")
    if pt:
        evidence.PG_EXTERNAL_PORT = int(pt)


def _parse_nmids(raw: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", str(raw or ""))]


def _normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _load_pg_adv(root: Path) -> list[dict[str, str]]:
    from scripts import ch_a1_evidence as evidence

    staging = root / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    out = staging / "pg_adv.csv"
    cols = "a.id, a.adv_id, a._search_adv_id, a.type, a.name, a.nmids, a.wb_bid_type"
    q = (
        f"SELECT {cols} FROM public.advsetting a "
        f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}'"
    )
    st = evidence.run_pg_query(_pg_db(), q, out, root / "sql" / "pg_adv.sql", csv_output=True)
    if not st["success"]:
        raise RuntimeError(st["stderr"])
    with out.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_keywords(root: Path, adv_setting_ids: set[int]) -> list[dict[str, str]]:
    if not adv_setting_ids:
        return []
    from scripts import ch_a1_evidence as evidence

    ids_sql = ", ".join(str(i) for i in sorted(adv_setting_ids))
    out = root / "staging" / "keywordsetting.csv"
    q = f"SELECT * FROM public.keywordsetting WHERE adv_setting_id IN ({ids_sql})"
    st = evidence.run_pg_query(_pg_db(), q, out, root / "sql" / "keywordsetting.sql", csv_output=True)
    if not st["success"]:
        return []
    with out.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _map_nmid_campaigns(pg: list[dict[str, str]]) -> tuple[dict[int, list[dict[str, Any]]], dict[int, int]]:
    """nmid -> campaign rows; adv_id -> adv_setting_id."""
    by_nmid: dict[int, list[dict[str, Any]]] = defaultdict(list)
    adv_to_setting: dict[int, int] = {}
    exact_set = set(EXACT_NMIDS)

    for row in pg:
        adv = _read_int(row, "adv_id")
        setting_id = _read_int(row, "id")
        if not adv:
            continue
        adv_to_setting[adv] = setting_id
        nmids = _parse_nmids(row.get("nmids") or "")
        search_adv = _read_int(row, "_search_adv_id")
        if search_adv:
            adv_to_setting[search_adv] = setting_id
        for nmid in nmids:
            if nmid not in exact_set:
                continue
            entry = {
                "adv_id": adv,
                "search_adv_id": search_adv,
                "adv_setting_id": setting_id,
                "name": row.get("name"),
                "wb_bid_type": row.get("wb_bid_type"),
            }
            by_nmid[nmid].append(entry)
            if search_adv:
                by_nmid[nmid].append(
                    {
                        **entry,
                        "adv_id": search_adv,
                        "is_search_leg": True,
                    }
                )

    for nmid in EXACT_NMIDS:
        seen: set[int] = set()
        deduped: list[dict[str, Any]] = []
        for c in by_nmid.get(nmid, []):
            aid = c["adv_id"]
            if aid in seen:
                continue
            seen.add(aid)
            deduped.append(c)
        by_nmid[nmid] = deduped
    return dict(by_nmid), adv_to_setting


def _candidate_pairs(by_nmid: dict[int, list[dict[str, Any]]]) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for nmid, camps in by_nmid.items():
        for c in camps:
            key = (c["adv_id"], nmid)
            if key not in seen:
                seen.add(key)
                pairs.append(key)
    return pairs


def _in_period(day: str) -> bool:
    try:
        d = date.fromisoformat(day[:10])
    except ValueError:
        return False
    return PERIOD_FROM <= d <= PERIOD_TO


def _semantics_row(
    *,
    nmid: int,
    adv_id: int,
    day: str,
    query_text: str,
    views: int = 0,
    clicks: int = 0,
    spend: float = 0.0,
    carts: int = 0,
    orders: int = 0,
    bid: Any = "",
    negative_state: str = "",
    whitelist_state: str = "",
    source: str,
) -> dict[str, Any]:
    nq = _normalize_query(query_text)
    return {
        "nmid": nmid,
        "adv_id": adv_id,
        "date": day,
        "query_text": query_text,
        "normalized_query": nq,
        "cluster": query_text,
        "views": views,
        "clicks": clicks,
        "spend": round(float(spend), 2) if spend else 0,
        "carts": carts,
        "orders": orders,
        "bid": bid if bid is not None else "",
        "negative_state": negative_state,
        "whitelist_state": whitelist_state,
        "source": source,
    }


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def _build_query_index(semantics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for row in semantics:
        key = row.get("normalized_query") or row.get("query_text") or ""
        if not key:
            continue
        g = groups.setdefault(
            key,
            {
                "query_or_cluster": row.get("cluster") or row.get("query_text") or key,
                "nmids": set(),
                "campaigns": set(),
                "total_views": 0,
                "total_clicks": 0,
                "total_spend": 0.0,
                "total_orders": 0,
                "sources": set(),
            },
        )
        g["nmids"].add(int(row["nmid"]))
        g["campaigns"].add(int(row["adv_id"]))
        g["total_views"] += int(row.get("views") or 0)
        g["total_clicks"] += int(row.get("clicks") or 0)
        g["total_spend"] += float(row.get("spend") or 0)
        g["total_orders"] += int(row.get("orders") or 0)
        if row.get("source"):
            g["sources"].add(str(row["source"]))
    out: list[dict[str, Any]] = []
    for g in sorted(groups.values(), key=lambda x: -x["total_spend"]):
        out.append(
            {
                "query_or_cluster": g["query_or_cluster"],
                "nmids_count": len(g["nmids"]),
                "nmids": ";".join(str(x) for x in sorted(g["nmids"])),
                "campaigns_count": len(g["campaigns"]),
                "total_views": g["total_views"],
                "total_clicks": g["total_clicks"],
                "total_spend": round(g["total_spend"], 2),
                "total_orders": g["total_orders"],
                "sources": ";".join(sorted(g["sources"])),
            }
        )
    return out


async def _prefilter_pairs_with_spend(
    pm: Any,
    pairs: list[tuple[int, int]],
) -> tuple[set[tuple[int, int]], dict[int, dict[str, float]]]:
    """Targeted fullstats только для candidate adv_ids."""
    adv_ids = sorted({a for a, _ in pairs})
    if not adv_ids:
        return set(), {}

    dates: list[date] = []
    d = PERIOD_FROM
    while d <= PERIOD_TO:
        dates.append(d)
        d += timedelta(days=1)
    stats_raw = list(await pm.get_full_adv_stat(adv_ids, dates) or [])
    raw_items = [jsonable(x) for x in stats_raw if isinstance(jsonable(x), dict)]
    _, day_rows = _nm_rows(raw_items)

    adv_totals: dict[int, dict[str, float]] = defaultdict(lambda: {"views": 0.0, "spend": 0.0})
    for row in day_rows:
        if not _in_period(row.get("date", "")):
            continue
        adv_id = _read_int(row, "advert_id")
        adv_totals[adv_id]["views"] += _read_int(row, "day_views")
        adv_totals[adv_id]["spend"] += _read_float(row, "day_spend")

    active: set[tuple[int, int]] = set()
    for adv_id, nmid in pairs:
        t = adv_totals.get(adv_id, {})
        if t.get("views", 0) > 0 or t.get("spend", 0) > 0:
            active.add((adv_id, nmid))
    return active, dict(adv_totals)


async def _collect_normquery_period(
    pm: Any,
    active_pairs: set[tuple[int, int]],
) -> list[dict[str, Any]]:
    """Normquery stats за весь период (≤30 дней — один API batch)."""
    from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
        GetNormqueryStatsCommand,
        GetNormqueryStatsCommandBatchForAdv,
    )

    adapter = pm._client.normquery_stats_adapter
    batches = [
        GetNormqueryStatsCommandBatchForAdv(adv_id=adv_id, nmid=nmid)
        for adv_id, nmid in sorted(active_pairs)
    ]
    if not batches:
        return []

    rows: list[dict[str, Any]] = []
    command = GetNormqueryStatsCommand(
        date_from=PERIOD_FROM,
        date_to=PERIOD_TO,
        batchs=batches,
    )
    try:
        dtos = await adapter.get_adv_v0_normquery_stats(command)
        for dto in dtos or []:
            dto_dict = jsonable(dto.model_dump() if hasattr(dto, "model_dump") else dto)
            adv_id = _read_int(dto_dict, "adv_id")
            nmid = _read_int(dto_dict, "nmid", "nm_id")
            for stat in dto_dict.get("stats") or []:
                if not isinstance(stat, dict):
                    continue
                q = str(stat.get("norm_query") or "")
                rows.append(
                    _semantics_row(
                        nmid=nmid,
                        adv_id=adv_id,
                        day=f"{PERIOD_FROM.isoformat()}..{PERIOD_TO.isoformat()}",
                        query_text=q,
                        views=_read_int(stat, "views"),
                        clicks=_read_int(stat, "clicks"),
                        spend=_read_float(stat, "spend"),
                        carts=_read_int(stat, "add_to_cart", "atbs"),
                        orders=_read_int(stat, "orders"),
                        source="POST /adv/v0/normquery/stats",
                    )
                )
    except Exception as exc:  # noqa: BLE001
        rows.append(
            _semantics_row(
                nmid=0,
                adv_id=0,
                day=f"{PERIOD_FROM.isoformat()}..{PERIOD_TO.isoformat()}",
                query_text="",
                source=f"normquery_stats_error:{str(exc)[:200]}",
            )
        )
    return rows


async def _collect_cluster_states(
    pm: Any,
    active_pairs: set[tuple[int, int]],
) -> tuple[list[dict[str, Any]], dict[tuple[int, int, str], int]]:
    from app.core.mp.wb.api.adapter.promotion_client.minus_phrases.get_adv_v0_normquery_get_minus import (
        GetMinusPhrasesCommand,
    )
    from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
    from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
        V0GetNormQueryBidsRequest,
        V0GetNormQueryBidsRequestItem,
    )
    from app.core.mp.wb.api.generated.promotion.v4.marketing_and_promotions_client.marketing_and_promotions_client.api.search_clusters.post_adv_v0_normquery_list import (
        asyncio_detailed as normquery_list_async,
    )
    from app.core.mp.wb.api.generated.promotion.v4.marketing_and_promotions_client.marketing_and_promotions_client.models import (
        V0GetNormQueryListRequest,
        V0GetNormQueryListRequestItem,
    )

    rows: list[dict[str, Any]] = []
    bid_map: dict[tuple[int, int, str], int] = {}
    client = pm._client
    minus_adapter = client.minus_phrases_adapter
    bids_adapter = client.normquery_bids_adapter

    list_items = [
        V0GetNormQueryListRequestItem(advert_id=adv_id, nm_id=nmid)
        for adv_id, nmid in sorted(active_pairs)
    ]
    if list_items:
        try:
            stats_adapter = pm._client.normquery_stats_adapter
            http = await stats_adapter.auth_client_handler.get_proxy_client(stats_adapter)
            resp = await with_raise_errors(
                normquery_list_async,
                http,
                body=V0GetNormQueryListRequest(items=list_items),
            )
            parsed = jsonable(resp.parsed)
            for item in (parsed.get("items") if isinstance(parsed, dict) else []) or []:
                if not isinstance(item, dict):
                    continue
                adv_id = _read_int(item, "advertId", "advert_id")
                nmid = _read_int(item, "nmId", "nm_id")
                nq = item.get("normQueries") or item.get("norm_queries") or {}
                if not isinstance(nq, dict):
                    continue
                for state_label, key in (("active", "active"), ("excluded", "excluded")):
                    for q in nq.get(key) or []:
                        if not q:
                            continue
                        rows.append(
                            _semantics_row(
                                nmid=nmid,
                                adv_id=adv_id,
                                day="",
                                query_text=str(q),
                                whitelist_state=state_label,
                                source="POST /adv/v0/normquery/list",
                            )
                        )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                _semantics_row(
                    nmid=0,
                    adv_id=0,
                    day="",
                    query_text="",
                    source=f"normquery_list_error:{str(exc)[:200]}",
                )
            )

    try:
        bid_items = [
            V0GetNormQueryBidsRequestItem(advert_id=adv_id, nm_id=nmid)
            for adv_id, nmid in sorted(active_pairs)
        ]
        if bid_items:
            bid_resp = await bids_adapter.post_adv_v0_normquery_get_bids(
                V0GetNormQueryBidsRequest(items=bid_items),
            )
            for b in bid_resp or []:
                bid_map[(b.advert_id, b.nm_id, _normalize_query(b.norm_query))] = b.bid
    except Exception:
        pass

    for adv_id, nmid in sorted(active_pairs):
        minus_set: set[str] = set()
        try:
            minus_list = await minus_adapter.post_adv_v0_normquery_get_minus(
                GetMinusPhrasesCommand(advert_id=adv_id, nm_id=nmid),
            )
            minus_set = {_normalize_query(m) for m in (minus_list or [])}
        except Exception:
            minus_set = set()
        for q_norm in minus_set:
            if not q_norm:
                continue
            rows.append(
                _semantics_row(
                    nmid=nmid,
                    adv_id=adv_id,
                    day="",
                    query_text=q_norm,
                    negative_state="minus",
                    bid=bid_map.get((adv_id, nmid, q_norm), ""),
                    source="POST /adv/v0/normquery/get-minus",
                )
            )

    return rows, bid_map


def _keyword_rows(
    keywords: list[dict[str, str]],
    by_nmid: dict[int, list[dict[str, Any]]],
    active_pairs: set[tuple[int, int]],
) -> list[dict[str, Any]]:
    pair_setting: dict[tuple[int, int], int] = {}
    for nmid, camps in by_nmid.items():
        for c in camps:
            key = (c["adv_id"], nmid)
            if key in active_pairs and c.get("adv_setting_id"):
                pair_setting[key] = int(c["adv_setting_id"])

    kw_by_setting: dict[int, list[dict[str, str]]] = defaultdict(list)
    for kw in keywords:
        sid = _read_int(kw, "adv_setting_id")
        if sid:
            kw_by_setting[sid].append(kw)

    rows: list[dict[str, Any]] = []
    for (adv_id, nmid), sid in sorted(pair_setting.items()):
        for kw in kw_by_setting.get(sid, []):
            text = str(kw.get("text") or "").strip()
            if not text:
                continue
            hs = _read_int(kw, "hard_status")
            neg = "blacklist" if hs == 0 else ""
            wl = HARD_STATUS_LABEL.get(hs, f"hard_status_{hs}")
            rows.append(
                _semantics_row(
                    nmid=nmid,
                    adv_id=adv_id,
                    day="",
                    query_text=text,
                    negative_state=neg,
                    whitelist_state=wl if hs in (0, 2, 4) else (wl if hs == 1 else ""),
                    source="postgresql.keywordsetting",
                )
            )
    return rows


async def run_collect(
    output_dir: Path,
    pg: list[dict[str, str]],
    keywords: list[dict[str, str]],
) -> dict[str, Any]:
    checked = _msk_now()
    root = output_dir
    by_nmid, adv_to_setting = _map_nmid_campaigns(pg)
    pairs = _candidate_pairs(by_nmid)

    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis

    app_config = AppConfig.create()
    rc = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=rc.host, port=rc.port, db=rc.db, password=rc.password, decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx = HttpxClientHandler()
    await httpx.init()

    semantics: list[dict[str, Any]] = []
    nmid_status: dict[int, str] = {}

    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        hub = WBManagerHubFactory(httpx_client_handler=httpx, redis_client_wrapper=redis_wrap).get_wb_manager_hub(SHOP_ID)
        pm = hub.wb_data_manager.promotion_manager

        active_pairs, adv_totals = await _prefilter_pairs_with_spend(pm, pairs)

        for nmid in EXACT_NMIDS:
            camps = by_nmid.get(nmid, [])
            if not camps:
                nmid_status[nmid] = "NO_AD_HISTORY"
                continue
            has_active = any((c["adv_id"], nmid) in active_pairs for c in camps)
            nmid_status[nmid] = "HAS_AD_HISTORY" if has_active else "NO_AD_HISTORY"

        if not active_pairs:
            normalized_dir = root / "06_NORMALIZED"
            _write_csv(normalized_dir / "exact_subject_semantics.csv", SEMANTICS_FIELDS, [])
            _write_csv(normalized_dir / "exact_subject_query_index.csv", INDEX_FIELDS, [])
            return {
                "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "PERIOD": {"from": PERIOD_FROM.isoformat(), "to": PERIOD_TO.isoformat()},
                "NMID_STATUS": nmid_status,
                "active_pairs": [],
                "semantics_rows": 0,
                "NO_WRITES": "CONFIRMED",
            }

        setting_ids = {
            adv_to_setting[adv_id]
            for adv_id, _ in active_pairs
            if adv_id in adv_to_setting
        }
        _ = setting_ids  # keywords preloaded in main()

        semantics.extend(await _collect_normquery_period(pm, active_pairs))
        cluster_rows, bid_map = await _collect_cluster_states(pm, active_pairs)
        semantics.extend(cluster_rows)
        semantics.extend(_keyword_rows(keywords, by_nmid, active_pairs))

        for row in semantics:
            if row.get("bid") in ("", None) and row.get("normalized_query"):
                key = (
                    int(row.get("adv_id") or 0),
                    int(row.get("nmid") or 0),
                    row.get("normalized_query") or "",
                )
                if key in bid_map:
                    row["bid"] = bid_map[key]

        index_rows = _build_query_index(semantics)
        normalized_dir = root / "06_NORMALIZED"
        _write_csv(normalized_dir / "exact_subject_semantics.csv", SEMANTICS_FIELDS, semantics)
        _write_csv(normalized_dir / "exact_subject_query_index.csv", INDEX_FIELDS, index_rows)

        manifest = {
            "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "SUBJECT": {"id": TARGET_SUBJECT_ID, "name": TARGET_SUBJECT_NAME},
            "PERIOD": {"from": PERIOD_FROM.isoformat(), "to": PERIOD_TO.isoformat()},
            "NMID_STATUS": nmid_status,
            "candidate_pairs": len(pairs),
            "active_pairs": sorted(
                [{"adv_id": a, "nmid": n} for a, n in active_pairs],
                key=lambda x: (x["nmid"], x["adv_id"]),
            ),
            "adv_totals_in_period": adv_totals,
            "semantics_rows": len(semantics),
            "index_rows": len(index_rows),
            "query_index_top20": index_rows[:20],
            "artifacts": {
                "semantics_csv": str(normalized_dir / "exact_subject_semantics.csv"),
                "query_index_csv": str(normalized_dir / "exact_subject_query_index.csv"),
            },
            "NO_WRITES": "CONFIRMED",
        }
        pkg = root / PACKAGE
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / f"{PACKAGE}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
        )
        return manifest
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="/tmp/a1_exact_subject_semantics")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    _bootstrap()
    pg = _load_pg_adv(root)
    by_nmid, adv_to_setting = _map_nmid_campaigns(pg)
    pairs = _candidate_pairs(by_nmid)
    setting_ids = {adv_to_setting[a] for a, _ in pairs if a in adv_to_setting}
    keywords = _load_keywords(root, setting_ids)
    payload = asyncio.run(run_collect(root, pg, keywords))
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    for row in payload.get("query_index_top20") or []:
        print("INDEX_ROW|" + json.dumps(row, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

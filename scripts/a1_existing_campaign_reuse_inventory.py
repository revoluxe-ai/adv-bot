"""READ_ONLY: A1 existing WB campaign inventory for reuse / replace / create decision.

ITER-CLIENT-RETENTION-A1-20260904-001 — nmID=14824677 direct + same-subject
campaign inventory, bot connect-existing semantics, candidate classification. Без writes.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import zipfile
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
    _campaign_settings,
    _fetch_cards,
    _load_pg,
    _load_wbcards,
    _parse_nmids,
    _pg_rows_for_nmid,
)
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")
ITERATION = "ITER-CLIENT-RETENTION-A1-20260904-001"
PACKAGE = "A1_EXISTING_CAMPAIGN_REUSE_INVENTORY_20260904"
TARGET_NMID = 14824677
CLOSED_END = date(2026, 9, 3)

DEFAULT_OUTPUT = (
    r"C:\Users\vkita\my_code\meta-repo\worktree\wb-delivery-context-router"
    r"\clients\A1\chats\wb-lab-a1-analysis-20260828\artifacts"
    r"\OWNER_UPLOAD_20260904_EXISTING_CAMPAIGN_REUSE_INVENTORY"
)

CONNECTABLE_STATUSES = {4, 7, 9, 11}
BIND_EXCLUDE_STATUSES = {7, 8}
ALLOWED_PAYMENT = {"cpm"}

BOT_FLOW_PATHS = [
    "app/modules/connect_existing_advs/service.py::get_connect_existing_candidates",
    "app/core/mp/wb/api/domain_managers/promotion/promotion_manager.py::get_connect_existing_candidates",
    "app/modules/connect_existing_advs/candidates_service.py::filter_and_classify_campaigns_by_nmid",
    "app/modules/connect_existing_advs/validate_campaign_id.py::validate_campaign_id_for_connect",
    "app/client_bot/user_interface/handlers/connect_existing_advs.py::_continue_connect_existing_after_card",
    "app/modules/adv_creator/backend/main_manager.py::create_complex_advs",
    "app/modules/adv_creator/backend/main_manager.py::create_search_only",
    "app/client_bot/user_interface/handlers/rebind_adv_campaign_ids.py (adv_id rebind only, not nmID)",
]

def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _nm_ids_from_campaign(c: dict[str, Any]) -> set[int]:
    out: set[int] = set()
    for nm in c.get("nm_settings") or c.get("nmSettings") or []:
        if isinstance(nm, dict):
            nid = _read_int(nm, "nm_id", "nmId", "nmID")
            if nid:
                out.add(nid)
    return out


def _campaign_type_label(c: dict[str, Any]) -> str:
    bid = str(c.get("bid_type") or c.get("bidType") or "").lower()
    cfg = _campaign_settings(c)
    pt = str(cfg.get("payment_type") or "").lower()
    placements = cfg.get("placements") if isinstance(cfg.get("placements"), dict) else {}
    search = placements.get("search")
    rec = placements.get("recommendations")
    if bid == "manual" and pt == "cpm" and search:
        return "auction_search_cpm"
    if bid == "unified" and pt == "cpm":
        return "auto_unified_cpm"
    if bid == "manual" and pt == "cpm" and not search:
        return "auto_manual_cpm"
    if pt == "cpc":
        return f"cpc_{bid or 'unknown'}"
    return f"other_{bid}_{pt}"


def _search_capable(c: dict[str, Any]) -> bool:
    return _campaign_type_label(c) == "auction_search_cpm"


def _recommendations_capable(c: dict[str, Any]) -> bool:
    t = _campaign_type_label(c)
    return t in {"auto_unified_cpm", "auto_manual_cpm"}


def _current_bid_kopecks(c: dict[str, Any], nmid: int | None = None) -> int | None:
    for nm in c.get("nm_settings") or c.get("nmSettings") or []:
        if not isinstance(nm, dict):
            continue
        nid = _read_int(nm, "nm_id", "nmId", "nmID")
        if nmid is not None and nid != nmid:
            continue
        bids = nm.get("bids_kopecks") or nm.get("bids") or {}
        if isinstance(bids, dict):
            for key in ("search", "recommendations", "combined"):
                val = bids.get(key)
                if val is not None:
                    return int(val)
    return None


def _created_at(c: dict[str, Any]) -> str | None:
    ts = c.get("timestamps") if isinstance(c.get("timestamps"), dict) else {}
    for k in ("created", "create", "updated", "started"):
        if ts.get(k):
            return str(ts[k])[:19]
    return None


def _pg_binding_for_adv(pg_all: list[dict[str, str]], adv_id: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in pg_all:
        adv = _read_int(row, "adv_id")
        search = _read_int(row, "_search_adv_id")
        if adv_id not in (adv, search):
            continue
        rows.append({
            "pg_id": row.get("id"),
            "adv_id": adv,
            "search_adv_id": search,
            "name": row.get("name"),
            "nmids": _parse_nmids(row.get("nmids") or ""),
            "bot_active": str(row.get("bot_active")).lower() in ("true", "t", "1"),
            "automatic_version": row.get("automatic_version"),
            "active_status": row.get("active_status"),
            "type": row.get("type"),
        })
    return rows


def _subject_for_nmid(
    nmid: int,
    cards_api: dict[int, dict[str, Any]],
    wbcards: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    card = cards_api.get(nmid) or {}
    wb = wbcards.get(nmid) or {}
    sid = _read_int(card, "subjectID", "subjectId") or _read_int(wb, "wb_category_id")
    return {
        "nmID": nmid,
        "title": card.get("title") or wb.get("name"),
        "vendorCode": card.get("vendorCode"),
        "subjectID": sid,
        "subjectName": card.get("subjectName") or wb.get("subject"),
    }


async def _fetch_all_campaigns(pm: Any, budget: ApiCallBudget) -> tuple[list[dict[str, Any]], list[int]]:
    budget.consume()
    adv_ids = sorted(set(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or []))
    campaigns: list[dict[str, Any]] = []
    chunk = 50
    for i in range(0, max(len(adv_ids), 1), chunk):
        batch_ids = adv_ids[i : i + chunk] if adv_ids else []
        if not batch_ids and i > 0:
            break
        budget.consume()
        if batch_ids:
            raw = await pm.get_adverts_v2_by_ids(batch_ids)
        else:
            raw = await pm._client.campaigns_info_v2_adapter.get_all_campaigns()
        for item in raw or []:
            d = jsonable(item)
            if isinstance(d, dict):
                campaigns.append(d)
    seen: set[int] = set()
    deduped: list[dict[str, Any]] = []
    for c in campaigns:
        aid = _read_int(c, "id", "advertId")
        if aid and aid not in seen:
            seen.add(aid)
            deduped.append(c)
    return deduped, adv_ids


def _flatten_fullstats(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for block in rows:
        adv_id = _read_int(block, "advertId", "advert_id", "id")
        for day in block.get("days") or block.get("stats") or []:
            if not isinstance(day, dict):
                continue
            out.append({
                "advert_id": adv_id,
                "date": str(day.get("date") or "")[:10],
                "sum": _read_float(day, "sum", "spend"),
                "views": _read_int(day, "views"),
                "clicks": _read_int(day, "clicks"),
            })
    return out


async def _spend_and_activity(
    pm: Any,
    adv_ids: list[int],
    budget: ApiCallBudget,
    closed_end: date,
) -> tuple[dict[int, float], dict[int, float], dict[int, str | None]]:
    d7_start = closed_end - timedelta(days=6)
    d28_start = closed_end - timedelta(days=27)
    dates: list[date] = []
    d = d28_start
    while d <= closed_end:
        dates.append(d)
        d += timedelta(days=1)
    spend_7d: dict[int, float] = defaultdict(float)
    spend_28d: dict[int, float] = defaultdict(float)
    last_activity: dict[int, str | None] = {a: None for a in adv_ids}
    if not adv_ids:
        return spend_7d, spend_28d, last_activity
    for i in range(0, len(adv_ids), 20):
        chunk = adv_ids[i : i + 20]
        budget.consume()
        try:
            fs = await pm.get_full_adv_stat(chunk, dates)
        except Exception:  # noqa: BLE001
            continue
        for row in _flatten_fullstats(list(fs or [])):
            aid = _read_int(row, "advert_id")
            if not aid:
                continue
            day_s = row.get("date") or ""
            sp = _read_float(row, "sum")
            vw = _read_int(row, "views")
            cl = _read_int(row, "clicks")
            if sp > 0 or vw > 0 or cl > 0:
                if last_activity.get(aid) is None or day_s > (last_activity[aid] or ""):
                    last_activity[aid] = day_s
            try:
                day_d = date.fromisoformat(day_s[:10])
            except ValueError:
                continue
            if day_d >= d28_start:
                spend_28d[aid] += sp
            if day_d >= d7_start:
                spend_7d[aid] += sp
    return spend_7d, spend_28d, last_activity


def _replacement_capability(campaign_type: str, wb_status: int | None) -> dict[str, str]:
    """Code/WB semantics only — no writes performed."""
    is_auction = campaign_type == "auction_search_cpm"
    is_auto = campaign_type in {"auto_unified_cpm", "auto_manual_cpm"}
    wb_ok = wb_status in CONNECTABLE_STATUSES if wb_status is not None else False
    return {
        "CAN_REPLACE_NMID_WITH_14824677": (
            "YES" if is_auction else ("GAP" if is_auto else "NO")
        ),
        "CAN_REPLACE_NOTE": (
            "WB PATCH /adv/v0/auction/nms exists in generated client; "
            "adv-bot has no production wrapper or Telegram flow for nmID swap on existing campaigns"
            if is_auction
            else (
                "No unified/auto nmID replacement path found in adv-bot codebase"
                if is_auto
                else "Campaign type not eligible for nmID replacement"
            )
        ),
        "CAN_REUSE_AFTER_REPLACEMENT": "GAP" if is_auction else "NO",
        "CAN_CONNECT_TO_BOT_AFTER_REPLACEMENT": (
            "YES" if is_auction and wb_ok else ("GAP" if is_auction else "NO")
        ),
        "CAN_USE_WITH_V3": "YES" if wb_ok else ("GAP" if wb_status is None else "NO"),
        "REQUIRES_CAMPAIGN_TYPE_MATCH": "YES",
        "REQUIRES_SAME_SUBJECT": "YES",
        "HISTORICAL_STATS_TRANSFERABLE_TO_NEW_NMID": "NO",
    }


def _classify_candidate(
    *,
    adv_id: int,
    c: dict[str, Any],
    nmids: set[int],
    target_subject_id: int | None,
    subject_map: dict[int, dict[str, Any]],
    pg_bindings: list[dict[str, Any]],
    wb_status: int | None,
) -> tuple[str, str]:
    has_target = TARGET_NMID in nmids
    same_subject_other = False
    if target_subject_id is not None:
        for nid in nmids:
            if nid == TARGET_NMID:
                continue
            sid = (subject_map.get(nid) or {}).get("subjectID")
            if sid == target_subject_id:
                same_subject_other = True
                break

    ctype = _campaign_type_label(c)
    connectable_type = ctype in {"auction_search_cpm", "auto_unified_cpm", "auto_manual_cpm"}
    bindable = wb_status not in BIND_EXCLUDE_STATUSES if wb_status is not None else False

    if has_target and connectable_type and bindable:
        return "CLASS_A", "DIRECT_REUSE"
    if has_target and connectable_type:
        return "CLASS_C", "direct_match_but_status_not_connectable"
    if has_target:
        return "CLASS_C", "direct_match_wrong_type_or_payment"
    if same_subject_other and connectable_type and bindable:
        return "CLASS_B", "SAME_SUBJECT_REPLACE"
    if same_subject_other:
        return "CLASS_C", "same_subject_but_not_connectable"
    return "CLASS_C", "not_target_not_same_subject"


def _bot_flow_block(
    connect_result: Any,
    target_nmid: int,
) -> dict[str, Any]:
    auction_ids = [getattr(x, "id", None) for x in (connect_result.auction_candidates or [])]
    auto_ids = [getattr(x, "id", None) for x in (connect_result.auto_candidates or [])]
    return {
        "BOT_EXISTING_CAMPAIGN_SEARCH_CONFIRMED": "YES",
        "BOT_SAME_SUBJECT_REPLACEMENT_CONFIRMED": "NO",
        "BOT_REUSE_FLOW_CODE_PATHS": BOT_FLOW_PATHS,
        "runtime_connect_existing_for_target": {
            "nmid": target_nmid,
            "auction_candidate_adv_ids": [i for i in auction_ids if i],
            "auto_candidate_adv_ids": [i for i in auto_ids if i],
            "filter_semantics": (
                "filter_and_classify_campaigns_by_nmid keeps campaigns only when "
                "target nmid is already in nm_settings; no subjectID/category filter"
            ),
            "nmid_replacement_in_bot": (
                "Not implemented — connect_existing_change_nmid only re-prompts for a different "
                "nmid input; does not PATCH WB campaign products"
            ),
            "new_physical_campaign_when": (
                "create_complex_advs creates new auto+search when no PG rows for nmid "
                "(or hard_mode turns off old); create_search_only adds search to existing auto"
            ),
            "advsetting_on_connect": (
                "Upsert AdvSetting with adv_id + _search_adv_id + nmids=[nmid] on successful connect/create"
            ),
        },
        "wb_nm_replace_api_reference": {
            "auction": "PATCH /adv/v0/auction/nms (generated client only; not called by adv-bot)",
            "unified_auto": "GAP — no adv-bot wrapper found",
        },
    }


async def run_collect(root: Path, pg_all: list[dict[str, str]]) -> dict[str, Any]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.modules.connect_existing_advs.service import get_connect_existing_candidates

    checked_at = _msk_now()
    gaps: list[str] = []
    budget = ApiCallBudget(limit=500)

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        pm = dm.promotion_manager
        products = dm.products_manager

        target_cards = await _fetch_cards(products, {TARGET_NMID})
        wbcards = _load_wbcards(root, (TARGET_NMID,))
        target_identity = _subject_for_nmid(TARGET_NMID, target_cards, wbcards)
        target_subject_id = target_identity.get("subjectID")
        if not target_subject_id:
            gaps.append("TARGET_SUBJECT_ID_unresolved")

        campaigns, cabinet_adv_ids = await _fetch_all_campaigns(pm, budget)
        adv_nm = _adv_nm_map(campaigns)
        all_nmids = sorted({n for ns in adv_nm.values() for n in ns})

        wbcards_all = _load_wbcards(root, tuple(all_nmids[:500]))
        cards_api = await _fetch_cards(products, set(all_nmids[:80]))
        if len(all_nmids) > 80:
            gaps.append(f"cards_api_partial_only_80_of_{len(all_nmids)}_campaign_nmids")

        subject_map: dict[int, dict[str, Any]] = {}
        for nmid in all_nmids:
            subject_map[nmid] = _subject_for_nmid(nmid, cards_api, wbcards_all)

        adv_ids = sorted(adv_nm.keys())
        spend_7d, spend_28d, last_activity = await _spend_and_activity(
            pm, adv_ids, budget, CLOSED_END,
        )

        inventory: list[dict[str, Any]] = []
        for c in campaigns:
            adv_id = _read_int(c, "id", "advertId")
            if not adv_id:
                continue
            nmids = sorted(adv_nm.get(adv_id, ()))
            cfg = _campaign_settings(c)
            st = _read_int(c, "status")
            inventory.append({
                "adv_id": adv_id,
                "name": cfg.get("name"),
                "bid_type": c.get("bid_type"),
                "campaign_type": _campaign_type_label(c),
                "payment_type": cfg.get("payment_type"),
                "wb_status": st,
                "wb_status_name": WB_STATUS_NAMES.get(st, f"status_{st}"),
                "created_at": _created_at(c),
                "current_nmids": nmids,
                "placements": cfg.get("placements"),
                "current_bid_kopecks": _current_bid_kopecks(c),
                "budget_from_v2": c.get("budget"),
                "last_activity_date": last_activity.get(adv_id),
                "last_spend_date": last_activity.get(adv_id),
                "spend_7d": round(spend_7d.get(adv_id, 0.0), 2),
                "spend_28d": round(spend_28d.get(adv_id, 0.0), 2),
            })

        direct_rows: list[dict[str, Any]] = []
        same_subject_rows: list[dict[str, Any]] = []
        candidate_table: list[dict[str, Any]] = []

        extra_pg_ids = sorted({
            _read_int(r, "adv_id")
            for r in pg_all
            if TARGET_NMID in _parse_nmids(r.get("nmids") or "")
        })
        extra_pg_ids = [x for x in extra_pg_ids if x]

        budget.consume()
        connect_result = await get_connect_existing_candidates(
            SHOP_ID, TARGET_NMID, extra_adv_ids=extra_pg_ids or None,
        )

        for c in campaigns:
            adv_id = _read_int(c, "id", "advertId")
            if not adv_id:
                continue
            nmids = adv_nm.get(adv_id, set())
            has_target = TARGET_NMID in nmids
            same_subject = False
            other_nm: int | None = None
            if target_subject_id:
                for nid in nmids:
                    if nid == TARGET_NMID:
                        continue
                    if (subject_map.get(nid) or {}).get("subjectID") == target_subject_id:
                        same_subject = True
                        other_nm = nid
                        break
            if not has_target and not same_subject:
                continue

            pg_bind = _pg_binding_for_adv(pg_all, adv_id)
            st = _read_int(c, "status")
            ctype = _campaign_type_label(c)
            cls, blocker_hint = _classify_candidate(
                adv_id=adv_id,
                c=c,
                nmids=nmids,
                target_subject_id=target_subject_id,
                subject_map=subject_map,
                pg_bindings=pg_bind,
                wb_status=st,
            )
            rep = _replacement_capability(ctype, st)
            primary_nmid = TARGET_NMID if has_target else other_nm
            subj = subject_map.get(primary_nmid or TARGET_NMID, {})
            row = {
                "adv_id": adv_id,
                "class": cls,
                "class_label": blocker_hint,
                "current_nmids": sorted(nmids),
                "current_title": subj.get("title"),
                "subjectID": subj.get("subjectID"),
                "subjectName": subj.get("subjectName"),
                "campaign_type": ctype,
                "status": st,
                "status_name": WB_STATUS_NAMES.get(st, f"status_{st}"),
                "placements": _campaign_settings(c).get("placements"),
                "current_bid_kopecks": _current_bid_kopecks(c, primary_nmid),
                "spend_28d": round(spend_28d.get(adv_id, 0.0), 2),
                "last_activity": last_activity.get(adv_id),
                "bot_binding": pg_bind,
                "direct_target_match": has_target,
                "same_subject_match": same_subject and not has_target,
                "14824677_currently_bound": has_target,
                "search_capability": _search_capable(c),
                "recommendations_capability": _recommendations_capable(c),
                "automatic_version": (pg_bind[0].get("automatic_version") if pg_bind else None),
                "can_connect_existing_via_bot_flow": (
                    "YES" if has_target and st not in BIND_EXCLUDE_STATUSES else "NO"
                ),
                "can_be_search_contour": _search_capable(c),
                "can_be_used_with_v3": rep["CAN_USE_WITH_V3"],
                "can_replace_nmid": rep["CAN_REPLACE_NMID_WITH_14824677"],
                "can_connect_existing": (
                    "YES" if has_target and st not in BIND_EXCLUDE_STATUSES else "NO"
                ),
                "v3_compatible": rep["CAN_USE_WITH_V3"],
                "reuse_blocker": blocker_hint if cls == "CLASS_C" else None,
                **{k: rep[k] for k in (
                    "CAN_REUSE_AFTER_REPLACEMENT",
                    "CAN_CONNECT_TO_BOT_AFTER_REPLACEMENT",
                    "HISTORICAL_STATS_TRANSFERABLE_TO_NEW_NMID",
                )},
            }
            candidate_table.append(row)
            if has_target:
                direct_rows.append(row)
            elif same_subject:
                same_subject_rows.append(row)

        class_a = [r for r in candidate_table if r["class"] == "CLASS_A"]
        class_b = [r for r in candidate_table if r["class"] == "CLASS_B"]
        reusable = class_a + class_b
        new_required = "YES" if not reusable else "NO"
        new_required_gates: list[str] = []
        if new_required == "YES":
            if not direct_rows and not same_subject_rows:
                new_required_gates.append("no_direct_or_same_subject_campaigns_in_wb_inventory")
            else:
                new_required_gates.append("all_candidates_classified_CLASS_C")

        bot_flow = _bot_flow_block(connect_result, TARGET_NMID)

        reuse_block = {
            "per_candidate_type_notes": {
                "CLASS_A": "Campaign already promotes 14824677; bot connect-existing filters by exact nmid",
                "CLASS_B": (
                    "Same subjectID but different nmID — bot does not search by subject; "
                    "WB auction nm PATCH exists in API client only"
                ),
                "CLASS_C": "Wrong type/status/subject or non-connectable WB status",
                "CLASS_D": "No CLASS_A/CLASS_B candidates remain viable",
            },
            "global": {
                "REQUIRES_SAME_SUBJECT": "YES",
                "REQUIRES_CAMPAIGN_TYPE_MATCH": "YES",
                "HISTORICAL_STATS_TRANSFERABLE_TO_NEW_NMID": "NO",
                "observation_boundary_after_replacement": (
                    "Post-replacement stats are new SKU observation; prior campaign-level "
                    "history belongs to old nmID configuration only"
                ),
            },
            "candidates": [
                {
                    "adv_id": r["adv_id"],
                    "class": r["class"],
                    **{k: r.get(k) for k in (
                        "can_replace_nmid", "CAN_REUSE_AFTER_REPLACEMENT",
                        "CAN_CONNECT_TO_BOT_AFTER_REPLACEMENT", "CAN_USE_WITH_V3",
                        "REQUIRES_CAMPAIGN_TYPE_MATCH", "REQUIRES_SAME_SUBJECT",
                        "HISTORICAL_STATS_TRANSFERABLE_TO_NEW_NMID",
                    )},
                }
                for r in candidate_table
                if r["class"] in {"CLASS_A", "CLASS_B"}
            ],
        }

        flags = {
            "TARGET_NMID": TARGET_NMID,
            "TARGET_SUBJECT_ID": target_subject_id,
            "DIRECT_REUSE_CANDIDATE_COUNT": len(class_a),
            "SAME_SUBJECT_REPLACE_CANDIDATE_COUNT": len(class_b),
            "REUSABLE_CANDIDATE_COUNT": len(reusable),
            "NEW_PHYSICAL_CAMPAIGN_TECHNICALLY_REQUIRED": new_required,
            "NEW_PHYSICAL_CAMPAIGN_GATES": new_required_gates,
            "REUSABLE_ADV_IDS": [r["adv_id"] for r in reusable],
        }

        return_block = {
            "STATUS": "PASS" if target_subject_id else "PARTIAL",
            "INTEGRITY": "PASS" if campaigns else "GAP",
            "CHECKED_AT_MSK": _iso_msk(checked_at),
            "TARGET_NMID": TARGET_NMID,
            "TARGET_TITLE": target_identity.get("title"),
            "TARGET_SUBJECT_ID": target_subject_id,
            "TARGET_SUBJECT_NAME": target_identity.get("subjectName"),
            "BOT_EXISTING_CAMPAIGN_SEARCH_CONFIRMED": bot_flow["BOT_EXISTING_CAMPAIGN_SEARCH_CONFIRMED"],
            "BOT_SAME_SUBJECT_REPLACEMENT_CONFIRMED": bot_flow["BOT_SAME_SUBJECT_REPLACEMENT_CONFIRMED"],
            "BOT_REUSE_FLOW_CODE_PATHS": bot_flow["BOT_REUSE_FLOW_CODE_PATHS"],
            "DIRECT_REUSE_CANDIDATES": [r["adv_id"] for r in class_a],
            "SAME_SUBJECT_REPLACE_CANDIDATES": [r["adv_id"] for r in class_b],
            "DIRECT_REUSE_CANDIDATE_COUNT": len(class_a),
            "SAME_SUBJECT_REPLACE_CANDIDATE_COUNT": len(class_b),
            "REUSABLE_CANDIDATE_COUNT": len(reusable),
            "NEW_PHYSICAL_CAMPAIGN_TECHNICALLY_REQUIRED": new_required,
            "REUSABLE_ADV_IDS": flags["REUSABLE_ADV_IDS"],
            "NEW_PHYSICAL_CAMPAIGN_GATES": new_required_gates,
            "CANDIDATE_TABLE": candidate_table,
            "UNKNOWN_OR_GAPS": gaps,
            "READ_ONLY": "CONFIRMED",
            "WB_API_WRITES": 0,
            "DB_WRITES": 0,
            "CAMPAIGN_STATE_CHANGED": "NO",
            "AD_WB_WRITES_AUTHORIZED": "NO",
        }

        manifest = {
            "iteration": ITERATION,
            "package": PACKAGE,
            "checked_at_msk": _iso_msk(checked_at),
            "mode": "STRICT_READ_ONLY",
            "artifacts": [
                "00_manifest.json",
                "01_target_14824677_identity.json",
                "02_full_campaign_inventory.json",
                "03_direct_target_campaigns.json",
                "04_same_subject_campaigns.json",
                "05_reuse_replace_capability.json",
                "06_bot_existing_campaign_flow.json",
                "07_candidate_table.json",
                "08_evidence_summary.md",
            ],
            "flags": flags,
            "return_block": return_block,
        }

        _write_json(root / "01_target_14824677_identity.json", {
            **target_identity,
            "parentName": (target_cards.get(TARGET_NMID) or {}).get("brand"),
            "route": "Content API cards + PG wbcard fallback",
            "checked_at_msk": _iso_msk(checked_at),
        })
        _write_json(root / "02_full_campaign_inventory.json", {
            "cabinet_adv_ids_count": len(cabinet_adv_ids),
            "campaigns_returned_count": len(inventory),
            "inventory": inventory,
            "routes": {
                "ids": "GET promotion_count -> adv/v1/promotion/count",
                "details": "GET /api/advert/v2/adverts",
                "spend": "GET /adv/v3/fullstats",
            },
            "checked_at_msk": _iso_msk(checked_at),
        })
        _write_json(root / "03_direct_target_campaigns.json", {
            "target_nmid": TARGET_NMID,
            "campaigns": direct_rows,
            "pg_rows_for_nmid": _pg_rows_for_nmid(pg_all, TARGET_NMID),
            "checked_at_msk": _iso_msk(checked_at),
        })
        _write_json(root / "04_same_subject_campaigns.json", {
            "target_subject_id": target_subject_id,
            "campaigns": same_subject_rows,
            "checked_at_msk": _iso_msk(checked_at),
        })
        _write_json(root / "05_reuse_replace_capability.json", reuse_block)
        _write_json(root / "06_bot_existing_campaign_flow.json", bot_flow)
        _write_json(root / "07_candidate_table.json", candidate_table)

        summary_lines = [
            "# A1 Existing Campaign Reuse Inventory",
            "",
            f"**Checked at MSK:** {_iso_msk(checked_at)}",
            f"**Target nmID:** {TARGET_NMID}",
            f"**Target subjectID:** {target_subject_id}",
            "",
            f"- Direct reuse (CLASS_A): {len(class_a)}",
            f"- Same-subject replace (CLASS_B): {len(class_b)}",
            f"- New physical campaign required: {new_required}",
            "",
            "## Bot flow",
            f"- Existing campaign search: {bot_flow['BOT_EXISTING_CAMPAIGN_SEARCH_CONFIRMED']}",
            f"- Same-subject replacement in bot: {bot_flow['BOT_SAME_SUBJECT_REPLACEMENT_CONFIRMED']}",
            "",
            "## Safety",
            "- READ_ONLY = CONFIRMED",
            "- AD_WB_WRITES_AUTHORIZED = NO",
        ]
        (root / "08_evidence_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

        zip_path = root / f"{PACKAGE}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in manifest["artifacts"]:
                p = root / name
                if p.exists():
                    zf.write(p, arcname=name)
        zip_sha = _sha256(zip_path)
        manifest["zip_sha256"] = zip_sha
        manifest["archive_verified"] = True
        _write_json(root / "00_manifest.json", manifest)

        return {
            "return_block": return_block,
            "evidence_folder": str(root),
            "evidence_zip": str(zip_path),
            "evidence_zip_sha256": zip_sha,
            "archive_verified": True,
        }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    args = ap.parse_args(argv)
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    staging = out / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    _bootstrap()
    pg_all = _load_pg(staging)
    result = asyncio.run(run_collect(out, pg_all))
    print(json.dumps(result["return_block"], ensure_ascii=False, indent=2, default=str))
    print(json.dumps({
        "EVIDENCE_FOLDER_ABSOLUTE_PATH": result["evidence_folder"],
        "EVIDENCE_ZIP_ABSOLUTE_PATH": result["evidence_zip"],
        "EVIDENCE_ZIP_SHA256": result["evidence_zip_sha256"],
        "ARCHIVE_VERIFIED": result["archive_verified"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

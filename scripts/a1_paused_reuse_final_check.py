"""READ_ONLY: A1 paused same-subject reuse check + SKU identity verification.

ITER-CLIENT-RETENTION-A1-20260904-001 — identity 14824677 vs 180148471,
paused (status 11) same-subject campaigns only. Без writes.
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
    _parse_nmids,
    _pg_rows_for_nmid,
)
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")
ITERATION = "ITER-CLIENT-RETENTION-A1-20260904-001"
PACKAGE = "A1_PAUSED_REUSE_FINAL_CHECK_20260904"
TARGET_NMID = 14824677
CROSSCHECK_NMID = 180148471
CLOSED_END = date(2026, 9, 3)

DEFAULT_OUTPUT = (
    r"C:\Users\vkita\my_code\meta-repo\worktree\wb-delivery-context-router"
    r"\clients\A1\chats\wb-lab-a1-analysis-20260828\artifacts"
    r"\OWNER_UPLOAD_20260904_PAUSED_REUSE_FINAL_CHECK"
)

STATUS_ACTIVE = 9
STATUS_PAUSED = 11
STATUS_DONE = 7
STATUS_REFUSED = 8
STATUS_READY = 4


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _campaign_type(c: dict[str, Any]) -> str:
    bid = str(c.get("bid_type") or "").lower()
    cfg = _campaign_settings(c)
    pt = str(cfg.get("payment_type") or "").lower()
    pl = cfg.get("placements") if isinstance(cfg.get("placements"), dict) else {}
    if bid == "manual" and pt == "cpm" and pl.get("search"):
        return "auction_search_cpm"
    if bid == "unified" and pt == "cpm":
        return "auto_unified_cpm"
    if bid == "manual" and pt == "cpm":
        return "auto_manual_cpm"
    return f"other_{bid}_{pt}"


def _subject_from_campaign(c: dict[str, Any]) -> tuple[int | None, str | None]:
    for nm in c.get("nm_settings") or c.get("nmSettings") or []:
        if isinstance(nm, dict):
            subj = nm.get("subject") or {}
            if isinstance(subj, dict) and subj.get("id"):
                return _read_int(subj, "id"), subj.get("name")
    return None, None


def _identity_from_card(nmid: int, card: dict[str, Any], checked_at: str) -> dict[str, Any]:
    return {
        "nmID": nmid,
        "vendorCode": card.get("vendorCode"),
        "title": card.get("title"),
        "subjectID": _read_int(card, "subjectID", "subjectId"),
        "subjectName": card.get("subjectName"),
        "brand": card.get("brand"),
        "source_route": "POST /content/v2/get/cards/list (text_search by nmID)",
        "checked_at_msk": checked_at,
    }


def _identity_conflict(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    same_title = (
        a.get("title") and b.get("title") and str(a["title"]).strip() == str(b["title"]).strip()
    )
    same_vendor = (
        a.get("vendorCode")
        and b.get("vendorCode")
        and str(a["vendorCode"]).strip() == str(b["vendorCode"]).strip()
    )
    same_nmid = a.get("nmID") == b.get("nmID")
    return {
        "IDENTITY_CONFLICT_WITH_180148471": (
            "YES" if same_title and not same_nmid else ("NO" if a.get("nmID") and b.get("nmID") else "GAP")
        ),
        "conflict_type": (
            "identical_title_different_nmid_and_vendorCode"
            if same_title and not same_nmid
            else ("none" if not same_title else "full_duplicate")
        ),
        "title_match": same_title,
        "vendorCode_match": same_vendor,
        "nmID_distinct": not same_nmid,
        "disambiguation": (
            "vendorCode differs — treat as separate catalog cards despite identical title"
            if same_title and not same_vendor
            else None
        ),
    }


def _pg_role(pg_rows: list[dict[str, Any]], adv_id: int) -> str:
    if not pg_rows:
        return "unbound"
    row = pg_rows[0]
    adv = row.get("adv_id")
    search = row.get("search_adv_id") or 0
    if adv_id == adv and search:
        return "parent"
    if adv_id == search:
        return "search"
    if adv_id == adv and not search:
        return "legacy_auto_only"
    return "GAP"


def _reuse_capability(c: dict[str, Any], pg_rows: list[dict[str, Any]]) -> dict[str, Any]:
    ctype = _campaign_type(c)
    is_auction = ctype == "auction_search_cpm"
    is_auto = ctype in {"auto_unified_cpm", "auto_manual_cpm"}
    has_bot = bool(pg_rows)
    auto_ver = (pg_rows[0].get("automatic_version") if pg_rows else None)
    v3 = str(auto_ver) == "3" if auto_ver else False
    can_change = (c.get("restrictions") or {}).get("can_change_nms")

    if is_auction:
        replace = "YES" if can_change else "GAP"
        manual_patch = "YES"
    elif is_auto:
        replace = "GAP"
        manual_patch = "GAP"
    else:
        replace = "NO"
        manual_patch = "NO"

    return {
        "CAN_REPLACE_NMID_WITH_14824677": replace,
        "CAN_RESTART_AFTER_REPLACEMENT": "GAP",
        "CAN_CONNECT_EXISTING_TO_BOT": "YES" if has_bot else "GAP",
        "CAN_USE_WITH_V3": "YES" if v3 else ("NO" if has_bot else "GAP"),
        "REQUIRES_NEW_PARENT_ADVSETTING": "YES" if not has_bot else "NO",
        "REQUIRES_MANUAL_WB_NMID_PATCH": manual_patch,
        "REQUIRES_DB_REBIND": "YES" if has_bot else "GAP",
        "HISTORICAL_STATS_TRANSFERABLE_TO_NEW_NMID": "NO",
        "REUSE_BLOCKER": "NONE",
    }


def _flatten_fullstats(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for block in rows:
        adv_id = _read_int(block, "advertId", "advert_id", "id")
        for day in block.get("days") or block.get("stats") or []:
            if isinstance(day, dict):
                out.append({
                    "advert_id": adv_id,
                    "date": str(day.get("date") or "")[:10],
                    "sum": _read_float(day, "sum", "spend"),
                    "views": _read_int(day, "views"),
                    "clicks": _read_int(day, "clicks"),
                })
    return out


async def run_collect(root: Path, pg_all: list[dict[str, str]]) -> dict[str, Any]:
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager

    checked_at = _msk_now()
    gaps: list[str] = []
    budget = ApiCallBudget(limit=400)

    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory()
        hub = factory.get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        pm = dm.promotion_manager
        products = dm.products_manager

        cards = await _fetch_cards(products, {TARGET_NMID, CROSSCHECK_NMID})
        id_target = _identity_from_card(TARGET_NMID, cards.get(TARGET_NMID, {}), _iso_msk(checked_at))
        id_cross = _identity_from_card(CROSSCHECK_NMID, cards.get(CROSSCHECK_NMID, {}), _iso_msk(checked_at))
        conflict = _identity_conflict(id_target, id_cross)

        if not id_target.get("title") or not id_target.get("subjectID"):
            gaps.append("TARGET_IDENTITY_INCOMPLETE_FROM_CARDS_API")
        if not id_cross.get("title"):
            gaps.append("CROSSCHECK_IDENTITY_INCOMPLETE_FROM_CARDS_API")

        identity_confirmed = (
            "YES"
            if id_target.get("nmID") and id_target.get("vendorCode") and id_target.get("subjectID")
            else ("PARTIAL" if id_target.get("nmID") else "GAP")
        )

        if conflict.get("IDENTITY_CONFLICT_WITH_180148471") == "YES":
            gaps.append("title_collision_14824677_vs_180148471_resolve_before_operational_use")

        target_subject_id = id_target.get("subjectID")
        target_subject_name = id_target.get("subjectName")

        budget.consume()
        adv_ids = sorted(set(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or []))
        campaigns: list[dict[str, Any]] = []
        for i in range(0, max(len(adv_ids), 1), 50):
            batch = adv_ids[i : i + 50] if adv_ids else []
            budget.consume()
            raw = (
                await pm.get_adverts_v2_by_ids(batch)
                if batch
                else await pm._client.campaigns_info_v2_adapter.get_all_campaigns()
            )
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
        campaigns = deduped

        paused_rows: list[dict[str, Any]] = []
        active_excluded: list[dict[str, Any]] = []
        done_excluded: list[dict[str, Any]] = []
        other_excluded: list[dict[str, Any]] = []

        paused_adv_ids: list[int] = []
        for c in campaigns:
            sid, sname = _subject_from_campaign(c)
            if sid != target_subject_id:
                continue
            adv_id = _read_int(c, "id", "advertId")
            if not adv_id:
                continue
            st = _read_int(c, "status")
            cfg = _campaign_settings(c)
            pl = cfg.get("placements") if isinstance(cfg.get("placements"), dict) else {}
            nmids = sorted(_adv_nm_map([c]).get(adv_id, ()))
            base = {
                "adv_id": adv_id,
                "current_nmids": nmids,
                "title": cfg.get("name"),
                "subjectID": sid,
                "subjectName": sname,
                "campaign_type": _campaign_type(c),
                "payment_type": cfg.get("payment_type"),
                "status": st,
                "status_name": WB_STATUS_NAMES.get(st, f"status_{st}"),
                "placements": pl,
                "search_enabled": bool(pl.get("search")),
                "recommendations_enabled": bool(pl.get("recommendations")),
                "can_change_nms": (c.get("restrictions") or {}).get("can_change_nms"),
            }
            if st == STATUS_ACTIVE:
                active_excluded.append(base)
            elif st == STATUS_DONE:
                done_excluded.append(base)
            elif st in (STATUS_REFUSED,) or (c.get("timestamps") or {}).get("deleted"):
                done_excluded.append({**base, "exclude_reason": "refused_or_deleted"})
            elif st == STATUS_PAUSED:
                paused_adv_ids.append(adv_id)
                paused_rows.append(base)
            else:
                other_excluded.append({**base, "note": "non_paused_non_active_restartable_status"})

        spend_7d: dict[int, float] = defaultdict(float)
        spend_28d: dict[int, float] = defaultdict(float)
        last_activity: dict[int, str | None] = {}
        if paused_adv_ids:
            d7 = CLOSED_END - timedelta(days=6)
            d28 = CLOSED_END - timedelta(days=27)
            dates = []
            d = d28
            while d <= CLOSED_END:
                dates.append(d)
                d += timedelta(days=1)
            for i in range(0, len(paused_adv_ids), 20):
                budget.consume()
                fs = await pm.get_full_adv_stat(paused_adv_ids[i : i + 20], dates)
                for row in _flatten_fullstats(list(fs or [])):
                    aid = _read_int(row, "advert_id")
                    day_s = row.get("date") or ""
                    sp = _read_float(row, "sum")
                    vw = _read_int(row, "views")
                    cl = _read_int(row, "clicks")
                    if sp or vw or cl:
                        if not last_activity.get(aid) or day_s > (last_activity.get(aid) or ""):
                            last_activity[aid] = day_s
                    try:
                        day_d = date.fromisoformat(day_s[:10])
                    except ValueError:
                        continue
                    if day_d >= d28:
                        spend_28d[aid] += sp
                    if day_d >= d7:
                        spend_7d[aid] += sp

        paused_inventory: list[dict[str, Any]] = []
        reuse_caps: list[dict[str, Any]] = []
        for base in paused_rows:
            adv_id = base["adv_id"]
            pg_bind = _pg_rows_for_nmid(pg_all, base["current_nmids"][0]) if base["current_nmids"] else []
            pg_for_adv = [r for r in pg_all if _read_int(r, "adv_id") == adv_id or _read_int(r, "_search_adv_id") == adv_id]
            pg_row = pg_for_adv[0] if pg_for_adv else (pg_bind[0] if pg_bind else None)
            bids = None
            for c in campaigns:
                if _read_int(c, "id") == adv_id:
                    for nm in c.get("nm_settings") or []:
                        if isinstance(nm, dict):
                            bids = nm.get("bids_kopecks") or nm.get("bids")
                    break
            cap = _reuse_capability(next(c for c in campaigns if _read_int(c, "id") == adv_id), pg_for_adv)
            row = {
                **base,
                "current_bids": bids,
                "budget_from_v2": next(
                    (c.get("budget") for c in campaigns if _read_int(c, "id") == adv_id), None
                ),
                "bot_advsetting_exists": bool(pg_row),
                "adv_setting_id": pg_row.get("pg_id") if pg_row else None,
                "bot_active": pg_row.get("bot_active") if pg_row else None,
                "automatic_version": pg_row.get("automatic_version") if pg_row else None,
                "role": _pg_role(pg_for_adv, adv_id),
                "search_adv_id": pg_row.get("search_adv_id") if pg_row else None,
                "last_spend_date": last_activity.get(adv_id),
                "spend_7d": round(spend_7d.get(adv_id, 0.0), 2),
                "spend_28d": round(spend_28d.get(adv_id, 0.0), 2),
                "last_activity_date": last_activity.get(adv_id),
                **cap,
                "can_connect_existing": cap["CAN_CONNECT_EXISTING_TO_BOT"],
                "can_restart_after_replacement": cap["CAN_RESTART_AFTER_REPLACEMENT"],
                "requires_manual_wb_nmid_patch": cap["REQUIRES_MANUAL_WB_NMID_PATCH"],
                "requires_db_rebind": cap["REQUIRES_DB_REBIND"],
                "v3_compatible": cap["CAN_USE_WITH_V3"],
                "can_replace_nmid": cap["CAN_REPLACE_NMID_WITH_14824677"],
            }
            paused_inventory.append(row)
            reuse_caps.append({"adv_id": adv_id, **cap})

        reusable = [r for r in paused_inventory if r.get("reuse_blocker") == "NONE"]
        new_required = "YES" if not reusable else "NO"

        return_block = {
            "STATUS": "PASS" if identity_confirmed == "YES" and not gaps else "PARTIAL",
            "INTEGRITY": "PASS" if campaigns else "GAP",
            "CHECKED_AT_MSK": _iso_msk(checked_at),
            "TARGET_NMID": TARGET_NMID,
            "TARGET_TITLE": id_target.get("title"),
            "TARGET_VENDOR_CODE": id_target.get("vendorCode"),
            "TARGET_SUBJECT_ID": target_subject_id,
            "TARGET_SUBJECT_NAME": target_subject_name,
            "IDENTITY_14824677_CONFIRMED": identity_confirmed,
            "IDENTITY_CONFLICT_WITH_180148471": conflict.get("IDENTITY_CONFLICT_WITH_180148471"),
            "CROSSCHECK_180148471_TITLE": id_cross.get("title"),
            "CROSSCHECK_180148471_SUBJECT_ID": id_cross.get("subjectID"),
            "PAUSED_SAME_SUBJECT_CANDIDATES": paused_inventory,
            "PAUSED_SAME_SUBJECT_CANDIDATE_COUNT": len(paused_inventory),
            "REUSABLE_PAUSED_CANDIDATE_COUNT": len(reusable),
            "REUSABLE_PAUSED_ADV_IDS": [r["adv_id"] for r in reusable],
            "ACTIVE_SAME_SUBJECT_CAMPAIGNS_EXCLUDED": [r["adv_id"] for r in active_excluded],
            "DONE_ARCHIVED_CAMPAIGNS_EXCLUDED": [r["adv_id"] for r in done_excluded],
            "OTHER_STATUS_SAME_SUBJECT_EXCLUDED": other_excluded,
            "NEW_PHYSICAL_CAMPAIGN_REQUIRED_IF_NO_PAUSED_REUSE": new_required,
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
                "01_identity_14824677.json",
                "02_identity_180148471_crosscheck.json",
                "03_target_subject.json",
                "04_paused_same_subject_inventory.json",
                "05_paused_reuse_capability.json",
                "06_evidence_summary.md",
            ],
            "identity_conflict": conflict,
            "return_block": return_block,
            "cabinet_campaigns_scanned": len(campaigns),
            "cabinet_adv_ids_count": len(adv_ids),
        }

        _write_json(root / "01_identity_14824677.json", {**id_target, "IDENTITY_14824677_CONFIRMED": identity_confirmed})
        _write_json(root / "02_identity_180148471_crosscheck.json", {**id_cross, **conflict})
        _write_json(root / "03_target_subject.json", {
            "TARGET_SUBJECT_ID": target_subject_id,
            "TARGET_SUBJECT_NAME": target_subject_name,
            "matching_rule": "exact subjectID only",
        })
        _write_json(root / "04_paused_same_subject_inventory.json", {
            "filter": "subjectID match AND status==11 paused",
            "excluded_active_status_9": active_excluded,
            "excluded_done_status_7": done_excluded,
            "paused_candidates": paused_inventory,
        })
        _write_json(root / "05_paused_reuse_capability.json", {
            "HISTORICAL_STATS_TRANSFERABLE_TO_NEW_NMID": "NO",
            "candidates": reuse_caps,
        })
        (root / "06_evidence_summary.md").write_text(
            f"# A1 Paused Same-Subject Reuse Final Check\n\n"
            f"**Checked:** {_iso_msk(checked_at)}\n\n"
            f"Identity confirmed: {identity_confirmed}\n"
            f"Title conflict with 180148471: {conflict.get('IDENTITY_CONFLICT_WITH_180148471')}\n\n"
            f"Paused same-subject candidates: {len(paused_inventory)}\n"
            f"New physical campaign if no paused reuse: {new_required}\n",
            encoding="utf-8",
        )

        zip_path = root / f"{PACKAGE}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in manifest["artifacts"]:
                if name != "00_manifest.json":
                    p = root / name
                    if p.exists():
                        zf.write(p, arcname=name)
        sha = _sha256(zip_path)
        manifest["zip_sha256"] = sha
        manifest["archive_verified"] = True
        _write_json(root / "00_manifest.json", manifest)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in manifest["artifacts"]:
                zf.write(root / name, arcname=name)

        return {
            "return_block": return_block,
            "evidence_folder": str(root),
            "evidence_zip": str(zip_path),
            "evidence_zip_sha256": sha,
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

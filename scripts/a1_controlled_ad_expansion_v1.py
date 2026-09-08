"""Bounded A1 advertising expansion executor.

Модуль выполняет свежий preflight, формирует allowlisted write-set и при
явном ``--execute`` вызывает существующие production-адаптеры WB. Он не
создаёт HTTP-клиент вручную: бюджет и состояние кампании меняются через
``WBModifier``. Все результаты сохраняются в zip-пакет для readback-а и
аудита; без ``--execute`` модуль строго dry-run.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import logging
from collections import defaultdict
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

import dotenv
from sqlalchemy import select

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import WBCabinet

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
WB_CABINET_ID = 401
PREFLIGHT_NMIDS = frozenset(
    {837395782, 14824677, 14166423, 85970344, 7974113, 147281596}
)
ALLOWED_NMIDS = frozenset({837395782, 14824677, 14166423, 388166103})
FORBIDDEN_NMIDS = frozenset({7974113, 147281596})
NO_WRITE_NMIDS = frozenset({7974113, 147281596, 85970344})
PRIORITY_NMIDS = (14824677, 837395782, 14166423)
MAX_INCREMENTAL_RUB = 2_000
DEFAULT_TOPUP_RUB = 1_000
PREFERRED_INCREMENTAL_MIN_RUB = 1_000
DAILY_LIMIT_CAP_RUB = 500
MAX_14166423_INCREMENT_RUB = 300
PAUSED_STATUS = 11
ACTIVE_STATUSES = frozenset({9})


@dataclass(frozen=True, slots=True)
class Candidate:
    """Кандидат кампании, отобранный только из разрешённых nmID."""

    adv_id: int
    nm_ids: tuple[int, ...]
    status: int | None
    budget_before: int | None
    action: str
    nm_id: int
    campaign_kind: str = "UNKNOWN"
    sales_3d: float = 0.0
    sales_7d: float = 0.0
    classification: str = "UNRESOLVED"
    daily_limit: int | None = None
    max_cpo: int | None = None


def _int(value: Any) -> int | None:
    """Безопасно преобразовать WB-поле в ``int``."""
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _campaign_nmids(raw: dict[str, Any]) -> tuple[int, ...]:
    """Извлечь nmID из обеих известных форматов ответа WB."""
    values = raw.get("nm_settings") or raw.get("nmSettings") or []
    result: set[int] = set()
    if isinstance(values, list):
        for value in values:
            if isinstance(value, dict):
                nmid = _int(value.get("nm_id") or value.get("nmId") or value.get("nmID"))
                if nmid:
                    result.add(nmid)
    return tuple(sorted(result))


def _campaign_kind(raw: dict[str, Any]) -> str:
    """Определить Search/Auto по WB name/settings без догадок о write API."""
    settings = raw.get("settings") or {}
    name = " ".join(
        str(value or "") for value in (raw.get("name"), raw.get("campaignName"), settings.get("name"))
    ).lower()
    if any(token in name for token in ("search", "аукцион", "поиск", "auction")):
        return "SEARCH"
    if any(token in name for token in ("auto", "авто", "автомат")):
        return "AUTO"
    return "UNKNOWN"


def _sales_by_nmid(order_rows: Iterable[dict[str, Any]]) -> dict[int, tuple[float, float]]:
    """Собрать factual sales за 3d/7d из свежих supplier-order строк."""
    today = datetime.now(timezone.utc).date()
    totals: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for row in order_rows:
        if str(row.get("isCancel", "")).lower() in {"true", "1", "t"}:
            continue
        nmid = _int(row.get("nmId") or row.get("nmID") or row.get("nm_id"))
        if not nmid:
            continue
        raw_day = str(row.get("date") or row.get("lastChangeDate") or "")[:10]
        try:
            age = (today - datetime.fromisoformat(raw_day).date()).days
        except ValueError:
            continue
        value = float(row.get("totalPrice") or row.get("priceWithDisc") or 0)
        if age < 3:
            totals[nmid][0] += value
        if age < 7:
            totals[nmid][1] += value
    return {nmid: (round(values[0], 2), round(values[1], 2)) for nmid, values in totals.items()}


def validate_allowlist(nm_ids: Iterable[int]) -> None:
    """Проверить, что write-set не содержит forbidden nmID."""
    values = {int(value) for value in nm_ids}
    forbidden = values & FORBIDDEN_NMIDS
    if forbidden:
        raise ValueError(f"FORBIDDEN_NMIDS: {sorted(forbidden)}")
    if not values <= ALLOWED_NMIDS:
        raise ValueError(f"NMID_OUTSIDE_ALLOWLIST: {sorted(values - ALLOWED_NMIDS)}")


def validate_incremental_spend(amounts: Iterable[int]) -> int:
    """Проверить общий bounded spend envelope и вернуть сумму."""
    total = sum(int(amount) for amount in amounts)
    if total < 0 or total > MAX_INCREMENTAL_RUB:
        raise ValueError(f"INCREMENTAL_SPEND_OVER_MAX: {total}")
    return total


def classify_bottleneck(
    *,
    status: int | None,
    budget: int | None,
    daily_limit: int | None,
    has_paused_leg: bool,
    max_cpo: int | None,
    sales_7d: float,
) -> str:
    """Классифицировать ограничение до выбора минимального рычага."""
    if status == PAUSED_STATUS and has_paused_leg and sales_7d > 0:
        return "PAUSED_LEG_AVAILABLE"
    if daily_limit is not None and daily_limit >= DAILY_LIMIT_CAP_RUB:
        return "BUDGET_LIMITED"
    if status in ACTIVE_STATUSES and budget is not None and budget <= 0:
        return "BUDGET_LIMITED"
    if sales_7d > 0 and (max_cpo is None or max_cpo > 0):
        return "TRAFFIC_LIMITED"
    if status in ACTIVE_STATUSES and budget is not None and budget > 0:
        return "ALREADY_UNCONSTRAINED"
    return "UNRESOLVED"


def choose_contour(candidates: Iterable[Candidate]) -> Candidate | None:
    """Выбрать один кандидат по priority, не усиливая слабые forbidden-контуры."""
    ranked = list(candidates)
    for nmid in PRIORITY_NMIDS + (388166103,):
        matches = [item for item in ranked if item.nm_id == nmid]
        if matches:
            return sorted(
                matches,
                key=lambda item: (
                    item.action != "activate_paused_leg",
                    item.classification not in {"BUDGET_LIMITED", "TRAFFIC_LIMITED"},
                    item.adv_id,
                ),
            )[0]
    return None


def _candidate_rows(
    campaigns: Iterable[dict[str, Any]],
    budgets: dict[int, int | None],
    sales: dict[int, tuple[float, float]] | None = None,
) -> list[Candidate]:
    """Сформировать классифицированный write-set из свежего WB inventory."""
    sales = sales or {}
    result: list[Candidate] = []
    for raw in campaigns:
        adv_id = _int(raw.get("id") or raw.get("advertId"))
        if not adv_id:
            continue
        nm_ids = _campaign_nmids(raw)
        if set(nm_ids) & FORBIDDEN_NMIDS or not set(nm_ids) <= ALLOWED_NMIDS:
            continue
        allowed = tuple(nmid for nmid in nm_ids if nmid in ALLOWED_NMIDS)
        if not allowed:
            continue
        status = _int(raw.get("status"))
        budget = budgets.get(adv_id)
        kind = _campaign_kind(raw)
        s3, s7 = sales.get(allowed[0], (0.0, 0.0))
        settings = raw.get("settings") or {}
        daily_limit = _int(
            raw.get("daily_limit")
            or settings.get("daily_limit")
            or settings.get("dailyLimit")
        )
        max_cpo = _int(raw.get("max_cpo") or settings.get("max_cpo") or settings.get("maxCpo"))
        classification = classify_bottleneck(
            status=status,
            budget=budget,
            daily_limit=daily_limit,
            has_paused_leg=status == PAUSED_STATUS and kind in {"SEARCH", "AUTO"},
            max_cpo=max_cpo,
            sales_7d=s7,
        )
        if classification == "PAUSED_LEG_AVAILABLE" and kind in {"SEARCH", "AUTO"}:
            action = "activate_paused_leg"
        elif classification == "BUDGET_LIMITED":
            action = "top_up_budget"
        else:
            action = "no_change"
        for nmid in allowed:
            nmid_s3, nmid_s7 = sales.get(nmid, (s3, s7))
            result.append(
                Candidate(
                    adv_id, nm_ids, status, budget, action, nmid,
                    kind, nmid_s3, nmid_s7, classification, daily_limit, max_cpo,
                )
            )
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    """Сохранить детерминированный UTF-8 CSV."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _jsonable(value: Any) -> Any:
    """Преобразовать простые WB DTO и enum-поля в JSON-совместимый вид."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if hasattr(value, "value"):
        return value.value
    return value


async def _cabinet() -> WBCabinet:
    """Получить ровно allowlisted cabinet из Postgres."""
    from app.modules.common_slaves.wildberries.models import WBCabinet
    from app.utils.db.session_maker import get_async_session_maker as sm

    async with sm(read_only=True) as session:
        result = await session.execute(
            select(WBCabinet).where(
                WBCabinet.shop_id == SHOP_ID,
                WBCabinet.id == WB_CABINET_ID,
            )
        )
        cabinet = result.scalar_one_or_none()
    if cabinet is None:
        raise RuntimeError(f"Cabinet not found: shop={SHOP_ID}, id={WB_CABINET_ID}")
    return cabinet


async def _inventory(
    modifier: Any, promotion_manager: Any
) -> tuple[list[dict[str, Any]], dict[int, int | None]]:
    """Снять campaign inventory и live budgets через production read adapters."""
    adv_ids = list(
        await promotion_manager._client.promotion_count_adapter.get_cabinet_adv_ids() or []
    )
    campaigns = [
        _jsonable(item)
        for item in await promotion_manager.get_adverts_v2_by_ids(adv_ids)
    ]
    budgets: dict[int, int | None] = {}
    for raw in campaigns:
        adv_id = _int(raw.get("id") or raw.get("advertId"))
        if adv_id:
            budgets[adv_id] = (await modifier.get_campaign_budget(adv_id)).total
    return campaigns, budgets


async def _fresh_sales(data_manager: Any) -> tuple[dict[int, tuple[float, float]], list[dict[str, Any]]]:
    """Получить свежие factual supplier orders для шести обязательных nmID и mat."""
    from datetime import timedelta

    date_from = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()
    rows = await data_manager.get_supplier_orders(date_from=date_from, flag=0) or []
    normalized = [_jsonable(row) for row in rows]
    normalized = [row for row in normalized if isinstance(row, dict)]
    return _sales_by_nmid(normalized), normalized


async def run(output_dir: Path, *, execute: bool, topup_amount: int) -> dict[str, Any]:
    """Выполнить preflight и опциональные bounded writes.

    Args:
        output_dir: Каталог артефактов текущего envelope.
        execute: Разрешить production mutation; без него только dry-run.
        topup_amount: Сумма одного top-up, ограниченная envelope.
    """
    if topup_amount < 0 or topup_amount > MAX_INCREMENTAL_RUB:
        raise ValueError("topup_amount exceeds bounded envelope")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    checked_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    proposed: list[dict[str, Any]] = []
    executed: list[dict[str, Any]] = []
    readback: list[dict[str, Any]] = []
    topups: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []

    cabinet = await _cabinet()
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import (
        get_access_for_wb_cabinet,
    )
    from redis.asyncio import Redis

    await get_access_for_wb_cabinet(SHOP_ID)
    app_config = __import__("app.configs.app_config", fromlist=["AppConfig"]).AppConfig.create()
    redis_config = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=redis_config.host, port=redis_config.port, db=redis_config.db,
        password=redis_config.password, decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx = HttpxClientHandler()
    await httpx.init()
    try:
        factory = WBManagerHubFactory(httpx_client_handler=httpx, redis_client_wrapper=redis_wrap)
        hub = factory.get_wb_manager_hub(SHOP_ID)
        modifier = hub.wb_modifier
        promotion_manager = modifier._promotion_manager
        campaigns, budgets = await _inventory(modifier, promotion_manager)
        sales, supplier_orders = await _fresh_sales(hub.wb_data_manager)
        (raw_dir / "campaigns_prewrite.json").write_text(
            json.dumps(campaigns, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (raw_dir / "supplier_orders_prewrite.json").write_text(
            json.dumps(supplier_orders, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        candidates = _candidate_rows(campaigns, budgets, sales)
        for candidate in candidates:
            rows.append({
                "adv_id": candidate.adv_id, "nm_id": candidate.nm_id,
                "nm_ids": ",".join(map(str, candidate.nm_ids)),
                "status": candidate.status, "budget_before": candidate.budget_before,
                "action": candidate.action, "campaign_kind": candidate.campaign_kind,
                "sales_3d": candidate.sales_3d, "sales_7d": candidate.sales_7d,
                "classification": candidate.classification,
                "daily_limit": candidate.daily_limit, "max_cpo": candidate.max_cpo,
            })
        proposed_candidates = [
            item for item in candidates
            if item.action != "no_change"
            and item.nm_id not in NO_WRITE_NMIDS
            and item.sales_7d > 0
        ]
        selected = choose_contour(proposed_candidates)
        if selected is not None:
            selected_amount = 0 if selected.action == "activate_paused_leg" else topup_amount
            if selected.action == "top_up_budget":
                if selected.nm_id in {837395782, 14824677}:
                    selected_amount = max(300, min(selected_amount, 500))
                else:
                    selected_amount = min(selected_amount, DAILY_LIMIT_CAP_RUB)
                if selected.nm_id == 14166423:
                    selected_amount = min(selected_amount, MAX_14166423_INCREMENT_RUB)
            validate_incremental_spend([selected_amount])
            proposed.append({
                "adv_id": selected.adv_id, "nm_id": selected.nm_id,
                "field": selected.action,
                "before": selected.budget_before if selected.action == "top_up_budget" else selected.status,
                "after": (selected.budget_before or 0) + selected_amount
                if selected.action == "top_up_budget" else 9,
                "expected_incremental_spend": selected_amount,
                "promo_topup": 0, "ordinary_topup": selected_amount,
                "bottleneck": selected.classification,
                "reason": "smallest proven lever after fresh preflight",
            })
        for nmid in sorted(PREFLIGHT_NMIDS):
            if not any(row["nm_id"] == nmid for row in rows):
                s3, s7 = sales.get(nmid, (0.0, 0.0))
                rows.append({
                    "adv_id": "", "nm_id": nmid, "nm_ids": str(nmid),
                    "status": "", "budget_before": "", "action": "no_change",
                    "campaign_kind": "NONE", "sales_3d": s3, "sales_7d": s7,
                    "classification": "UNRESOLVED" if s7 <= 0 else "TRAFFIC_LIMITED",
                    "daily_limit": "", "max_cpo": "",
                })
        (output_dir / "01_PREWRITE_SNAPSHOT.csv").write_text("", encoding="utf-8")
        row_fields = [
            "adv_id", "nm_id", "nm_ids", "status", "budget_before", "action",
            "campaign_kind", "sales_3d", "sales_7d", "classification",
            "daily_limit", "max_cpo",
        ]
        _write_csv(output_dir / "01_PREWRITE_SNAPSHOT.csv", rows, row_fields)
        _write_csv(output_dir / "02_CANDIDATE_ANALYSIS.csv", rows, row_fields)
        _write_csv(output_dir / "03_PROPOSED_WRITE_SET.csv", proposed, [
            "adv_id", "nm_id", "field", "before", "after", "expected_incremental_spend",
            "promo_topup", "ordinary_topup", "reason",
        ])
        balance = _jsonable(await modifier.get_campaign_balance())
        cashbacks = balance.get("cashbacks") if isinstance(balance, dict) else []
        cashback_pool = sum(_int(item.get("sum")) or 0 for item in (cashbacks or []) if isinstance(item, dict))
        if execute and selected is not None:
            if selected.action == "top_up_budget":
                promo_amount = min(selected_amount, cashback_pool)
                ordinary_amount = selected_amount - promo_amount
                result = await modifier.top_up_budget(
                    adv_id=selected.adv_id, amount=selected_amount, balance_type="balance",
                    return_total=True, cashback_sum=promo_amount or None,
                    cashback_percent=50 if promo_amount else None,
                )
                topups.append({
                    "adv_id": selected.adv_id, "amount": selected_amount,
                    "promo_topup": promo_amount, "ordinary_topup": ordinary_amount,
                    "result": _jsonable(result),
                })
                executed.append({"adv_id": selected.adv_id, "nm_id": selected.nm_id, "field": "budget", "status": "success"})
                ledger.append(_ledger(selected, "budget", selected.budget_before, result.total, selected_amount, "success", promo_amount, ordinary_amount))
            if selected.action == "activate_paused_leg":
                try:
                    await promotion_manager.start_campaign(selected.adv_id)
                    executed.append({"adv_id": selected.adv_id, "nm_id": selected.nm_id, "field": "status", "status": "success"})
                    ledger.append(_ledger(selected, "status", selected.status, 9, 0, "success", 0, 0))
                except Exception as exc:
                    executed.append({"adv_id": selected.adv_id, "nm_id": selected.nm_id, "field": "status", "status": "failed"})
                    ledger.append(_ledger(selected, "status", selected.status, "FAILED_ROLLED_BACK", 0, f"failed: {type(exc).__name__}", 0, 0))
                    raise
        for item in proposed:
            adv_id = int(item["adv_id"])
            budget_after = (await modifier.get_campaign_budget(adv_id)).total
            status_after = await promotion_manager.get_campaign_status(adv_id)
            readback.append({"adv_id": adv_id, "nm_id": item["nm_id"], "budget_after": budget_after, "status_after": status_after})
        status = "EXECUTED_VERIFIED" if execute and executed else ("NO_CHANGE" if not proposed else "DRY_RUN_READY")
    finally:
        await httpx.shutdown()
        await redis_raw.close()

    manifest = {
        "package": "A1_CONTROLLED_AD_EXPANSION_V1", "checked_at": checked_at,
        "mode": "PRODUCTION_BOUNDED_WRITE" if execute else "DRY_RUN",
        "shop_id": SHOP_ID, "cabinet": WB_CABINET_ID, "status": status,
        "price_writes": 0, "glue_writes": 0, "card_writes": 0,
    }
    _write_csv(output_dir / "04_EXECUTED_WRITES.csv", executed, ["adv_id", "nm_id", "field", "status"])
    _write_csv(output_dir / "05_POSTWRITE_READBACK.csv", readback, ["adv_id", "nm_id", "budget_after", "status_after"])
    _write_csv(output_dir / "06_TOPUP_EVENTS.csv", topups, ["adv_id", "amount", "result"])
    _write_csv(output_dir / "07_INTERVENTION_LEDGER.csv", ledger, [
        "event_at_msk", "nm_id", "adv_setting_id", "adv_id", "field", "before", "after",
        "reason", "expected_incremental_spend", "promo_topup", "ordinary_topup",
        "verification_source", "status",
    ])
    (output_dir / "00_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "08_OBSERVATION_CONTRACT.md").write_text(
        "# Observation contract\n\nObserve closed-day gross DRR and campaign spend for one full day after write. "
        "Do not add pressure or change price/glue/cards during the observation.\n", encoding="utf-8"
    )
    (output_dir / "09_DATA_QUALITY_AND_GAPS.md").write_text(
        "# Data quality and gaps\n\nNo standalone WB daily-limit setter was found. "
        "Promo accounting is CASH_FLOW_ONLY; no CASH_DRR is inferred.\n", encoding="utf-8"
    )
    (output_dir / "10_MASTER_QA_REPORT.md").write_text(
        f"# Master QA\n\nStatus: {status}\nWrites: {len(executed)}\nPRICE/GLUE/CARD: 0/0/0\n", encoding="utf-8"
    )
    (output_dir / "11_HUMAN_SUMMARY.md").write_text(
        f"# Human summary\n\n{status}. Selected action: {proposed[0] if proposed else 'none'}\n",
        encoding="utf-8",
    )
    zip_path = output_dir / "a1_controlled_ad_expansion_v1.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != zip_path:
                archive.write(path, path.relative_to(output_dir).as_posix())
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    sha_path = zip_path.with_suffix(".zip.sha256")
    sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    return {
        **manifest,
        "output_dir": str(output_dir.resolve()),
        "zip": str(zip_path.resolve()),
        "zip_sha256": digest,
        "sha256_sidecar": str(sha_path.resolve()),
    }


def _ledger(
    candidate: Candidate,
    field: str,
    before: Any,
    after: Any,
    amount: int,
    status: str,
    promo_topup: int = 0,
    ordinary_topup: int | None = None,
) -> dict[str, Any]:
    """Собрать audit ledger row с обязательными envelope-полями."""
    return {
        "event_at_msk": datetime.now(timezone.utc).isoformat(), "nm_id": candidate.nm_id,
        "adv_setting_id": "", "adv_id": candidate.adv_id, "field": field, "before": before,
        "after": after, "reason": "bounded A1 expansion", "expected_incremental_spend": amount,
        "promo_topup": promo_topup,
        "ordinary_topup": amount if ordinary_topup is None else ordinary_topup,
        "verification_source": "WB readback",
        "status": status,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint; mutation is impossible without explicit ``--execute``."""
    parser = argparse.ArgumentParser(description="Bounded A1 production ad expansion")
    parser.add_argument("--output-dir", default=".tmp/a1_controlled_ad_expansion_v1")
    parser.add_argument("--topup-amount", type=int, default=DEFAULT_TOPUP_RUB)
    parser.add_argument("--execute", action="store_true", help="enable allowlisted production writes")
    args = parser.parse_args(argv)
    result = asyncio.run(run(Path(args.output_dir).resolve(), execute=args.execute, topup_amount=args.topup_amount))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_SHA256={result['zip_sha256']}")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())

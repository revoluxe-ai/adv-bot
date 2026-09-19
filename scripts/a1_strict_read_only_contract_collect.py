"""STRICT_READ_ONLY factual collector for the A1 Web handoff contract.

Модуль собирает только фактические snapshots из уже существующих
read-only WB/PG adapters: состояние кампаний, closed-day performance,
топологию карточек, store aggregates, promo balance и доступный top-up log.
Он не содержит анализа, рекомендаций или production write-paths. Результат
имеет фиксированный ZIP-контракт с локальным SHA-256 sidecar.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from tools.scripts.receipts import (
    invocation_output_path,
    prepare_invocation_output_dir,
)
from scripts import ch_a1_evidence as evidence
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


# Identity is supplied by the invocation contract. Compatibility wrappers set
# these module values before calling ``run_collect``.
SHOP_ID = ""
EXPECTED_WB_CABINET_ID = 0
MSK = ZoneInfo("Europe/Moscow")
PACKAGE_NAME = "A1-STRICT-READ-ONLY-CONTRACT"

TARGET_NMIDS: frozenset[int] = frozenset()
RECONCILE_CAMPAIGNS: dict[int, frozenset[int]] = {
    837395782: frozenset({39900256, 39900211}),
    14824677: frozenset({39943926, 39943851}),
}
PERFORMANCE_WINDOWS = (1, 3, 7, 14)
PG_SETTING_FIELDS = (
    "id",
    "adv_id",
    "_search_adv_id",
    "type",
    "name",
    "nmids",
    "active_status",
    "bot_active",
    "automatic_version",
    "strategy",
    "aggressiveness",
    "target_price_for_order",
    "max_price_for_order",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "wb_bid_type",
    "wb_placement_search",
    "wb_placement_recommendations",
)
SAFETY_WRITE_COUNTS = {
    "WB_API_WRITES": 0,
    "CAMPAIGN_WRITES": 0,
    "STATUS_WRITES": 0,
    "BID_WRITES": 0,
    "BUDGET_WRITES": 0,
    "TOPUP_WRITES": 0,
    "CPO_WRITES": 0,
    "AGGRESSION_WRITES": 0,
    "EXCEL_WRITES": 0,
    "POSTGRES_WRITES": 0,
    "CLICKHOUSE_WRITES": 0,
    "REDIS_WRITES": 0,
}
PRIMARY_FILES = (
    "00_MANIFEST.json",
    "01_STORE.csv",
    "02_CAMPAIGNS_CURRENT.csv",
    "03_PERFORMANCE.csv",
    "04_MATS.csv",
    "05_PROMO.json",
    "06_TOPUPS.csv",
    "07_GAPS.md",
)


class _SourceError(RuntimeError):
    """Ошибка read-only источника с привязкой к coverage gap."""

    def __init__(self, source: str, error: str, coverage_gap: str) -> None:
        super().__init__(error)
        self.source = source
        self.error = error
        self.coverage_gap = coverage_gap


def _msk_now() -> datetime:
    """Вернуть текущее время в часовом поясе контракта."""
    return datetime.now(timezone.utc).astimezone(MSK)


def _iso_msk(value: datetime) -> str:
    """Сериализовать timestamp в ISO-8601 с Europe/Moscow offset."""
    return value.astimezone(MSK).isoformat()


def _closed_end_day(now: datetime | None = None) -> date:
    """Вернуть последний полностью закрытый день: вчера по MSK."""
    return (now or _msk_now()).date() - timedelta(days=1)


def _closed_dates(closed_end: date, days: int) -> set[str]:
    """Вернуть ровно ``days`` closed-day дат, заканчивая ``closed_end``."""
    start = closed_end - timedelta(days=days - 1)
    return {
        (start + timedelta(days=offset)).isoformat() for offset in range(days)
    }


def _window_bounds(closed_end: date, days: int) -> tuple[date, date]:
    """Вернуть начало и конец closed-only окна."""
    return closed_end - timedelta(days=days - 1), closed_end


def _pg_database() -> str:
    """Получить имя PostgreSQL database из штатной конфигурации."""
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap_cluster_infra() -> None:
    """Переключить существующий PG adapter на in-cluster endpoints."""
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    if user and password:
        evidence._PG_CREDENTIALS = user, password
    pg_host = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get(
        "POSTGRES_REPLICA_HOST"
    )
    pg_port = os.environ.get("POSTGRES_PORT")
    if pg_host:
        evidence.PG_EXTERNAL_HOST = pg_host
    if pg_port:
        evidence.PG_EXTERNAL_PORT = int(pg_port)


def _safe_error(value: Any) -> str:
    """Сделать ошибку однострочной и удалить очевидные credential values."""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return re.sub(
        r"(?i)(password|token|secret|authorization)\s*[=:]\s*\S+",
        r"\1=<redacted>",
        text,
    )[:1000]


def _gap_line(source: str, error: Any, coverage_gap: str) -> str:
    """Сформировать единственный допустимый формат строки ``07_GAPS.md``."""
    return (
        f"- source={source}; error={_safe_error(error)}; "
        f"coverage_gap={coverage_gap}"
    )


def _write_gaps(path: Path, gaps: list[str]) -> None:
    """Записать только source/error/coverage-gap сведения."""
    lines = ["# Gaps", ""]
    lines.extend(gaps)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    """Записать UTF-8 CSV с фиксированной схемой контракта."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Записать raw rows в UTF-8 JSONL без credential enrichment."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(_jsonable(row), ensure_ascii=False, separators=(",", ":"))
            )
            handle.write("\n")


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Прочитать CSV, возвращая пустой список для пустого результата."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_nmids(raw: Any) -> list[int]:
    """Нормализовать PG ``nmids`` JSON-поле без эвристических замен."""
    if isinstance(raw, (list, tuple)):
        values = raw
    else:
        text = str(raw or "").strip()
        if not text:
            return []
        try:
            values = json.loads(text.replace("'", '"'))
        except json.JSONDecodeError:
            return []
    if not isinstance(values, list):
        return []
    result: list[int] = []
    for value in values:
        try:
            nmid = int(value)
        except (TypeError, ValueError):
            continue
        if nmid:
            result.append(nmid)
    return sorted(set(result))


def _model_dict(value: Any) -> dict[str, Any]:
    """Привести generated WB model к обычному словарю."""
    if isinstance(value, dict):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        if isinstance(result, dict):
            return result
    return {}


def _field_or_gap(value: Any) -> Any:
    """Сохранить валидные false/zero values и заменить только отсутствующие."""
    return "GAP" if value in (None, "") else value


def _campaign_nmids(
    campaign: dict[str, Any], pg_row: dict[str, str] | None = None
) -> set[int]:
    """Извлечь только явно присутствующие nmID из WB/PG campaign state."""
    result: set[int] = set()
    nm_settings = campaign.get("nm_settings") or campaign.get("nmSettings") or []
    if isinstance(nm_settings, list):
        for item in nm_settings:
            if isinstance(item, dict):
                nmid = _read_int(item, "nm_id", "nmId", "nmID")
                if nmid:
                    result.add(nmid)
    if pg_row:
        result.update(_parse_nmids(pg_row.get("nmids")))
    return result


def _campaign_id(campaign: dict[str, Any]) -> int:
    """Получить WB campaign/advert ID из известных API naming variants."""
    return _read_int(campaign, "id", "advertId", "advert_id")


def _campaign_type(
    campaign: dict[str, Any], pg_row: dict[str, str] | None
) -> str:
    """Вернуть тип кампании из raw/API fields без business classification."""
    settings = campaign.get("settings")
    settings_dict = settings if isinstance(settings, dict) else {}
    for source in (campaign, settings_dict, pg_row or {}):
        for key in ("campaign_type", "type"):
            value = source.get(key)
            if value not in (None, ""):
                return str(value)
    bid_type = campaign.get("bid_type") or campaign.get("bidType")
    payment_type = settings_dict.get("payment_type")
    if bid_type not in (None, "") and payment_type not in (None, ""):
        return f"{bid_type}/{payment_type}"
    if bid_type not in (None, ""):
        return str(bid_type)
    if payment_type not in (None, ""):
        return str(payment_type)
    return "GAP"


def _placements(
    campaign: dict[str, Any], pg_row: dict[str, str] | None
) -> str:
    """Сериализовать WB/PG placement flags как фактический JSON."""
    settings = campaign.get("settings")
    settings_dict = settings if isinstance(settings, dict) else {}
    raw = settings_dict.get("placements") or campaign.get("placements")
    if isinstance(raw, dict):
        return json.dumps(raw, ensure_ascii=False, sort_keys=True)
    if pg_row and (
        pg_row.get("wb_placement_search") not in (None, "")
        or pg_row.get("wb_placement_recommendations") not in (None, "")
    ):
        return json.dumps(
            {
                "search": pg_row.get("wb_placement_search"),
                "recommendations": pg_row.get("wb_placement_recommendations"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    return "GAP"


def _pg_maps(
    pg_rows: list[dict[str, str]],
) -> tuple[dict[int, dict[str, str]], dict[int, dict[str, str]]]:
    """Построить auto- и search-campaign maps на одну PG advsetting."""
    by_auto: dict[int, dict[str, str]] = {}
    by_search: dict[int, dict[str, str]] = {}
    for row in pg_rows:
        auto_id = _read_int(row, "adv_id")
        search_id = _read_int(row, "_search_adv_id")
        if auto_id:
            by_auto[auto_id] = row
        if search_id:
            by_search[search_id] = row
    return by_auto, by_search


def _pg_row_for_campaign(
    campaign_id: int,
    by_auto: dict[int, dict[str, str]],
    by_search: dict[int, dict[str, str]],
) -> dict[str, str]:
    """Найти PG state для auto либо search campaign ID."""
    return by_auto.get(campaign_id) or by_search.get(campaign_id) or {}


def _load_pg_identity_and_settings(
    root: Path,
) -> tuple[int, list[dict[str, str]]]:
    """Загрузить cabinet identity и factual advsetting state через PG SELECT."""
    raw_dir = root / "raw"
    sql_dir = raw_dir / "sql"
    raw_dir.mkdir(parents=True, exist_ok=True)
    identity_path = raw_dir / "wbcabinet.csv"
    identity_query = (
        "SELECT id, shop_id, balance, bonus "
        "FROM public.wbcabinet "
        "WHERE shop_id = $1"
    )
    identity_status = evidence.run_pg_query(
        _pg_database(),
        identity_query,
        identity_path,
        sql_dir / "pg_wbcabinet_shop.sql",
        query_params=(SHOP_ID,),
        csv_output=True,
    )
    if not identity_status["success"]:
        raise _SourceError(
            "PG public.wbcabinet",
            identity_status["stderr"],
            "shop-to-wb-cabinet identity",
        )
    identity_rows = _read_csv(identity_path)
    if not identity_rows:
        raise _SourceError(
            "PG public.wbcabinet",
            "no row for requested shop_id",
            "shop-to-wb-cabinet identity",
        )
    try:
        wb_cabinet_id = int(identity_rows[0].get("id") or 0)
    except (TypeError, ValueError) as exc:
        raise _SourceError(
            "PG public.wbcabinet",
            f"invalid cabinet id: {identity_rows[0].get('id')}",
            "shop-to-wb-cabinet identity",
        ) from exc
    if wb_cabinet_id != EXPECTED_WB_CABINET_ID:
        raise _SourceError(
            "PG public.wbcabinet",
            f"expected wb_cabinet_id={EXPECTED_WB_CABINET_ID}, got {wb_cabinet_id}",
            "requested wb_cabinet_id",
        )

    settings_path = raw_dir / "advsetting.csv"
    columns = ", ".join(f"a.{field}" for field in PG_SETTING_FIELDS)
    settings_query = (
        f"SELECT {columns} "
        "FROM public.advsetting a "
        "JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        "WHERE c.shop_id = $1"
    )
    settings_status = evidence.run_pg_query(
        _pg_database(),
        settings_query,
        settings_path,
        sql_dir / "pg_advsetting_shop.sql",
        query_params=(SHOP_ID,),
        csv_output=True,
    )
    if not settings_status["success"]:
        raise _SourceError(
            "PG public.advsetting",
            settings_status["stderr"],
            "campaign/bot state fields",
        )
    return wb_cabinet_id, _read_csv(settings_path)


def _load_topups(
    root: Path, wb_cabinet_id: int, closed_end: date
) -> tuple[list[dict[str, str]], str | None]:
    """Загрузить доступный last-7-closed-day top-up log без raw payload export."""
    raw_dir = root / "raw"
    sql_dir = raw_dir / "sql"
    path = raw_dir / "topups_source.csv"
    date_from = closed_end - timedelta(days=6)
    query = (
        "SELECT t.id, t.adv_setting_id, t.adv_id, t.campaign_type, "
        "t.date_msk, t.amount, t.request_payload, t.created_at "
        "FROM public.wbautobudgettopup t "
        "JOIN public.advsetting a ON t.adv_setting_id = a.id "
        "WHERE a.wb_cabinet_id = $1 "
        "AND t.date_msk >= $2 "
        "ORDER BY t.created_at"
    )
    status = evidence.run_pg_query(
        _pg_database(),
        query,
        path,
        sql_dir / "pg_wbautobudgettopup_last_7_closed.sql",
        query_params=(wb_cabinet_id, date_from),
        csv_output=True,
    )
    if not status["success"]:
        return [], _safe_error(status["stderr"])
    return _read_csv(path), None


def _timestamp_msk(row: dict[str, str]) -> str:
    """Нормализовать top-up timestamp в Europe/Moscow, если он parseable."""
    raw = str(row.get("created_at") or row.get("date_msk") or "")
    if not raw:
        return "GAP"
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return _iso_msk(value)


def _topup_day(row: dict[str, str]) -> date | None:
    """Извлечь MSK date для closed-window фильтра."""
    timestamp = _timestamp_msk(row)
    try:
        return datetime.fromisoformat(timestamp).date()
    except ValueError:
        raw = str(row.get("date_msk") or "")[:10]
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None


def _json_object(raw: Any) -> dict[str, Any]:
    """Безопасно распарсить request_payload top-up."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        value = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _normalize_topups(
    rows: list[dict[str, str]], closed_end: date
) -> list[dict[str, Any]]:
    """Оставить last seven closed days и вернуть только contract fields."""
    date_from = closed_end - timedelta(days=6)
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        day = _topup_day(row)
        if day is None or not date_from <= day <= closed_end:
            continue
        key = str(row.get("id") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        try:
            total = float(row.get("amount") or 0)
        except (TypeError, ValueError):
            total = 0.0
        request = _json_object(row.get("request_payload"))
        try:
            promo = float(request.get("cashback_sum") or 0)
        except (TypeError, ValueError):
            promo = 0.0
        normalized.append(
            {
                "timestamp": _timestamp_msk(row),
                "adv_id": row.get("adv_id") or "GAP",
                "total": round(total, 2),
                "promo": round(promo, 2),
                "ordinary": round(max(total - promo, 0.0), 2),
            }
        )
    return normalized


async def _collect_wb(
    root: Path,
    closed_end: date,
    pg_rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Собрать raw WB campaigns/cards/orders/fullstats/balance/budgets."""
    from app.core.di.app_container import AppContainer
    from app.core.di.di_manager import DIManager
    from app.core.mp.wb.api.adapter.promotion_client.fullstats.chunked import (
        run_chunked_single_range,
    )

    raw_dir = root / "raw"
    begin = closed_end - timedelta(days=13)
    async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
        factory = (
            container.module_resources.wb_manager_hub_factory_container
            .wb_manager_hub_factory()
        )
        hub = factory.get_wb_manager_hub(SHOP_ID)
        dm = hub.wb_data_manager
        promotion = dm.promotion_manager
        finance = promotion._client.finance_adapter
        budget = ApiCallBudget(max_seconds=1800.0, max_api_calls=5000)

        balance_response = await finance.get_campaign_balance()
        balance_raw = _model_dict(balance_response)

        cabinet_ids_raw = await promotion._client.promotion_count_adapter.get_cabinet_adv_ids()
        cabinet_adv_ids = sorted(
            {int(value) for value in (cabinet_ids_raw or []) if str(value).isdigit()}
        )
        campaigns_response = await promotion.get_adverts_v2_by_ids(cabinet_adv_ids)
        campaigns = [
            jsonable(item)
            for item in (campaigns_response or [])
            if isinstance(jsonable(item), dict)
        ]

        cards_store = RawStore(raw_dir / "cards_api")
        _, cards = await collect_cards(
            dm,
            store=cards_store,
            budget=budget,
            page_limit=100,
        )

        reports_manager = getattr(dm, "reports_manager", None)

        async def fetch_orders(date_from: str) -> list[object]:
            if reports_manager is not None:
                return list(
                    await reports_manager.get_supplier_orders(
                        date_from=date_from, flag=0
                    )
                    or []
                )
            return list(await dm.get_supplier_orders(date_from=date_from, flag=0) or [])

        orders_result = await _paginate_supplier_rows(
            fetch=fetch_orders,
            initial_date_from=begin.isoformat(),
            budget=budget,
            max_pages=1500,
        )
        orders = [
            jsonable(row)
            for row in orders_result.rows
            if isinstance(jsonable(row), dict)
        ]

        fullstats_ids = sorted(set(cabinet_adv_ids) | set().union(*RECONCILE_CAMPAIGNS.values()))
        fullstats_raw: list[dict[str, Any]] = []
        if fullstats_ids:
            adapter = promotion._client.fullstats_adapter

            async def fetcher(
                chunk: list[int], from_day: date, to_day: date
            ) -> list[Any]:
                return await adapter._request_chunk(chunk, from_day, to_day)

            fullstats_items = await run_chunked_single_range(
                fullstats_ids,
                begin,
                closed_end,
                fetcher,
            )
            fullstats_raw = [
                _jsonable(item.to_dict())
                for item in fullstats_items
                if hasattr(item, "to_dict")
            ]

        by_auto, by_search = _pg_maps(pg_rows)
        card_by_nmid = {
            _read_int(card, "nmID", "nmId", "nmid"): card
            for card in cards
            if _read_int(card, "nmID", "nmId", "nmid")
        }
        scope_nmids = _scope_nmids(card_by_nmid)
        campaign_map: dict[int, set[int]] = defaultdict(set)
        for campaign in campaigns:
            campaign_map[_campaign_id(campaign)].update(
                _campaign_nmids(campaign, _pg_row_for_campaign(_campaign_id(campaign), by_auto, by_search))
            )
        for row in pg_rows:
            setting_nmids = set(_parse_nmids(row.get("nmids")))
            auto_id = _read_int(row, "adv_id")
            search_id = _read_int(row, "_search_adv_id")
            if auto_id:
                campaign_map[auto_id].update(setting_nmids)
            if search_id:
                campaign_map[search_id].update(setting_nmids)
        relevant_budget_ids = {
            campaign_id
            for campaign_id, nmids in campaign_map.items()
            if nmids & scope_nmids
        }
        relevant_budget_ids.update(
            campaign_id
            for campaign_ids in RECONCILE_CAMPAIGNS.values()
            for campaign_id in campaign_ids
        )
        budgets: dict[int, Any] = {}
        budget_errors: dict[int, str] = {}
        for campaign_id in sorted(relevant_budget_ids):
            try:
                response = await finance.get_campaign_budget(campaign_id)
                data = _model_dict(response)
                budgets[campaign_id] = data.get("total", "GAP")
            except Exception as exc:  # noqa: BLE001
                budget_errors[campaign_id] = _safe_error(exc)

    _write_jsonl(raw_dir / "content_cards.jsonl", cards)
    _write_jsonl(raw_dir / "campaigns_v2.jsonl", campaigns)
    _write_jsonl(raw_dir / "supplier_orders.jsonl", orders)
    _write_jsonl(raw_dir / "fullstats_v3.jsonl", fullstats_raw)
    (raw_dir / "balance.json").write_text(
        json.dumps(_jsonable(balance_raw), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_jsonl(
        raw_dir / "campaign_budgets.jsonl",
        [
            {"adv_id": campaign_id, "campaign_balance": balance}
            for campaign_id, balance in sorted(budgets.items())
        ],
    )
    return {
        "balance": balance_raw,
        "campaigns": campaigns,
        "cards": cards,
        "orders": orders,
        "fullstats": fullstats_raw,
        "budgets": budgets,
        "budget_errors": budget_errors,
        "cabinet_adv_ids": cabinet_adv_ids,
    }


def _scope_nmids(card_by_nmid: dict[int, dict[str, Any]]) -> set[int]:
    """Вернуть target nmIDs плюс members двух явно заданных IMT groups."""
    members_by_imt: dict[int, set[int]] = defaultdict(set)
    for nmid, card in card_by_nmid.items():
        imt = _read_int(card, "imtID", "imtId", "imt_id")
        if imt:
            members_by_imt[imt].add(nmid)
    result = set(TARGET_NMIDS)
    for seed in (85970344, 388166103):
        imt = _read_int(card_by_nmid.get(seed, {}), "imtID", "imtId", "imt_id")
        if imt:
            result.update(members_by_imt.get(imt, set()))
    return result


def _campaign_map(
    campaigns: list[dict[str, Any]], pg_rows: list[dict[str, str]]
) -> tuple[dict[int, set[int]], dict[int, dict[str, Any]]]:
    """Сопоставить campaign ID с nmIDs и сохранить WB raw state."""
    by_auto, by_search = _pg_maps(pg_rows)
    nmids_by_campaign: dict[int, set[int]] = defaultdict(set)
    raw_by_campaign: dict[int, dict[str, Any]] = {}
    for campaign in campaigns:
        campaign_id = _campaign_id(campaign)
        if not campaign_id:
            continue
        raw_by_campaign[campaign_id] = campaign
        nmids_by_campaign[campaign_id].update(
            _campaign_nmids(campaign, _pg_row_for_campaign(campaign_id, by_auto, by_search))
        )
    for row in pg_rows:
        nmids = set(_parse_nmids(row.get("nmids")))
        for key in ("adv_id", "_search_adv_id"):
            campaign_id = _read_int(row, key)
            if campaign_id:
                nmids_by_campaign[campaign_id].update(nmids)
    return nmids_by_campaign, raw_by_campaign


def _related_campaign_ids(
    nmids_by_campaign: dict[int, set[int]], scope_nmids: set[int]
) -> set[int]:
    """Вернуть unique campaigns touching the requested topology plus reconciles."""
    result = {
        campaign_id
        for campaign_id, campaign_nmids in nmids_by_campaign.items()
        if campaign_nmids & scope_nmids
    }
    result.update(
        campaign_id
        for campaign_ids in RECONCILE_CAMPAIGNS.values()
        for campaign_id in campaign_ids
    )
    return result


def _target_campaign_ids(
    nmid: int, nmids_by_campaign: dict[int, set[int]]
) -> set[int]:
    """Вернуть campaigns for one target, включая его independent reconcile IDs."""
    result = {
        campaign_id
        for campaign_id, campaign_nmids in nmids_by_campaign.items()
        if nmid in campaign_nmids
    }
    result.update(RECONCILE_CAMPAIGNS.get(nmid, frozenset()))
    return result


def _aggregate_day_rows(
    fullstats_raw: list[dict[str, Any]], closed_end: date
) -> dict[tuple[int, str], dict[str, Any]]:
    """Агрегировать campaign-day totals, не используя nm-level spend повторно."""
    _, day_rows = _nm_rows(fullstats_raw)
    result: dict[tuple[int, str], dict[str, Any]] = {}
    for row in day_rows:
        campaign_id = _read_int(row, "advert_id", "advertId")
        day = str(row.get("date") or "")[:10]
        try:
            parsed_day = date.fromisoformat(day)
        except ValueError:
            continue
        if not campaign_id or parsed_day > closed_end:
            continue
        key = campaign_id, day
        bucket = result.setdefault(
            key,
            {
                "adv_id": campaign_id,
                "date": day,
                "views": 0,
                "clicks": 0,
                "spend": 0.0,
            },
        )
        bucket["views"] += _read_int(row, "day_views", "views")
        bucket["clicks"] += _read_int(row, "day_clicks", "clicks")
        bucket["spend"] += _read_float(row, "day_spend", "sum", "spend")
    for bucket in result.values():
        bucket["spend"] = round(float(bucket["spend"]), 2)
    return result


def _aggregate_nm_rows(
    fullstats_raw: list[dict[str, Any]], closed_end: date
) -> dict[tuple[int, str, int], dict[str, Any]]:
    """Агрегировать nm attribution для direct/associated factual metrics."""
    nm_rows, _ = _nm_rows(fullstats_raw)
    result: dict[tuple[int, str, int], dict[str, Any]] = {}
    for row in nm_rows:
        campaign_id = _read_int(row, "advert_id", "advertId")
        ordered_nmid = _read_int(row, "ordered_nm_id", "nmID", "nmId")
        day = str(row.get("date") or "")[:10]
        try:
            parsed_day = date.fromisoformat(day)
        except ValueError:
            continue
        if not campaign_id or not ordered_nmid or parsed_day > closed_end:
            continue
        key = campaign_id, day, ordered_nmid
        bucket = result.setdefault(
            key,
            {
                "adv_id": campaign_id,
                "date": day,
                "nm_id": ordered_nmid,
                "views": 0,
                "clicks": 0,
                "carts": 0,
                "orders": 0,
                "gmv": 0.0,
            },
        )
        bucket["views"] += _read_int(row, "views")
        bucket["clicks"] += _read_int(row, "clicks")
        bucket["carts"] += _read_int(row, "atbs", "carts")
        bucket["orders"] += _read_int(row, "orders")
        bucket["gmv"] += _read_float(row, "sum_price")
    for bucket in result.values():
        bucket["gmv"] = round(float(bucket["gmv"]), 2)
    return result


def _sales_by_nmid_day(
    orders: list[dict[str, Any]], closed_end: date
) -> dict[tuple[int, str], dict[str, Any]]:
    """Агрегировать supplier orders, исключая cancelled rows и open/future dates."""
    result: dict[tuple[int, str], dict[str, Any]] = {}
    for row in orders:
        if str(row.get("isCancel")).lower() in {"true", "1", "t"}:
            continue
        nmid = _read_int(row, "nmId", "nmID", "nm_id")
        day = str(row.get("date") or row.get("lastChangeDate") or "")[:10]
        try:
            parsed_day = date.fromisoformat(day)
        except ValueError:
            continue
        if not nmid or parsed_day > closed_end:
            continue
        quantity = _read_int(row, "quantity", "qty") or 1
        price = _read_float(row, "totalPrice", "priceWithDisc", "finishedPrice")
        key = nmid, day
        bucket = result.setdefault(
            key,
            {"nmid": nmid, "date": day, "events": 0, "units": 0, "sales": 0.0},
        )
        bucket["events"] += 1
        bucket["units"] += quantity
        bucket["sales"] += price * quantity if price else 0.0
    for bucket in result.values():
        bucket["sales"] = round(float(bucket["sales"]), 2)
    return result


def _sum_sales(
    sales: dict[tuple[int, str], dict[str, Any]], nmid: int, dates: set[str]
) -> dict[str, Any]:
    """Суммировать factual supplier-order fields для одного nmID/window."""
    result = {"events": 0, "units": 0, "sales": 0.0}
    for (row_nmid, day), row in sales.items():
        if row_nmid != nmid or day not in dates:
            continue
        result["events"] += int(row["events"])
        result["units"] += int(row["units"])
        result["sales"] += float(row["sales"])
    result["sales"] = round(float(result["sales"]), 2)
    return result


def _campaign_window_metrics(
    campaign_ids: set[int],
    dates: set[str],
    day_rows: dict[tuple[int, str], dict[str, Any]],
    nm_rows: dict[tuple[int, str, int], dict[str, Any]],
    *,
    target_nmid: int | None = None,
    promoted_nmids_by_campaign: dict[int, set[int]] | None = None,
) -> dict[str, Any]:
    """Собрать factual campaign metrics из unique campaign-day/nm rows."""
    result: dict[str, Any] = {
        "ad_spend": 0.0,
        "views": 0,
        "clicks": 0,
        "carts": 0,
        "direct_orders": 0,
        "associated_orders": 0,
        "direct_gmv": 0.0,
        "associated_gmv": 0.0,
    }
    for campaign_id in campaign_ids:
        for (row_campaign_id, day), row in day_rows.items():
            if row_campaign_id != campaign_id or day not in dates:
                continue
            result["ad_spend"] += float(row["spend"])
            result["views"] += int(row["views"])
            result["clicks"] += int(row["clicks"])
        for (row_campaign_id, day, ordered_nmid), row in nm_rows.items():
            if row_campaign_id != campaign_id or day not in dates:
                continue
            promoted_nmids = (promoted_nmids_by_campaign or {}).get(campaign_id, set())
            is_direct = (
                ordered_nmid == target_nmid
                if target_nmid is not None
                else ordered_nmid in promoted_nmids
            )
            result["carts"] += int(row["carts"])
            if is_direct:
                result["direct_orders"] += int(row["orders"])
                result["direct_gmv"] += float(row["gmv"])
            else:
                result["associated_orders"] += int(row["orders"])
                result["associated_gmv"] += float(row["gmv"])
    result["ad_spend"] = round(float(result["ad_spend"]), 2)
    result["direct_gmv"] = round(float(result["direct_gmv"]), 2)
    result["associated_gmv"] = round(float(result["associated_gmv"]), 2)
    return result


def _campaign_rows(
    relevant_campaign_ids: set[int],
    scope_nmids: set[int],
    raw_by_campaign: dict[int, dict[str, Any]],
    nmids_by_campaign: dict[int, set[int]],
    pg_rows: list[dict[str, str]],
    balances: dict[int, Any],
) -> list[dict[str, Any]]:
    """Построить factual current state rows для nmID/campaign pairs."""
    by_auto, by_search = _pg_maps(pg_rows)
    rows: list[dict[str, Any]] = []
    for campaign_id in sorted(relevant_campaign_ids):
        campaign = raw_by_campaign.get(campaign_id, {})
        pg_row = _pg_row_for_campaign(campaign_id, by_auto, by_search)
        row_nmids = sorted(nmids_by_campaign.get(campaign_id, set()) & scope_nmids)
        if not row_nmids:
            row_nmids = [0]
        for nmid in row_nmids:
            rows.append(
                {
                    "nm_id": nmid or "GAP",
                    "adv_setting_id": pg_row.get("id") or "GAP",
                    "adv_id": campaign_id,
                    "campaign_type": _campaign_type(campaign, pg_row),
                    "placements": _placements(campaign, pg_row),
                    "WB_status": _field_or_gap(campaign.get("status")),
                    "PG_active_status": _field_or_gap(pg_row.get("active_status")),
                    "bot_active": _field_or_gap(pg_row.get("bot_active")),
                    "automatic_version": _field_or_gap(
                        pg_row.get("automatic_version")
                    ),
                    "strategy": _field_or_gap(pg_row.get("strategy")),
                    "aggressiveness": _field_or_gap(pg_row.get("aggressiveness")),
                    "target_CPO": _field_or_gap(
                        pg_row.get("target_price_for_order")
                    ),
                    "max_CPO": _field_or_gap(pg_row.get("max_price_for_order")),
                    "Auto_daily_limit": _field_or_gap(
                        pg_row.get("auto_budget_daily_limit")
                    ),
                    "Search_daily_limit": _field_or_gap(
                        pg_row.get("search_auto_budget_daily_limit")
                    ),
                    "campaign_balance": balances.get(campaign_id, "GAP"),
                }
            )
    return rows


def _performance_rows(
    target_nmids: set[int],
    relevant_campaign_ids: set[int],
    nmids_by_campaign: dict[int, set[int]],
    day_rows: dict[tuple[int, str], dict[str, Any]],
    nm_rows: dict[tuple[int, str, int], dict[str, Any]],
    sales: dict[tuple[int, str], dict[str, Any]],
    closed_end: date,
) -> list[dict[str, Any]]:
    """Построить closed-only target rows и независимые campaign rows."""
    rows: list[dict[str, Any]] = []
    for days in PERFORMANCE_WINDOWS:
        date_from, date_to = _window_bounds(closed_end, days)
        dates = _closed_dates(closed_end, days)
        label = f"{days}d"
        for nmid in sorted(target_nmids):
            campaign_ids = _target_campaign_ids(nmid, nmids_by_campaign)
            campaign_ids &= relevant_campaign_ids
            sale = _sum_sales(sales, nmid, dates)
            metrics = _campaign_window_metrics(
                campaign_ids,
                dates,
                day_rows,
                nm_rows,
                target_nmid=nmid,
                promoted_nmids_by_campaign=nmids_by_campaign,
            )
            ad_fields: dict[str, Any]
            if campaign_ids:
                ad_fields = metrics
            else:
                ad_fields = {
                    key: "GAP"
                    for key in (
                        "ad_spend",
                        "views",
                        "clicks",
                        "carts",
                        "direct_orders",
                        "associated_orders",
                        "direct_gmv",
                        "associated_gmv",
                    )
                }
            rows.append(
                {
                    "scope": "TARGET_NMID",
                    "nm_id": nmid,
                    "campaign_id": "",
                    "campaign_ids": ",".join(str(x) for x in sorted(campaign_ids))
                    or "GAP",
                    "window": label,
                    "period_from": date_from.isoformat(),
                    "period_to": date_to.isoformat(),
                    "factual_sales": sale["sales"],
                    "units": sale["units"],
                    **ad_fields,
                }
            )
        for campaign_id in sorted(relevant_campaign_ids):
            metrics = _campaign_window_metrics(
                {campaign_id},
                dates,
                day_rows,
                nm_rows,
                promoted_nmids_by_campaign=nmids_by_campaign,
            )
            rows.append(
                {
                    "scope": "CAMPAIGN",
                    "nm_id": "",
                    "campaign_id": campaign_id,
                    "campaign_ids": campaign_id,
                    "window": label,
                    "period_from": date_from.isoformat(),
                    "period_to": date_to.isoformat(),
                    "factual_sales": "GAP",
                    "units": "GAP",
                    **metrics,
                }
            )
    return rows


def _store_rows(
    sales: dict[tuple[int, str], dict[str, Any]],
    day_rows: dict[tuple[int, str], dict[str, Any]],
    closed_end: date,
) -> list[dict[str, Any]]:
    """Построить closed-only store 3d/7d arithmetic rows."""
    rows: list[dict[str, Any]] = []
    for days in (3, 7):
        date_from, date_to = _window_bounds(closed_end, days)
        dates = _closed_dates(closed_end, days)
        events = units = 0
        factual_sales = 0.0
        for row in sales.values():
            if row["date"] not in dates:
                continue
            events += int(row["events"])
            units += int(row["units"])
            factual_sales += float(row["sales"])
        gross_ad_spend = sum(
            float(row["spend"])
            for (campaign_id, day), row in day_rows.items()
            if day in dates and campaign_id
        )
        factual_sales = round(factual_sales, 2)
        gross_ad_spend = round(gross_ad_spend, 2)
        gross_drr: float | str = (
            round(100.0 * gross_ad_spend / factual_sales, 4)
            if factual_sales
            else "GAP"
        )
        rows.append(
            {
                "window": f"{days}d",
                "period_from": date_from.isoformat(),
                "period_to": date_to.isoformat(),
                "sales": factual_sales,
                "events": events,
                "units": units,
                "gross_ad_spend": gross_ad_spend,
                "gross_drr": gross_drr,
            }
        )
    return rows


def _promo_snapshot(
    balance_raw: dict[str, Any], checked_at: datetime
) -> dict[str, Any]:
    """Вывести только свежие cashback fields из GET /adv/v1/balance."""
    raw_cashbacks = balance_raw.get("cashbacks") or []
    cashbacks: list[dict[str, Any]] = []
    for item in raw_cashbacks:
        value = _model_dict(item)
        cashbacks.append(
            {
                "cashback_sum": value.get("sum", value.get("sum_")),
                "cashback_percent": value.get("percent"),
                "expiration_date": value.get("expiration_date"),
                "checked_at_msk": _iso_msk(checked_at),
            }
        )
    sums = [row["cashback_sum"] for row in cashbacks]
    percents = [row["cashback_percent"] for row in cashbacks]
    expirations = [row["expiration_date"] for row in cashbacks]
    if len(cashbacks) == 1:
        cashback_sum: Any = sums[0]
        cashback_percent: Any = percents[0]
        expiration_date: Any = expirations[0]
    elif len(cashbacks) > 1:
        cashback_sum = round(
            sum(float(value or 0) for value in sums),
            2,
        )
        cashback_percent = percents
        expiration_date = expirations
    else:
        cashback_sum = 0
        cashback_percent = None
        expiration_date = None
    return {
        "cashback_sum": cashback_sum,
        "cashback_percent": cashback_percent,
        "expiration_date": expiration_date,
        "checked_at_msk": _iso_msk(checked_at),
        "shop_id": SHOP_ID,
        "wb_cabinet_id": EXPECTED_WB_CABINET_ID,
        "endpoint": "GET /adv/v1/balance",
        "cashbacks": cashbacks,
    }


def _mats_rows(
    mat_nmids: set[int],
    cards: dict[int, dict[str, Any]],
    nmids_by_campaign: dict[int, set[int]],
    raw_by_campaign: dict[int, dict[str, Any]],
    sales: dict[tuple[int, str], dict[str, Any]],
    day_rows: dict[tuple[int, str], dict[str, Any]],
    nm_rows: dict[tuple[int, str, int], dict[str, Any]],
    closed_end: date,
) -> list[dict[str, Any]]:
    """Построить factual rows для всей glue/mat topology."""
    rows: list[dict[str, Any]] = []
    for nmid in sorted(mat_nmids):
        campaign_ids = {
            campaign_id
            for campaign_id, campaign_nmids in nmids_by_campaign.items()
            if nmid in campaign_nmids
        }
        campaign_ids.update(RECONCILE_CAMPAIGNS.get(nmid, frozenset()))
        dates: dict[int, set[str]] = {
            days: _closed_dates(closed_end, days) for days in (3, 7, 14)
        }
        sale_windows = {
            days: _sum_sales(sales, nmid, dates[days]) for days in (3, 7, 14)
        }
        spend_windows = {
            days: round(
                sum(
                    float(row["spend"])
                    for (campaign_id, day), row in day_rows.items()
                    if campaign_id in campaign_ids and day in dates[days]
                ),
                2,
            )
            for days in (3, 7, 14)
        }
        attr_7 = _campaign_window_metrics(
            campaign_ids,
            dates[7],
            day_rows,
            nm_rows,
            target_nmid=nmid,
            promoted_nmids_by_campaign=nmids_by_campaign,
        )
        statuses = [
            f"{campaign_id}:{raw_by_campaign.get(campaign_id, {}).get('status', 'GAP')}"
            for campaign_id in sorted(campaign_ids)
        ]
        rows.append(
            {
                "nm_id": nmid,
                "title": cards.get(nmid, {}).get("title") or "GAP",
                "sales_3d": sale_windows[3]["sales"],
                "sales_7d": sale_windows[7]["sales"],
                "sales_14d": sale_windows[14]["sales"],
                "units_3d": sale_windows[3]["units"],
                "units_7d": sale_windows[7]["units"],
                "units_14d": sale_windows[14]["units"],
                "campaign_ids": ",".join(str(x) for x in sorted(campaign_ids))
                or "GAP",
                "campaign_statuses": ";".join(statuses) or "GAP",
                "spend_3d": spend_windows[3] if campaign_ids else "GAP",
                "spend_7d": spend_windows[7] if campaign_ids else "GAP",
                "spend_14d": spend_windows[14] if campaign_ids else "GAP",
                "direct_orders_7d": attr_7["direct_orders"]
                if campaign_ids
                else "GAP",
                "associated_orders_7d": attr_7["associated_orders"]
                if campaign_ids
                else "GAP",
            }
        )
    return rows


def _archive_exact(root: Path) -> tuple[Path, str]:
    """Создать ZIP с exact root entries и рядом ``.zip.sha256``."""
    archive = root.parent / f"{PACKAGE_NAME}.zip"
    sidecar = archive.with_name(f"{archive.name}.sha256")
    if archive.exists():
        archive.unlink()
    if sidecar.exists():
        sidecar.unlink()
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED
    ) as handle:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                handle.write(path, path.relative_to(root).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive, digest


def _validate_layout(root: Path) -> None:
    """Проверить exact primary root contract before archiving."""
    names = {path.name for path in root.iterdir()}
    expected = set(PRIMARY_FILES) | {"raw"}
    if names != expected:
        raise RuntimeError(
            f"primary layout mismatch: expected={sorted(expected)} got={sorted(names)}"
        )
    if not (root / "raw").is_dir():
        raise RuntimeError("primary layout missing raw directory")


def run_collect(output_dir: Path) -> dict[str, Any]:
    """Собрать ZIP contract и вернуть factual execution summary.

    Args:
        output_dir: Новый каталог package contents, заранее вычисленный внутри
            `.tmp/opsx-scripts/<run_id>/`.

    Returns:
        Summary with primary ZIP path, SHA-256, coverage and zero write counts.

    Raises:
        _SourceError: если обязательный PG/WB read-only source unavailable.
        RuntimeError: если local primary layout or secret scan fails.
    """
    root = prepare_invocation_output_dir(output_dir)
    (root / "raw").mkdir(parents=True, exist_ok=True)
    gaps: list[str] = []
    checked_at = _msk_now()
    closed_end = _closed_end_day(checked_at)

    _bootstrap_cluster_infra()
    try:
        wb_cabinet_id, pg_rows = _load_pg_identity_and_settings(root)
    except _SourceError as exc:
        _write_gaps(root / "07_GAPS.md", [_gap_line(exc.source, exc.error, exc.coverage_gap)])
        raise

    try:
        wb = asyncio.run(_collect_wb(root, closed_end, pg_rows))
    except _SourceError as exc:
        gaps.append(_gap_line(exc.source, exc.error, exc.coverage_gap))
        _write_gaps(root / "07_GAPS.md", gaps)
        raise
    except Exception as exc:  # noqa: BLE001
        line = _gap_line(
            "WB read-only adapters",
            exc,
            "campaign/card/order/fullstats/promo source",
        )
        _write_gaps(root / "07_GAPS.md", [line])
        raise _SourceError(
            "WB read-only adapters",
            _safe_error(exc),
            "campaign/card/order/fullstats/promo source",
        ) from exc

    cards = {
        _read_int(card, "nmID", "nmId", "nmid"): card
        for card in wb["cards"]
        if _read_int(card, "nmID", "nmId", "nmid")
    }
    scope_nmids = _scope_nmids(cards)
    mat_nmids = set(scope_nmids)
    for seed in (85970344, 388166103):
        imt = _read_int(cards.get(seed, {}), "imtID", "imtId", "imt_id")
        if not imt:
            gaps.append(
                _gap_line(
                    "WB Content API cards",
                    f"nm_id={seed} has no imtID",
                    f"glue/mat topology for nm_id={seed}",
                )
            )
    missing_targets = sorted(set(TARGET_NMIDS) - set(cards))
    for nmid in missing_targets:
        gaps.append(
            _gap_line(
                "WB Content API cards",
                f"nm_id={nmid} absent from current cards response",
                f"target nm_id={nmid} current title/topology",
            )
        )

    nmids_by_campaign, raw_by_campaign = _campaign_map(wb["campaigns"], pg_rows)
    relevant_campaign_ids = _related_campaign_ids(nmids_by_campaign, scope_nmids)
    missing_campaigns = sorted(
        campaign_id
        for campaign_id in relevant_campaign_ids
        if campaign_id not in raw_by_campaign
    )
    for campaign_id in missing_campaigns:
        gaps.append(
            _gap_line(
                "WB campaigns",
                f"campaign_id={campaign_id} absent from current state",
                f"campaign state and performance reconciliation for adv_id={campaign_id}",
            )
        )

    by_auto, by_search = _pg_maps(pg_rows)
    for campaign_id in sorted(relevant_campaign_ids):
        if not _pg_row_for_campaign(campaign_id, by_auto, by_search):
            gaps.append(
                _gap_line(
                    "PG public.advsetting",
                    f"campaign_id={campaign_id} has no advsetting mapping",
                    f"PG campaign/bot state for adv_id={campaign_id}",
                )
            )

    for campaign_id, error in sorted(wb["budget_errors"].items()):
        gaps.append(
            _gap_line(
                "WB GET /adv/v1/budget",
                f"adv_id={campaign_id}: {error}",
                f"campaign_balance for adv_id={campaign_id}",
            )
        )

    fullstats_campaign_ids = {
        _read_int(row, "advertId", "advert_id")
        for row in wb["fullstats"]
        if _read_int(row, "advertId", "advert_id")
    }
    for campaign_id in sorted(relevant_campaign_ids - fullstats_campaign_ids):
        gaps.append(
            _gap_line(
                "WB GET /adv/v3/fullstats",
                f"campaign_id={campaign_id} absent from response",
                f"closed performance windows for adv_id={campaign_id}",
            )
        )

    day_rows = _aggregate_day_rows(wb["fullstats"], closed_end)
    nm_rows = _aggregate_nm_rows(wb["fullstats"], closed_end)
    sales = _sales_by_nmid_day(wb["orders"], closed_end)

    topup_raw, topup_error = _load_topups(root, wb_cabinet_id, closed_end)
    if topup_error:
        gaps.append(
            _gap_line(
                "PG public.wbautobudgettopup",
                topup_error,
                "optional last-7-closed-day top-up log",
            )
        )
    topups = _normalize_topups(topup_raw, closed_end)

    campaign_current = _campaign_rows(
        relevant_campaign_ids,
        scope_nmids,
        raw_by_campaign,
        nmids_by_campaign,
        pg_rows,
        wb["budgets"],
    )
    performance = _performance_rows(
        set(TARGET_NMIDS),
        relevant_campaign_ids,
        nmids_by_campaign,
        day_rows,
        nm_rows,
        sales,
        closed_end,
    )
    store = _store_rows(sales, day_rows, closed_end)
    mats = _mats_rows(
        mat_nmids,
        cards,
        nmids_by_campaign,
        raw_by_campaign,
        sales,
        day_rows,
        nm_rows,
        closed_end,
    )
    promo = _promo_snapshot(wb["balance"], checked_at)

    _write_csv(
        root / "01_STORE.csv",
        store,
        [
            "window",
            "period_from",
            "period_to",
            "sales",
            "events",
            "units",
            "gross_ad_spend",
            "gross_drr",
        ],
    )
    _write_csv(
        root / "02_CAMPAIGNS_CURRENT.csv",
        campaign_current,
        [
            "nm_id",
            "adv_setting_id",
            "adv_id",
            "campaign_type",
            "placements",
            "WB_status",
            "PG_active_status",
            "bot_active",
            "automatic_version",
            "strategy",
            "aggressiveness",
            "target_CPO",
            "max_CPO",
            "Auto_daily_limit",
            "Search_daily_limit",
            "campaign_balance",
        ],
    )
    _write_csv(
        root / "03_PERFORMANCE.csv",
        performance,
        [
            "scope",
            "nm_id",
            "campaign_id",
            "campaign_ids",
            "window",
            "period_from",
            "period_to",
            "factual_sales",
            "units",
            "ad_spend",
            "views",
            "clicks",
            "carts",
            "direct_orders",
            "associated_orders",
            "direct_gmv",
            "associated_gmv",
        ],
    )
    _write_csv(
        root / "04_MATS.csv",
        mats,
        [
            "nm_id",
            "title",
            "sales_3d",
            "sales_7d",
            "sales_14d",
            "units_3d",
            "units_7d",
            "units_14d",
            "campaign_ids",
            "campaign_statuses",
            "spend_3d",
            "spend_7d",
            "spend_14d",
            "direct_orders_7d",
            "associated_orders_7d",
        ],
    )
    (root / "05_PROMO.json").write_text(
        json.dumps(promo, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        root / "06_TOPUPS.csv",
        topups,
        ["timestamp", "adv_id", "total", "promo", "ordinary"],
    )
    _write_gaps(root / "07_GAPS.md", gaps)

    handoff_ready = not gaps
    manifest = {
        "mode": "STRICT_READ_ONLY",
        "no_analysis": True,
        "package": PACKAGE_NAME,
        "shop_id": SHOP_ID,
        "wb_cabinet_id": wb_cabinet_id,
        "timezone": "Europe/Moscow",
        "checked_at_msk": _iso_msk(checked_at),
        "last_fully_closed_day": closed_end.isoformat(),
        "target_nmids": sorted(TARGET_NMIDS),
        "target_nmids_covered": sorted(set(TARGET_NMIDS) & set(cards)),
        "mat_nmids": sorted(mat_nmids),
        "mat_nmids_covered": sorted(set(mat_nmids) & set(cards)),
        "campaigns_covered": sorted(relevant_campaign_ids),
        "reconcile_campaigns": {
            str(nmid): sorted(campaign_ids)
            for nmid, campaign_ids in RECONCILE_CAMPAIGNS.items()
        },
        "primary_files": list(PRIMARY_FILES),
        "store_windows": ["3d", "7d"],
        "performance_windows": ["1d", "3d", "7d", "14d"],
        "topup_window": "last_7_fully_closed_days",
        "web_handoff_ready": "YES" if handoff_ready else "NO",
        "gaps_count": len(gaps),
        "write_counts": SAFETY_WRITE_COUNTS,
    }
    (root / "00_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    findings = evidence.secret_scan(root)
    if findings:
        raise RuntimeError(f"secret scan failed: {findings[:3]}")
    _validate_layout(root)
    archive, digest = _archive_exact(root)
    return {
        "EXECUTION_STATUS": "COMPLETE" if handoff_ready else "COMPLETE_WITH_GAPS",
        "MODE": "STRICT_READ_ONLY",
        "SHOP_ID": SHOP_ID,
        "WB_CABINET_ID": wb_cabinet_id,
        "LAST_FULLY_CLOSED_DAY": closed_end.isoformat(),
        "TARGET_NMIDS_COVERED": sorted(set(TARGET_NMIDS) & set(cards)),
        "MAT_NMIDS_COVERED": sorted(set(mat_nmids) & set(cards)),
        "CAMPAIGNS_COVERED": sorted(relevant_campaign_ids),
        "STORE_3D_COVERAGE": "CLOSED_ONLY",
        "STORE_7D_COVERAGE": "CLOSED_ONLY",
        "PROMO_SNAPSHOT": promo,
        "GAPS": gaps,
        "ZIP_ABSOLUTE_PATH": str(archive.resolve()),
        "ZIP_SHA256": digest,
        "PRIMARY_ARTIFACT": archive.name,
        "PRIMARY_SHA256": digest,
        "WEB_HANDOFF_READY": "YES" if handoff_ready else "NO",
        **SAFETY_WRITE_COUNTS,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать CLI args для deterministic Job/local execution."""
    parser = argparse.ArgumentParser(
        description="A1 strict factual read-only contract collector."
    )
    parser.add_argument(
        "--shop-id",
        required=True,
        help="WB shop identity supplied by the resolver contract.",
    )
    parser.add_argument(
        "--wb-cabinet-id",
        required=True,
        type=int,
        help="WB cabinet identity supplied by the resolver contract.",
    )
    parser.add_argument(
        "--target-nmids",
        required=True,
        help="Comma-separated target NMIDs supplied by the resolver contract.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional precomputed invocation-owned output directory.",
    )
    parser.add_argument("--run-id", default="local-run")
    parser.add_argument("--caller-root", default=".")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить collector, напечатать machine-readable primary handoff."""
    args = parse_args(argv)
    global SHOP_ID, EXPECTED_WB_CABINET_ID, TARGET_NMIDS
    SHOP_ID = args.shop_id
    EXPECTED_WB_CABINET_ID = args.wb_cabinet_id
    TARGET_NMIDS = frozenset(
        int(value) for value in args.target_nmids.split(",") if value.strip()
    )
    if not SHOP_ID or not TARGET_NMIDS:
        print("ops-script: failed; identity arguments must be non-empty", file=sys.stderr)
        return 1
    try:
        output_dir = (
            Path(args.output_dir)
            if args.output_dir
            else invocation_output_path(
                Path(args.caller_root).resolve(),
                args.run_id,
                "a1-strict-read-only-contract",
            )
        )
        result = run_collect(output_dir)
    except Exception as exc:  # noqa: BLE001
        print(f"ops-script: failed; error={_safe_error(exc)}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_SHA256={result['PRIMARY_SHA256']}")
    print(f"PRIMARY_ARTIFACT={result['PRIMARY_ARTIFACT']}")
    print(f"WEB_HANDOFF_READY={result['WEB_HANDOFF_READY']}")
    for key, value in SAFETY_WRITE_COUNTS.items():
        print(f"{key}={value}")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

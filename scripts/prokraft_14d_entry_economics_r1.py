"""PROKRAFT_14D_ENTRY_ECONOMICS_R1 strict read-only economics collector.

Собирает для одного WB-магазина и включительного 14-дневного окна
фактические заказы из supplier orders, физический рекламный расход из
promotion fullstats и настройки кампаний из PostgreSQL. Auto/Search/прочие
физические кампании сводятся в одну логическую запись на явно заявленный
nmID. Производственные записи отсутствуют: WB, PostgreSQL и Redis читаются
только через существующие read-only adapters.

Первичный результат -- ``PROKRAFT_14D_ENTRY_ECONOMICS_R1.zip`` с JSON,
JSONL, CSV, Markdown и SHA-256 sidecar. Если spend кампании нельзя без
эвристики отнести к одному nmID, запись остаётся с ``null``-метриками и
явным evidence gap; glue/imt membership для attribution не используется.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import re
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    MSK = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    # Windows/minimal images may omit tzdata; Moscow has a fixed UTC+3 offset.
    MSK = timezone(timedelta(hours=3), "Europe/Moscow")
CONTRACT_ID = "PROKRAFT_14D_ENTRY_ECONOMICS_R1"
PRIMARY_ARTIFACT = f"{CONTRACT_ID}.zip"
SHOP_ID = "5586b2ff-449c-4151-9518-60f46d32b7d9"
WB_CABINET_ID = 573
STOP_LOW_STOCK_NMID = 751657528
PRIORITY_NMIDS = (
    751657528,
    266109990,
    143023475,
    234375724,
    214754056,
    1256595631,
)
WRITE_COUNTS = {
    "ALL_PRODUCTION_WRITES": 0,
    "WB_API_WRITES": 0,
    "POSTGRES_WRITES": 0,
    "CLICKHOUSE_WRITES": 0,
    "REDIS_WRITES": 0,
    "EXCEL_WRITES": 0,
}


class CollectorBlocked(RuntimeError):
    """Остановить запуск с машинно-читаемой причиной без подмены данных."""

    def __init__(self, reason: str, evidence: str, *, formal_change: bool) -> None:
        super().__init__(evidence)
        self.reason = reason
        self.evidence = evidence
        self.formal_change = formal_change


def _jsonable(value: Any) -> Any:
    """Привести DTO, даты и вложенные контейнеры к JSON-совместимому виду."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _jsonable(to_dict())
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return str(value)


def _read_number(row: dict[str, Any], *names: str) -> float | None:
    """Вернуть первое явно присутствующее числовое поле, иначе ``None``."""
    for name in names:
        value = row.get(name)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _read_int(row: dict[str, Any], *names: str) -> int:
    """Вернуть первое положительное целочисленное поле из API aliases."""
    value = _read_number(row, *names)
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_error(value: Any) -> str:
    """Удалить из сообщения ошибки строки, похожие на credential values."""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return re.sub(
        r"(?i)(password|token|secret|authorization)\s*[=:]\s*\S+",
        r"\1=<redacted>",
        text,
    )[:1000]


def _parse_day(value: Any) -> date | None:
    """Нормализовать ISO date/datetime к календарному дню Europe/Moscow."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=MSK)
        return dt.astimezone(MSK).date()
    if isinstance(value, date):
        return value
    text = str(value)
    try:
        if "T" in text or " " in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(
                MSK
            ).date()
        return date.fromisoformat(text[:10])
    except (TypeError, ValueError):
        return None


def _row_day(row: dict[str, Any]) -> date | None:
    """Извлечь дату фактической строки с учётом разных WB aliases."""
    for key in ("date", "lastChangeDate", "orderDate", "createdAt"):
        parsed = _parse_day(row.get(key))
        if parsed is not None:
            return parsed
    return None


def _parse_nmids(raw: Any) -> set[int]:
    """Извлечь только явно перечисленные nmID из PG JSON/text поля."""
    if isinstance(raw, (list, tuple, set, frozenset)):
        values = raw
    else:
        text = str(raw or "").strip()
        if not text:
            return set()
        try:
            values = json.loads(text.replace("'", '"'))
        except json.JSONDecodeError:
            return {
                int(item)
                for item in re.findall(r"\d+", text)
                if int(item) > 0
            }
    if not isinstance(values, (list, tuple, set, frozenset)):
        return set()
    return {
        int(value)
        for value in values
        if str(value).strip().isdigit() and int(value) > 0
    }


def _campaign_id(row: dict[str, Any]) -> int:
    """Прочитать физический advert ID из WB campaign payload."""
    return _read_int(row, "id", "advertId", "advert_id")


def _campaign_membership(
    campaign: dict[str, Any], pg_row: dict[str, Any] | None
) -> tuple[set[int], list[str]]:
    """Собрать только явную WB/PG campaign-to-nmID membership."""
    result: set[int] = set()
    sources: list[str] = []
    for key in ("nm_settings", "nmSettings"):
        items = campaign.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                nmid = _read_int(item, "nm_id", "nmId", "nmID")
                if nmid:
                    result.add(nmid)
        if result:
            sources.append(f"WB.{key}")
            break
    if not result:
        settings = campaign.get("settings")
        if isinstance(settings, dict):
            for key in ("nmids", "nm_ids", "nmIds"):
                parsed = _parse_nmids(settings.get(key))
                if parsed:
                    result.update(parsed)
                    sources.append(f"WB.settings.{key}")
                    break
    if not result and pg_row is not None:
        parsed = _parse_nmids(pg_row.get("nmids"))
        if parsed:
            result.update(parsed)
            sources.append("PG.advsetting.nmids")
    return result, sources


def _campaign_type(
    campaign_id: int, pg_row: dict[str, Any] | None
) -> str:
    """Классифицировать физическую кампанию только по явным ID mapping."""
    if pg_row and _read_int(pg_row, "adv_id") == campaign_id:
        return "AUTO"
    if pg_row and _read_int(pg_row, "_search_adv_id") == campaign_id:
        return "SEARCH"
    return "OTHER"


def _pg_for_campaign(
    campaign_id: int, pg_rows: Iterable[dict[str, Any]]
) -> dict[str, Any] | None:
    """Найти родительский advsetting для Auto или Search physical ID."""
    for row in pg_rows:
        if campaign_id in {
            _read_int(row, "adv_id"),
            _read_int(row, "_search_adv_id"),
        }:
            return row
    return None


def _stable_row_key(row: dict[str, Any], fields: tuple[str, ...]) -> str:
    """Сформировать детерминированный ключ для защиты от page duplicates."""
    for field in fields:
        value = row.get(field)
        if value not in (None, ""):
            return f"{field}:{value}"
    payload = json.dumps(_jsonable(row), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _unique_rows(
    rows: Iterable[dict[str, Any]], fields: tuple[str, ...]
) -> list[dict[str, Any]]:
    """Удалить только повторные source rows с одинаковым stable identity."""
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = _stable_row_key(row, fields)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Посчитать ratio; нулевой/неизвестный denominator остаётся ``None``."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _money(value: float | None) -> float | None:
    """Округлить рублёвое число, сохранив ``None`` как unknown."""
    return None if value is None else round(float(value), 2)


def _day_state(day: date, as_of: date) -> str:
    """Вернуть статус дня окна относительно заданной MSK даты запуска."""
    if day == as_of:
        return "OPEN_PARTIAL"
    if day < as_of:
        return "CLOSED"
    return "FUTURE_UNSUPPORTED"


def _parse_date_argument(raw: str, name: str) -> date:
    """Разобрать CLI date и дать короткую ошибку контракта."""
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be ISO date YYYY-MM-DD: {raw}") from exc


def _write_json(path: Path, payload: Any) -> None:
    """Записать UTF-8 JSON без platform-default encoding."""
    path.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    """Записать UTF-8 JSONL с одной нормализованной записью на строку."""
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(_jsonable(row), ensure_ascii=False, separators=(",", ":"))
                + "\n"
            )


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    """Записать стабильную CSV-схему для ручного анализа без Excel side effects."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    column: (
                        json.dumps(row[column], ensure_ascii=False, sort_keys=True)
                        if isinstance(row.get(column), (dict, list))
                        else row.get(column, "")
                    )
                    for column in columns
                }
            )


def _aggregate_orders(
    rows: list[dict[str, Any]], start: date, end: date
) -> tuple[dict[str, dict[str, Any]], dict[int, dict[str, Any]], list[str]]:
    """Свернуть supplier orders в store/day и factual nmID metrics.

    Отменённые строки не входят в factual totals, но сохраняются в gap
    counters. ``orders`` -- число supplier order events, ``units`` -- явное
    quantity либо row-count fallback с отдельной семантикой.
    """
    daily: dict[str, dict[str, Any]] = {}
    by_nmid: dict[int, dict[str, Any]] = {}
    gaps: list[str] = []
    selected = [
        row
        for row in _unique_rows(
            rows,
            ("srid", "gNumber", "orderUid", "orderId", "id"),
        )
        if start <= (_row_day(row) or date.min) <= end
    ]
    for row in selected:
        day = _row_day(row)
        if day is None or str(row.get("isCancel", "")).lower() in {
            "true",
            "1",
            "t",
        }:
            continue
        day_key = day.isoformat()
        bucket = daily.setdefault(
            day_key,
            {
                "date": day_key,
                "factual_orders": 0,
                "factual_units": 0.0,
                "factual_gmv_known_rub": 0.0,
                "gmv_missing_rows": 0,
                "units_fallback_rows": 0,
            },
        )
        nmid = _read_int(row, "nmId", "nmID", "nm_id", "nmid")
        target = by_nmid.setdefault(
            nmid,
            {
                "nm_id": nmid or None,
                "factual_orders": 0,
                "factual_units": 0.0,
                "factual_gmv_known_rub": 0.0,
                "gmv_missing_rows": 0,
                "units_fallback_rows": 0,
            },
        )
        quantity = _read_number(row, "quantity", "qty", "count")
        if quantity is None:
            quantity = 1.0
            bucket["units_fallback_rows"] += 1
            target["units_fallback_rows"] += 1
        price = _read_number(
            row,
            "finishedPrice",
            "priceWithDisc",
            "totalPrice",
            "forPay",
        )
        bucket["factual_orders"] += 1
        bucket["factual_units"] += quantity
        target["factual_orders"] += 1
        target["factual_units"] += quantity
        if price is None:
            bucket["gmv_missing_rows"] += 1
            target["gmv_missing_rows"] += 1
        else:
            bucket["factual_gmv_known_rub"] += price
            target["factual_gmv_known_rub"] += price
    if any(row.get("gmv_missing_rows") for row in daily.values()):
        gaps.append("SUPPLIER_ORDER_GMV_FIELD_MISSING")
    for bucket in daily.values():
        bucket["factual_gmv_rub"] = (
            None
            if bucket["gmv_missing_rows"]
            else _money(bucket["factual_gmv_known_rub"])
        )
        bucket["factual_units"] = _money(bucket["factual_units"])
        bucket["factual_gmv_known_rub"] = _money(bucket["factual_gmv_known_rub"])
        bucket["units_semantics"] = (
            "EXPLICIT_QUANTITY"
            if not bucket["units_fallback_rows"]
            else "EXPLICIT_OR_ROW_COUNT_FALLBACK"
        )
    for bucket in by_nmid.values():
        bucket["factual_gmv_rub"] = (
            None
            if bucket["gmv_missing_rows"]
            else _money(bucket["factual_gmv_known_rub"])
        )
        bucket["factual_units"] = _money(bucket["factual_units"])
        bucket["factual_gmv_known_rub"] = _money(bucket["factual_gmv_known_rub"])
        bucket["units_semantics"] = (
            "EXPLICIT_QUANTITY"
            if not bucket["units_fallback_rows"]
            else "EXPLICIT_OR_ROW_COUNT_FALLBACK"
        )
    return daily, by_nmid, gaps


def _expand_fullstats(
    raw_items: list[dict[str, Any]], start: date, end: date
) -> tuple[
    dict[tuple[int, str], dict[str, Any]],
    dict[tuple[int, str, int], dict[str, Any]],
]:
    """Развернуть fullstats в campaign-day и campaign-day-ordered-nm rows."""
    day_rows: dict[tuple[int, str], dict[str, Any]] = {}
    nm_rows: dict[tuple[int, str, int], dict[str, Any]] = {}
    seen_days: set[str] = set()
    seen_nm: set[str] = set()
    for item in raw_items:
        adv_id = _campaign_id(item)
        if not adv_id:
            continue
        days = item.get("days")
        if not isinstance(days, list):
            continue
        for day in days:
            if not isinstance(day, dict):
                continue
            parsed_day = _parse_day(day.get("date"))
            if parsed_day is None or not start <= parsed_day <= end:
                continue
            day_key = (adv_id, parsed_day.isoformat())
            source_key = _stable_row_key(
                {
                    "adv_id": adv_id,
                    "date": parsed_day.isoformat(),
                    "day": day,
                },
                ("source_id",),
            )
            if source_key not in seen_days:
                seen_days.add(source_key)
                bucket = day_rows.setdefault(
                    day_key,
                    {
                        "adv_id": adv_id,
                        "date": parsed_day.isoformat(),
                        "spend_rub": 0.0,
                        "views": 0,
                        "clicks": 0,
                    },
                )
                bucket["spend_rub"] += _read_number(day, "sum", "spend") or 0.0
                bucket["views"] += _read_int(day, "views")
                bucket["clicks"] += _read_int(day, "clicks")
            apps = day.get("apps")
            if not isinstance(apps, list):
                continue
            for app in apps:
                if not isinstance(app, dict):
                    continue
                app_type = str(app.get("appType", app.get("app_type", "")))
                nms = app.get("nms")
                if not isinstance(nms, list):
                    continue
                for nm in nms:
                    if not isinstance(nm, dict):
                        continue
                    ordered_nmid = _read_int(nm, "nmId", "nmID", "nm_id", "id")
                    if not ordered_nmid:
                        continue
                    nm_key = (adv_id, parsed_day.isoformat(), ordered_nmid)
                    source_key = _stable_row_key(
                        {
                            "adv_id": adv_id,
                            "date": parsed_day.isoformat(),
                            "app_type": app_type,
                            "nm": nm,
                        },
                        ("source_id",),
                    )
                    if source_key in seen_nm:
                        continue
                    seen_nm.add(source_key)
                    bucket = nm_rows.setdefault(
                        nm_key,
                        {
                            "adv_id": adv_id,
                            "date": parsed_day.isoformat(),
                            "ordered_nm_id": ordered_nmid,
                            "spend_rub": 0.0,
                            "orders": 0,
                            "gmv_known_rub": 0.0,
                            "gmv_missing_rows": 0,
                            "app_types": set(),
                        },
                    )
                    bucket["spend_rub"] += _read_number(nm, "sum", "spend") or 0.0
                    bucket["orders"] += _read_int(nm, "orders")
                    gmv = _read_number(nm, "sum_price")
                    if gmv is None:
                        bucket["gmv_missing_rows"] += 1
                    else:
                        bucket["gmv_known_rub"] += gmv
                    bucket["app_types"].add(app_type)
    for bucket in day_rows.values():
        bucket["spend_rub"] = _money(bucket["spend_rub"])
    for bucket in nm_rows.values():
        bucket["spend_rub"] = _money(bucket["spend_rub"])
        bucket["gmv_rub"] = (
            None
            if bucket["gmv_missing_rows"]
            else _money(bucket["gmv_known_rub"])
        )
        bucket["gmv_known_rub"] = _money(bucket["gmv_known_rub"])
        bucket["app_types"] = sorted(bucket["app_types"])
    return day_rows, nm_rows


def _limit_value(pg_row: dict[str, Any] | None, campaign_type: str) -> float | None:
    """Выбрать фактический daily budget limit для конкретной physical leg."""
    if pg_row is None:
        return None
    common = _read_number(pg_row, "common_budget_daily_limit")
    use_common = str(pg_row.get("use_common_budget", "")).lower() in {
        "true",
        "t",
        "1",
    }
    if use_common and common is not None and common > 0:
        return _money(common)
    if campaign_type == "AUTO":
        return _money(_read_number(pg_row, "auto_budget_daily_limit"))
    if campaign_type == "SEARCH":
        return _money(_read_number(pg_row, "search_auto_budget_daily_limit"))
    return None


def _candidate_value(
    values: Iterable[float | None],
) -> tuple[float | None, str]:
    """Вернуть единственное согласованное значение или explicit conflict."""
    normalized = sorted({round(float(value), 6) for value in values if value is not None})
    if not normalized:
        return None, "MISSING"
    if len(normalized) > 1:
        return None, "CONFLICTING_VALUES"
    return _money(normalized[0]), "SUPPORTED"


def _build_physical_rows(
    campaigns: list[dict[str, Any]],
    pg_rows: list[dict[str, Any]],
    day_rows: dict[tuple[int, str], dict[str, Any]],
    nm_rows: dict[tuple[int, str, int], dict[str, Any]],
    start: date,
    end: date,
) -> tuple[list[dict[str, Any]], dict[int, set[int]], list[str]]:
    """Построить physical campaign rows и явную campaign membership map."""
    by_id: dict[int, dict[str, Any]] = {}
    memberships: dict[int, set[int]] = {}
    membership_sources: dict[int, list[str]] = {}
    gaps: list[str] = []
    for campaign in campaigns:
        campaign_id = _campaign_id(campaign)
        if not campaign_id:
            continue
        pg_row = _pg_for_campaign(campaign_id, pg_rows)
        nmids, sources = _campaign_membership(campaign, pg_row)
        by_id[campaign_id] = campaign
        memberships[campaign_id] = nmids
        membership_sources[campaign_id] = sources
        if not nmids:
            gaps.append(f"CAMPAIGN_NMID_MEMBERSHIP_MISSING:adv_id={campaign_id}")
    for pg_row in pg_rows:
        for field in ("adv_id", "_search_adv_id"):
            campaign_id = _read_int(pg_row, field)
            if campaign_id and campaign_id not in memberships:
                nmids = _parse_nmids(pg_row.get("nmids"))
                memberships[campaign_id] = nmids
                membership_sources[campaign_id] = ["PG.advsetting.nmids"] if nmids else []
                if not nmids:
                    gaps.append(f"CAMPAIGN_NMID_MEMBERSHIP_MISSING:adv_id={campaign_id}")
    physical: list[dict[str, Any]] = []
    campaign_ids = sorted(set(memberships) | {key[0] for key in day_rows})
    days = [
        (start + timedelta(days=index)).isoformat()
        for index in range((end - start).days + 1)
    ]
    for campaign_id in campaign_ids:
        pg_row = _pg_for_campaign(campaign_id, pg_rows)
        campaign = by_id.get(campaign_id, {})
        campaign_type = _campaign_type(campaign_id, pg_row)
        explicit_nmids = sorted(memberships.get(campaign_id, set()))
        daily: list[dict[str, Any]] = []
        for day in days:
            source = day_rows.get((campaign_id, day))
            nm_day = [
                row
                for (adv_id, row_day, _), row in nm_rows.items()
                if adv_id == campaign_id and row_day == day
            ]
            direct = sum(
                row["orders"]
                for row in nm_day
                if row["ordered_nm_id"] in explicit_nmids
            )
            associated = sum(
                row["orders"]
                for row in nm_day
                if row["ordered_nm_id"] not in explicit_nmids
            )
            direct_gmv_known = sum(
                row["gmv_known_rub"]
                for row in nm_day
                if row["ordered_nm_id"] in explicit_nmids
            )
            associated_gmv_known = sum(
                row["gmv_known_rub"]
                for row in nm_day
                if row["ordered_nm_id"] not in explicit_nmids
            )
            direct_missing = any(
                row["gmv_missing_rows"] > 0
                for row in nm_day
                if row["ordered_nm_id"] in explicit_nmids
            )
            associated_missing = any(
                row["gmv_missing_rows"] > 0
                for row in nm_day
                if row["ordered_nm_id"] not in explicit_nmids
            )
            daily.append(
                {
                    "date": day,
                    "day_state": _day_state(
                        date.fromisoformat(day),
                        end,
                    ),
                    "physical_spend_rub": source["spend_rub"] if source else 0.0,
                    "direct_orders": direct,
                    "direct_gmv_rub": None if direct_missing else _money(direct_gmv_known),
                    "associated_orders": associated,
                    "associated_gmv_rub": (
                        None if associated_missing else _money(associated_gmv_known)
                    ),
                    "fullstats_row_count": len(nm_day),
                }
            )
        physical.append(
            {
                "adv_id": campaign_id,
                "campaign_type": campaign_type,
                "campaign_name": (
                    campaign.get("name")
                    or (campaign.get("settings") or {}).get("name")
                    if isinstance(campaign.get("settings"), dict)
                    else campaign.get("name")
                ),
                "explicit_nmids": explicit_nmids,
                "membership_source": membership_sources.get(campaign_id, []),
                "membership_status": (
                    "EXPLICIT"
                    if explicit_nmids
                    else "MISSING"
                ),
                "target_cpo_rub": (
                    _money(_read_number(pg_row or {}, "target_price_for_order"))
                ),
                "max_cpo_rub": _money(_read_number(pg_row or {}, "max_price_for_order")),
                "daily_limit_rub": _limit_value(pg_row, campaign_type),
                "advsetting_id": _read_int(pg_row or {}, "id") or None,
                "daily": daily,
                "days_with_spend": sum(
                    1 for row in daily if float(row["physical_spend_rub"] or 0) > 0
                ),
                "window_physical_spend_rub": _money(
                    sum(float(row["physical_spend_rub"] or 0) for row in daily)
                ),
                "evidence_quality": [
                    "PHYSICAL_CAMPAIGN_DAY_SPEND",
                    "FULLSTATS_DIRECT_ASSOCIATED_ROWS",
                ],
            }
        )
    return physical, memberships, sorted(set(gaps))


def _build_entry_rows(
    physical: list[dict[str, Any]],
    memberships: dict[int, set[int]],
    factual_by_nmid: dict[int, dict[str, Any]],
    pg_rows: list[dict[str, Any]],
    start: date,
    end: date,
    priority_nmids: tuple[int, ...],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Свести physical campaigns в canonical logical entry/NMID rows."""
    all_nmids = set(priority_nmids)
    for nmids in memberships.values():
        all_nmids.update(nmids)
    entries: list[dict[str, Any]] = []
    gaps: list[str] = []
    days = [
        (start + timedelta(days=index)).isoformat()
        for index in range((end - start).days + 1)
    ]
    for nmid in sorted(all_nmids):
        historical_only = nmid == STOP_LOW_STOCK_NMID
        campaign_rows = (
            []
            if historical_only
            else [
                row for row in physical if nmid in set(row["explicit_nmids"])
            ]
        )
        single_rows = [
            row for row in campaign_rows if len(row["explicit_nmids"]) == 1
        ]
        multi_rows = [
            row for row in campaign_rows if len(row["explicit_nmids"]) > 1
        ]
        daily: list[dict[str, Any]] = []
        for day in days:
            single_day = [
                row["daily"][index]
                for row in single_rows
                for index in [days.index(day)]
            ]
            known_spend = sum(
                float(row["physical_spend_rub"] or 0) for row in single_day
            )
            multi_spend = sum(
                float(row["daily"][days.index(day)]["physical_spend_rub"] or 0)
                for row in multi_rows
            )
            direct_orders = sum(row["direct_orders"] for row in single_day)
            associated_orders = sum(row["associated_orders"] for row in single_day)
            direct_gmv_unknown = any(row["direct_gmv_rub"] is None for row in single_day)
            associated_gmv_unknown = any(
                row["associated_gmv_rub"] is None for row in single_day
            )
            direct_gmv = sum(
                float(row["direct_gmv_rub"] or 0)
                for row in single_day
                if row["direct_gmv_rub"] is not None
            )
            associated_gmv = sum(
                float(row["associated_gmv_rub"] or 0)
                for row in single_day
                if row["associated_gmv_rub"] is not None
            )
            spend_complete = bool(single_rows) and not multi_rows
            spend_for_metrics = _money(known_spend) if spend_complete else None
            direct_gmv_for_metrics = None if direct_gmv_unknown else _money(direct_gmv)
            associated_gmv_for_metrics = (
                None if associated_gmv_unknown else _money(associated_gmv)
            )
            total_orders = direct_orders + associated_orders
            daily.append(
                {
                    "date": day,
                    "day_state": _day_state(date.fromisoformat(day), end),
                    "spend_rub": spend_for_metrics,
                    "spend_known_rub": _money(known_spend),
                    "unallocated_multi_nmid_spend_rub": _money(multi_spend),
                    "direct_orders": direct_orders,
                    "direct_gmv_rub": direct_gmv_for_metrics,
                    "associated_orders": associated_orders,
                    "associated_gmv_rub": associated_gmv_for_metrics,
                    "direct_drr": _ratio(spend_for_metrics, direct_gmv_for_metrics),
                    "direct_cpo_rub": _ratio(spend_for_metrics, float(direct_orders)),
                    "effective_cpo_rub": _ratio(spend_for_metrics, float(total_orders)),
                    "associated_share": _ratio(
                        float(associated_orders), float(total_orders)
                    ),
                }
            )
        physical_ids = [row["adv_id"] for row in campaign_rows]
        target_cpo, target_status = _candidate_value(
            row["target_cpo_rub"] for row in campaign_rows
        )
        max_cpo, max_status = _candidate_value(
            row["max_cpo_rub"] for row in campaign_rows
        )
        daily_limit, daily_limit_status = _candidate_value(
            row["daily_limit_rub"] for row in campaign_rows
        )
        factual = factual_by_nmid.get(
            nmid,
            {
                "factual_orders": 0,
                "factual_units": 0.0,
                "factual_gmv_rub": 0.0,
                "factual_gmv_known_rub": 0.0,
                "gmv_missing_rows": 0,
                "units_fallback_rows": 0,
            },
        )
        spend_complete = bool(single_rows) and not multi_rows
        spend_known = sum(row["window_physical_spend_rub"] or 0 for row in single_rows)
        direct_orders = sum(
            item["direct_orders"] for row in single_rows for item in row["daily"]
        )
        associated_orders = sum(
            item["associated_orders"] for row in single_rows for item in row["daily"]
        )
        direct_unknown = any(
            item["direct_gmv_rub"] is None
            for row in single_rows
            for item in row["daily"]
        )
        associated_unknown = any(
            item["associated_gmv_rub"] is None
            for row in single_rows
            for item in row["daily"]
        )
        direct_gmv = _money(
            sum(
                item["direct_gmv_rub"] or 0
                for row in single_rows
                for item in row["daily"]
            )
        )
        associated_gmv = _money(
            sum(
                item["associated_gmv_rub"] or 0
                for row in single_rows
                for item in row["daily"]
            )
        )
        if direct_unknown:
            direct_gmv = None
        if associated_unknown:
            associated_gmv = None
        spend = _money(spend_known) if spend_complete else None
        total_attributed_orders = direct_orders + associated_orders
        factual_gmv = factual.get("factual_gmv_rub")
        target_spend = (
            None
            if factual_gmv is None
            else _money(float(factual_gmv) * 0.10)
        )
        full_uplift = (
            None
            if target_spend is None or spend is None
            else _money(max(target_spend - spend, 0))
        )
        effective_cpo = _ratio(spend, float(total_attributed_orders))
        quality = ["EXPLICIT_CAMPAIGN_NMID_MEMBERSHIP"]
        if multi_rows:
            quality.append("MULTI_NMID_CAMPAIGN_SPEND_UNALLOCATED")
            gaps.append(
                f"MULTI_NMID_CAMPAIGN_SPEND_UNALLOCATED:nmid={nmid}:"
                + ",".join(str(row["adv_id"]) for row in multi_rows)
            )
        if not campaign_rows:
            quality.append("NO_CURRENT_PHYSICAL_CAMPAIGN")
        if nmid == STOP_LOW_STOCK_NMID:
            quality.append("STOP_LOW_STOCK_HISTORICAL_ONLY")
        if direct_unknown or associated_unknown:
            quality.append("DIRECT_ASSOCIATED_GMV_MISSING")
        if target_status == "CONFLICTING_VALUES" or max_status == "CONFLICTING_VALUES":
            quality.append("CPO_LIMIT_CONFLICT")
        entry = {
            "nm_id": nmid,
            "logical_entry_key": f"nmid:{nmid}",
            "historical_only": historical_only,
            "priority": nmid in priority_nmids,
            "physical_campaign_ids": physical_ids,
            "physical_campaign_types": sorted(
                {row["campaign_type"] for row in campaign_rows}
            ),
            "spend_allocation": (
                "EXACT_SINGLE_NMID"
                if spend_complete and single_rows
                else "NULL_MULTI_NMID_AMBIGUOUS"
                if multi_rows
                else "NO_CURRENT_CAMPAIGN"
            ),
            "spend_rub": spend,
            "spend_known_rub": _money(spend_known),
            "days_with_spend": sum(
                1
                for row in single_rows
                for item in row["daily"]
                if float(item["physical_spend_rub"] or 0) > 0
            ),
            "target_cpo_rub": target_cpo,
            "max_cpo_rub": max_cpo,
            "daily_limit_rub": daily_limit,
            "target_cpo_status": target_status,
            "max_cpo_status": max_status,
            "daily_limit_status": daily_limit_status,
            "factual_orders": factual.get("factual_orders", 0),
            "factual_units": factual.get("factual_units", 0.0),
            "factual_gmv_rub": factual_gmv,
            "factual_gmv_known_rub": factual.get("factual_gmv_known_rub", 0.0),
            "direct_orders": direct_orders,
            "direct_units": direct_orders,
            "direct_gmv_rub": direct_gmv,
            "associated_orders": associated_orders,
            "associated_units": associated_orders,
            "associated_gmv_rub": associated_gmv,
            "direct_drr": _ratio(spend, direct_gmv),
            "direct_cpo_rub": _ratio(spend, float(direct_orders)),
            "effective_cpo_rub": effective_cpo,
            "associated_share": _ratio(
                float(associated_orders), float(total_attributed_orders)
            ),
            "store_drr_uplift_to_10_rub": full_uplift,
            "store_drr_delta_to_10_rub": (
                None
                if target_spend is None or spend is None
                else _money(target_spend - spend)
            ),
            "model_target_cpo_rub": target_cpo,
            "model_cpo_multiplier": _ratio(target_cpo, effective_cpo),
            "model_cpo_delta_rub": (
                None
                if target_cpo is None or effective_cpo is None
                else _money(target_cpo - effective_cpo)
            ),
            "daily": daily,
            "evidence_quality": quality,
        }
        entries.append(entry)
    return entries, sorted(set(gaps))


def _build_daily_store_rows(
    start: date,
    end: date,
    as_of: date,
    order_daily: dict[str, dict[str, Any]],
    physical: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Объединить factual store totals и весь physical spend по каждому дню."""
    rows: list[dict[str, Any]] = []
    for index in range((end - start).days + 1):
        day = (start + timedelta(days=index)).isoformat()
        factual = order_daily.get(
            day,
            {
                "factual_orders": 0,
                "factual_units": 0.0,
                "factual_gmv_rub": 0.0,
                "factual_gmv_known_rub": 0.0,
                "gmv_missing_rows": 0,
            },
        )
        spend = _money(
            sum(
                float(campaign["daily"][index]["physical_spend_rub"] or 0)
                for campaign in physical
                if len(campaign["daily"]) > index
            )
        )
        gmv = factual.get("factual_gmv_rub")
        rows.append(
            {
                "date": day,
                "day_state": _day_state(date.fromisoformat(day), as_of),
                "factual_orders": factual.get("factual_orders", 0),
                "factual_units": factual.get("factual_units", 0.0),
                "factual_gmv_rub": gmv,
                "factual_gmv_known_rub": factual.get("factual_gmv_known_rub", 0.0),
                "physical_spend_rub": spend,
                "store_drr": _ratio(spend, gmv),
                "headroom_5_rub": (
                    None if gmv is None else _money(float(gmv) * 0.05 - float(spend or 0))
                ),
                "headroom_6_rub": (
                    None if gmv is None else _money(float(gmv) * 0.06 - float(spend or 0))
                ),
                "headroom_8_rub": (
                    None if gmv is None else _money(float(gmv) * 0.08 - float(spend or 0))
                ),
                "headroom_10_rub": (
                    None if gmv is None else _money(float(gmv) * 0.10 - float(spend or 0))
                ),
                "source_quality": (
                    "FACTUAL_GMV_PARTIAL"
                    if factual.get("gmv_missing_rows")
                    else "FACTUAL_GMV_SUPPORTED"
                ),
            }
        )
    return rows


def _window_store_summary(daily: list[dict[str, Any]]) -> dict[str, Any]:
    """Посчитать window totals и descriptive store DRR/headroom."""
    gmv_missing = any(row["factual_gmv_rub"] is None for row in daily if row["factual_orders"])
    known_gmv = _money(sum(float(row["factual_gmv_known_rub"] or 0) for row in daily))
    gmv = None if gmv_missing else known_gmv
    spend = _money(sum(float(row["physical_spend_rub"] or 0) for row in daily))
    result: dict[str, Any] = {
        "factual_orders": sum(int(row["factual_orders"] or 0) for row in daily),
        "factual_units": _money(sum(float(row["factual_units"] or 0) for row in daily)),
        "factual_gmv_rub": gmv,
        "factual_gmv_known_rub": known_gmv,
        "physical_spend_rub": spend,
        "days_with_spend": sum(1 for row in daily if float(row["physical_spend_rub"] or 0) > 0),
        "store_drr": _ratio(spend, gmv),
        "headroom_5_rub": None if gmv is None else _money(float(gmv) * 0.05 - float(spend or 0)),
        "headroom_6_rub": None if gmv is None else _money(float(gmv) * 0.06 - float(spend or 0)),
        "headroom_8_rub": None if gmv is None else _money(float(gmv) * 0.08 - float(spend or 0)),
        "headroom_10_rub": None if gmv is None else _money(float(gmv) * 0.10 - float(spend or 0)),
        "factual_gmv_quality": "PARTIAL_MISSING_ROWS" if gmv_missing else "SUPPORTED",
    }
    return result


async def _load_pg(
    shop_id: str, cabinet: int
) -> list[dict[str, Any]]:
    """Загрузить identity и advsetting через explicit PURE_READ session."""
    try:
        from sqlalchemy import text
        from app.utils.db.session_maker import get_async_session_maker
    except (ImportError, ModuleNotFoundError) as exc:
        raise CollectorBlocked(
            "REQUIRED_CAPABILITY_ABSENT",
            f"read-only PostgreSQL adapter unavailable: {_safe_error(exc)}",
            formal_change=True,
        ) from exc
    try:
        async with get_async_session_maker(read_only=True) as session:
            identity = (
                await session.execute(
                    text(
                        "SELECT id, shop_id FROM public.wbcabinet "
                        "WHERE id = :cabinet"
                    ),
                    {"cabinet": cabinet},
                )
            ).mappings().all()
            if not identity:
                raise CollectorBlocked(
                    "PG_IDENTITY_MISSING",
                    f"public.wbcabinet id={cabinet} returned no rows",
                    formal_change=False,
                )
            actual_shop = str(identity[0]["shop_id"])
            if actual_shop != shop_id:
                raise CollectorBlocked(
                    "PG_IDENTITY_MISMATCH",
                    f"cabinet={cabinet} expected shop_id={shop_id} got={actual_shop}",
                    formal_change=False,
                )
            rows = (
                await session.execute(
                    text(
                        """
                        SELECT a.id, a.adv_id, a._search_adv_id, a.name, a.nmids,
                               a.type, a.active_status, a.bot_active,
                               a.automatic_version, a.strategy,
                               a.target_price_for_order, a.max_price_for_order,
                               a.auto_budget_daily_limit,
                               a.search_auto_budget_daily_limit,
                               a.use_common_budget, a.common_budget_daily_limit
                        FROM public.advsetting a
                        WHERE a.wb_cabinet_id = :cabinet
                        """
                    ),
                    {"cabinet": cabinet},
                )
            ).mappings().all()
        return [dict(row) for row in rows]
    except CollectorBlocked:
        raise
    except Exception as exc:
        raise CollectorBlocked(
            "PG_CONNECTIVITY",
            f"read-only PostgreSQL SELECT failed for cabinet={cabinet}: {_safe_error(exc)}",
            formal_change=False,
        ) from exc


async def _load_wb(
    shop_id: str,
    start: date,
    end: date,
    extra_campaign_ids: Iterable[int] = (),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Собрать campaign config, fullstats и supplier orders через GET adapters."""
    try:
        from app.core.di.app_container import AppContainer
        from app.core.di.di_manager import DIManager
        from app.core.mp.wb.api.adapter.promotion_client.fullstats.chunked import (
            run_chunked_single_range,
        )
        from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
        from scripts.wb_api_readonly_ops.collect.orders_sales import (
            _paginate_supplier_rows,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        raise CollectorBlocked(
            "REQUIRED_CAPABILITY_ABSENT",
            f"read-only WB adapter unavailable: {_safe_error(exc)}",
            formal_change=True,
        ) from exc
    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            factory = (
                container.module_resources.wb_manager_hub_factory_container
                .wb_manager_hub_factory()
            )
            hub = factory.get_wb_manager_hub(shop_id)
            promotion = hub.wb_data_manager.promotion_manager
            campaign_ids_raw = (
                await promotion._client.promotion_count_adapter.get_cabinet_adv_ids()
            )
            campaign_ids = sorted(
                {
                    int(value)
                    for value in campaign_ids_raw or []
                    if str(value).isdigit()
                }
                | {int(value) for value in extra_campaign_ids if int(value) > 0}
            )
            campaigns: list[dict[str, Any]] = []
            for offset in range(0, len(campaign_ids), 100):
                payload = await promotion.get_adverts_v2_by_ids(
                    campaign_ids[offset : offset + 100]
                )
                campaigns.extend(
                    item
                    for item in (_jsonable(value) for value in payload or [])
                    if isinstance(item, dict)
                )
            fullstats: list[dict[str, Any]] = []
            if campaign_ids:
                adapter = promotion._client.fullstats_adapter

                async def fetcher(
                    chunk: list[int], from_day: date, to_day: date
                ) -> list[Any]:
                    return await adapter._request_chunk(chunk, from_day, to_day)

                items = await run_chunked_single_range(
                    campaign_ids,
                    start,
                    end,
                    fetcher,
                )
                fullstats = [
                    _jsonable(item.to_dict())
                    for item in items
                    if hasattr(item, "to_dict")
                ]
            reports_manager = getattr(hub.wb_data_manager, "reports_manager", None)

            async def fetch_orders(date_from: str) -> list[object]:
                if reports_manager is not None:
                    return list(
                        await reports_manager.get_supplier_orders(
                            date_from=date_from, flag=0
                        )
                        or []
                    )
                return list(
                    await hub.wb_data_manager.get_supplier_orders(
                        date_from=date_from, flag=0
                    )
                    or []
                )

            budget = ApiCallBudget(max_seconds=1800.0, max_api_calls=5000)
            order_result = await _paginate_supplier_rows(
                fetch=fetch_orders,
                initial_date_from=start.isoformat(),
                budget=budget,
                max_pages=1500,
            )
            orders = [
                _jsonable(row)
                for row in order_result.rows
                if isinstance(_jsonable(row), dict)
            ]
        return campaigns, fullstats, orders
    except CollectorBlocked:
        raise
    except Exception as exc:
        raise CollectorBlocked(
            "WB_READ_FAILURE",
            f"read-only WB GET collection failed: {_safe_error(exc)}",
            formal_change=False,
        ) from exc


def _sha256(path: Path) -> str:
    """Посчитать SHA-256 файла потоково."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_report(
    output_dir: Path,
    report: dict[str, Any],
    entries: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    physical: list[dict[str, Any]],
    gaps: list[str],
) -> dict[str, Any]:
    """Материализовать JSON/JSONL/CSV/Markdown и immutable primary ZIP."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "entry_economics.json"
    entries_path = output_dir / "entry_economics.jsonl"
    daily_path = output_dir / "daily_economics.jsonl"
    physical_path = output_dir / "physical_campaign_spend.jsonl"
    csv_path = output_dir / "entry_economics.csv"
    report_path = output_dir / "SCRIPTS_REPORT.md"
    manifest_path = output_dir / "MANIFEST.json"
    _write_json(json_path, report)
    _write_jsonl(entries_path, entries)
    _write_jsonl(daily_path, daily)
    _write_jsonl(physical_path, physical)
    _write_csv(
        csv_path,
        entries,
        [
            "nm_id",
            "logical_entry_key",
            "historical_only",
            "priority",
            "physical_campaign_ids",
            "spend_allocation",
            "spend_rub",
            "factual_orders",
            "factual_units",
            "factual_gmv_rub",
            "direct_orders",
            "direct_gmv_rub",
            "associated_orders",
            "associated_gmv_rub",
            "direct_drr",
            "direct_cpo_rub",
            "effective_cpo_rub",
            "associated_share",
            "store_drr_uplift_to_10_rub",
            "model_target_cpo_rub",
            "model_cpo_multiplier",
            "model_cpo_delta_rub",
            "evidence_quality",
        ],
    )
    _write_json(
        manifest_path,
        {
            "schema_version": 1,
            "contract_id": CONTRACT_ID,
            "primary_artifact": PRIMARY_ARTIFACT,
            "primary_sha256": "see sidecar",
            "files": [
                json_path.name,
                entries_path.name,
                daily_path.name,
                physical_path.name,
                csv_path.name,
                report_path.name,
                manifest_path.name,
            ],
            "write_counts": WRITE_COUNTS,
            "gaps": gaps,
        },
    )
    gap_lines = [f"- {gap}" for gap in gaps] or ["- NONE"]
    report_path.write_text(
        "\n".join(
            [
                f"# {CONTRACT_ID}",
                "",
                "- mode: `STRICT_READ_ONLY`",
                "- ALL_PRODUCTION_WRITES=0",
                f"- identity: `{report['identity']}`",
                f"- window: `{report['window']}`",
                f"- entries: `{len(entries)}`",
                f"- physical campaigns: `{len(physical)}`",
                f"- gaps: `{len(gaps)}`",
                "",
                "## Evidence quality",
                "",
                *gap_lines,
                "",
                "## Semantics",
                "",
                "- direct/associated metrics use only explicit fullstats ordered nmID and campaign membership.",
                "- multi-NMID campaign spend is not allocated heuristically; affected entry ratios are NULL.",
                "- store factual orders/units/GMV use supplier orders, while store spend uses all physical fullstats campaign days.",
                "- NULL denotes missing/unsupported data or a zero denominator; zero is a factual zero.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    package_files = [
        json_path,
        entries_path,
        daily_path,
        physical_path,
        csv_path,
        report_path,
        manifest_path,
    ]
    primary_path = output_dir / PRIMARY_ARTIFACT
    with zipfile.ZipFile(primary_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in package_files:
            archive.write(path, path.name)
    digest = _sha256(primary_path)
    sidecar_path = output_dir / f"{PRIMARY_ARTIFACT}.sha256"
    sidecar_path.write_text(f"{digest}  {PRIMARY_ARTIFACT}\n", encoding="utf-8")
    checksums_path = output_dir / "checksums.sha256"
    checksum_files = package_files + [primary_path, sidecar_path]
    checksums_path.write_text(
        "\n".join(f"{_sha256(path)}  {path.name}" for path in checksum_files) + "\n",
        encoding="utf-8",
    )
    return {
        "PRIMARY_ARTIFACT": PRIMARY_ARTIFACT,
        "PRIMARY_SHA256": digest,
        "ALL_PRODUCTION_WRITES": 0,
        "LOCAL_REPORT_PATH": str(report_path),
        "OUTPUT_FILES": [path.name for path in checksum_files] + [checksums_path.name],
    }


async def collect(
    *,
    shop_id: str,
    cabinet: int,
    start: date,
    end: date,
    as_of: date,
    output_dir: Path,
    priority_nmids: tuple[int, ...] = PRIORITY_NMIDS,
) -> dict[str, Any]:
    """Собрать и записать полный strict read-only economics contract.

    Args:
        shop_id: WB shop UUID, проверяемый против PostgreSQL cabinet identity.
        cabinet: Expected ``public.wbcabinet.id``.
        start: Inclusive first MSK day.
        end: Inclusive last MSK day; the requested 14-day window ends here.
        as_of: MSK business date used for ``OPEN_PARTIAL`` day state.
        output_dir: Local/pod output directory.
        priority_nmids: Explicit target list; no card/imt expansion is inferred.
    Returns:
        Primary artifact filename, digest and output paths.
    Raises:
        CollectorBlocked: When a required read-only capability or source is unavailable.
        ValueError: When the date contract is not exactly fourteen non-future days.
    """
    if (end - start).days != 13:
        raise ValueError("PROKRAFT_14D window must contain exactly 14 inclusive days")
    if end > as_of:
        raise ValueError("window end cannot be later than as_of date")
    if _day_state(end, as_of) != "OPEN_PARTIAL":
        raise ValueError("requested window end must be the current OPEN_PARTIAL day")
    pg_rows = await _load_pg(shop_id, cabinet)
    pg_campaign_ids = [
        campaign_id
        for row in pg_rows
        for campaign_id in (
            _read_int(row, "adv_id"),
            _read_int(row, "_search_adv_id"),
        )
        if campaign_id
    ]
    campaigns, fullstats, orders = await _load_wb(
        shop_id,
        start,
        end,
        extra_campaign_ids=pg_campaign_ids,
    )
    order_daily, factual_by_nmid, order_gaps = _aggregate_orders(orders, start, end)
    campaign_day, campaign_nm = _expand_fullstats(fullstats, start, end)
    physical, memberships, physical_gaps = _build_physical_rows(
        campaigns,
        pg_rows,
        campaign_day,
        campaign_nm,
        start,
        end,
    )
    entries, entry_gaps = _build_entry_rows(
        physical,
        memberships,
        factual_by_nmid,
        pg_rows,
        start,
        end,
        priority_nmids,
    )
    daily = _build_daily_store_rows(
        start,
        end,
        as_of,
        order_daily,
        physical,
    )
    gaps = sorted(set(order_gaps + physical_gaps + entry_gaps))
    store = _window_store_summary(daily)
    report = {
        "contract_id": CONTRACT_ID,
        "schema_version": 1,
        "identity": {
            "shop_id": shop_id,
            "wb_cabinet_id": cabinet,
            "timezone": "Europe/Moscow",
        },
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "inclusive_days": 14,
            "as_of": as_of.isoformat(),
            "end_day_state": "OPEN_PARTIAL",
            "closed_days": 13,
        },
        "model": {
            "logical_key": "nmid:<nm_id>",
            "physical_campaign_types": ["AUTO", "SEARCH", "OTHER"],
            "direct": "fullstats ordered_nm_id explicitly belongs to campaign membership",
            "associated": "fullstats ordered_nm_id explicitly differs from campaign membership",
            "spend_allocation": "whole campaign spend only when exactly one explicit nmID exists",
            "forbidden_inference": ["glue", "imt_membership", "name_heuristics"],
            "zero_denominator": "NULL",
            "headroom": "factual GMV * target DRR - physical spend; target DRR 5/6/8/10%",
            "model_cpo": "target_price_for_order compared descriptively with effective attributed CPO",
        },
        "priority_targets": [
            {
                "nm_id": nmid,
                "historical_only": nmid == STOP_LOW_STOCK_NMID,
                "stop_reason": (
                    "STOP_LOW_STOCK"
                    if nmid == STOP_LOW_STOCK_NMID
                    else None
                ),
            }
            for nmid in priority_nmids
        ],
        "store": {
            "window": store,
            "daily": daily,
            "physical_campaign_count": len(physical),
            "source_semantics": {
                "orders_units_gmv": "WB supplier orders GET rows",
                "physical_spend": "WB promotion fullstats campaign-day rows",
            },
        },
        "entries": entries,
        "gaps": gaps,
        "source_counts": {
            "pg_advsetting_rows": len(pg_rows),
            "wb_campaign_rows": len(campaigns),
            "wb_fullstats_campaign_rows": len(fullstats),
            "supplier_order_rows": len(orders),
        },
        "write_counts": WRITE_COUNTS,
    }
    return _write_report(output_dir, report, entries, daily, physical, gaps)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать non-interactive CLI параметры Job/local execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shop-id", default=SHOP_ID)
    parser.add_argument("--cabinet", default=str(WB_CABINET_ID), type=int)
    parser.add_argument("--start-date", default="2026-09-05")
    parser.add_argument("--end-date", default="2026-09-18")
    parser.add_argument("--as-of-date", default="2026-09-18")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--priority-nmid", action="append", type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Запустить collector и вывести artifact/blocked handoff fields."""
    args = parse_args(argv)
    try:
        start = _parse_date_argument(args.start_date, "start-date")
        end = _parse_date_argument(args.end_date, "end-date")
        as_of = _parse_date_argument(args.as_of_date, "as-of-date")
        priority = tuple(args.priority_nmid or PRIORITY_NMIDS)
        result = asyncio.run(
            collect(
                shop_id=args.shop_id,
                cabinet=args.cabinet,
                start=start,
                end=end,
                as_of=as_of,
                output_dir=Path(args.output_dir),
                priority_nmids=priority,
            )
        )
    except CollectorBlocked as exc:
        print("STATUS=BLOCKED")
        print(f"BLOCK_REASON={exc.reason}")
        print(f"FORMAL_CHANGE_REQUIRED={'YES' if exc.formal_change else 'NO'}")
        print(f"EVIDENCE={exc.evidence}")
        print("ALL_PRODUCTION_WRITES=0")
        return 2
    except Exception as exc:  # noqa: BLE001
        print("STATUS=BLOCKED")
        print("BLOCK_REASON=CONTRACT_OR_RUNTIME_ERROR")
        print("FORMAL_CHANGE_REQUIRED=NO")
        print(f"EVIDENCE={_safe_error(exc)}")
        print("ALL_PRODUCTION_WRITES=0")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PRIMARY_ARTIFACT={result['PRIMARY_ARTIFACT']}")
    print(f"PRIMARY_SHA256={result['PRIMARY_SHA256']}")
    print("ARTIFACT_CLASS=PROKRAFT_14D_ENTRY_ECONOMICS_R1")
    print("CONTRACT_ID=PROKRAFT_14D_ENTRY_ECONOMICS_R1")
    print("ALL_PRODUCTION_WRITES=0")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

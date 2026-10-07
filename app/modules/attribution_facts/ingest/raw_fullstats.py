"""Нормализация raw WB fullstats days→apps→nms до DayStats collapse."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.modules.attribution_facts.domain.ingest_models import (
    RawCampaignDayRow,
    RawNmContributionRow,
)


def _read_int(row: Mapping[str, Any], *names: str) -> int:
    for name in names:
        value = row.get(name)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return 0


def _read_decimal(row: Mapping[str, Any], *names: str) -> Decimal:
    for name in names:
        value = row.get(name)
        if value is not None:
            try:
                return Decimal(str(value))
            except (TypeError, ValueError):
                continue
    return Decimal(0)


def _parse_event_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def fullstats_item_to_raw_rows(
    item: Mapping[str, Any],
) -> tuple[RawNmContributionRow, ...]:
    """
    Развернуть один fullstats item в nm/app строки.

    Args:
        item: dict или API item с ``advertId`` и ``days[].apps[].nms[]``.

    Returns:
        Кортеж RawNmContributionRow; пустой если apps/nms отсутствуют.
    """
    physical_adv_id = _read_int(item, "advertId", "advert_id")
    if physical_adv_id <= 0:
        return ()
    days_raw = item.get("days")
    if not isinstance(days_raw, list):
        return ()
    rows: list[RawNmContributionRow] = []
    for day in days_raw:
        if not isinstance(day, dict):
            continue
        event_date = _parse_event_date(day.get("date"))
        if event_date is None:
            continue
        apps = day.get("apps")
        if not isinstance(apps, list):
            continue
        for app in apps:
            if not isinstance(app, dict):
                continue
            app_type = _read_int(app, "appType", "app_type")
            nms = app.get("nms")
            if not isinstance(nms, list):
                continue
            for nm in nms:
                if not isinstance(nm, dict):
                    continue
                ordered_nm_id = _read_int(nm, "nmId", "nm_id", "nm")
                if ordered_nm_id <= 0:
                    continue
                rows.append(
                    RawNmContributionRow(
                        physical_adv_id=physical_adv_id,
                        event_date=event_date,
                        app_type=app_type,
                        ordered_nm_id=ordered_nm_id,
                        orders=_read_int(nm, "orders"),
                        gmv_rub=_read_decimal(nm, "sum_price", "sumPrice"),
                        atc=_read_int(nm, "atbs") or None,
                        units_shks=_read_int(nm, "shks") or None,
                    )
                )
    return tuple(rows)


def fullstats_items_to_campaign_day_rows(
    items: Sequence[Mapping[str, Any]],
) -> tuple[RawCampaignDayRow, ...]:
    """Собрать дневные totals из raw days (тот же payload, что nm breakdown)."""
    result: list[RawCampaignDayRow] = []
    for item in items:
        physical_adv_id = _read_int(item, "advertId", "advert_id")
        days_raw = item.get("days")
        if physical_adv_id <= 0 or not isinstance(days_raw, list):
            continue
        for day in days_raw:
            if not isinstance(day, dict):
                continue
            event_date = _parse_event_date(day.get("date"))
            if event_date is None:
                continue
            result.append(
                RawCampaignDayRow(
                    physical_adv_id=physical_adv_id,
                    event_date=event_date,
                    orders=_read_int(day, "orders"),
                    gmv_rub=_read_decimal(day, "sum_price", "sumPrice"),
                )
            )
    return tuple(result)

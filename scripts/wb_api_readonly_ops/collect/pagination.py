"""Cursor pagination helpers для statistics-api orders/sales (lastChangeDate)."""

from __future__ import annotations

from typing import Any

from app.core.mp.wb.api.generated.reports.v1.reports_client.types import UNSET

from scripts.wb_api_readonly_ops.collect.jsonable import jsonable


def extract_last_change_date(row: object) -> str | None:
    """Извлечь lastChangeDate из OrdersItem/SalesItem или dict."""
    if hasattr(row, "last_change_date"):
        raw = getattr(row, "last_change_date")
    elif isinstance(row, dict):
        raw = row.get("lastChangeDate") or row.get("last_change_date")
    else:
        return None
    if raw is UNSET or raw is None:
        return None
    text = str(raw).strip()
    if not text or text.startswith("0001"):
        return None
    return text


def row_dedup_key(row: object, *, fallback_prefix: str) -> str:
    """Deterministic dedup key: srid/saleID, иначе stable JSON fallback."""
    if isinstance(row, dict):
        mapping = row
    else:
        mapping = jsonable(row)
        if not isinstance(mapping, dict):
            return f"{fallback_prefix}:obj:{hash(str(mapping))}"
    for key in ("srid", "saleID", "gNumber"):
        val = mapping.get(key)
        if val:
            return f"{key}:{val}"
    serialized = repr(jsonable(row))
    return f"{fallback_prefix}:hash:{hash(serialized)}"


def merge_unique_rows(
    existing: list[dict[str, Any]],
    new_page: list[object],
) -> tuple[list[dict[str, Any]], int, bool]:
    """Добавить страницу с dedup; вернуть (merged, added_count, duplicate_page)."""
    seen = {row_dedup_key(r, fallback_prefix="row"): r for r in existing}
    added = 0
    for item in new_page:
        as_dict = jsonable(item)
        if not isinstance(as_dict, dict):
            as_dict = {"value": as_dict}
        key = row_dedup_key(as_dict, fallback_prefix="row")
        if key not in seen:
            seen[key] = as_dict
            added += 1
    duplicate_page = added == 0 and bool(new_page)
    return list(seen.values()), added, duplicate_page


def should_fetch_next_page(
    page_rows: list[object],
    *,
    previous_cursor: str | None,
    new_cursor: str | None,
) -> bool:
    """True если нужна следующая страница (не empty, не duplicate cursor)."""
    if not page_rows:
        return False
    if previous_cursor is not None and new_cursor == previous_cursor:
        return False
    return new_cursor is not None

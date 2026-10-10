"""
Один bounded multi-page read supplier orders на магазин и окно.

Пагинация по ``lastChangeDate``, ``flag=0``. Неполный бюджет, повтор страницы
или застой курсора не считаются полным окном.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.core.mp.wb.api.generated.reports.v1.reports_client.types import UNSET
from app.modules.ad_control_settings.runtime.ports import SupplierOrdersPagePort
from app.modules.ad_control_settings.runtime.shop_order_gmv import (
    CollectionStop,
    CollectionVerdict,
    SupplierOrderLine,
    parse_moscow_datetime,
)
from app.modules.attribution_facts.domain.models import DateWindow

DEFAULT_MAX_PAGES = 200
DEFAULT_API_BUDGET = 200


@dataclass(frozen=True, slots=True)
class CollectedSupplierOrders:
    """Сырые нормализованные строки и вердикт пагинации."""

    lines: tuple[SupplierOrderLine, ...]
    verdict: CollectionVerdict


def normalize_supplier_order_row(row: object) -> SupplierOrderLine:
    """Привести OrdersItem или dict к строке агрегатора. Чужие цены не читаются."""
    srid_raw = _field(row, "srid")
    price_raw = _field(row, "price_with_disc", "priceWithDisc")
    cancel_raw = _field(row, "is_cancel", "isCancel")
    event_raw = _field(row, "date")
    cursor_raw = _field(row, "last_change_date", "lastChangeDate")
    cart_raw = _field(row, "g_number", "gNumber")
    price, absent = _price(price_raw)
    srid = _text(srid_raw)
    event_at = parse_moscow_datetime(event_raw) if not _missing(event_raw) else None
    cursor_at = parse_moscow_datetime(cursor_raw) if not _missing(cursor_raw) else None
    return SupplierOrderLine(
        srid=srid,
        price_with_disc=price,
        is_cancel=cancel_raw is True,
        event_date=None if event_at is None else event_at.date(),
        last_change_at=cursor_at,
        g_number=_text(cart_raw),
        field_absent=absent,
    )


async def collect_supplier_orders(
    port: SupplierOrdersPagePort,
    *,
    window: DateWindow,
    collected_at: datetime,
    max_pages: int = DEFAULT_MAX_PAGES,
    api_budget: int = DEFAULT_API_BUDGET,
) -> CollectedSupplierOrders:
    """
    Собрать ленту один раз, начиная с полуночи MSK ``window.start``.

    Вызывающий обязан не повторять сбор на кампанию или nmID.
    """
    date_from = f"{window.start.isoformat()}T00:00:00"
    previous_cursor: str | None = None
    seen_srids: set[str] = set()
    lines: list[SupplierOrderLine] = []
    pages = 0
    api_calls = 0
    max_cursor: datetime | None = None
    stop = CollectionStop.MAX_PAGES
    while pages < max_pages:
        if api_calls >= api_budget:
            stop = CollectionStop.API_BUDGET
            break
        api_calls += 1
        page = list(await port.get_supplier_orders(date_from=date_from, flag=0) or [])
        pages += 1
        if not page:
            stop = CollectionStop.NATURAL_END
            break
        page_lines = tuple(normalize_supplier_order_row(item) for item in page)
        new_srids = 0
        for line in page_lines:
            lines.append(line)
            if line.last_change_at is not None and (
                max_cursor is None or line.last_change_at > max_cursor
            ):
                max_cursor = line.last_change_at
            if line.srid and line.srid not in seen_srids:
                seen_srids.add(line.srid)
                new_srids += 1
        if new_srids == 0:
            stop = CollectionStop.DUPLICATE_PAGE
            break
        cursor = _cursor_text(page[-1])
        if cursor is None or cursor == previous_cursor:
            stop = CollectionStop.CURSOR_STALL
            break
        previous_cursor = cursor
        date_from = cursor
    else:
        stop = CollectionStop.MAX_PAGES
    return CollectedSupplierOrders(
        lines=tuple(lines),
        verdict=CollectionVerdict(
            stop=stop,
            first_date_from_is_window_start=True,
            pages_fetched=pages,
            max_last_change_at=max_cursor,
            collected_at=collected_at,
        ),
    )


def _cursor_text(row: object) -> str | None:
    raw = _field(row, "last_change_date", "lastChangeDate")
    if _missing(raw):
        return None
    text = str(raw).strip()
    if not text or text.startswith("0001"):
        return None
    return text


def _field(row: object, *names: str) -> object:
    if isinstance(row, dict):
        for name in names:
            if name in row:
                return row[name]
        return UNSET
    for name in names:
        if hasattr(row, name):
            value = getattr(row, name)
            if value is not UNSET:
                return value
    return UNSET


def _missing(value: object) -> bool:
    return value is None or value is UNSET


def _text(value: object) -> str | None:
    if _missing(value):
        return None
    text = str(value).strip()
    return text or None


def _price(value: object) -> tuple[Decimal | None, bool]:
    if _missing(value):
        return None, True
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None, True
    try:
        return Decimal(str(value)), False
    except (InvalidOperation, ValueError):
        return None, True

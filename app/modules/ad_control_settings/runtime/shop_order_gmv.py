"""
Агрегат whole-shop order GMV из supplier-order строк.

Денежное поле — только ``priceWithDisc``. Дедуп по ``srid``. Отмена
``isCancel`` исключается. Дата заказа — ``date`` в Europe/Moscow.
``lastChangeDate`` сюда не входит как бизнес-дата.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.attribution_facts.domain.models import DateWindow

MOSCOW = ZoneInfo("Europe/Moscow")
V1_REVENUE_BASIS = "ORDERS_OR_SALES_REPORTS_READ"


class ShopOrderGmvStatus(StrEnum):
    """Итог покрытия supplier-orders для одного окна."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    FIELD_ABSENT = "FIELD_ABSENT"
    STALE = "STALE"


class CollectionStop(StrEnum):
    """Почему остановилась пагинация."""

    NATURAL_END = "NATURAL_END"
    MAX_PAGES = "MAX_PAGES"
    API_BUDGET = "API_BUDGET"
    DUPLICATE_PAGE = "DUPLICATE_PAGE"
    CURSOR_STALL = "CURSOR_STALL"
    DATE_FROM_MISMATCH = "DATE_FROM_MISMATCH"


@dataclass(frozen=True, slots=True)
class SupplierOrderLine:
    """Нормализованная строка ленты заказов (ещё не отфильтрованная)."""

    srid: str | None
    price_with_disc: Decimal | None
    is_cancel: bool
    event_date: date | None
    last_change_at: datetime | None
    g_number: str | None
    field_absent: bool


@dataclass(frozen=True, slots=True)
class CollectionVerdict:
    """Честность cursor-сбора, отдельно от суммы GMV."""

    stop: CollectionStop
    first_date_from_is_window_start: bool
    pages_fetched: int
    max_last_change_at: datetime | None
    collected_at: datetime


@dataclass(frozen=True, slots=True)
class ShopOrderGmvAggregate:
    """Shop GMV за окно. Число есть только при COMPLETE и ненулевом или нулевом полном окне."""

    status: ShopOrderGmvStatus
    whole_shop_order_gmv_rub: Decimal | None
    order_item_count: int
    reason: AdControlReasonCode | None
    window: DateWindow
    revenue_basis: str
    pages_fetched: int
    stop: CollectionStop


def window_id(window: DateWindow) -> str:
    """Стабильный идентификатор включительного календарного окна."""
    return f"{window.start.isoformat()}/{window.end.isoformat()}"


def window_end_exclusive(window: DateWindow) -> datetime:
    """Момент закрытия окна: 00:00 MSK дня, следующего за ``end``."""
    closed = date.fromordinal(window.end.toordinal() + 1)
    return datetime(closed.year, closed.month, closed.day, tzinfo=MOSCOW)


def as_moscow(moment: datetime) -> datetime:
    """Привести момент к Europe/Moscow. Naive считается уже московским."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=MOSCOW)
    return moment.astimezone(MOSCOW)


def parse_moscow_datetime(raw: object) -> datetime | None:
    """Разобрать WB datetime. Пустое и sentinel ``0001`` — None."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.startswith("0001"):
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return as_moscow(parsed)


def is_collection_complete(verdict: CollectionVerdict) -> bool:
    """Полный сбор: естественный хвост и честный первый ``dateFrom``."""
    return (
        verdict.stop == CollectionStop.NATURAL_END
        and verdict.first_date_from_is_window_start
        and verdict.pages_fetched > 0
    )


def is_feed_stale(verdict: CollectionVerdict, window: DateWindow) -> bool:
    """
    Свежесть не лечит неполное покрытие.

    Закрытое окно свежее, только если сбор не раньше 00:00 MSK следующего дня.
    """
    collected = as_moscow(verdict.collected_at)
    return collected < window_end_exclusive(window)


def aggregate_shop_order_gmv(
    lines: tuple[SupplierOrderLine, ...],
    window: DateWindow,
    verdict: CollectionVerdict,
    *,
    revenue_basis: str = V1_REVENUE_BASIS,
) -> ShopOrderGmvAggregate:
    """
    Свернуть строки в whole-shop GMV.

    Неполное покрытие, отсутствующее поле и stale не отдают числовой GMV.
    Нулевой полный GMV остаётся COMPLETE (деление блокирует слой economics).
    """
    if revenue_basis != V1_REVENUE_BASIS:
        return ShopOrderGmvAggregate(
            status=ShopOrderGmvStatus.INCOMPLETE,
            whole_shop_order_gmv_rub=None,
            order_item_count=0,
            reason=AdControlReasonCode.REVENUE_BASIS_UNSUPPORTED,
            window=window,
            revenue_basis=revenue_basis,
            pages_fetched=verdict.pages_fetched,
            stop=verdict.stop,
        )
    if not is_collection_complete(verdict):
        return _blocked(
            ShopOrderGmvStatus.INCOMPLETE,
            AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE,
            window,
            verdict,
            revenue_basis,
        )
    by_srid: dict[str, SupplierOrderLine] = {}
    for line in lines:
        if line.event_date is None:
            return _blocked(
                ShopOrderGmvStatus.INCOMPLETE,
                AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE,
                window,
                verdict,
                revenue_basis,
            )
        if not line.srid:
            return _blocked(
                ShopOrderGmvStatus.INCOMPLETE,
                AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE,
                window,
                verdict,
                revenue_basis,
            )
        by_srid[line.srid] = line
    total = Decimal(0)
    count = 0
    for line in by_srid.values():
        if line.event_date is None:
            continue
        if line.event_date < window.start or line.event_date > window.end:
            continue
        if line.is_cancel:
            continue
        if line.field_absent or line.price_with_disc is None:
            return _blocked(
                ShopOrderGmvStatus.FIELD_ABSENT,
                AdControlReasonCode.SHOP_ORDER_GMV_FIELD_ABSENT,
                window,
                verdict,
                revenue_basis,
            )
        total += line.price_with_disc
        count += 1
    if is_feed_stale(verdict, window):
        return _blocked(
            ShopOrderGmvStatus.STALE,
            AdControlReasonCode.SHOP_ORDER_GMV_STALE,
            window,
            verdict,
            revenue_basis,
        )
    return ShopOrderGmvAggregate(
        status=ShopOrderGmvStatus.COMPLETE,
        whole_shop_order_gmv_rub=total,
        order_item_count=count,
        reason=None,
        window=window,
        revenue_basis=revenue_basis,
        pages_fetched=verdict.pages_fetched,
        stop=verdict.stop,
    )


def _blocked(
    status: ShopOrderGmvStatus,
    reason: AdControlReasonCode,
    window: DateWindow,
    verdict: CollectionVerdict,
    revenue_basis: str,
) -> ShopOrderGmvAggregate:
    return ShopOrderGmvAggregate(
        status=status,
        whole_shop_order_gmv_rub=None,
        order_item_count=0,
        reason=reason,
        window=window,
        revenue_basis=revenue_basis,
        pages_fetched=verdict.pages_fetched,
        stop=verdict.stop,
    )

"""Shop GMV grain и shop DRR/headroom (Task 4.1)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.modules.ad_control_settings.domain.enums import DataSufficiency
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.runtime.shop_factual import shop_factual_economics
from app.modules.ad_control_settings.runtime.shop_order_gmv import (
    MOSCOW,
    CollectionStop,
    CollectionVerdict,
    ShopOrderGmvStatus,
    SupplierOrderLine,
    aggregate_shop_order_gmv,
    window_end_exclusive,
)
from app.modules.ad_control_settings.runtime.supplier_orders_collect import (
    collect_supplier_orders,
)
from app.modules.attribution_facts.domain.models import DateWindow

pytestmark = pytest.mark.unit

_WINDOW = DateWindow(start=date(2026, 10, 1), end=date(2026, 10, 7))
_FRESH = datetime(2026, 10, 8, 3, tzinfo=MOSCOW)


def _line(
    srid: str,
    price: Decimal | None,
    *,
    day: date = date(2026, 10, 3),
    cancel: bool = False,
    absent: bool = False,
    g_number: str = "cart",
) -> SupplierOrderLine:
    return SupplierOrderLine(
        srid=srid,
        price_with_disc=price,
        is_cancel=cancel,
        event_date=day,
        last_change_at=_FRESH,
        g_number=g_number,
        field_absent=absent or price is None,
    )


def _verdict(
    stop: CollectionStop = CollectionStop.NATURAL_END,
    *,
    collected_at: datetime = _FRESH,
    pages: int = 1,
    date_from_ok: bool = True,
) -> CollectionVerdict:
    return CollectionVerdict(
        stop=stop,
        first_date_from_is_window_start=date_from_ok,
        pages_fetched=pages,
        max_last_change_at=collected_at,
        collected_at=collected_at,
    )


def test_shop_gmv_uses_price_with_disc_srid_and_excludes_cancel() -> None:
    """Последний srid побеждает. Отмена и чужая дата не входят. gNumber не дедупит."""
    lines = (
        _line("a", Decimal(600), g_number="same"),
        _line("a", Decimal(999), g_number="same"),
        _line("b", Decimal(400), g_number="same"),
        _line("c", Decimal(50), cancel=True),
        _line("d", Decimal(70), day=date(2026, 9, 1)),
    )
    aggregate = aggregate_shop_order_gmv(lines, _WINDOW, _verdict())
    assert aggregate.status == ShopOrderGmvStatus.COMPLETE
    assert aggregate.whole_shop_order_gmv_rub == Decimal(1399)
    assert aggregate.order_item_count == 2


def test_duplicate_srid_keeps_latest_row() -> None:
    """Повтор srid на следующей странице заменяется более свежей строкой."""
    lines = (
        _line("a", Decimal(10), cancel=False),
        _line("a", Decimal(25), cancel=True),
    )
    aggregate = aggregate_shop_order_gmv(lines, _WINDOW, _verdict())
    assert aggregate.whole_shop_order_gmv_rub == Decimal(0)
    assert aggregate.order_item_count == 0
    assert aggregate.status == ShopOrderGmvStatus.COMPLETE


@pytest.mark.parametrize(
    ("stop", "date_ok", "reason"),
    [
        (CollectionStop.MAX_PAGES, True, AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE),
        (CollectionStop.API_BUDGET, True, AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE),
        (CollectionStop.DUPLICATE_PAGE, True, AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE),
        (CollectionStop.CURSOR_STALL, True, AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE),
        (CollectionStop.NATURAL_END, False, AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE),
    ],
)
def test_incomplete_collection_has_no_numeric_gmv(
    stop: CollectionStop,
    date_ok: bool,
    reason: AdControlReasonCode,
) -> None:
    aggregate = aggregate_shop_order_gmv(
        (_line("a", Decimal(100)),),
        _WINDOW,
        _verdict(stop, date_from_ok=date_ok),
    )
    assert aggregate.whole_shop_order_gmv_rub is None
    assert aggregate.reason == reason


def test_missing_price_with_disc_fails_closed() -> None:
    aggregate = aggregate_shop_order_gmv(
        (_line("a", None, absent=True),),
        _WINDOW,
        _verdict(),
    )
    assert aggregate.status == ShopOrderGmvStatus.FIELD_ABSENT
    assert aggregate.reason == AdControlReasonCode.SHOP_ORDER_GMV_FIELD_ABSENT
    assert aggregate.whole_shop_order_gmv_rub is None


def test_missing_srid_is_incomplete() -> None:
    broken = SupplierOrderLine(
        srid=None,
        price_with_disc=Decimal(10),
        is_cancel=False,
        event_date=date(2026, 10, 3),
        last_change_at=_FRESH,
        g_number="cart",
        field_absent=False,
    )
    aggregate = aggregate_shop_order_gmv((broken,), _WINDOW, _verdict())
    assert aggregate.reason == AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE


def test_stale_when_collected_before_window_closes() -> None:
    early = window_end_exclusive(_WINDOW) - timedelta(minutes=1)
    aggregate = aggregate_shop_order_gmv(
        (_line("a", Decimal(10)),),
        _WINDOW,
        _verdict(collected_at=early),
    )
    assert aggregate.status == ShopOrderGmvStatus.STALE
    assert aggregate.whole_shop_order_gmv_rub is None


@pytest.mark.parametrize(
    ("gmv", "spend", "allowed", "headroom", "drr"),
    [
        (Decimal(1_000_000), Decimal(70_000), Decimal(80_000), Decimal(10_000), Decimal("7.00")),
        (Decimal(1_000_000), Decimal(80_000), Decimal(80_000), Decimal(0), Decimal("8.00")),
        (Decimal(1_000_000), Decimal(90_000), Decimal(80_000), Decimal(-10_000), Decimal("9.00")),
    ],
)
def test_shop_headroom_sign(
    gmv: Decimal,
    spend: Decimal,
    allowed: Decimal,
    headroom: Decimal,
    drr: Decimal,
) -> None:
    aggregate = aggregate_shop_order_gmv((_line("a", gmv),), _WINDOW, _verdict())
    economics = shop_factual_economics(
        aggregate,
        spend_rub=spend,
        spend_window=_WINDOW,
        shop_target_drr_percent=Decimal(8),
    )
    assert economics.sufficiency == DataSufficiency.SUFFICIENT
    assert economics.allowed_spend_rub == allowed
    assert economics.headroom_rub == headroom
    assert economics.actual_drr_percent == drr


def test_zero_shop_gmv_does_not_divide() -> None:
    aggregate = aggregate_shop_order_gmv((), _WINDOW, _verdict())
    economics = shop_factual_economics(
        aggregate,
        spend_rub=Decimal(10),
        spend_window=_WINDOW,
        shop_target_drr_percent=Decimal(8),
    )
    assert economics.actual_drr_percent is None
    assert economics.headroom_rub is None
    assert economics.sufficiency == DataSufficiency.INSUFFICIENT
    assert AdControlReasonCode.ACTUAL_DRR_INSUFFICIENT in economics.reason_codes
    assert "zero_shop_order_gmv" in economics.blockers


def test_spend_incomplete_and_window_mismatch() -> None:
    aggregate = aggregate_shop_order_gmv((_line("a", Decimal(100)),), _WINDOW, _verdict())
    missing_spend = shop_factual_economics(
        aggregate,
        spend_rub=None,
        spend_window=_WINDOW,
        shop_target_drr_percent=Decimal(8),
    )
    assert AdControlReasonCode.SHOP_SPEND_INCOMPLETE in missing_spend.reason_codes
    assert missing_spend.actual_drr_percent is None
    other = DateWindow(start=date(2026, 9, 1), end=date(2026, 9, 7))
    mismatch = shop_factual_economics(
        aggregate,
        spend_rub=Decimal(10),
        spend_window=other,
        shop_target_drr_percent=Decimal(8),
    )
    assert AdControlReasonCode.CPO_INPUTS_INCOMPLETE in mismatch.reason_codes


def test_unsupported_revenue_basis_skips_numeric_gmv() -> None:
    aggregate = aggregate_shop_order_gmv(
        (_line("a", Decimal(100)),),
        _WINDOW,
        _verdict(),
        revenue_basis="WB_COMMON_STAT",
    )
    assert aggregate.reason == AdControlReasonCode.REVENUE_BASIS_UNSUPPORTED
    economics = shop_factual_economics(
        aggregate,
        spend_rub=Decimal(10),
        spend_window=_WINDOW,
        shop_target_drr_percent=Decimal(8),
    )
    assert economics.sufficiency == DataSufficiency.UNSUPPORTED


class _Pages:
    def __init__(self, pages: list[list[dict[str, object]]]) -> None:
        self._pages = pages
        self.calls: list[tuple[str, int]] = []

    async def get_supplier_orders(
        self,
        *,
        date_from: str,
        flag: int = 0,
    ) -> list[dict[str, object]]:
        self.calls.append((date_from, flag))
        if not self._pages:
            return []
        return self._pages.pop(0)


@pytest.mark.asyncio
async def test_collector_paginates_once_and_stops_on_empty_tail() -> None:
    port = _Pages(
        [
            [
                {
                    "srid": "1",
                    "priceWithDisc": 10,
                    "isCancel": False,
                    "date": "2026-10-02T10:00:00",
                    "lastChangeDate": "2026-10-02T11:00:00",
                    "gNumber": "g",
                }
            ],
            [],
        ]
    )
    collected = await collect_supplier_orders(
        port,
        window=_WINDOW,
        collected_at=_FRESH,
        max_pages=5,
        api_budget=5,
    )
    assert collected.verdict.stop == CollectionStop.NATURAL_END
    assert port.calls[0] == ("2026-10-01T00:00:00", 0)
    assert port.calls[1][0] == "2026-10-02T11:00:00"
    assert len(port.calls) == 2


@pytest.mark.asyncio
async def test_collector_budget_exhaustion_is_not_complete() -> None:
    port = _Pages(
        [
            [
                {
                    "srid": "1",
                    "priceWithDisc": 10,
                    "date": "2026-10-02T10:00:00",
                    "lastChangeDate": "2026-10-02T11:00:00",
                }
            ]
        ]
    )
    collected = await collect_supplier_orders(
        port,
        window=_WINDOW,
        collected_at=_FRESH,
        max_pages=10,
        api_budget=1,
    )
    assert collected.verdict.stop == CollectionStop.API_BUDGET
    aggregate = aggregate_shop_order_gmv(collected.lines, _WINDOW, collected.verdict)
    assert aggregate.whole_shop_order_gmv_rub is None

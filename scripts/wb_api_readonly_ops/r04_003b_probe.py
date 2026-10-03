"""Live flag=1 single-day probe для ORDERS_OR_SALES_REPORTS_READ (COL-R04-003B).

Job runtime only. Не возвращает raw rows — только counts и метаданные probe.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, cast

from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op
from scripts.wb_api_readonly_ops.r04_003b_constants import (
    LOCAL_ADAPTER_REF,
    METHOD_CLASS,
    OFFICIAL_SEMANTICS_ORDERS,
    OFFICIAL_SEMANTICS_SALES,
    ORDERS_ENDPOINT,
    PROBE_DATE,
    PROBE_FLAG,
    SALES_ENDPOINT,
)


def _str_list() -> list[str]:
    return []


@dataclass
class OrdersSalesProbeEvidence:
    """Результат live probe orders+sales (без raw rows в RETURN)."""

    orders_status: str  # PASS | REFUSED
    sales_status: str
    orders_http_attempts: int
    sales_http_attempts: int
    orders_rows_count: int
    sales_rows_count: int
    orders_http_status_class: str
    sales_http_status_class: str
    orders_error: str | None = None
    sales_error: str | None = None
    gap_or_refusal_ids: list[str] = field(default_factory=_str_list)
    schema_fingerprint_orders: str = "ABSENT"
    schema_fingerprint_sales: str = "ABSENT"
    captured_at: str | None = None


def _count_fingerprint(endpoint: str, rows_count: int, flag: int) -> str:
    meta = {
        "endpoint": endpoint,
        "probe_date": PROBE_DATE,
        "flag": flag,
        "rows_count": rows_count,
    }
    blob = json.dumps(meta, sort_keys=True)
    return f"fp_probe_{hashlib.sha256(blob.encode()).hexdigest()[:16]}"


async def run_orders_sales_flag1_probe(wb_data_manager: object) -> OrdersSalesProbeEvidence:
    """Один calendar-day probe: orders+sales GET flag=1 на PROBE_DATE.

    HTTP 200 с пустым списком — admissible access evidence (не downgrade).
    """
    assert_read_only_op("get_supplier_orders")
    assert_read_only_op("get_supplier_sales")

    dm = cast(Any, wb_data_manager)
    reports_manager = getattr(dm, "reports_manager", None)
    gaps: list[str] = []

    orders_count = 0
    sales_count = 0
    orders_error: str | None = None
    sales_error: str | None = None
    orders_attempts = 0
    sales_attempts = 0
    orders_http = "NONE"
    sales_http = "NONE"

    try:
        orders_attempts = 1
        if reports_manager is not None:
            orders_raw = await reports_manager.get_supplier_orders(
                date_from=PROBE_DATE,
                flag=PROBE_FLAG,
            )
        else:
            orders_raw = await dm.get_supplier_orders(
                date_from=PROBE_DATE,
                flag=PROBE_FLAG,
            )
        orders_count = len(list(orders_raw or []))
        orders_http = "HTTP_200"
    except Exception as exc:  # noqa: BLE001
        orders_error = f"{type(exc).__name__}: {exc}"
        orders_http = "HTTP_ERROR"
        gaps.append("orders_probe_failed")

    try:
        sales_attempts = 1
        if reports_manager is not None:
            sales_raw = await reports_manager.get_supplier_sales(
                date_from=PROBE_DATE,
                flag=PROBE_FLAG,
            )
        else:
            sales_raw = await dm.get_supplier_sales(
                date_from=PROBE_DATE,
                flag=PROBE_FLAG,
            )
        sales_count = len(list(sales_raw or []))
        sales_http = "HTTP_200"
    except Exception as exc:  # noqa: BLE001
        sales_error = f"{type(exc).__name__}: {exc}"
        sales_http = "HTTP_ERROR"
        gaps.append("sales_probe_failed")

    orders_pass = orders_error is None and orders_http == "HTTP_200"
    sales_pass = sales_error is None and sales_http == "HTTP_200"

    if not orders_pass:
        gaps.append("NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET")
    if not sales_pass:
        gaps.append("NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET")

    return OrdersSalesProbeEvidence(
        orders_status="PASS" if orders_pass else "REFUSED",
        sales_status="PASS" if sales_pass else "REFUSED",
        orders_http_attempts=orders_attempts,
        sales_http_attempts=sales_attempts,
        orders_rows_count=orders_count,
        sales_rows_count=sales_count,
        orders_http_status_class=orders_http,
        sales_http_status_class=sales_http,
        orders_error=orders_error,
        sales_error=sales_error,
        gap_or_refusal_ids=gaps,
        schema_fingerprint_orders=_count_fingerprint(
            ORDERS_ENDPOINT, orders_count, PROBE_FLAG
        ),
        schema_fingerprint_sales=_count_fingerprint(
            SALES_ENDPOINT, sales_count, PROBE_FLAG
        ),
    )


def orders_family_pass(ev: OrdersSalesProbeEvidence) -> bool:
    """PASS: both endpoints admissible HTTP 200 (empty list ok)."""
    return ev.orders_status == "PASS" and ev.sales_status == "PASS"


def probe_to_family_payload(ev: OrdersSalesProbeEvidence) -> dict[str, object]:
    """Минимальный payload для evidence JSON (без raw rows)."""
    return {
        "family_id": "orders_or_sales_reports_read",
        "orders_endpoint": ORDERS_ENDPOINT,
        "sales_endpoint": SALES_ENDPOINT,
        "method_class": METHOD_CLASS,
        "official_semantics_orders": OFFICIAL_SEMANTICS_ORDERS,
        "official_semantics_sales": OFFICIAL_SEMANTICS_SALES,
        "local_adapter": LOCAL_ADAPTER_REF,
        "probe_date": PROBE_DATE,
        "flag": PROBE_FLAG,
        "orders_rows_count": ev.orders_rows_count,
        "sales_rows_count": ev.sales_rows_count,
        "empty_response_admissible": True,
        "orders_http_status_class": ev.orders_http_status_class,
        "sales_http_status_class": ev.sales_http_status_class,
        "gap_or_refusal_ids": ev.gap_or_refusal_ids,
    }

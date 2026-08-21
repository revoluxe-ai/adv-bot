"""Full READ_ONLY collect orchestrator (core dataset families)."""

from __future__ import annotations

import datetime
import logging
import tempfile
from pathlib import Path
from typing import Any

from scripts.wb_api_readonly_ops.collect.ads import collect_ads
from scripts.wb_api_readonly_ops.collect.api_budget import ApiBudgetExhausted, ApiCallBudget
from scripts.wb_api_readonly_ops.collect.archive import CollectReport, write_collect_archive
from scripts.wb_api_readonly_ops.collect.cards import collect_cards
from scripts.wb_api_readonly_ops.collect.coverage import ArtifactIntegrityError
from scripts.wb_api_readonly_ops.collect.funnel import collect_funnel
from scripts.wb_api_readonly_ops.collect.normqueries import collect_normqueries
from scripts.wb_api_readonly_ops.collect.orders_sales import collect_orders_sales
from scripts.wb_api_readonly_ops.collect.raw_store import RawStore
from scripts.wb_api_readonly_ops.models import OverallStatus

logger = logging.getLogger(__name__)

# WB sales-funnel products/history: см. swagger — max last 7 days on this endpoint.

MISSING_COLLECTOR_CAPABILITIES: list[str] = [
    "finance_realization",
    "stocks",
    "prices",
    "promotions",
    "adv_v0_config_norms_limits",
    "search_report_separate_family_if_permission_gap",
    "funnel_historical_beyond_7_days_requires_separate_surface",
    "normquery_historical_beyond_30_days_requires_separate_surface",
]


async def run_full_collect(
    *,
    shop_id: str,
    wb_data_manager: object,
    output_dir: Path,
    orders_date_from: str,
    max_seconds: float,
    max_api_calls: int,
    ads_date_from: str | None = None,
    ads_date_to: str | None = None,
    funnel_nmid_batch_size: int = 20,
    cards_page_limit: int = 100,
) -> CollectReport:
    """Собрать core analytical dataset без sample truncation."""
    budget = ApiCallBudget(max_seconds=max_seconds, max_api_calls=max_api_calls)
    staging = Path(tempfile.mkdtemp(prefix="wb_ro_collect_"))
    store = RawStore(output_dir=staging)
    integrity_errors: list[str] = []
    overall = OverallStatus.OK

    try:
        orders_rows, sales_rows = await collect_orders_sales(
            wb_data_manager,
            store=store,
            budget=budget,
            orders_date_from=orders_date_from,
        )
    except (ApiBudgetExhausted, ArtifactIntegrityError) as exc:
        integrity_errors.append(f"orders_sales: {exc}")
        orders_rows, sales_rows = [], []
        overall = OverallStatus.PARTIAL
    except Exception as exc:  # noqa: BLE001 — best-effort collect must archive
        logger.exception("orders_sales collect failed")
        integrity_errors.append(f"orders_sales: {type(exc).__name__}: {exc}")
        orders_rows, sales_rows = [], []
        overall = OverallStatus.PARTIAL

    try:
        nmids, _cards = await collect_cards(
            wb_data_manager,
            store=store,
            budget=budget,
            page_limit=cards_page_limit,
        )
    except (ApiBudgetExhausted, ArtifactIntegrityError) as exc:
        integrity_errors.append(f"cards: {exc}")
        nmids = _nmids_from_orders(orders_rows, sales_rows)
        overall = OverallStatus.PARTIAL
    except Exception as exc:  # noqa: BLE001
        logger.exception("cards collect failed")
        integrity_errors.append(f"cards: {type(exc).__name__}: {exc}")
        nmids = _nmids_from_orders(orders_rows, sales_rows)
        overall = OverallStatus.PARTIAL

    ads_from, ads_to = _resolve_ads_dates(
        orders_date_from=orders_date_from,
        orders_rows=orders_rows,
        ads_date_from=ads_date_from,
        ads_date_to=ads_date_to,
    )
    try:
        _adv_ids, campaign_rows = await collect_ads(
            wb_data_manager,
            store=store,
            budget=budget,
            date_from=ads_from,
            date_to=ads_to,
        )
    except (ApiBudgetExhausted, ArtifactIntegrityError) as exc:
        integrity_errors.append(f"ads: {exc}")
        campaign_rows = []
        overall = OverallStatus.PARTIAL
    except Exception as exc:  # noqa: BLE001
        logger.exception("ads collect failed")
        integrity_errors.append(f"ads: {type(exc).__name__}: {exc}")
        campaign_rows = []
        overall = OverallStatus.PARTIAL

    funnel_to = ads_to
    funnel_nmids = nmids or _nmids_from_orders(orders_rows, sales_rows)
    try:
        await collect_funnel(
            wb_data_manager,
            store=store,
            budget=budget,
            nmids=funnel_nmids,
            date_from=ads_from,
            date_to=funnel_to,
            nmid_batch_size=funnel_nmid_batch_size,
        )
    except (ApiBudgetExhausted, ArtifactIntegrityError) as exc:
        integrity_errors.append(f"funnel: {exc}")
        overall = OverallStatus.PARTIAL
    except Exception as exc:  # noqa: BLE001
        logger.exception("funnel collect failed")
        integrity_errors.append(f"funnel: {type(exc).__name__}: {exc}")
        overall = OverallStatus.PARTIAL

    try:
        await collect_normqueries(
            wb_data_manager,
            store=store,
            budget=budget,
            campaign_rows=campaign_rows,
            date_from=ads_from,
            date_to=ads_to,
        )
    except (ApiBudgetExhausted, ArtifactIntegrityError) as exc:
        integrity_errors.append(f"normqueries: {exc}")
        overall = OverallStatus.PARTIAL
    except Exception as exc:  # noqa: BLE001
        logger.exception("normqueries collect failed")
        integrity_errors.append(f"normqueries: {type(exc).__name__}: {exc}")
        overall = OverallStatus.PARTIAL

    try:
        store.finalize_integrity()
        integrity_pass = True
    except ArtifactIntegrityError as exc:
        integrity_pass = False
        integrity_errors.append(str(exc))
        overall = OverallStatus.FAILED

    report = CollectReport(
        shop_id=shop_id,
        overall_status=overall.value,
        coverage=list(store.coverage),
        integrity_pass=integrity_pass,
        integrity_errors=integrity_errors,
        api_budget={
            "max_seconds": budget.max_seconds,
            "max_api_calls": budget.max_api_calls,
            "api_calls_used": budget.api_calls_used,
            "exhausted": budget.exhausted,
        },
        missing_capabilities=list(MISSING_COLLECTOR_CAPABILITIES),
    )
    archive_path, digest = write_collect_archive(
        report, staging_dir=staging, output_dir=output_dir
    )
    report.archive_sha256 = digest
    logger.info(
        "full_collect done shop_id=%s overall=%s archive=%s sha256=%s",
        shop_id,
        report.overall_status,
        archive_path,
        digest,
    )
    return report


def _nmids_from_orders(
    orders_rows: list[dict[str, Any]], sales_rows: list[dict[str, Any]]
) -> list[int]:
    nmids: set[int] = set()
    for row in orders_rows + sales_rows:
        for key in ("nmId", "nm_id"):
            val = row.get(key)
            if val is not None:
                try:
                    nmids.add(int(val))
                except (TypeError, ValueError):
                    pass
    return sorted(nmids)


def _parse_date(text: str | None, default: datetime.date) -> datetime.date:
    if not text:
        return default
    return datetime.date.fromisoformat(text[:10])


def _resolve_ads_dates(
    *,
    orders_date_from: str,
    orders_rows: list[dict[str, Any]],
    ads_date_from: str | None,
    ads_date_to: str | None,
) -> tuple[datetime.date, datetime.date]:
    today = datetime.date.today()
    default_from = _parse_date(orders_date_from, datetime.date(2010, 1, 1))
    if orders_rows:
        dates = [
            str(r.get("date", ""))[:10]
            for r in orders_rows
            if r.get("date") and not str(r.get("date")).startswith("0001")
        ]
        if dates:
            default_from = min(datetime.date.fromisoformat(d) for d in dates)
    date_from = _parse_date(ads_date_from, default_from)
    date_to = _parse_date(ads_date_to, today)
    if date_to < date_from:
        date_to = date_from
    return date_from, date_to

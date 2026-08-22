"""Read-only dry-run entrypoint for rec_system bid recommendations.

Example:
    poetry run python run_rec_bid_recommendations_debug.py

Required env:
    REC_BID_DEBUG_NMID
    REC_BID_DEBUG_DATE_FROM
    REC_BID_DEBUG_DATE_TO

Optional env:
    REC_BID_DEBUG_MODE

Plan context env:
    REC_BID_DEBUG_SALES_PLAN
    REC_BID_DEBUG_CURRENT_FACT_SALES
    REC_BID_DEBUG_TARGET_ORDER_COST
    REC_BID_DEBUG_MAX_ORDER_COST
    REC_BID_DEBUG_CLICK_TO_ORDER_CR_7D
    REC_BID_DEBUG_ADV_ID
    REC_BID_DEBUG_CURRENT_SALES_FORECAST_OVERRIDE
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import dotenv

from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_analytics_repository import (
    AutoShelfBidControlAnalyticsRepository,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_recommendation_read_service import (
    AutoShelfBidRecommendationReadService,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from python_modules.logger import setup_logging

dotenv.load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)


def _required_env(name: str) -> str:
    """Возвращает обязательную переменную окружения или завершает скрипт."""
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env: {name}")
    return value


def _parse_datetime(value: str) -> datetime:
    """Парсит datetime в ISO-формате, поддерживает дату без времени."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(
            f"Invalid datetime in env: {value!r}. Expected ISO format."
        ) from exc
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


def _parse_float_env(name: str) -> float:
    """Парсит обязательный float из env."""
    return float(_required_env(name))


def _plan_context_from_env(current_sales_forecast: float) -> PlanContext:
    """???????? PlanContext ?? env ??? read-only dry-run."""
    return PlanContext(
        sales_plan=_parse_float_env("REC_BID_DEBUG_SALES_PLAN"),
        current_fact_sales=_parse_float_env("REC_BID_DEBUG_CURRENT_FACT_SALES"),
        current_sales_forecast=current_sales_forecast,
        target_order_cost=_parse_float_env("REC_BID_DEBUG_TARGET_ORDER_COST"),
        max_order_cost=_parse_float_env("REC_BID_DEBUG_MAX_ORDER_COST"),
        click_to_order_cr_7d=_parse_float_env("REC_BID_DEBUG_CLICK_TO_ORDER_CR_7D"),
    )


def _print_section(title: str) -> None:
    """Печатает визуальный разделитель."""
    print()
    print(title)
    print("-" * len(title))


def _print_table(rows: list[dict[str, Any]], columns: list[str]) -> None:
    """Печатает список словарей как простую таблицу без pandas."""
    if not rows:
        print("(empty)")
        return

    values: list[list[str]] = []
    widths = [len(column) for column in columns]
    for row in rows:
        rendered_row: list[str] = []
        for index, column in enumerate(columns):
            value = row.get(column, "")
            rendered = "" if value is None else str(value)
            rendered_row.append(rendered)
            widths[index] = max(widths[index], len(rendered))
        values.append(rendered_row)

    header = " | ".join(
        column.ljust(widths[index]) for index, column in enumerate(columns)
    )
    print(header)
    print("-+-".join("-" * width for width in widths))
    for rendered_row in values:
        print(
            " | ".join(
                rendered_row[index].ljust(widths[index])
                for index in range(len(columns))
            )
        )


async def _run() -> int:
    """Выполняет read-only dry-run и печатает полный ranking.

    Локальная БД — только через host/port из ``.env`` (spec local-dev-db-connectivity);
    in-app kubectl port-forward LEGACY удалён.
    """
    nmid = int(_required_env("REC_BID_DEBUG_NMID"))
    date_from = _parse_datetime(_required_env("REC_BID_DEBUG_DATE_FROM"))
    date_to = _parse_datetime(_required_env("REC_BID_DEBUG_DATE_TO"))
    mode_raw = os.getenv("REC_BID_DEBUG_MODE", "").strip()
    mode = mode_raw or None

    current_sales_forecast: float | None = None
    adv_id_raw = os.getenv("REC_BID_DEBUG_ADV_ID", "").strip()
    if adv_id_raw:
        plan_fact_reader = PlanFactReader()
        summary = await plan_fact_reader.get_latest_plan_fact(int(adv_id_raw))
        if summary is not None and summary.fact_predict_orders is not None:
            current_sales_forecast = float(summary.fact_predict_orders)

    if current_sales_forecast is None:
        override = os.getenv(
            "REC_BID_DEBUG_CURRENT_SALES_FORECAST_OVERRIDE", ""
        ).strip()
        if override:
            current_sales_forecast = float(override)

    if current_sales_forecast is None:
        raise SystemExit(
            "Missing current sales forecast. Set REC_BID_DEBUG_ADV_ID or REC_BID_DEBUG_CURRENT_SALES_FORECAST_OVERRIDE."
        )

    plan_context = _plan_context_from_env(current_sales_forecast)

    repository = AutoShelfBidControlAnalyticsRepository()
    service = AutoShelfBidRecommendationReadService(repository)
    ctr_by_bid = await repository.fetch_rec_bid_ctr_by_bid_for_nmid(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
    )
    _ = await repository.fetch_rec_bid_click_to_order_cr_7d_for_nmid(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
    )
    if not ctr_by_bid:
        print("No CTR data for selected nmid/mode/date range")
        return 0

    result = await service.get_rec_bid_recommendations(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
        plan_context=plan_context,
        ctr_by_bid=ctr_by_bid,
    )

    view = result["view"]
    diagnostics = view["diagnostics"]
    plan_ranked = view["plan_ranked"]
    expected_ranked = view["expected_ranked"]

    _print_section("diagnostics")
    _print_table(
        [
            {
                "bucket_count": diagnostics["bucket_count"],
                "hour_observation_count": diagnostics["hour_observation_count"],
                "bid_count": diagnostics["bid_count"],
                "hour_count": diagnostics["hour_count"],
            }
        ],
        [
            "bucket_count",
            "hour_observation_count",
            "bid_count",
            "hour_count",
        ],
    )

    print()
    print(f"best_expected_bid: {view['best_expected_bid']}")
    print(f"best_plan_bid: {view['best_plan_bid']}")

    if not expected_ranked or not plan_ranked:
        print()
        print("No valid hour observations for selected nmid/mode/date range")
        return 0

    _print_section("expected ranked top/all")
    _print_table(
        expected_ranked,
        [
            "bid",
            "expected_daily_impressions",
            "confidence",
            "uncertainty",
            "own_anchor",
            "main_score",
            "test_score",
        ],
    )

    _print_section("plan ranked top/all")
    _print_table(
        plan_ranked,
        [
            "bid",
            "ctr",
            "expected_impressions",
            "expected_clicks",
            "expected_orders",
            "expected_cost_rub",
            "expected_order_cost_rub",
            "resolved_order_cost_rub",
            "projected_sales",
            "sales_gap",
            "abs_sales_gap",
            "sales_dist",
            "order_cost_overlimit_rub",
            "order_cost_overlimit_dist",
            "plan_distance_score",
        ],
    )

    return 0


def main() -> None:
    """Root entrypoint for the read-only rec bid recommendation dry-run."""
    try:
        asyncio.run(_run())
    except ValueError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")


if __name__ == "__main__":
    main()

"""Свёртка дневных фактов и ключевых окон в строки витрин.

Сырые дни не копируются. Нога Auto и нога Search не складываются в одну строку.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import cast

from app.modules.ai_package_v1.analysis.catalog import window_day_count
from app.modules.ai_package_v1.analysis.constants import (
    ATTRIBUTION_BLOCKERS,
    CAMPAIGN_CPO_METRIC,
    CAMPAIGN_ORDERS_METRIC,
    FORBIDDEN_NUMERIC_METRICS,
    KEYWORD_CPO_METRIC,
    KEYWORD_ORDERS_METRIC,
    METRIC_DEFINITION_VERSION,
    SHOP_DRR_BLOCKERS,
    SHOP_SPEND_BLOCKERS,
    SKU_ECONOMICS_BLOCKERS,
)
from app.modules.ai_package_v1.analysis.coverage import (
    effective_range,
    resolve_coverage_status,
)
from app.modules.ai_package_v1.analysis.attribution_evidence import (
    build_leg_attribution_outputs,
    package_attribution_uncomputable,
)
from app.modules.ai_package_v1.analysis.models import CampaignDailyFact
from app.modules.attribution_facts.domain.models import AttributionQueryResult
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.enums import WindowSpendStatus
from app.modules.ai_package_v1.keyword_performance.domain.models import KeywordWindowRowV1
from app.modules.ai_package_v1.keyword_performance.windows.engine import WindowSpec


def legs_from_scope(
    scope: tuple[object, ...],
) -> list[tuple[int, str]]:
    """Физические ноги пакета: Auto и Search отдельно, без слияния id."""
    found: list[tuple[int, str]] = []
    seen: set[int] = set()
    for item in scope:
        auto_id = int(getattr(item, "auto_adv_id"))
        search_raw = getattr(item, "search_adv_id")
        search_id = int(search_raw) if search_raw is not None else None
        if auto_id not in seen:
            found.append((auto_id, "AUTO"))
            seen.add(auto_id)
        if search_id is not None and search_id not in seen:
            found.append((search_id, "SEARCH"))
            seen.add(search_id)
    return found


def fold_campaign_windows(
    *,
    shop_id: str,
    cutoff: PackageCutoff,
    windows: list[WindowSpec],
    legs: list[tuple[int, str]],
    facts: tuple[CampaignDailyFact, ...],
    source_complete_through: date | None,
    source_first: date | None,
    source_last: date | None,
    custom_forced_partial: bool,
    attribution_by_leg_window: dict[tuple[str, int], AttributionQueryResult] | None = None,
) -> list[dict[str, object]]:
    """Одна строка на физическую ногу и окно."""
    by_leg: dict[int, list[CampaignDailyFact]] = defaultdict(list)
    allowed = {adv_id for adv_id, _role in legs}
    for fact in facts:
        if fact.adv_id in allowed:
            by_leg[fact.adv_id].append(fact)
    rows: list[dict[str, object]] = []
    for index, spec in enumerate(windows):
        for adv_id, role in legs:
            rows.append(
                _campaign_row(
                    shop_id=shop_id,
                    cutoff=cutoff,
                    spec=spec,
                    catalog_index=index,
                    adv_id=adv_id,
                    leg_role=role,
                    facts=by_leg.get(adv_id, []),
                    source_complete_through=source_complete_through,
                    source_first=source_first,
                    source_last=source_last,
                    custom_forced_partial=custom_forced_partial,
                    attribution_query=(
                        (attribution_by_leg_window or {}).get((spec.window_id, adv_id))
                    ),
                )
            )
    return rows


def fold_package_scope(
    campaign_rows: list[dict[str, object]],
    *,
    shop_id: str,
    cutoff: PackageCutoff,
    windows: list[WindowSpec],
    source_complete_through: date | None,
    source_first: date | None,
    source_last: date | None,
) -> list[dict[str, object]]:
    """Сумма ног, которые реально вошли в пакет. Это не расход всего магазина."""
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in campaign_rows:
        grouped[str(row["window_id"])].append(row)
    rows: list[dict[str, object]] = []
    for index, spec in enumerate(windows):
        members = grouped.get(spec.window_id, [])
        rows.append(
            _package_row(
                shop_id=shop_id,
                cutoff=cutoff,
                spec=spec,
                catalog_index=index,
                members=members,
                source_complete_through=source_complete_through,
                source_first=source_first,
                source_last=source_last,
            )
        )
    return rows


def fold_keyword_products(
    keyword_windows: tuple[KeywordWindowRowV1, ...],
    *,
    shop_id: str,
    cutoff: PackageCutoff,
    source_complete_through: date | None,
    source_first: date | None,
    source_last: date | None,
) -> list[dict[str, object]]:
    """Артикул × нога × уже посчитанное ключевое окно.

    Нового скана ключевого зерна нет: свёртка только готовых строк.
    """
    grouped: dict[tuple[int, str, int, str], list[KeywordWindowRowV1]] = defaultdict(list)
    for row in keyword_windows:
        key = (row.adv_id, str(row.leg_role), row.nmid, row.window_id)
        grouped[key].append(row)
    product_rows: list[dict[str, object]] = []
    for key in sorted(grouped):
        members = grouped[key]
        product_rows.append(
            _keyword_product_row(
                shop_id=shop_id,
                cutoff=cutoff,
                members=members,
                source_complete_through=source_complete_through,
                source_first=source_first,
                source_last=source_last,
            )
        )
    return product_rows


def _campaign_row(
    *,
    shop_id: str,
    cutoff: PackageCutoff,
    spec: WindowSpec,
    catalog_index: int,
    adv_id: int,
    leg_role: str,
    facts: list[CampaignDailyFact],
    source_complete_through: date | None,
    source_first: date | None,
    source_last: date | None,
    custom_forced_partial: bool,
    attribution_query: AttributionQueryResult | None = None,
) -> dict[str, object]:
    observed = {fact.stat_date for fact in facts}
    in_window = [fact for fact in facts if spec.start <= fact.stat_date <= spec.end]
    force = spec.window_id == "requested_custom" and custom_forced_partial
    status = resolve_coverage_status(
        nominal_start=spec.start,
        nominal_end=spec.end,
        observed_dates=observed,
        source_complete_through=source_complete_through,
        force_partial=force,
    )
    covered_start, covered_end = effective_range(
        nominal_start=spec.start,
        nominal_end=spec.end,
        observed_dates=observed,
        source_complete_through=source_complete_through,
    )
    metrics, uncomputable = _campaign_metrics(in_window, status)
    uncomputable.extend(_reserved_shop_uncomputable())
    if attribution_query is not None:
        attr_metrics, attr_gaps = build_leg_attribution_outputs(
            attribution_query,
            physical_adv_id=adv_id,
            window_start=spec.start,
            window_end=spec.end,
            campaign_facts_in_window=in_window,
            campaign_coverage_status=status,
        )
        metrics.update(attr_metrics)
        uncomputable.extend(attr_gaps)
    else:
        uncomputable.extend(_attribution_blocked_uncomputable())
    return _base_row(
        shop_id=shop_id,
        cutoff=cutoff,
        spec=spec,
        catalog_index=catalog_index,
        entity_kind="CAMPAIGN_LEG",
        scope="CAMPAIGN_WB_STAT",
        adv_id=adv_id,
        leg_role=leg_role,
        nmid=None,
        coverage_status=status,
        observed_days=len({fact.stat_date for fact in in_window}),
        source_complete_through=source_complete_through,
        source_first=source_first,
        source_last=source_last,
        covered_start=covered_start,
        covered_end=covered_end,
        metrics=metrics,
        uncomputable=uncomputable,
        included_adv_ids=[adv_id],
    )


def _package_row(
    *,
    shop_id: str,
    cutoff: PackageCutoff,
    spec: WindowSpec,
    catalog_index: int,
    members: list[dict[str, object]],
    source_complete_through: date | None,
    source_first: date | None,
    source_last: date | None,
) -> dict[str, object]:
    statuses = [str(row["coverage_status"]) for row in members]
    if not members or all(item == "NO_DATA" for item in statuses):
        status = "NO_DATA"
    elif all(item == "COMPLETE" for item in statuses):
        status = "COMPLETE"
    else:
        status = "PARTIAL"
    metrics, metric_gaps = _sum_member_metrics(members)
    observed = 0
    if members:
        observed_values = [
            value
            for row in members
            if isinstance((value := row.get("observed_days")), int)
        ]
        if observed_values:
            observed = min(observed_values)
    covered_dates: list[date] = []
    for row in members:
        start = _parse_optional_date(_range_field(row, "effective_covered_range", "start"))
        end = _parse_optional_date(_range_field(row, "effective_covered_range", "end"))
        if start is not None:
            covered_dates.append(start)
        if end is not None:
            covered_dates.append(end)
    covered_start = min(covered_dates) if covered_dates else None
    covered_end = max(covered_dates) if covered_dates else None
    included: list[int] = []
    for row in members:
        adv_raw = row.get("adv_id")
        if isinstance(adv_raw, int) and not isinstance(adv_raw, bool):
            included.append(adv_raw)
    uncomputable = list(metric_gaps)
    uncomputable.extend(_reserved_shop_uncomputable())
    uncomputable.extend(package_attribution_uncomputable(len(included)))
    return _base_row(
        shop_id=shop_id,
        cutoff=cutoff,
        spec=spec,
        catalog_index=catalog_index,
        entity_kind="PACKAGE_CAMPAIGN_SCOPE",
        scope="PACKAGE_CAMPAIGN_SCOPE",
        adv_id=None,
        leg_role=None,
        nmid=None,
        coverage_status=status,
        observed_days=observed,
        source_complete_through=source_complete_through,
        source_first=source_first,
        source_last=source_last,
        covered_start=covered_start,
        covered_end=covered_end,
        metrics=metrics,
        uncomputable=uncomputable,
        included_adv_ids=included,
    )


def _keyword_product_row(
    *,
    shop_id: str,
    cutoff: PackageCutoff,
    members: list[KeywordWindowRowV1],
    source_complete_through: date | None,
    source_first: date | None,
    source_last: date | None,
) -> dict[str, object]:
    sample = members[0]
    start = date.fromisoformat(sample.window_start)
    end = date.fromisoformat(sample.window_end)
    observed_days = sum(row.observed_days for row in members)
    requested = max(row.requested_days for row in members)
    any_partial = any(row.partial for row in members) or observed_days < requested
    observed_proxy: set[date] = {start} if observed_days > 0 else set()
    if any_partial and observed_days > 0:
        status = resolve_coverage_status(
            nominal_start=start,
            nominal_end=end,
            observed_dates=observed_proxy,
            source_complete_through=source_complete_through,
            force_partial=True,
        )
    else:
        status = resolve_coverage_status(
            nominal_start=start,
            nominal_end=end,
            observed_dates=observed_proxy if observed_days else set(),
            source_complete_through=source_complete_through,
            force_partial=False,
        )
        if observed_days and observed_days < requested:
            status = "PARTIAL" if status != "NO_DATA" else status
    metrics, gaps = _keyword_metrics(members)
    spec = WindowSpec(sample.window_id, start, end, requested_days=requested)
    return _base_row(
        shop_id=shop_id,
        cutoff=cutoff,
        spec=spec,
        catalog_index=_keyword_sort_index(sample.window_id),
        entity_kind="KEYWORD_PRODUCT",
        scope="KEYWORD_PERFORMANCE_PRODUCT_SCOPE",
        adv_id=sample.adv_id,
        leg_role=str(sample.leg_role),
        nmid=sample.nmid,
        coverage_status=status if observed_days else "NO_DATA",
        observed_days=observed_days,
        source_complete_through=source_complete_through,
        source_first=source_first,
        source_last=source_last,
        covered_start=start if observed_days else None,
        covered_end=end if observed_days else None,
        metrics=metrics,
        uncomputable=[*gaps, *_reserved_keyword_uncomputable()],
        included_adv_ids=[sample.adv_id],
    )


def _campaign_metrics(
    facts: list[CampaignDailyFact],
    coverage_status: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not facts or coverage_status == "NO_DATA":
        return {}, [{"metric_id": "CAMPAIGN_WB_STAT", "reason_codes": ["NO_DATA"]}]
    views = _sum_optional([fact.views for fact in facts])
    clicks = _sum_optional([fact.clicks for fact in facts])
    spend = _sum_optional_float([fact.spend_rub for fact in facts])
    carts = _sum_optional([fact.added_to_cart for fact in facts])
    orders = _sum_optional([fact.orders for fact in facts])
    order_sum = _sum_optional_float([fact.order_sum_rub for fact in facts])
    metrics: dict[str, object] = {}
    gaps: list[dict[str, object]] = []
    _put_metric(metrics, gaps, "CAMPAIGN_WB_STAT_VIEWS", views, "METRIC_ABSENT")
    _put_metric(metrics, gaps, "CAMPAIGN_WB_STAT_CLICKS", clicks, "METRIC_ABSENT")
    _put_metric(metrics, gaps, "CAMPAIGN_WB_STAT_SPEND_RUB", spend, "METRIC_ABSENT")
    _put_metric(metrics, gaps, "CAMPAIGN_WB_STAT_ADD_TO_CART", carts, "METRIC_ABSENT")
    _put_metric(metrics, gaps, CAMPAIGN_ORDERS_METRIC, orders, "METRIC_ABSENT")
    _put_metric(metrics, gaps, "CAMPAIGN_WB_STAT_ORDER_SUM", order_sum, "METRIC_ABSENT")
    _put_ratio(metrics, gaps, "CAMPAIGN_WB_STAT_CTR", clicks, views)
    _put_ratio(metrics, gaps, "CAMPAIGN_WB_STAT_CPC", spend, clicks)
    _put_ratio(metrics, gaps, CAMPAIGN_CPO_METRIC, spend, orders)
    return metrics, gaps


def _keyword_metrics(
    members: list[KeywordWindowRowV1],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    metrics: dict[str, object] = {}
    gaps: list[dict[str, object]] = []
    views = _sum_optional([row.views_sum for row in members])
    clicks = _sum_optional([row.clicks_sum for row in members])
    orders = _sum_optional([row.orders_sum for row in members])
    factual = all(row.spend_status == WindowSpendStatus.FACTUAL for row in members)
    spend = (
        _sum_optional_float([row.spend_rub_sum for row in members]) if factual else None
    )
    _put_metric(metrics, gaps, "KEYWORD_VIEWS", views, "METRIC_ABSENT")
    _put_metric(metrics, gaps, "KEYWORD_CLICKS", clicks, "METRIC_ABSENT")
    _put_metric(metrics, gaps, KEYWORD_ORDERS_METRIC, orders, "METRIC_ABSENT")
    if factual:
        _put_metric(metrics, gaps, "KEYWORD_SPEND_RUB", spend, "METRIC_ABSENT")
    else:
        gaps.append({"metric_id": "KEYWORD_SPEND_RUB", "reason_codes": ["SPEND_NOT_FACTUAL"]})
    _put_ratio(metrics, gaps, "KEYWORD_CTR", clicks, views)
    _put_ratio(metrics, gaps, KEYWORD_CPO_METRIC, spend if factual else None, orders)
    return metrics, gaps


def _sum_member_metrics(
    members: list[dict[str, object]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    metric_ids = (
        "CAMPAIGN_WB_STAT_VIEWS",
        "CAMPAIGN_WB_STAT_CLICKS",
        "CAMPAIGN_WB_STAT_SPEND_RUB",
        "CAMPAIGN_WB_STAT_ADD_TO_CART",
        CAMPAIGN_ORDERS_METRIC,
        "CAMPAIGN_WB_STAT_ORDER_SUM",
    )
    metrics: dict[str, object] = {}
    gaps: list[dict[str, object]] = []
    if not members:
        return metrics, [{"metric_id": "PACKAGE_CAMPAIGN_SCOPE", "reason_codes": ["NO_DATA"]}]
    for metric_id in metric_ids:
        values: list[int | float | None] = []
        for row in members:
            cell = _metric_cell(row, metric_id)
            values.append(None if cell is None else cell)
        if any(value is None for value in values):
            gaps.append({"metric_id": metric_id, "reason_codes": ["MISSING_INCLUDED_LEG"]})
            continue
        numeric = [value for value in values if value is not None]
        total: int | float = (
            sum(int(value) for value in numeric)
            if all(isinstance(value, int) for value in numeric)
            else float(sum(float(value) for value in numeric))
        )
        _put_metric(metrics, gaps, metric_id, total, "MISSING_INCLUDED_LEG")
    views = _metric_value(metrics, "CAMPAIGN_WB_STAT_VIEWS")
    clicks = _metric_value(metrics, "CAMPAIGN_WB_STAT_CLICKS")
    spend = _metric_value(metrics, "CAMPAIGN_WB_STAT_SPEND_RUB")
    orders = _metric_value(metrics, CAMPAIGN_ORDERS_METRIC)
    _put_ratio(metrics, gaps, "CAMPAIGN_WB_STAT_CTR", clicks, views)
    _put_ratio(metrics, gaps, "CAMPAIGN_WB_STAT_CPC", spend, clicks)
    _put_ratio(metrics, gaps, CAMPAIGN_CPO_METRIC, spend, orders)
    return metrics, gaps


def _attribution_blocked_uncomputable() -> list[dict[str, object]]:
    from app.modules.ai_package_v1.analysis.attribution_evidence import (
        ATTRIBUTION_DIRECT_GMV_RUB,
        ATTRIBUTION_DIRECT_ORDERS,
        ATTRIBUTION_LINKED_GMV_RUB,
        ATTRIBUTION_LINKED_ORDERS,
    )

    metric_ids = (
        ATTRIBUTION_DIRECT_ORDERS,
        ATTRIBUTION_DIRECT_GMV_RUB,
        ATTRIBUTION_LINKED_ORDERS,
        ATTRIBUTION_LINKED_GMV_RUB,
        "CPO_FACT_DIRECT",
        "DRR_FACT_DIRECT",
        "CPO_FACT_LINKED",
        "DRR_FACT_LINKED",
    )
    return [
        {"metric_id": metric_id, "reason_codes": list(ATTRIBUTION_BLOCKERS)}
        for metric_id in metric_ids
    ]


def _reserved_shop_uncomputable() -> list[dict[str, object]]:
    blocked: list[dict[str, object]] = []
    blocked.append({"metric_id": "SHOP_DRR", "reason_codes": list(SHOP_DRR_BLOCKERS)})
    blocked.append(
        {"metric_id": "ALL_SHOP_AD_SPEND", "reason_codes": list(SHOP_SPEND_BLOCKERS)}
    )
    blocked.append({"metric_id": "SHOP_AD_SPEND", "reason_codes": list(SHOP_SPEND_BLOCKERS)})
    return blocked


def _reserved_keyword_uncomputable() -> list[dict[str, object]]:
    blocked: list[dict[str, object]] = [
        {"metric_id": metric_id, "reason_codes": list(SKU_ECONOMICS_BLOCKERS)}
        for metric_id in ("SKU_GMV", "SKU_DRR", "SKU_ORDERS")
    ]
    blocked.extend(_reserved_shop_uncomputable())
    blocked.extend(_attribution_blocked_uncomputable())
    return blocked


def _base_row(
    *,
    shop_id: str,
    cutoff: PackageCutoff,
    spec: WindowSpec,
    catalog_index: int,
    entity_kind: str,
    scope: str,
    adv_id: int | None,
    leg_role: str | None,
    nmid: int | None,
    coverage_status: str,
    observed_days: int,
    source_complete_through: date | None,
    source_first: date | None,
    source_last: date | None,
    covered_start: date | None,
    covered_end: date | None,
    metrics: dict[str, object],
    uncomputable: list[dict[str, object]],
    included_adv_ids: list[int],
) -> dict[str, object]:
    requested = spec.requested_days or window_day_count(spec.start, spec.end)
    _assert_no_forbidden_numbers(metrics)
    return {
        "entity_kind": entity_kind,
        "scope": scope,
        "shop_id": shop_id,
        "adv_id": adv_id,
        "leg_role": leg_role,
        "nmid": nmid,
        "included_adv_ids": included_adv_ids,
        "window_id": spec.window_id,
        "catalog_index": catalog_index,
        "window_start": spec.start.isoformat(),
        "window_end": spec.end.isoformat(),
        "nominal_window_end": spec.end.isoformat(),
        "package_cutoff_date": cutoff.last_closed_calendar_day.isoformat(),
        "generation_utc_date": cutoff.package_cutoff_date.isoformat(),
        "source_available_range": {
            "start": source_first.isoformat() if source_first else None,
            "end": source_last.isoformat() if source_last else None,
        },
        "source_complete_through": (
            source_complete_through.isoformat() if source_complete_through else None
        ),
        "effective_covered_range": {
            "start": covered_start.isoformat() if covered_start else None,
            "end": covered_end.isoformat() if covered_end else None,
        },
        "coverage_status": coverage_status,
        "observed_days": observed_days,
        "requested_days": requested,
        "missing_days": max(requested - observed_days, 0),
        "metrics": metrics,
        "uncomputable": uncomputable,
        "reason_codes": _coverage_reasons(coverage_status, source_complete_through),
        "metric_definition_version": METRIC_DEFINITION_VERSION,
    }


def _coverage_reasons(status: str, source_complete_through: date | None) -> list[str]:
    reasons: list[str] = []
    if source_complete_through is None:
        reasons.append("SOURCE_COMPLETENESS_NOT_PROVEN")
    if status == "NO_DATA":
        reasons.append("NO_DATA")
    elif status == "PARTIAL":
        reasons.append("PARTIAL_COVERAGE")
    elif status == "GAP":
        reasons.append("GAP")
    return reasons


def _put_metric(
    metrics: dict[str, object],
    gaps: list[dict[str, object]],
    metric_id: str,
    value: int | float | None,
    absent_reason: str,
) -> None:
    if metric_id in FORBIDDEN_NUMERIC_METRICS:
        gaps.append({"metric_id": metric_id, "reason_codes": ["FORBIDDEN_NUMERIC"]})
        return
    if value is None:
        gaps.append({"metric_id": metric_id, "reason_codes": [absent_reason]})
        return
    metrics[metric_id] = {
        "value": value,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "scope_note": "value is not shop GMV and not direct or linked attribution",
    }


def _put_ratio(
    metrics: dict[str, object],
    gaps: list[dict[str, object]],
    metric_id: str,
    numerator: int | float | None,
    denominator: int | float | None,
) -> None:
    if numerator is None or denominator is None:
        gaps.append({"metric_id": metric_id, "reason_codes": ["MISSING_SOURCE"]})
        return
    if denominator == 0:
        gaps.append({"metric_id": metric_id, "reason_codes": ["ZERO_DENOMINATOR"]})
        return
    _put_metric(metrics, gaps, metric_id, float(numerator) / float(denominator), "MISSING_SOURCE")


def _sum_optional(values: list[int | None]) -> int | None:
    if not values or any(value is None for value in values):
        return None
    return sum(int(value) for value in values if value is not None)


def _sum_optional_float(values: list[float | None]) -> float | None:
    if not values or any(value is None for value in values):
        return None
    return float(sum(float(value) for value in values if value is not None))


def _metric_cell(row: dict[str, object], metric_id: str) -> int | float | None:
    metrics = _object_mapping(row.get("metrics"))
    if metrics is None or metric_id not in metrics:
        return None
    cell = _object_mapping(metrics.get(metric_id))
    if cell is None or "value" not in cell:
        return None
    return _number(cell.get("value"))


def _metric_value(metrics: dict[str, object], metric_id: str) -> int | float | None:
    cell = _object_mapping(metrics.get(metric_id))
    if cell is None:
        return None
    return _number(cell.get("value"))


def _object_mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)


def _number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _assert_no_forbidden_numbers(metrics: dict[str, object]) -> None:
    overlap = FORBIDDEN_NUMERIC_METRICS.intersection(metrics)
    if overlap:
        raise ValueError(f"forbidden numeric metrics: {sorted(overlap)}")


def _range_field(row: dict[str, object], field: str, side: str) -> object:
    block = _object_mapping(row.get(field))
    if block is None:
        return None
    return block.get(side)


def _parse_optional_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    return date.fromisoformat(value)


def _keyword_sort_index(window_id: str) -> int:
    order = (
        "1d",
        "prev_1d",
        "3d",
        "prev_3d",
        "7d",
        "prev_7d",
        "14d",
        "prev_14d",
        "30d",
        "prev_30d",
        "90d",
        "prev_90d",
        "180d",
        "prev_180d",
        "365d",
        "prev_365d",
    )
    if window_id in order:
        return order.index(window_id)
    return 1000

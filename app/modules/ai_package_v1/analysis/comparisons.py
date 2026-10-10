"""Статус сопоставимости пар окон.

Два числа без статуса не являются сравнением. Вложенные горизонты не
объявляются независимыми выборками.
"""

from __future__ import annotations

from typing import cast

from app.modules.ai_package_v1.analysis.constants import (
    CAMPAIGN_CPO_METRIC,
    CAMPAIGN_ORDERS_METRIC,
    KEYWORD_CPO_METRIC,
    KEYWORD_ORDERS_METRIC,
    METRIC_DEFINITION_VERSION,
    MINIMUM_SAMPLE_ORDERS,
)

COMPARISON_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("1d", "3d", "NESTED"),
    ("3d", "7d", "NESTED"),
    ("7d", "30d", "NESTED"),
    ("30d", "90d", "NESTED"),
    ("90d", "365d", "NESTED"),
    ("year_to_date", "prev_year_to_date", "CALENDAR_PRIOR_SEGMENT"),
    ("3d", "prev_3d", "PREVIOUS_NON_OVERLAPPING"),
    ("7d", "prev_7d", "PREVIOUS_NON_OVERLAPPING"),
    ("14d", "prev_14d", "PREVIOUS_NON_OVERLAPPING"),
    ("30d", "prev_30d", "PREVIOUS_NON_OVERLAPPING"),
    ("90d", "prev_90d", "PREVIOUS_NON_OVERLAPPING"),
    ("180d", "prev_180d", "PREVIOUS_NON_OVERLAPPING"),
    ("365d", "prev_365d", "PREVIOUS_NON_OVERLAPPING"),
)


def build_comparisons(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Пары для каждой сущности витрины. Порядок стабильный."""
    grouped: dict[tuple[str, str, str, str], dict[str, dict[str, object]]] = {}
    for row in rows:
        key = _entity_key(row)
        grouped.setdefault(key, {})[str(row["window_id"])] = row
    comparisons: list[dict[str, object]] = []
    for key in sorted(grouped):
        windows = grouped[key]
        sample = next(iter(windows.values()))
        orders_metric, cpo_metric = _metric_ids(str(sample["entity_kind"]))
        for pair_index, (left_id, right_id, relationship) in enumerate(COMPARISON_PAIRS):
            comparisons.append(
                judge_comparison(
                    left=windows.get(left_id),
                    right=windows.get(right_id),
                    left_window_id=left_id,
                    right_window_id=right_id,
                    relationship=relationship,
                    pair_index=pair_index,
                    entity_key=key,
                    orders_metric=orders_metric,
                    cpo_metric=cpo_metric,
                )
            )
    return comparisons


def judge_comparison(
    *,
    left: dict[str, object] | None,
    right: dict[str, object] | None,
    left_window_id: str,
    right_window_id: str,
    relationship: str,
    pair_index: int,
    entity_key: tuple[str, str, str, str],
    orders_metric: str,
    cpo_metric: str,
) -> dict[str, object]:
    """Один статус пары. Отказ закрыт, если полнота, область или знаменатель не сходятся."""
    status = "COMPARABLE"
    reasons: list[str] = []
    if left is None or right is None:
        status = "NOT_COMPARABLE"
        reasons.append("ENTITY_ABSENT")
    else:
        status, reasons = _judge_present(
            left, right, orders_metric=orders_metric, cpo_metric=cpo_metric
        )
    return {
        "entity_kind": entity_key[0],
        "scope": entity_key[1],
        "adv_id": None if entity_key[2] == "" else int(entity_key[2]),
        "nmid": None if entity_key[3] == "" else int(entity_key[3]),
        "left_window_id": left_window_id,
        "right_window_id": right_window_id,
        "relationship": relationship,
        "sample_relationship": relationship,
        "nested": relationship == "NESTED",
        "independent_sample": False,
        "metric_id": cpo_metric,
        "orders_metric_id": orders_metric,
        "status": status,
        "reason_codes": reasons,
        "pair_index": pair_index,
        "left_orders": None if left is None else _metric_value(left, orders_metric),
        "right_orders": None if right is None else _metric_value(right, orders_metric),
        "metric_definition_version": METRIC_DEFINITION_VERSION,
    }


def _judge_present(
    left: dict[str, object],
    right: dict[str, object],
    *,
    orders_metric: str,
    cpo_metric: str,
) -> tuple[str, list[str]]:
    if str(left.get("scope")) != str(right.get("scope")):
        return "NOT_COMPARABLE", ["INCOMPATIBLE_SCOPE"]
    if _version(left, orders_metric) != _version(right, orders_metric):
        return "NOT_COMPARABLE", ["INCOMPATIBLE_METRIC_VERSION"]
    if _version(left, cpo_metric) != _version(right, cpo_metric) and (
        _has_metric(left, cpo_metric) or _has_metric(right, cpo_metric)
    ):
        return "NOT_COMPARABLE", ["INCOMPATIBLE_METRIC_VERSION"]
    left_orders = _metric_value(left, orders_metric)
    right_orders = _metric_value(right, orders_metric)
    if left_orders == 0 or right_orders == 0:
        return "NOT_COMPARABLE", ["ZERO_DENOMINATOR"]
    if _blocked(left) or _blocked(right):
        return "NOT_COMPARABLE", ["SOURCE_COMPLETENESS_NOT_PROVEN"]
    if left_orders is None or right_orders is None:
        return "NOT_COMPARABLE", ["MISSING_SOURCE"]
    left_status = str(left.get("coverage_status"))
    right_status = str(right.get("coverage_status"))
    if "GAP" in (left_status, right_status):
        return "NOT_COMPARABLE", ["MISSING_SOURCE"]
    if left_status != "COMPLETE" or right_status != "COMPLETE":
        return "PARTIAL", ["PARTIAL_COVERAGE"]
    if left_orders < MINIMUM_SAMPLE_ORDERS or right_orders < MINIMUM_SAMPLE_ORDERS:
        return "PARTIAL", ["INSUFFICIENT_SAMPLE"]
    return "COMPARABLE", []


def _blocked(row: dict[str, object]) -> bool:
    reasons = row.get("reason_codes")
    if not isinstance(reasons, list):
        return True
    return "SOURCE_COMPLETENESS_NOT_PROVEN" in reasons


def _entity_key(row: dict[str, object]) -> tuple[str, str, str, str]:
    adv = row.get("adv_id")
    nmid = row.get("nmid")
    return (
        str(row.get("entity_kind")),
        str(row.get("scope")),
        "" if adv is None else str(adv),
        "" if nmid is None else str(nmid),
    )


def _metric_ids(entity_kind: str) -> tuple[str, str]:
    if entity_kind == "KEYWORD_PRODUCT":
        return KEYWORD_ORDERS_METRIC, KEYWORD_CPO_METRIC
    return CAMPAIGN_ORDERS_METRIC, CAMPAIGN_CPO_METRIC


def _metric_value(row: dict[str, object], metric_id: str) -> int | None:
    metrics = _mapping(row.get("metrics"))
    if metrics is None:
        return None
    cell = _mapping(metrics.get(metric_id))
    if cell is None:
        return None
    value = cell.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _has_metric(row: dict[str, object], metric_id: str) -> bool:
    metrics = _mapping(row.get("metrics"))
    return metrics is not None and metric_id in metrics


def _version(row: dict[str, object], metric_id: str) -> str:
    metrics = _mapping(row.get("metrics"))
    if metrics is None:
        return str(row.get("metric_definition_version"))
    cell = _mapping(metrics.get(metric_id))
    if cell is None:
        return str(row.get("metric_definition_version"))
    version = cell.get("metric_definition_version")
    if not isinstance(version, str):
        return str(row.get("metric_definition_version"))
    return version


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)

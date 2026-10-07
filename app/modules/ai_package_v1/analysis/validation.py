"""Проверка аналитического слоя пакета. Форму не считает: отвергает ложную семантику."""

from __future__ import annotations

import json
from typing import Any, cast

from app.modules.ai_package_v1.analysis.constants import (
    AI_GUIDE_LOGICAL,
    ANALYSIS_CONTRACT_LOGICAL,
    CAMPAIGNS_LOGICAL,
    COMPARISONS_LOGICAL,
    CUTOFF_NOT_COMPLETENESS,
    FORBIDDEN_NUMERIC_METRICS,
    KEYWORD_PRODUCT_SCOPE_LOGICAL,
    PACKAGE_CAMPAIGN_SCOPE_LOGICAL,
)
from app.modules.ai_package_v1.domain.manifest import PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS

FORBIDDEN_LOGICAL_NAMES = frozenset(
    {
        "analysis/windows/shop.jsonl",
        "analysis/windows/products.jsonl",
        "analysis/windows/keywords.jsonl",
    }
)
REQUIRED_LOGICAL_NAMES = (
    ANALYSIS_CONTRACT_LOGICAL,
    AI_GUIDE_LOGICAL,
    PACKAGE_CAMPAIGN_SCOPE_LOGICAL,
    CAMPAIGNS_LOGICAL,
    KEYWORD_PRODUCT_SCOPE_LOGICAL,
    COMPARISONS_LOGICAL,
)


class AnalysisValidationError(Exception):
    """Пакет нарушает семантику аналитического слоя."""


def validate_analysis_files(files: dict[str, bytes], *, schema_version: str) -> None:
    """Проверяет слой, если схема пакета заявляет анализ."""
    present = FORBIDDEN_LOGICAL_NAMES.intersection(files)
    if present:
        raise AnalysisValidationError(f"forbidden analysis names: {sorted(present)}")
    has_contract = ANALYSIS_CONTRACT_LOGICAL in files
    if schema_version != PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS:
        if has_contract:
            raise AnalysisValidationError("analysis layer requires package schema 1.1.0")
        return
    for name in REQUIRED_LOGICAL_NAMES:
        if name not in files:
            raise AnalysisValidationError(f"missing analysis payload: {name}")
    guide = files[AI_GUIDE_LOGICAL].decode("utf-8")
    if CUTOFF_NOT_COMPLETENESS not in guide:
        raise AnalysisValidationError("guide missing cutoff completeness statement")
    contract = _json_object(files[ANALYSIS_CONTRACT_LOGICAL], ANALYSIS_CONTRACT_LOGICAL)
    _reject_latest_complete_date(contract, ANALYSIS_CONTRACT_LOGICAL)
    if contract.get("package_schema_version") != PACKAGE_SCHEMA_VERSION_WITH_ANALYSIS:
        raise AnalysisValidationError("analysis contract schema must be 1.1.0")
    for logical_name in (
        PACKAGE_CAMPAIGN_SCOPE_LOGICAL,
        CAMPAIGNS_LOGICAL,
        KEYWORD_PRODUCT_SCOPE_LOGICAL,
        COMPARISONS_LOGICAL,
    ):
        for row in _jsonl(files[logical_name], logical_name):
            _validate_row(row, logical_name)


def _validate_row(row: dict[str, Any], logical_name: str) -> None:
    _reject_latest_complete_date(row, logical_name)
    if logical_name == COMPARISONS_LOGICAL:
        if row.get("status") not in {"COMPARABLE", "PARTIAL", "NOT_COMPARABLE"}:
            raise AnalysisValidationError("comparison missing status")
        return
    metrics = row.get("metrics")
    if not isinstance(metrics, dict):
        raise AnalysisValidationError(f"{logical_name} metrics must be an object")
    metric_map = cast(dict[str, Any], metrics)
    overlap = FORBIDDEN_NUMERIC_METRICS.intersection(metric_map)
    if overlap:
        raise AnalysisValidationError(f"numeric forbidden metric in {logical_name}: {overlap}")
    if (
        row.get("coverage_status") == "COMPLETE"
        and not row.get("source_complete_through")
    ):
        raise AnalysisValidationError(
            "COMPLETE coverage without source_complete_through"
        )
    cutoff = row.get("package_cutoff_date")
    complete_through = row.get("source_complete_through")
    window_end = row.get("nominal_window_end")
    if (
        row.get("coverage_status") == "COMPLETE"
        and isinstance(complete_through, str)
        and isinstance(window_end, str)
        and window_end > complete_through
    ):
        raise AnalysisValidationError("COMPLETE past source_complete_through")
    if row.get("window_id") == "1d" and isinstance(cutoff, str):
        generation = row.get("generation_utc_date")
        if row.get("window_end") != cutoff:
            raise AnalysisValidationError("1d window_end must be package_cutoff_date")
        if isinstance(generation, str) and str(row.get("window_start")) >= generation:
            raise AnalysisValidationError("1d includes package generation date")
    if logical_name == KEYWORD_PRODUCT_SCOPE_LOGICAL:
        if row.get("scope") != "KEYWORD_PERFORMANCE_PRODUCT_SCOPE":
            raise AnalysisValidationError("keyword product row missing scope")
    if logical_name == PACKAGE_CAMPAIGN_SCOPE_LOGICAL:
        if row.get("scope") != "PACKAGE_CAMPAIGN_SCOPE":
            raise AnalysisValidationError("package scope row missing scope")


def _reject_latest_complete_date(payload: dict[str, Any], logical_name: str) -> None:
    if "latest_complete_date" in payload:
        raise AnalysisValidationError(f"{logical_name} contains latest_complete_date")


def _json_object(content: bytes, logical_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AnalysisValidationError(f"{logical_name} is not JSON") from exc
    if not isinstance(parsed, dict):
        raise AnalysisValidationError(f"{logical_name} must be an object")
    return cast(dict[str, Any], parsed)


def _jsonl(content: bytes, logical_name: str) -> list[dict[str, Any]]:
    if not content:
        return []
    rows: list[dict[str, Any]] = []
    for line in content.decode("utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AnalysisValidationError(f"{logical_name} row is not JSON") from exc
        if not isinstance(parsed, dict):
            raise AnalysisValidationError(f"{logical_name} row must be an object")
        rows.append(cast(dict[str, Any], parsed))
    return rows

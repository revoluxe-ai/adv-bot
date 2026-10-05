"""Валидация входов export (fail-closed до CH/PG)."""

from __future__ import annotations

from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.shop_id import manifest_shop_id


def validate_export_period(period: ExportPeriod) -> None:
    """
    Проверяет календарный период export.

    Args:
        period: Инclusive start/end.

    Raises:
        ValueError: если ``end < start``.
    """
    if period.end < period.start:
        raise ValueError(
            f"export period end before start: {period.start} > {period.end}"
        )


def validate_export_shop_id(shop_id: str) -> int:
    """
    Проверяет PG ``shop_id`` и возвращает manifest int.

    Args:
        shop_id: ``WBCabinet.shop_id``.

    Returns:
        Целочисленный shop id для manifest/CH.

    Raises:
        ValueError: если shop_id не numeric (fail-closed v1).
    """
    return manifest_shop_id(shop_id)


def validate_export_inputs(shop_id: str, period: ExportPeriod) -> int:
    """
    Единая точка валидации ``export(shop_id, period)``.

    Returns:
        Manifest shop id после успешной проверки.
    """
    manifest_id = validate_export_shop_id(shop_id)
    validate_export_period(period)
    return manifest_id

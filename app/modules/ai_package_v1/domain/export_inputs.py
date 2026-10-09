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


def validate_export_shop_id(shop_id: str) -> str:
    """
    Проверяет PG ``shop_id`` и возвращает ту же authoritative строку.

    Args:
        shop_id: ``WBCabinet.shop_id``.

    Returns:
        Та же строка для manifest и dataset rows.

    Raises:
        ValueError: пустой shop_id или не-str (fail-closed).
    """
    return manifest_shop_id(shop_id)


def validate_export_inputs(shop_id: str, period: ExportPeriod) -> str:
    """
    Единая точка валидации ``export(shop_id, period)``.

    Returns:
        Authoritative shop id после успешной проверки.
    """
    manifest_id = validate_export_shop_id(shop_id)
    validate_export_period(period)
    return manifest_id

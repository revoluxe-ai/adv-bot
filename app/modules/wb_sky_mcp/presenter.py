"""Presenter AI-пакета: тот же ExportService, лимит вложения, без второго SQL.

Крупный файл не обрезается молча: дескриптор ``OMITTED_OVER_BUDGET``.
Содержимое магазина остаётся данными и не становится инструкцией модели.
"""

from __future__ import annotations

import datetime
from typing import Any

from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.manifest import DomainPayload, sha256_hex
from app.modules.ai_package_v1.export.export_service import ExportResult, ExportService
from app.modules.ai_package_v1.export.family_gaps import (
    attach_family_gaps,
    build_family_gaps_document,
)
from app.modules.wb_sky_mcp.config import McpConfig
from app.modules.wb_sky_mcp.errors import McpError

_TEXT_PREFIXES = ("datasets/",)
_TEXT_SUFFIXES = (".json", ".csv", ".txt")


def parse_period(period_start: object, period_end: object) -> ExportPeriod:
    """Включительные даты. Длина не больше 366 дней.

    Raises:
        McpError: даты некорректны.
    """
    if not isinstance(period_start, str) or not isinstance(period_end, str):
        raise McpError("INVALID_ARGUMENT", "period must be ISO dates")
    try:
        start = datetime.date.fromisoformat(period_start)
        end = datetime.date.fromisoformat(period_end)
    except ValueError as exc:
        raise McpError("INVALID_ARGUMENT", "period must be ISO dates") from exc
    if end < start or (end - start).days > 365:
        raise McpError("INVALID_ARGUMENT", "period is out of range")
    return ExportPeriod(start=start, end=end)


def _is_text_payload(payload: DomainPayload) -> bool:
    name = payload.logical_name.lower()
    if name.endswith(_TEXT_SUFFIXES):
        return True
    return name.startswith(_TEXT_PREFIXES)


def _inline_text(content: bytes) -> str | None:
    try:
        return content.decode("utf-8")
    except UnicodeError:
        return None


def present_export_result(
    result: ExportResult,
    *,
    authoritative_shop_id: str,
    config: McpConfig,
) -> dict[str, Any]:
    """Собрать структурный конверт MCP из уже полученного export.

    Не вызывает сборщиков и не переписывает coverage карточек.
    ``authoritative_shop_id`` — строка аргумента, не int из manifest.
    """
    enriched, _gaps_payload = attach_family_gaps(result)
    gaps_document = build_family_gaps_document(result)
    files: list[dict[str, Any]] = []
    inline_used = 0
    ordered = sorted(enriched.payloads, key=lambda item: item.logical_name)
    for payload in ordered:
        digest = sha256_hex(payload.content)
        descriptor: dict[str, Any] = {
            "logical_name": payload.logical_name,
            "dataset_id": payload.dataset_id,
            "sha256": digest,
            "size_bytes": len(payload.content),
        }
        text = _inline_text(payload.content) if _is_text_payload(payload) else None
        too_big = (
            text is None
            or len(payload.content) > config.inline_file_max_bytes
            or inline_used + len(payload.content) > config.inline_total_max_bytes
        )
        if too_big:
            descriptor["status"] = "OMITTED_OVER_BUDGET"
        else:
            descriptor["status"] = "INLINE"
            descriptor["inline_text"] = text
            inline_used += len(payload.content)
        files.append(descriptor)
    cards = [card.to_manifest_dict() for card in enriched.manifest.datasets]
    return {
        "content_trust": "data",
        "package_schema_version": enriched.manifest.package_schema_version,
        "authoritative_shop_id": authoritative_shop_id,
        "manifest": enriched.manifest.to_domain_dict(),
        "dataset_cards": cards,
        "package_family_gaps": gaps_document,
        "files": files,
    }


async def export_ai_package(
    export_service: ExportService,
    *,
    shop_id: str,
    period: ExportPeriod,
    config: McpConfig,
) -> dict[str, Any]:
    """Вызвать канонический ``ExportService.export`` и представить результат.

    Side effect: только чтение через экспортёр. WB API и коллекторы не
    запускаются этим адаптером.
    """
    result = await export_service.export(shop_id, period)
    return present_export_result(
        result,
        authoritative_shop_id=shop_id,
        config=config,
    )

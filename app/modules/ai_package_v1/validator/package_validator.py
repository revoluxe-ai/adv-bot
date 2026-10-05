"""Детерминированная валидация manifest и целостности payload (без сети/WB)."""

from __future__ import annotations

import json
from typing import Any, cast

from pydantic import ValidationError

from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
    SCHEMA_VERSION,
    CampaignSettingsSnapshotV1,
)
from app.modules.ai_package_v1.domain.manifest import (
    PACKAGE_SCHEMA_VERSION,
    sha256_hex,
)
from app.modules.ai_package_v1.export.dataset_cards import CAMPAIGN_SETTINGS_JSON_LOGICAL
from app.modules.ai_package_v1.zip_transport.encode import decode_package


class PackageValidationError(Exception):
    """Ошибка валидации пакета AI Package v1."""


def validate_domain_manifest(
    manifest: dict[str, Any],
    files: dict[str, bytes],
) -> None:
    """
    Проверяет schema version, обязательные поля и sha256 каждого файла.

    Raises:
        PackageValidationError: при несоответствии контракту или хешу.
    """
    version = manifest.get("package_schema_version")
    if version != PACKAGE_SCHEMA_VERSION:
        raise PackageValidationError(
            f"unsupported package_schema_version: {version!r}",
        )
    for key in ("shop_id", "period", "datasets", "files"):
        if key not in manifest:
            raise PackageValidationError(f"missing manifest key: {key}")

    listed_raw = manifest.get("files", [])
    if not isinstance(listed_raw, list):
        raise PackageValidationError("files must be a list")
    listed = cast(list[Any], listed_raw)

    for entry_obj in listed:
        if not isinstance(entry_obj, dict):
            raise PackageValidationError("file entry must be object")
        entry = cast(dict[str, Any], entry_obj)
        logical_name = entry.get("logical_name")
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if not logical_name or not expected_hash:
            raise PackageValidationError("file entry missing logical_name or sha256")
        content = files.get(logical_name)
        if content is None:
            raise PackageValidationError(f"missing payload file: {logical_name}")
        actual_hash = sha256_hex(content)
        if actual_hash != expected_hash:
            raise PackageValidationError(
                f"hash mismatch for {logical_name}: expected {expected_hash}, got {actual_hash}",
            )
        if expected_size is not None and len(content) != expected_size:
            raise PackageValidationError(
                f"size mismatch for {logical_name}: expected {expected_size}, got {len(content)}",
            )

    _validate_shop_orders_card(manifest)
    _validate_campaign_settings_payload(manifest, files)


def validate_zip_package(zip_bytes: bytes) -> None:
    """
    Валидирует ZIP-пакет: manifest + перечисленные payloads.

    Raises:
        PackageValidationError: при ошибке структуры или хеша.
    """
    try:
        manifest, files = decode_package(zip_bytes)
    except (ValueError, OSError) as exc:
        raise PackageValidationError(str(exc)) from exc
    validate_domain_manifest(manifest, files)


def _validate_shop_orders_card(manifest: dict[str, Any]) -> None:
    datasets = cast(list[Any], manifest.get("datasets", []))
    for card_obj in datasets:
        if not isinstance(card_obj, dict):
            continue
        card = cast(dict[str, Any], card_obj)
        if card.get("dataset_id") != "shop_product_orders_sales":
            continue
        provenance_value = card.get("provenance")
        if isinstance(provenance_value, dict):
            prov = cast(dict[str, Any], provenance_value)
        else:
            prov: dict[str, Any] = {}
        source = prov.get("primary_source")
        if source not in ("SOURCE_NOT_ASSIGNED", "UNKNOWN"):
            raise PackageValidationError(
                "shop_product_orders_sales must declare SOURCE_NOT_ASSIGNED or UNKNOWN",
            )
        if card.get("row_count") not in (None, 0):
            raise PackageValidationError(
                "shop_product_orders_sales must not contain data rows in v1",
            )


def _validate_campaign_settings_payload(
    manifest: dict[str, Any],
    files: dict[str, bytes],
) -> None:
    """Проверяет detailed ``CampaignSettingsSnapshotV1`` payload и provenance."""
    datasets = cast(list[Any], manifest.get("datasets", []))
    settings_card: dict[str, Any] | None = None
    for card_obj in datasets:
        if not isinstance(card_obj, dict):
            continue
        card = cast(dict[str, Any], card_obj)
        if card.get("dataset_id") == "campaign_settings_snapshot":
            settings_card = card
            break
    if settings_card is None:
        return

    row_file = settings_card.get("row_file")
    if row_file != CAMPAIGN_SETTINGS_JSON_LOGICAL:
        raise PackageValidationError(
            "campaign_settings_snapshot must reference detailed JSON payload",
        )
    provenance = settings_card.get("provenance")
    if isinstance(provenance, dict):
        primary_source = cast(dict[str, Any], provenance).get("primary_source")
        if primary_source != "postgresql.adv_setting_detailed_settings":
            raise PackageValidationError(
                "campaign_settings_snapshot provenance must be detailed settings",
            )

    content = files.get(CAMPAIGN_SETTINGS_JSON_LOGICAL)
    if content is None:
        raise PackageValidationError(
            f"missing detailed settings payload: {CAMPAIGN_SETTINGS_JSON_LOGICAL}",
        )
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError(
            "campaign_settings_snapshot payload is not valid JSON",
        ) from exc
    if data.get("schema_version") != SCHEMA_VERSION:
        raise PackageValidationError(
            f"unsupported settings schema_version: {data.get('schema_version')!r}",
        )
    try:
        parsed = CampaignSettingsSnapshotV1.model_validate(data)
    except ValidationError as exc:
        raise PackageValidationError(
            f"campaign_settings_snapshot contract validation failed: {exc}",
        ) from exc
    manifest_shop_id = manifest.get("shop_id")
    if manifest_shop_id is not None and parsed.shop_id != str(manifest_shop_id):
        raise PackageValidationError(
            "campaign_settings_snapshot shop_id must match manifest shop_id",
        )
    if parsed.completeness.coverage.value == "FULL":
        raise PackageValidationError(
            "campaign_settings_snapshot must not claim FULL coverage in slice 1",
        )

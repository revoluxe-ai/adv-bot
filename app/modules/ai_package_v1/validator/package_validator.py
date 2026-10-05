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
from app.modules.ai_package_v1.domain.enums import FamilyStatus
from app.modules.ai_package_v1.export.family_gaps import (
    GAP_DOCUMENT_KIND,
    PACKAGE_FAMILY_GAPS_LOGICAL,
    build_family_gap_catalog,
)
from app.modules.ai_package_v1.export.family_status import (
    derive_family_status_from_card,
    derive_keyword_performance_family_status,
    family_status_for_gap_entry,
)
from app.modules.ai_package_v1.export.package_summary import (
    PACKAGE_SUMMARY_LOGICAL,
    SUMMARY_DOCUMENT_KIND,
)
from app.modules.ai_package_v1.domain.enums import (
    CollectionOutcome,
    Coverage,
    DatasetId,
    FreshnessStatus,
    PrimarySource,
)
from app.modules.ai_package_v1.domain.dataset_card import DatasetCard, Provenance
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
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
    _validate_keyword_root_payloads(manifest, files)
    _validate_family_gaps_payload(manifest, files)
    _validate_package_summary_payload(manifest, files)


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


def _validate_keyword_root_payloads(
    manifest: dict[str, Any],
    files: dict[str, bytes],
) -> None:
    """Validate DATA_MAP.json and coverage.json when keyword export present."""
    datasets = cast(list[Any], manifest.get("datasets", []))
    has_keyword = False
    for card_obj in datasets:
        if not isinstance(card_obj, dict):
            continue
        card = cast(dict[str, Any], card_obj)
        dataset_id = str(card.get("dataset_id", ""))
        if dataset_id.startswith("keyword"):
            has_keyword = True
            break
    if not has_keyword:
        return
    for logical_name in ("DATA_MAP.json", "coverage.json"):
        content = files.get(logical_name)
        if content is None:
            raise PackageValidationError(f"missing keyword root payload: {logical_name}")
        try:
            parsed_json = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackageValidationError(
                f"{logical_name} is not valid JSON",
            ) from exc
        if not isinstance(parsed_json, dict):
            raise PackageValidationError(f"{logical_name} must be a JSON object")
        data = cast(dict[str, Any], parsed_json)
        schema_version = data.get("schema_version")
        if schema_version is None:
            raise PackageValidationError(f"{logical_name} missing schema_version")


def _validate_family_gaps_payload(
    manifest: dict[str, Any],
    files: dict[str, bytes],
) -> None:
    """Проверяет PACKAGE_FAMILY_GAPS.json при наличии карточки package_family_gaps."""
    datasets = cast(list[Any], manifest.get("datasets", []))
    has_gaps_card = False
    for card_obj in datasets:
        if not isinstance(card_obj, dict):
            continue
        card = cast(dict[str, Any], card_obj)
        if card.get("dataset_id") == "package_family_gaps":
            has_gaps_card = True
            break
    if not has_gaps_card:
        return
    content = files.get(PACKAGE_FAMILY_GAPS_LOGICAL)
    if content is None:
        raise PackageValidationError(
            f"missing family gaps payload: {PACKAGE_FAMILY_GAPS_LOGICAL}",
        )
    try:
        parsed_json = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError(
            f"{PACKAGE_FAMILY_GAPS_LOGICAL} is not valid JSON",
        ) from exc
    if not isinstance(parsed_json, dict):
        raise PackageValidationError(
            f"{PACKAGE_FAMILY_GAPS_LOGICAL} must be a JSON object",
        )
    data = cast(dict[str, Any], parsed_json)
    if data.get("document_kind") != GAP_DOCUMENT_KIND:
        raise PackageValidationError(
            f"{PACKAGE_FAMILY_GAPS_LOGICAL} missing document_kind",
        )
    gaps_raw = data.get("gaps")
    if not isinstance(gaps_raw, list):
        raise PackageValidationError(f"{PACKAGE_FAMILY_GAPS_LOGICAL} gaps must be a list")
    gaps = cast(list[Any], gaps_raw)
    expected_len = len(build_family_gap_catalog())
    if len(gaps) != expected_len:
        raise PackageValidationError(
            f"{PACKAGE_FAMILY_GAPS_LOGICAL} gaps length mismatch",
        )
    for entry_obj in gaps:
        if not isinstance(entry_obj, dict):
            raise PackageValidationError("gap entry must be object")
        entry = cast(dict[str, Any], entry_obj)
        status_token = entry.get("family_status")
        if status_token is None:
            raise PackageValidationError(
                f"{PACKAGE_FAMILY_GAPS_LOGICAL} gap missing family_status",
            )
        try:
            _ = FamilyStatus(str(status_token))
        except ValueError:
            raise PackageValidationError(
                f"{PACKAGE_FAMILY_GAPS_LOGICAL} invalid family_status: {status_token!r}",
            )


def _cards_from_manifest_dict(manifest: dict[str, Any]) -> list[DatasetCard]:
    datasets = cast(list[Any], manifest.get("datasets", []))
    cards: list[DatasetCard] = []
    period_raw = manifest.get("period", {})
    if not isinstance(period_raw, dict):
        return cards
    period = ExportPeriod.model_validate(period_raw)
    for card_obj in datasets:
        if not isinstance(card_obj, dict):
            continue
        card_dict = cast(dict[str, Any], card_obj)
        dataset_id = card_dict.get("dataset_id")
        if dataset_id in ("package_family_gaps", "package_summary"):
            continue
        prov_raw = card_dict.get("provenance", {})
        prov = cast(dict[str, Any], prov_raw) if isinstance(prov_raw, dict) else {}
        primary_source_raw = str(prov.get("primary_source", "UNKNOWN"))
        try:
            primary_source = PrimarySource(primary_source_raw)
        except ValueError:
            primary_source = PrimarySource.UNKNOWN
        cards.append(
            DatasetCard(
                dataset_id=DatasetId(str(dataset_id)),
                provenance=Provenance(
                    primary_source=primary_source,
                    grain=str(prov.get("grain", "")),
                    notes=prov.get("notes"),
                ),
                period=period,
                collection_outcome=CollectionOutcome(
                    str(card_dict.get("collection_outcome", "UNKNOWN")),
                ),
                coverage=Coverage(str(card_dict.get("coverage", "UNKNOWN"))),
                reason_codes=card_dict.get("reason_codes", []),
                freshness=FreshnessStatus(str(card_dict.get("freshness", "UNKNOWN"))),
                row_file=card_dict.get("row_file"),
                row_count=card_dict.get("row_count"),
            ),
        )
    return cards


def _validate_package_summary_payload(
    manifest: dict[str, Any],
    files: dict[str, bytes],
) -> None:
    """Проверяет PACKAGE_SUMMARY.json и согласованность family_status."""
    datasets = cast(list[Any], manifest.get("datasets", []))
    has_summary_card = any(
        isinstance(c, dict) and cast(dict[str, Any], c).get("dataset_id") == "package_summary"
        for c in datasets
    )
    if not has_summary_card:
        return
    content = files.get(PACKAGE_SUMMARY_LOGICAL)
    if content is None:
        raise PackageValidationError(
            f"missing package summary payload: {PACKAGE_SUMMARY_LOGICAL}",
        )
    try:
        parsed_json = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError(
            f"{PACKAGE_SUMMARY_LOGICAL} is not valid JSON",
        ) from exc
    if not isinstance(parsed_json, dict):
        raise PackageValidationError(f"{PACKAGE_SUMMARY_LOGICAL} must be a JSON object")
    data = cast(dict[str, Any], parsed_json)
    if data.get("document_kind") != SUMMARY_DOCUMENT_KIND:
        raise PackageValidationError(
            f"{PACKAGE_SUMMARY_LOGICAL} missing document_kind",
        )
    families_raw = data.get("families")
    if not isinstance(families_raw, list):
        raise PackageValidationError(f"{PACKAGE_SUMMARY_LOGICAL} families must be a list")
    if data.get("campaign_identity") is None:
        raise PackageValidationError(
            f"{PACKAGE_SUMMARY_LOGICAL} missing campaign_identity",
        )
    if data.get("missing_zero_null") is None:
        raise PackageValidationError(
            f"{PACKAGE_SUMMARY_LOGICAL} missing missing_zero_null semantics",
        )
    for entry_obj in cast(list[Any], families_raw):
        if not isinstance(entry_obj, dict):
            raise PackageValidationError("summary family entry must be object")
        entry = cast(dict[str, Any], entry_obj)
        token = entry.get("family_status")
        if token is None:
            raise PackageValidationError("summary family missing family_status")
        try:
            _ = FamilyStatus(str(token))
        except ValueError:
            raise PackageValidationError(
                f"summary invalid family_status: {token!r}",
            )
    cards = _cards_from_manifest_dict(manifest)
    common_sales = _family_status_from_summary(data, "shop_common_sales")
    if common_sales != FamilyStatus.GAP:
        raise PackageValidationError("shop_common_sales must be GAP in v1")
    campaign_card = next(
        (c for c in cards if c.dataset_id == DatasetId.CAMPAIGN_FULL_STAT),
        None,
    )
    if campaign_card is not None:
        adv_status = derive_family_status_from_card(campaign_card)
        summary_adv = _family_status_from_summary(data, "campaign_advertising")
        if summary_adv is not None and summary_adv != adv_status:
            raise PackageValidationError(
                "campaign_advertising family_status inconsistent with dataset card",
            )
    keyword_status = derive_keyword_performance_family_status(cards)
    summary_kw = _family_status_from_summary(data, "keyword_performance")
    if summary_kw is not None and summary_kw != keyword_status:
        raise PackageValidationError(
            "keyword_performance family_status inconsistent with keyword cards",
        )
    gaps_content = files.get(PACKAGE_FAMILY_GAPS_LOGICAL)
    if gaps_content is not None:
        gaps_parsed = json.loads(gaps_content.decode("utf-8"))
        if isinstance(gaps_parsed, dict):
            gaps_doc = cast(dict[str, Any], gaps_parsed)
            gaps_list = gaps_doc.get("gaps", [])
            if not isinstance(gaps_list, list):
                gaps_list = []
            for gap in cast(list[Any], gaps_list):
                if not isinstance(gap, dict):
                    continue
                gap_dict = cast(dict[str, Any], gap)
                gap_id = str(gap_dict.get("family_id", ""))
                gap_status = family_status_for_gap_entry(
                    str(gap_dict.get("family_status", "GAP")),
                )
                if gap_id == "campaign_settings_history":
                    hist = _family_status_from_summary(data, "campaign_settings_history")
                    if hist is not None and hist != gap_status:
                        raise PackageValidationError(
                            "settings history status mismatch gaps vs summary",
                        )


def _family_status_from_summary(
    summary: dict[str, Any],
    family_id: str,
) -> FamilyStatus | None:
    families = summary.get("families")
    if not isinstance(families, list):
        return None
    families_list = cast(list[Any], families)
    for entry_obj in families_list:
        if not isinstance(entry_obj, dict):
            continue
        entry = cast(dict[str, Any], entry_obj)
        if entry.get("family_id") == family_id:
            token = entry.get("family_status")
            if token is None:
                return None
            return family_status_for_gap_entry(str(token))
    return None

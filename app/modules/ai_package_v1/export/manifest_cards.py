"""Manifest card builder для dataset campaign_settings_snapshot."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
    CampaignSettingsSnapshotV1,
    SCHEMA_VERSION,
)


def serialize_campaign_settings_payload(
    payload: CampaignSettingsSnapshotV1,
) -> bytes:
    """Сериализует domain payload в canonical JSON bytes для sha256.

    Args:
        payload: Domain contract CampaignSettingsSnapshotV1.

    Returns:
        UTF-8 JSON bytes с sorted keys и default=str для datetime.
    """
    data = payload.model_dump(mode="json")
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )


def payload_sha256(payload: CampaignSettingsSnapshotV1) -> str:
    """Вычисляет sha256 domain payload."""
    return hashlib.sha256(serialize_campaign_settings_payload(payload)).hexdigest()


def build_campaign_settings_snapshot_card(
    payload: CampaignSettingsSnapshotV1,
    *,
    payload_filename: str = "campaign_settings_snapshot.json",
) -> dict[str, Any]:
    """Строит manifest card metadata для detailed settings export.

    Args:
        payload: Собранный domain snapshot.
        payload_filename: Логическое имя файла payload в ZIP/manifest.

    Returns:
        Manifest card dict с `detailed_settings_export: true` и four dimensions.
    """
    digest = payload_sha256(payload)
    completeness = payload.completeness
    return {
        "dataset_id": "campaign_settings_snapshot",
        "schema_version": SCHEMA_VERSION,
        "detailed_settings_export": True,
        "payload_file": payload_filename,
        "sha256": digest,
        "shop_id": payload.shop_id,
        "snapshot_assembled_at": payload.snapshot_assembled_at.isoformat(),
        "collection_outcome": completeness.collection_outcome.value,
        "coverage": completeness.coverage.value,
        "reason_codes": [code.value for code in completeness.reason_codes],
        "freshness": completeness.freshness.value,
        "record_count": len(payload.records),
    }

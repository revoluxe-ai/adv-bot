"""Контракт: authoritative WBCabinet.shop_id сохраняется строкой в Full AI Package.

Фикстура — UUID-подобный shop id реального кабинета, не synthetic int.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock

from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
    CampaignSettingsSnapshotV1,
    CompletenessBlockV1,
)
from app.modules.ai_package_v1.domain.campaign_stat import CampaignStatRow
from app.modules.ai_package_v1.domain.export_inputs import validate_export_shop_id
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.funnel_stat import FunnelStatRow
from app.modules.ai_package_v1.domain.manifest import (
    PACKAGE_SCHEMA_VERSION,
    ExportManifest,
)
from app.modules.ai_package_v1.domain.settings_enums import (
    SettingsCollectionOutcome,
    SettingsCoverageLevel,
    SettingsFreshnessLevel,
)
from app.modules.ai_package_v1.domain.shop_id import (
    manifest_shop_id,
    require_authoritative_shop_id,
)
from app.modules.ai_package_v1.export.export_service import ExportService
from app.modules.ai_package_v1.export.package_summary import PACKAGE_SUMMARY_LOGICAL
from app.modules.ai_package_v1.export.package_zip_assembler import PackageZipAssembler
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from app.modules.ai_package_v1.validator.package_validator import (
    PackageValidationError,
    validate_domain_manifest,
    validate_zip_package,
)
from app.modules.ai_package_v1.zip_transport.encode import decode_package
from tests.unit.ai_package_v1.keyword_performance.conftest import (
    GENERATED_AT,
    FakeKeywordDeps,
    build_fake_assembler,
    make_daily_raw,
    make_scope_row,
)

pytestmark = pytest.mark.unit

UUID_SHOP_ID = "155c426c-0c58-59d2-9578-ec9747ecbc90"
DECIMAL_SHOP_ID = "00155"
PERIOD = ExportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 7))


def test_blank_shop_id_fails_closed() -> None:
    """Пустой и whitespace-only идентификатор не экспортируется."""
    for blank in ("", " ", "   ", "\t", "\n"):
        with pytest.raises(ValueError, match="non-blank"):
            validate_export_shop_id(blank)


def test_decimal_string_shop_id_is_not_coerced_to_int() -> None:
    """Десятичная строка остаётся строкой, включая ведущие нули."""
    preserved = validate_export_shop_id(DECIMAL_SHOP_ID)
    assert preserved == DECIMAL_SHOP_ID
    assert isinstance(preserved, str)
    assert preserved != "155"

    numeric_payload: dict[str, object] = {
        "shop_id": 155,
        "campaign_id": 111,
        "date": "2026-01-01",
    }
    with pytest.raises(ValidationError):
        CampaignStatRow.model_validate(numeric_payload)

    manifest_payload: dict[str, object] = {
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "shop_id": 155,
        "period": {"start": "2026-01-01", "end": "2026-01-07"},
        "generated_at": GENERATED_AT,
        "datasets": [],
    }
    with pytest.raises(ValidationError):
        ExportManifest.model_validate(manifest_payload)

    bad_manifest: dict[str, Any] = {
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "shop_id": 155,
        "period": {"start": "2026-01-01", "end": "2026-01-07"},
        "datasets": [],
        "files": [],
    }
    with pytest.raises(PackageValidationError, match="authoritative string"):
        validate_domain_manifest(bad_manifest, {})

    blank_manifest = dict(bad_manifest)
    blank_manifest["shop_id"] = "   "
    with pytest.raises(PackageValidationError, match="non-blank"):
        validate_domain_manifest(blank_manifest, {})


def test_whitespace_is_not_stripped_from_shop_id() -> None:
    """Краевые пробелы легитимного id не переписываются молча."""
    padded = f" {UUID_SHOP_ID} "
    assert manifest_shop_id(padded) == padded
    assert require_authoritative_shop_id(padded) == padded


class _StampCampaignReader:
    """Возвращает одну campaign-строку с переданным shop_id."""

    async def fetch_rows(
        self,
        shop_id: str,
        adv_ids: Sequence[int],
        period: ExportPeriod,
    ) -> list[CampaignStatRow]:
        return [
            CampaignStatRow(
                shop_id=shop_id,
                campaign_id=adv_id,
                date=period.start,
                views=3,
                clicks=1,
            )
            for adv_id in adv_ids
        ]


class _StampFunnelReader:
    """Возвращает одну funnel-строку с переданным shop_id."""

    async def fetch_rows(
        self,
        shop_id: str,
        nmids: Sequence[int],
        period: ExportPeriod,
    ) -> list[FunnelStatRow]:
        if not nmids:
            return []
        return [
            FunnelStatRow(
                shop_id=shop_id,
                nmid=nmids[0],
                date=period.start,
                open_card=1,
                orders=0,
            ),
        ]


class _NoFreshness:
    async def max_full_adv_version(self, *_args: object, **_kwargs: object) -> None:
        return None

    async def max_common_stat_version(self, *_args: object, **_kwargs: object) -> None:
        return None


def _settings_snapshot(shop_id: str) -> CampaignSettingsSnapshotV1:
    return CampaignSettingsSnapshotV1(
        shop_id=shop_id,
        snapshot_assembled_at=datetime(2026, 1, 7, tzinfo=UTC),
        records=(),
        completeness=CompletenessBlockV1(
            collection_outcome=SettingsCollectionOutcome.NO_DATA,
            coverage=SettingsCoverageLevel.UNKNOWN,
            freshness=SettingsFreshnessLevel.UNKNOWN,
        ),
    )


def _csv_shop_ids(content: bytes) -> list[str]:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    return [row["shop_id"] for row in reader]


def _jsonl_shop_ids(content: bytes) -> list[object]:
    values: list[object] = []
    for line in content.decode("utf-8").splitlines():
        if not line.strip():
            continue
        raw: object = json.loads(line)
        if not isinstance(raw, dict) or "shop_id" not in raw:
            continue
        row = cast(dict[str, object], raw)
        values.append(row["shop_id"])
    return values


@pytest.mark.asyncio
async def test_uuid_shop_id_roundtrip_through_package() -> None:
    """UUID shop id проходит input, manifest, payloads, summary и validator."""
    assert validate_export_shop_id(UUID_SHOP_ID) == UUID_SHOP_ID

    deps = FakeKeywordDeps(
        scope_rows=[make_scope_row(shop_id=UUID_SHOP_ID)],
        daily_raw=[make_daily_raw()],
    )
    settings = MagicMock()
    settings.assemble = AsyncMock(return_value=_settings_snapshot(UUID_SHOP_ID))
    service = ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=_StampCampaignReader(),  # type: ignore[arg-type]
        funnel_reader=_StampFunnelReader(),  # type: ignore[arg-type]
        freshness_reader=_NoFreshness(),  # type: ignore[arg-type]
        settings_assembler=settings,
        keyword_assembler=build_fake_assembler(deps),
    )
    scope = [
        ExportScopeAdv(
            shop_id=UUID_SHOP_ID,
            auto_adv_id=111,
            search_adv_id=222,
            main_nmid=500,
            name="auto",
            active_status="active",
            bot_active=False,
        ),
    ]
    assembler = PackageZipAssembler(export_service=service)
    zip_bytes = await assembler.assemble_zip_with_scope(
        UUID_SHOP_ID,
        PERIOD,
        scope,
        generated_at=GENERATED_AT,
    )
    validate_zip_package(zip_bytes)
    manifest, files = decode_package(zip_bytes)

    assert manifest["shop_id"] == UUID_SHOP_ID
    assert isinstance(manifest["shop_id"], str)

    summary = json.loads(files[PACKAGE_SUMMARY_LOGICAL].decode("utf-8"))
    gaps = json.loads(files["PACKAGE_FAMILY_GAPS.json"].decode("utf-8"))
    settings_doc = json.loads(
        files["datasets/campaign_settings_snapshot.json"].decode("utf-8"),
    )
    data_map = json.loads(files["DATA_MAP.json"].decode("utf-8"))
    assert summary["shop_id"] == UUID_SHOP_ID
    assert isinstance(summary["shop_id"], str)
    assert gaps["shop_id"] == UUID_SHOP_ID
    assert settings_doc["shop_id"] == UUID_SHOP_ID

    campaign_ids = _csv_shop_ids(files["datasets/campaign_full_stat.csv"])
    funnel_ids = _csv_shop_ids(files["datasets/complex_adv_funnel.csv"])
    assert campaign_ids
    assert funnel_ids
    assert set(campaign_ids) == {UUID_SHOP_ID}
    assert set(funnel_ids) == {UUID_SHOP_ID}

    keyword_ids = _jsonl_shop_ids(files["keyword_performance/keyword_daily.jsonl"])
    assert keyword_ids
    assert all(value == UUID_SHOP_ID and isinstance(value, str) for value in keyword_ids)

    shop_units = [
        row["units"]
        for row in data_map["export_field_matrix"]
        if row["field"] == "shop_id"
    ]
    assert shop_units
    assert set(shop_units) == {"str"}

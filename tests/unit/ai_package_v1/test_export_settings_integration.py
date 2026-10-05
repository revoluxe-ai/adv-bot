"""Integration: CampaignSettingsSnapshotV1 wired into ExportService manifest."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import SCHEMA_VERSION
from app.modules.ai_package_v1.domain.enums import Coverage, DatasetId, PrimarySource
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.export.dataset_cards import CAMPAIGN_SETTINGS_JSON_LOGICAL
from app.modules.ai_package_v1.export.export_service import ExportService
from app.modules.ai_package_v1.export.manifest_cards import payload_sha256
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from app.modules.ai_package_v1.validator.package_validator import (
    PackageValidationError,
    validate_domain_manifest,
    validate_zip_package,
)
from app.modules.ai_package_v1.zip_transport.encode import encode_package
from tests.unit.ai_package_v1.conftest import make_adv_setting

pytestmark = pytest.mark.unit

PERIOD = ExportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 7))
SHOP_ID = "1"
GENERATED_AT = "2026-10-03T12:00:00Z"


class _NoOpReader:
    async def fetch_rows(self, *args: object, **kwargs: object) -> list[object]:
        return []

    async def max_full_adv_version(self, *args: object, **kwargs: object) -> None:
        return None

    async def max_common_stat_version(self, *args: object, **kwargs: object) -> None:
        return None


def _scope_for_shop(*, shop_id: str = SHOP_ID) -> list[ExportScopeAdv]:
    return [
        ExportScopeAdv(
            shop_id=shop_id,
            auto_adv_id=111,
            search_adv_id=222,
            main_nmid=500,
            name="auto",
            active_status="active",
            bot_active=False,
        )
    ]


def _export_service(assembler_factory, rows: list[object]) -> ExportService:
    assembler = assembler_factory(rows)
    return ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=_NoOpReader(),  # type: ignore[arg-type]
        funnel_reader=_NoOpReader(),  # type: ignore[arg-type]
        freshness_reader=_NoOpReader(),  # type: ignore[arg-type]
        settings_assembler=assembler,
    )


@pytest.mark.asyncio
async def test_export_service_emits_detailed_settings_json_payload(
    assembler_factory,
) -> None:
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = _export_service(assembler_factory, [row])
    result = await service.export_with_scope(
        SHOP_ID,
        PERIOD,
        _scope_for_shop(),
        generated_at=GENERATED_AT,
    )
    settings_card = next(
        c
        for c in result.manifest.datasets
        if c.dataset_id == DatasetId.CAMPAIGN_SETTINGS_SNAPSHOT
    )
    assert settings_card.coverage == Coverage.PARTIAL
    assert settings_card.provenance.primary_source == (
        PrimarySource.POSTGRES_CAMPAIGN_SETTINGS
    )
    assert settings_card.row_file == CAMPAIGN_SETTINGS_JSON_LOGICAL
    settings_payload = next(
        p for p in result.payloads if p.logical_name == CAMPAIGN_SETTINGS_JSON_LOGICAL
    )
    data = json.loads(settings_payload.content.decode("utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["records"][0]["auto_leg"]["wb_adv_id"] == 111
    assert data["records"][0]["search_leg"]["wb_adv_id"] == 222
    manifest_dict = result.manifest.to_domain_dict()
    files = {p.logical_name: p.content for p in result.payloads}
    validate_domain_manifest(manifest_dict, files)


@pytest.mark.asyncio
async def test_export_zip_deterministic_settings_hash(assembler_factory) -> None:
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = _export_service(assembler_factory, [row])
    first = await service.export_with_scope(
        SHOP_ID,
        PERIOD,
        _scope_for_shop(),
        generated_at=GENERATED_AT,
    )
    second = await service.export_with_scope(
        SHOP_ID,
        PERIOD,
        _scope_for_shop(),
        generated_at=GENERATED_AT,
    )
    settings_payload = next(
        p for p in first.payloads if p.logical_name == CAMPAIGN_SETTINGS_JSON_LOGICAL
    )
    expected_hash = hashlib.sha256(settings_payload.content).hexdigest()
    file_entry = next(
        f
        for f in first.manifest.files
        if f.logical_name == CAMPAIGN_SETTINGS_JSON_LOGICAL
    )
    assert file_entry.sha256 == expected_hash
    zip_a = encode_package(first.manifest, first.payloads)
    zip_b = encode_package(second.manifest, second.payloads)
    validate_zip_package(zip_a)
    assert hashlib.sha256(zip_a).hexdigest() == hashlib.sha256(zip_b).hexdigest()


@pytest.mark.asyncio
async def test_other_dataset_cards_unchanged_with_detailed_settings(
    assembler_factory,
) -> None:
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = _export_service(assembler_factory, [row])
    result = await service.export_with_scope(
        SHOP_ID,
        PERIOD,
        _scope_for_shop(),
        generated_at=GENERATED_AT,
    )
    by_id = {c.dataset_id: c for c in result.manifest.datasets}
    campaign = by_id[DatasetId.CAMPAIGN_FULL_STAT]
    funnel = by_id[DatasetId.COMPLEX_ADV_FUNNEL]
    shop_orders = by_id[DatasetId.SHOP_PRODUCT_ORDERS_SALES]
    assert campaign.provenance.primary_source == (
        PrimarySource.CLICKHOUSE_FULL_ADV_WB_STAT
    )
    assert campaign.row_file == "datasets/campaign_full_stat.csv"
    assert funnel.provenance.primary_source == PrimarySource.CLICKHOUSE_WB_COMMON_STAT
    assert funnel.row_file == "datasets/complex_adv_funnel.csv"
    assert shop_orders.provenance.primary_source == PrimarySource.SOURCE_NOT_ASSIGNED
    assert shop_orders.row_count in (None, 0)


@pytest.mark.asyncio
async def test_export_shop_isolation_on_settings_payload(assembler_factory) -> None:
    foreign = make_adv_setting(
        shop_id="999",
        adv_setting_id=999,
        adv_id=333,
        search_adv_id=334,
    )
    own = make_adv_setting(
        shop_id=SHOP_ID,
        adv_setting_id=101,
        adv_id=111,
        search_adv_id=222,
    )
    service = _export_service(assembler_factory, [foreign, own])
    result = await service.export_with_scope(
        SHOP_ID,
        PERIOD,
        _scope_for_shop(),
        generated_at=GENERATED_AT,
    )
    settings_payload = next(
        p for p in result.payloads if p.logical_name == CAMPAIGN_SETTINGS_JSON_LOGICAL
    )
    data = json.loads(settings_payload.content.decode("utf-8"))
    assert len(data["records"]) == 1
    assert data["records"][0]["inventory"]["adv_setting_id"] == 101


@pytest.mark.asyncio
async def test_validator_rejects_tampered_settings_payload(assembler_factory) -> None:
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = _export_service(assembler_factory, [row])
    result = await service.export_with_scope(
        SHOP_ID,
        PERIOD,
        _scope_for_shop(),
        generated_at=GENERATED_AT,
    )
    manifest_dict = result.manifest.to_domain_dict()
    files = {p.logical_name: p.content for p in result.payloads}
    tampered = dict(files)
    tampered[CAMPAIGN_SETTINGS_JSON_LOGICAL] = b'{"schema_version":"broken"}'
    with pytest.raises(PackageValidationError, match="hash mismatch"):
        validate_domain_manifest(manifest_dict, tampered)


@pytest.mark.asyncio
async def test_manifest_payload_hash_matches_domain_contract(
    assembler_factory,
) -> None:
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    payload = await assembler_factory([row]).assemble(SHOP_ID)
    digest = payload_sha256(payload)
    service = _export_service(assembler_factory, [row])
    result = await service.export_with_scope(
        SHOP_ID,
        PERIOD,
        _scope_for_shop(),
        generated_at=GENERATED_AT,
    )
    settings_payload = next(
        p for p in result.payloads if p.logical_name == CAMPAIGN_SETTINGS_JSON_LOGICAL
    )
    assert hashlib.sha256(settings_payload.content).hexdigest() == digest

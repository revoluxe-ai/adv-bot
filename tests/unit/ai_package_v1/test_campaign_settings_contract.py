"""Contract tests: non-aliasing vs A1/Redis DTOs and payload type guard."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from datetime import date

from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
    CampaignSettingsSnapshotV1,
    SCHEMA_VERSION,
)
from app.modules.ai_package_v1.domain.enums import Coverage, PrimarySource
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.export.dataset_cards import (
    build_campaign_settings_inventory_card,
)
from app.modules.ai_package_v1.export.manifest_cards import (
    build_campaign_settings_snapshot_card,
    serialize_campaign_settings_payload,
)
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from app.snapshot_data_updater.dto import AdvSettingsSnapshotDTO
from tests.unit.ai_package_v1.a1_contract_stub import CampaignResourceSnapshotV1Stub
from tests.unit.ai_package_v1.conftest import AssemblerFactory, make_adv_setting


@pytest.mark.unit
@pytest.mark.asyncio
async def test_payload_not_adv_settings_snapshot_dto(
    assembler_factory: AssemblerFactory,
) -> None:
    payload = await assembler_factory([make_adv_setting()]).assemble("shop-1")
    raw = serialize_campaign_settings_payload(payload)
    data = json.loads(raw)
    assert data["schema_version"] == SCHEMA_VERSION
    with pytest.raises(ValidationError):
        _ = AdvSettingsSnapshotDTO.model_validate(data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_payload_type_guard_non_aliasing(assembler_factory: AssemblerFactory,
) -> None:
    payload = await assembler_factory([make_adv_setting()]).assemble("shop-1")
    raw = serialize_campaign_settings_payload(payload)
    data = json.loads(raw)
    parsed = CampaignSettingsSnapshotV1.model_validate(data)
    assert parsed.schema_version == SCHEMA_VERSION
    with pytest.raises(ValidationError):
        _ = CampaignResourceSnapshotV1Stub.model_validate(data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detailed_contract_golden_legs(assembler_factory: AssemblerFactory,
) -> None:
    row = make_adv_setting(adv_id=111, search_adv_id=222)
    payload = await assembler_factory([row]).assemble("shop-1")
    raw = serialize_campaign_settings_payload(payload)
    data = json.loads(raw)
    record = data["records"][0]
    assert record["auto_leg"]["wb_adv_id"] == 111
    assert record["search_leg"]["wb_adv_id"] == 222
    assert record["auto_leg"]["leg_role"] == "AUTO"
    assert record["search_leg"]["leg_role"] == "SEARCH"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settings_export_spy_no_wb_calls(assembler_factory: AssemblerFactory,
) -> None:
    """Contract-test authority: zero WB API on settings path (paired S11/S20)."""
    from unittest.mock import MagicMock, patch

    wb_spy = MagicMock()
    with patch.dict("sys.modules", {"app.core.mp.wb.api": wb_spy}):
        payload = await assembler_factory([make_adv_setting()]).assemble("shop-1")
    assert payload.records
    wb_spy.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inventory_partial_before_detailed(
    assembler_factory: AssemblerFactory,
) -> None:
    """S18: legacy inventory card builder keeps PARTIAL grain without detailed export."""
    period = ExportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 7))
    inventory_rows = [
        ExportScopeAdv(
            shop_id="shop-1",
            auto_adv_id=111,
            search_adv_id=222,
            main_nmid=500,
            name="auto",
            active_status="active",
            bot_active=False,
        )
    ]
    legacy_card = build_campaign_settings_inventory_card(
        period,
        inventory_rows=inventory_rows,
    )
    assert legacy_card.coverage == Coverage.PARTIAL
    assert legacy_card.coverage != Coverage.FULL
    assert legacy_card.provenance.primary_source == PrimarySource.POSTGRES_INVENTORY
    assert legacy_card.provenance.notes is not None
    assert "detailed settings deferred" in legacy_card.provenance.notes.lower()

    manifest = legacy_card.to_manifest_dict()
    assert manifest.get("detailed_settings_export") is not True
    assert manifest["coverage"] != Coverage.FULL.value

    detailed_payload = await assembler_factory([make_adv_setting()]).assemble("shop-1")
    detailed_card = build_campaign_settings_snapshot_card(detailed_payload)
    assert detailed_card["detailed_settings_export"] is True
    assert detailed_card["coverage"] != Coverage.FULL.value

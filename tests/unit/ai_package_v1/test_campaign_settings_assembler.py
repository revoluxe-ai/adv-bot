"""Unit tests: CampaignSettingsAssembler and manifest wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import SCHEMA_VERSION
from app.modules.ai_package_v1.domain.settings_enums import (
    AuthorityClass,
    SettingsCoverageLevel,
    SettingsReasonCode,
)
from app.modules.ai_package_v1.export.manifest_cards import (
    build_campaign_settings_snapshot_card,
)
from app.modules.ai_package_v1.scope.pg_adv_setting_inventory_reader import (
    PgAdvSettingInventoryReader,
)
from tests.unit.ai_package_v1.conftest import AssemblerFactory, make_adv_setting


@pytest.mark.unit
@pytest.mark.asyncio
async def test_payload_schema_is_campaign_settings_snapshot_v1(
    assembler_factory: AssemblerFactory,
) -> None:
    row = make_adv_setting()
    assembler = assembler_factory([row])
    payload = await assembler.assemble("shop-1")
    assert payload.schema_version == SCHEMA_VERSION


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auto_and_search_legs_distinguishable(assembler_factory: AssemblerFactory,
) -> None:
    row = make_adv_setting(adv_id=7001, search_adv_id=7002)
    payload = await assembler_factory([row]).assemble("shop-1")
    record = payload.records[0]
    assert record.auto_leg is not None
    assert record.search_leg is not None
    assert record.auto_leg.wb_adv_id == 7001
    assert record.search_leg.wb_adv_id == 7002
    assert record.auto_leg.wb_adv_id != record.search_leg.wb_adv_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_primary_grain_adv_setting_id(assembler_factory: AssemblerFactory,
) -> None:
    row = make_adv_setting(adv_setting_id=555)
    payload = await assembler_factory([row]).assemble("shop-1")
    assert payload.records[0].inventory.adv_setting_id == 555
    assert payload.records[0].inventory.shop_id == "shop-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_policy_provenance_not_wb_authoritative(
    assembler_factory: AssemblerFactory,
) -> None:
    row = make_adv_setting(bot_active=False)
    payload = await assembler_factory([row]).assemble("shop-1")
    local = payload.records[0].local_policy
    assert local.bot_active is False
    bot_prov = next(
        p for p in local.field_provenance if p.field_path == "local_policy.bot_active"
    )
    assert bot_prov.authority_class == AuthorityClass.LOCAL_POLICY


@pytest.mark.unit
@pytest.mark.asyncio
async def test_null_pg_column_stays_null(assembler_factory: AssemblerFactory,
) -> None:
    row = make_adv_setting(wb_bid_type=None, search_adv_id=None)
    payload = await assembler_factory([row]).assemble("shop-1")
    record = payload.records[0]
    assert record.auto_leg is not None
    assert record.auto_leg.wb_bid_type is None
    assert record.search_leg is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unsupported_field_explicit(assembler_factory: AssemblerFactory,
) -> None:
    row = make_adv_setting()
    payload = await assembler_factory([row]).assemble("shop-1")
    auto_leg = payload.records[0].auto_leg
    assert auto_leg is not None
    status_prov = next(
        p for p in auto_leg.field_provenance if p.field_path == "auto_leg.wb_status"
    )
    assert status_prov.authority_class == AuthorityClass.UNSUPPORTED
    assert SettingsReasonCode.UNSUPPORTED_FIELD in status_prov.reason_codes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_partial_pg_wb_sync_explicit(assembler_factory: AssemblerFactory,
) -> None:
    payload = await assembler_factory([make_adv_setting()]).assemble("shop-1")
    assert payload.completeness.coverage == SettingsCoverageLevel.PARTIAL
    assert SettingsReasonCode.PARTIAL_PG_WB_SYNC in payload.completeness.reason_codes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_four_completeness_dimensions_independent(assembler_factory: AssemblerFactory,
) -> None:
    payload = await assembler_factory([make_adv_setting()]).assemble("shop-1")
    card = build_campaign_settings_snapshot_card(payload)
    assert card["collection_outcome"]
    assert card["coverage"]
    assert card["reason_codes"]
    assert card["freshness"]
    assert card["coverage"] == SettingsCoverageLevel.PARTIAL.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detailed_export_flag_true(assembler_factory: AssemblerFactory,
) -> None:
    payload = await assembler_factory([make_adv_setting()]).assemble("shop-1")
    card = build_campaign_settings_snapshot_card(payload)
    assert card["detailed_settings_export"] is True
    assert card["dataset_id"] == "campaign_settings_snapshot"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manifest_references_domain_payload(assembler_factory: AssemblerFactory,
) -> None:
    payload = await assembler_factory([make_adv_setting()]).assemble("shop-1")
    card = build_campaign_settings_snapshot_card(payload)
    assert card["payload_file"] == "campaign_settings_snapshot.json"
    assert card["sha256"]
    assert len(card["sha256"]) == 64


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shop_isolation_filters_foreign_shop(assembler_factory: AssemblerFactory,
) -> None:
    foreign = make_adv_setting(shop_id="shop-foreign", adv_setting_id=999)
    own = make_adv_setting(shop_id="shop-1", adv_setting_id=101)
    payload = await assembler_factory([foreign, own]).assemble("shop-1")
    assert len(payload.records) == 1
    assert payload.records[0].inventory.adv_setting_id == 101


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scope_not_bot_active_only(assembler_factory: AssemblerFactory,
) -> None:
    inactive = make_adv_setting(bot_active=False)
    payload = await assembler_factory([inactive]).assemble("shop-1")
    assert len(payload.records) == 1
    assert payload.records[0].local_policy.bot_active is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settings_export_zero_wb_api_calls(assembler_factory: AssemblerFactory,
) -> None:
    wb_spy = MagicMock()
    with patch.dict(
        "sys.modules",
        {"app.core.mp.wb.api": wb_spy},
    ):
        payload = await assembler_factory([make_adv_setting()]).assemble("shop-1")
    assert payload.schema_version == SCHEMA_VERSION
    wb_spy.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_export_does_not_write_state(assembler_factory: AssemblerFactory,
) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    session_factory = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=session), __aexit__=AsyncMock()))
    session_maker = MagicMock(return_value=session_factory)

    from app.modules.ai_package_v1.export.campaign_settings_assembler import (
        CampaignSettingsAssembler,
    )

    assembler = CampaignSettingsAssembler(session_maker=session_maker)
    _ = await assembler.assemble("shop-1")
    session.add.assert_not_called()
    session.commit.assert_not_called()
    session.flush.assert_not_called()


@pytest.mark.unit
def test_pg_scope_query_has_no_bot_active_filter() -> None:
    stmt = PgAdvSettingInventoryReader.build_inventory_query("shop-1")
    where_sql = str(stmt.whereclause).lower()
    assert "bot_active" not in where_sql
    assert "shop_id" in where_sql
    assert "active_status" in where_sql

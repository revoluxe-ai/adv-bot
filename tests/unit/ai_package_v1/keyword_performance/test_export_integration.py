"""ExportService integration, hash, tamper, default keyword cards (S29,S35,S36,S49,S50,S37,S38)."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.ai_package_v1.domain.enums import DatasetId
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.export.export_service import ExportService
from app.modules.ai_package_v1.validator.package_validator import (
    PackageValidationError,
    validate_domain_manifest,
)
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from tests.unit.ai_package_v1.keyword_performance.conftest import (
    FakeKeywordDeps,
    GENERATED_AT,
    SHOP_ID,
    build_fake_assembler,
    make_daily_raw,
)

pytestmark = pytest.mark.unit

PERIOD = ExportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 7))


class _NoOpReader:
    async def fetch_rows(self, *args: object, **kwargs: object) -> list[object]:
        return []

    async def max_full_adv_version(self, *args: object, **kwargs: object) -> None:
        return None

    async def max_common_stat_version(self, *args: object, **kwargs: object) -> None:
        return None


def _scope() -> list[ExportScopeAdv]:
    return [
        ExportScopeAdv(
            shop_id=SHOP_ID,
            auto_adv_id=111,
            search_adv_id=222,
            main_nmid=500,
            name="auto",
            active_status="active",
            bot_active=False,
        )
    ]


def _empty_settings_snapshot() -> object:
    from datetime import UTC, datetime

    from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
        CampaignSettingsSnapshotV1,
        CompletenessBlockV1,
    )
    from app.modules.ai_package_v1.domain.settings_enums import (
        SettingsCollectionOutcome,
        SettingsCoverageLevel,
        SettingsFreshnessLevel,
    )

    return CampaignSettingsSnapshotV1(
        shop_id=SHOP_ID,
        snapshot_assembled_at=datetime.now(tz=UTC),
        records=(),
        completeness=CompletenessBlockV1(
            collection_outcome=SettingsCollectionOutcome.NO_DATA,
            coverage=SettingsCoverageLevel.UNKNOWN,
            freshness=SettingsFreshnessLevel.UNKNOWN,
        ),
    )


@pytest.mark.asyncio
async def test_default_export_keyword_enabled(fake_deps: FakeKeywordDeps) -> None:
    service = ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=_NoOpReader(),  # type: ignore[arg-type]
        funnel_reader=_NoOpReader(),  # type: ignore[arg-type]
        freshness_reader=_NoOpReader(),  # type: ignore[arg-type]
        settings_assembler=MagicMock(),
        keyword_assembler=build_fake_assembler(fake_deps),
    )
    service._settings_assembler.assemble = AsyncMock(  # type: ignore[method-assign, union-attr]
        return_value=_empty_settings_snapshot()
    )
    result = await service.export_with_scope(
        SHOP_ID, PERIOD, _scope(), generated_at=GENERATED_AT
    )
    ids = {c.dataset_id for c in result.manifest.datasets}
    assert DatasetId.KEYWORD_DAILY in ids
    assert DatasetId.DATA_MAP in ids


@pytest.mark.asyncio
async def test_contract_default_keyword_cards(fake_deps: FakeKeywordDeps) -> None:
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID,
        manifest_shop_id=1,
        period=PERIOD,
        generated_at=GENERATED_AT,
    )
    assert len(result.cards) == 10
    assert len(result.payloads) == 10


@pytest.mark.asyncio
async def test_keyword_manifest_deterministic(fake_deps: FakeKeywordDeps) -> None:
    assembler = build_fake_assembler(fake_deps)
    first = await assembler.assemble(
        shop_id=SHOP_ID, manifest_shop_id=1, period=PERIOD, generated_at=GENERATED_AT
    )
    second = await assembler.assemble(
        shop_id=SHOP_ID, manifest_shop_id=1, period=PERIOD, generated_at=GENERATED_AT
    )
    h1 = hashlib.sha256(first.payloads[0].content).hexdigest()
    h2 = hashlib.sha256(second.payloads[0].content).hexdigest()
    assert h1 == h2


@pytest.mark.asyncio
async def test_datamap_tamper_fails(fake_deps: FakeKeywordDeps) -> None:
    assembler = build_fake_assembler(fake_deps)
    service = ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=_NoOpReader(),  # type: ignore[arg-type]
        funnel_reader=_NoOpReader(),  # type: ignore[arg-type]
        freshness_reader=_NoOpReader(),  # type: ignore[arg-type]
        settings_assembler=MagicMock(),
        keyword_assembler=assembler,
    )
    service._settings_assembler.assemble = AsyncMock(  # type: ignore[method-assign, union-attr]
        return_value=_empty_settings_snapshot()
    )
    export = await service.export_with_scope(
        SHOP_ID, PERIOD, _scope(), generated_at=GENERATED_AT
    )
    manifest_dict = export.manifest.to_domain_dict()
    files = {p.logical_name: p.content for p in export.payloads}
    tampered = dict(files)
    tampered["DATA_MAP.json"] = b'{"schema_version":"broken"}'
    with pytest.raises(PackageValidationError, match="hash mismatch"):
        validate_domain_manifest(manifest_dict, tampered)


@pytest.mark.asyncio
async def test_keyword_dates_ignore_period_end(fake_deps: FakeKeywordDeps) -> None:
    fake_deps.daily_raw.append(make_daily_raw(stat_date=date(2026, 2, 15)))
    assembler = build_fake_assembler(fake_deps)
    result = await assembler.assemble(
        shop_id=SHOP_ID,
        manifest_shop_id=1,
        period=PERIOD,
        generated_at=GENERATED_AT,
    )
    daily_payload = next(p for p in result.payloads if p.dataset_id == "keyword_daily")
    lines = daily_payload.content.decode("utf-8").strip().split("\n")
    dates = {json.loads(line)["date"] for line in lines if line}
    assert "2026-02-15" in dates


@pytest.mark.asyncio
async def test_default_export_service_no_wb(fake_deps: FakeKeywordDeps) -> None:
    """S37 on default ExportService wiring: zero WB API module loads."""
    wb_spy = MagicMock()
    service = ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=_NoOpReader(),  # type: ignore[arg-type]
        funnel_reader=_NoOpReader(),  # type: ignore[arg-type]
        freshness_reader=_NoOpReader(),  # type: ignore[arg-type]
        settings_assembler=MagicMock(),
        keyword_assembler=build_fake_assembler(fake_deps),
    )
    service._settings_assembler.assemble = AsyncMock(  # type: ignore[method-assign, union-attr]
        return_value=_empty_settings_snapshot()
    )
    with patch.dict("sys.modules", {"app.core.mp.wb.api": wb_spy}):
        _ = await service.export_with_scope(
            SHOP_ID, PERIOD, _scope(), generated_at=GENERATED_AT
        )
    wb_spy.assert_not_called()


@pytest.mark.asyncio
async def test_default_export_service_no_writes(fake_deps: FakeKeywordDeps) -> None:
    """S38 on default ExportService: spies on get_clickhouse_client and PG session."""
    service = ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=_NoOpReader(),  # type: ignore[arg-type]
        funnel_reader=_NoOpReader(),  # type: ignore[arg-type]
        freshness_reader=_NoOpReader(),  # type: ignore[arg-type]
        settings_assembler=MagicMock(),
        keyword_assembler=build_fake_assembler(fake_deps),
    )
    service._settings_assembler.assemble = AsyncMock(  # type: ignore[method-assign, union-attr]
        return_value=_empty_settings_snapshot()
    )
    with (
        patch(
            "app.utils.db.session_maker.get_async_session_maker",
            side_effect=AssertionError("PG session must not open on keyword path"),
        ),
        patch(
            "app.utils.click_house.client.get_clickhouse_client",
            side_effect=AssertionError("CH client must not open on keyword path"),
        ),
    ):
        _ = await service.export_with_scope(
            SHOP_ID, PERIOD, _scope(), generated_at=GENERATED_AT
        )

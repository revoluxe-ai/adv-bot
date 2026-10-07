"""S37/S38: default ExportService + default KeywordPerformanceAssembler boundary proof."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.ai_package_v1.domain.enums import DatasetId
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.export.export_service import ExportService
from app.modules.ai_package_v1.keyword_performance.export.keyword_assembler import (
    KeywordPerformanceAssembler,
)
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from tests.unit.ai_package_v1.keyword_performance.boundary_fakes import (
    production_keyword_boundary,
)
from tests.unit.ai_package_v1.keyword_performance.conftest import GENERATED_AT, SHOP_ID

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


def _default_export_service() -> ExportService:
    """ExportService with default KeywordPerformanceAssembler — no keyword injection."""
    settings = MagicMock()
    settings.assemble = AsyncMock(return_value=_empty_settings_snapshot())
    return ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=_NoOpReader(),  # type: ignore[arg-type]
        funnel_reader=_NoOpReader(),  # type: ignore[arg-type]
        freshness_reader=_NoOpReader(),  # type: ignore[arg-type]
        settings_assembler=settings,
    )


@pytest.mark.asyncio
async def test_default_keyword_assembler_no_wb_at_boundary() -> None:
    """S37: default KeywordPerformanceAssembler — zero WB API at production boundary."""
    wb_spy = MagicMock()
    with production_keyword_boundary(), patch.dict(
        "sys.modules", {"app.core.mp.wb.api": wb_spy}
    ):
        assembler = KeywordPerformanceAssembler()
        _ = await assembler.assemble(
            shop_id=SHOP_ID,
            manifest_shop_id="1",
            period=PERIOD,
            generated_at=GENERATED_AT,
        )
    wb_spy.assert_not_called()


@pytest.mark.asyncio
async def test_default_keyword_assembler_no_store_writes_at_boundary() -> None:
    """S38: default KeywordPerformanceAssembler — no PG commit / Redis / CH open bypass."""
    with production_keyword_boundary() as redis_set:
        assembler = KeywordPerformanceAssembler()
        result = await assembler.assemble(
            shop_id=SHOP_ID,
            manifest_shop_id="1",
            period=PERIOD,
            generated_at=GENERATED_AT,
        )
    redis_set.assert_not_called()
    assert any(p.dataset_id == "DATA_MAP" for p in result.payloads)


@pytest.mark.asyncio
async def test_default_export_service_no_wb_at_boundary() -> None:
    """S37: default ExportService() wires default assembler — zero WB calls."""
    wb_spy = MagicMock()
    service = _default_export_service()
    with production_keyword_boundary(), patch.dict(
        "sys.modules", {"app.core.mp.wb.api": wb_spy}
    ):
        export = await service.export_with_scope(
            SHOP_ID, PERIOD, _scope(), generated_at=GENERATED_AT
        )
    wb_spy.assert_not_called()
    assert any(c.dataset_id == DatasetId.KEYWORD_DAILY for c in export.manifest.datasets)


@pytest.mark.asyncio
async def test_default_export_service_no_writes_at_boundary() -> None:
    """S38: default ExportService() — boundary fakes; no Redis control-plane writes."""
    service = _default_export_service()
    with production_keyword_boundary() as redis_set:
        export = await service.export_with_scope(
            SHOP_ID, PERIOD, _scope(), generated_at=GENERATED_AT
        )
    redis_set.assert_not_called()
    assert any(c.dataset_id == DatasetId.KEYWORD_COVERAGE for c in export.manifest.datasets)

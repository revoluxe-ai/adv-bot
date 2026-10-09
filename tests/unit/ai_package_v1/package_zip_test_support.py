"""Shared helpers for PackageZipAssembler contract tests (public imports)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

from app.modules.ai_package_v1.analysis.campaign_reader import (
    EmptyAnalysisCampaignReader,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.export.export_service import ExportService
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from tests.unit.ai_package_v1.conftest import AssemblerFactory
from tests.unit.ai_package_v1.keyword_performance.conftest import (
    FakeKeywordDeps,
    build_fake_assembler,
)

PERIOD = ExportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 7))
SHOP_ID = "1"
GENERATED_AT = "2026-10-05T12:00:00Z"


class NoOpReader:
    """CH reader stub returning empty rows for zip contract tests."""

    async def fetch_rows(self, *args: object, **kwargs: object) -> list[object]:
        return []

    async def max_full_adv_version(self, *args: object, **kwargs: object) -> None:
        return None

    async def max_common_stat_version(self, *args: object, **kwargs: object) -> None:
        return None


def scope_for_shop(*, shop_id: str = SHOP_ID) -> list[ExportScopeAdv]:
    return [
        ExportScopeAdv(
            shop_id=shop_id,
            auto_adv_id=111,
            search_adv_id=222,
            main_nmid=500,
            name="auto",
            active_status="active",
            bot_active=False,
        ),
    ]


def build_export_service_for_zip(
    assembler_factory: AssemblerFactory,
    rows: list[object],
    *,
    keyword_deps: FakeKeywordDeps,
) -> ExportService:
    assembler = assembler_factory(rows)
    keyword = build_fake_assembler(keyword_deps)
    return ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=NoOpReader(),  # type: ignore[arg-type]
        funnel_reader=NoOpReader(),  # type: ignore[arg-type]
        freshness_reader=NoOpReader(),  # type: ignore[arg-type]
        analysis_campaign_reader=EmptyAnalysisCampaignReader(),
        settings_assembler=assembler,
        keyword_assembler=keyword,
    )

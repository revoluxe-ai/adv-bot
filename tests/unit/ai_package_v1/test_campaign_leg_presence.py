"""Контракт: missing physical leg ≠ synthetic merge ≠ нулевая нога.

Канонический случай «оба id есть в источнике» сохраняет отдельные строки.
Отсутствие строк по одной ноге не валит export и не фабрикует нули.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
    CampaignSettingsSnapshotV1,
    CompletenessBlockV1,
)
from app.modules.ai_package_v1.domain.dataset_card import DatasetCard
from app.modules.ai_package_v1.domain.campaign_stat import (
    CampaignStatRow,
    ScopedAdvIds,
    assert_no_synthetic_merge,
    preserve_distinct_adv_ids,
)
from app.modules.ai_package_v1.domain.enums import (
    Coverage,
    DatasetId,
    FamilyStatus,
    ReasonCode,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.settings_enums import (
    SettingsCollectionOutcome,
    SettingsCoverageLevel,
    SettingsFreshnessLevel,
)
from app.modules.ai_package_v1.analysis.campaign_reader import (
    EmptyAnalysisCampaignReader,
)
from app.modules.ai_package_v1.export.export_service import ExportService
from app.modules.ai_package_v1.export.family_status import derive_family_status_from_card
from app.modules.ai_package_v1.export.package_summary import build_package_summary_document
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from tests.unit.ai_package_v1.keyword_performance.conftest import (
    FakeKeywordDeps,
    build_fake_assembler,
    make_daily_raw,
    make_scope_row,
)

pytestmark = pytest.mark.unit

SHOP_ID = "1"
AUTO_ID = 111
SEARCH_ID = 222
SYNTHETIC_ID = 999
PERIOD = ExportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 7))
GENERATED_AT = "2026-10-03T12:00:00Z"


def _row(campaign_id: int, *, day: int = 1, views: int = 4, clicks: int = 1) -> CampaignStatRow:
    return CampaignStatRow(
        shop_id=SHOP_ID,
        campaign_id=campaign_id,
        date=date(2026, 1, day),
        views=views,
        clicks=clicks,
    )


def _scope() -> list[ExportScopeAdv]:
    return [
        ExportScopeAdv(
            shop_id=SHOP_ID,
            auto_adv_id=AUTO_ID,
            search_adv_id=SEARCH_ID,
            main_nmid=500,
            name="complex",
            active_status="active",
            bot_active=False,
        )
    ]


class _FixtureCampaignReader:
    """Отдаёт фикстурные строки как есть, включая id вне PG scope."""

    def __init__(self, rows: list[CampaignStatRow]) -> None:
        self._rows = rows

    async def fetch_rows(
        self,
        shop_id: str,
        adv_ids: Sequence[int],
        period: ExportPeriod,
    ) -> list[CampaignStatRow]:
        _ = adv_ids, period
        return [
            CampaignStatRow(
                shop_id=shop_id,
                campaign_id=row.campaign_id,
                date=row.date,
                views=row.views,
                clicks=row.clicks,
            )
            for row in self._rows
        ]


class _EmptyFunnelReader:
    async def fetch_rows(self, *_args: object, **_kwargs: object) -> list[object]:
        return []


class _NoFreshness:
    async def max_full_adv_version(self, *_args: object, **_kwargs: object) -> None:
        return None

    async def max_common_stat_version(self, *_args: object, **_kwargs: object) -> None:
        return None


def _settings_snapshot() -> CampaignSettingsSnapshotV1:
    return CampaignSettingsSnapshotV1(
        shop_id=SHOP_ID,
        snapshot_assembled_at=datetime(2026, 1, 7, tzinfo=UTC),
        records=(),
        completeness=CompletenessBlockV1(
            collection_outcome=SettingsCollectionOutcome.NO_DATA,
            coverage=SettingsCoverageLevel.UNKNOWN,
            freshness=SettingsFreshnessLevel.UNKNOWN,
        ),
    )


def _service(rows: list[CampaignStatRow]) -> ExportService:
    settings = MagicMock()
    settings.assemble = AsyncMock(return_value=_settings_snapshot())
    deps = FakeKeywordDeps(
        scope_rows=[
            make_scope_row(
                shop_id=SHOP_ID,
                auto_adv_id=AUTO_ID,
                search_adv_id=SEARCH_ID,
            )
        ],
        daily_raw=[make_daily_raw(adv_id=AUTO_ID)],
    )
    return ExportService(
        scope_reader=AsyncMock(),
        campaign_reader=_FixtureCampaignReader(rows),  # type: ignore[arg-type]
        funnel_reader=_EmptyFunnelReader(),  # type: ignore[arg-type]
        freshness_reader=_NoFreshness(),  # type: ignore[arg-type]
        analysis_campaign_reader=EmptyAnalysisCampaignReader(),
        settings_assembler=settings,
        keyword_assembler=build_fake_assembler(deps),
    )


def _campaign_csv_ids(content: bytes) -> list[int]:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    return [int(row["campaign_id"]) for row in reader]


async def _export(
    rows: list[CampaignStatRow],
) -> tuple[list[int], DatasetCard, dict[str, Any]]:
    result = await _service(rows).export_with_scope(
        SHOP_ID,
        PERIOD,
        _scope(),
        generated_at=GENERATED_AT,
    )
    payload = next(
        item for item in result.payloads if item.dataset_id == "campaign_full_stat"
    )
    card = next(
        item
        for item in result.manifest.datasets
        if item.dataset_id == DatasetId.CAMPAIGN_FULL_STAT
    )
    summary = build_package_summary_document(result)
    families: dict[str, dict[str, Any]] = {}
    for item in cast(list[object], summary["families"]):
        if not isinstance(item, dict):
            continue
        row = cast(dict[str, Any], item)
        families[str(row["family_id"])] = row
    return _campaign_csv_ids(payload.content), card, families["campaign_advertising"]


def test_assert_no_synthetic_merge_allows_missing_leg() -> None:
    """Одна физическая нога и пустой срез не являются synthetic merge."""
    assert_no_synthetic_merge([_row(AUTO_ID), _row(AUTO_ID, day=2)], AUTO_ID, SEARCH_ID)
    assert_no_synthetic_merge([_row(SEARCH_ID)], AUTO_ID, SEARCH_ID)
    assert_no_synthetic_merge([], AUTO_ID, SEARCH_ID)
    assert_no_synthetic_merge([_row(AUTO_ID), _row(SEARCH_ID)], AUTO_ID, SEARCH_ID)


def test_assert_no_synthetic_merge_rejects_unexpected_id() -> None:
    """Id вне {Auto, Search} отклоняется даже рядом с физическими ногами."""
    with pytest.raises(ValueError, match="synthetic campaign_id 999"):
        assert_no_synthetic_merge([_row(SYNTHETIC_ID)], AUTO_ID, SEARCH_ID)
    with pytest.raises(ValueError, match="synthetic campaign_id 999"):
        assert_no_synthetic_merge(
            [_row(AUTO_ID), _row(SEARCH_ID), _row(SYNTHETIC_ID)],
            AUTO_ID,
            SEARCH_ID,
        )


def test_preserve_distinct_adv_ids_keeps_single_leg_rows() -> None:
    """Несколько дат одной ноги не считаются схлопыванием Auto и Search."""
    rows = [_row(AUTO_ID, day=1, views=3), _row(AUTO_ID, day=2, views=8)]
    kept = preserve_distinct_adv_ids(
        rows,
        ScopedAdvIds(auto_adv_id=AUTO_ID, auction_adv_id=SEARCH_ID),
    )
    assert [row.campaign_id for row in kept] == [AUTO_ID, AUTO_ID]
    assert SEARCH_ID not in {row.campaign_id for row in kept}


@pytest.mark.asyncio
async def test_both_physical_legs_are_preserved() -> None:
    """Строки A и K остаются отдельными campaign_id."""
    ids, card, family = await _export([_row(AUTO_ID, views=5), _row(SEARCH_ID, views=6)])
    assert set(ids) == {AUTO_ID, SEARCH_ID}
    assert card.coverage != Coverage.FULL
    assert derive_family_status_from_card(card) != FamilyStatus.COMPLETE
    assert family["family_status"] != str(FamilyStatus.COMPLETE)
    assert ReasonCode.PARTIAL_COLLECTION not in card.reason_codes


@pytest.mark.asyncio
async def test_auto_only_exports_without_fake_search_row() -> None:
    """Нет строк Search — export идёт дальше, нулевая Search-нога не создаётся."""
    ids, card, family = await _export(
        [_row(AUTO_ID, day=1, views=5), _row(AUTO_ID, day=2, views=9)]
    )
    assert ids == [AUTO_ID, AUTO_ID]
    assert SEARCH_ID not in ids
    assert card.coverage == Coverage.PARTIAL
    assert card.coverage != Coverage.FULL
    assert ReasonCode.PARTIAL_COLLECTION in card.reason_codes
    assert derive_family_status_from_card(card) == FamilyStatus.PARTIAL
    assert family["family_status"] == str(FamilyStatus.PARTIAL)
    assert "PARTIAL_COLLECTION" in family["status_reason_codes"]


@pytest.mark.asyncio
async def test_search_only_exports_without_fake_auto_row() -> None:
    """Нет строк Auto — export идёт дальше, нулевая Auto-нога не создаётся."""
    ids, card, family = await _export([_row(SEARCH_ID, views=7)])
    assert ids == [SEARCH_ID]
    assert AUTO_ID not in ids
    assert card.coverage == Coverage.PARTIAL
    assert ReasonCode.PARTIAL_COLLECTION in card.reason_codes
    assert derive_family_status_from_card(card) != FamilyStatus.COMPLETE
    assert family["family_status"] != str(FamilyStatus.COMPLETE)


@pytest.mark.asyncio
async def test_both_legs_missing_is_fail_closed_without_zero_rows() -> None:
    """Пустой срез не фабрикует нули и не объявляет FULL/COMPLETE."""
    ids, card, family = await _export([])
    assert ids == []
    assert card.row_count == 0
    assert card.coverage != Coverage.FULL
    assert card.coverage == Coverage.UNKNOWN
    assert ReasonCode.NO_DATA in card.reason_codes
    assert derive_family_status_from_card(card) != FamilyStatus.COMPLETE
    assert family["family_status"] != str(FamilyStatus.COMPLETE)


@pytest.mark.asyncio
async def test_unexpected_synthetic_campaign_id_is_rejected() -> None:
    """Чужой campaign_id не подменяет физические Auto/Search."""
    with pytest.raises(ValueError, match="synthetic campaign_id 999"):
        await _export([_row(SYNTHETIC_ID, views=1)])
    with pytest.raises(ValueError, match="synthetic campaign_id 999"):
        await _export([_row(AUTO_ID), _row(SYNTHETIC_ID)])

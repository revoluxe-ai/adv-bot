"""Fixtures and fake readers for keyword performance unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import pytest

from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.export.keyword_assembler import (
    KeywordAssemblyResult,
    KeywordPerformanceAssembler,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
    BidDecisionAvailability,
    BidDecisionSourceStatus,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_reader import (
    RawBidDecisionRow,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
    SourceBounds,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_daily_reader import (
    RawDailySnapshotRow,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_position_reader import (
    RawPositionRow,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_keyword_policy_reader import (
    CampaignPolicySnapshot,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_keyword_query_policy_reader import (
    KeywordQueryPolicySnapshot,
)
from app.modules.ai_package_v1.keyword_performance.scope.dto import KeywordScopeRow


GENERATED_AT = "2026-10-03T12:00:00Z"
PERIOD = ExportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 7))
SHOP_ID = "1"
MANIFEST_SHOP_ID = "1"


@dataclass
class FakeKeywordDeps:
    """In-memory fake CH/PG/Redis deps for assembler tests."""

    scope_rows: list[KeywordScopeRow] = field(default_factory=lambda: list[KeywordScopeRow]())
    overlap: dict[int, list[tuple[str, int]]] = field(
        default_factory=lambda: dict[int, list[tuple[str, int]]]()
    )
    daily_raw: list[RawDailySnapshotRow] = field(
        default_factory=lambda: list[RawDailySnapshotRow]()
    )
    position_raw: list[RawPositionRow] = field(
        default_factory=lambda: list[RawPositionRow]()
    )
    bid_decision_raw: list[RawBidDecisionRow] = field(
        default_factory=lambda: list[RawBidDecisionRow]()
    )
    bid_decision_timeline: list[RawBidDecisionRow] = field(
        default_factory=lambda: list[RawBidDecisionRow]()
    )
    policies: dict[int, CampaignPolicySnapshot] = field(
        default_factory=lambda: dict[int, CampaignPolicySnapshot]()
    )
    query_policies: dict[tuple[int, str], KeywordQueryPolicySnapshot] = field(
        default_factory=lambda: dict[tuple[int, str], KeywordQueryPolicySnapshot]()
    )
    daily_bounds: SourceBounds = field(
        default_factory=lambda: SourceBounds(date(2026, 1, 1), date(2026, 1, 5))
    )
    position_bounds: SourceBounds = field(
        default_factory=lambda: SourceBounds(date(2026, 1, 1), date(2026, 1, 5))
    )
    rebound_unavailable: bool = False
    bid_decision_status: BidDecisionSourceStatus = BidDecisionSourceStatus.UNSUPPORTED
    bid_decision_probe_result: BidDecisionAvailability | None = None


class FakeScopeReader:
    def __init__(self, deps: FakeKeywordDeps) -> None:
        self._deps = deps

    async def load_keyword_scope(
        self, shop_id: str
    ) -> tuple[list[KeywordScopeRow], bool]:
        rows = [r for r in self._deps.scope_rows if r.shop_id == shop_id]
        return rows, self._deps.rebound_unavailable

    async def load_global_adv_id_overlap(
        self, adv_ids: frozenset[int], session: object = None
    ) -> dict[int, list[tuple[str, int]]]:
        return {
            adv_id: owners
            for adv_id, owners in self._deps.overlap.items()
            if adv_id in adv_ids
        }


class FakeBoundsReader:
    def __init__(self, deps: FakeKeywordDeps) -> None:
        self._deps = deps

    async def fetch_daily_bounds(
        self, adv_ids: frozenset[int], cutoff: PackageCutoff
    ) -> SourceBounds:
        return self._deps.daily_bounds

    async def fetch_position_bounds(
        self, nmids: frozenset[int], cutoff: PackageCutoff
    ) -> SourceBounds:
        return self._deps.position_bounds


class FakeDailyReader:
    def __init__(self, deps: FakeKeywordDeps) -> None:
        self._deps = deps

    @property
    def query_text(self) -> str:
        return "default_db.clusters_adv_stats"

    async def fetch_rows(
        self,
        adv_ids: frozenset[int],
        first_available: date,
        cutoff: PackageCutoff,
    ) -> list[RawDailySnapshotRow]:
        return [
            r
            for r in self._deps.daily_raw
            if r.adv_id in adv_ids and r.stat_date >= first_available
        ]


class FakePositionReader:
    def __init__(self, deps: FakeKeywordDeps) -> None:
        self._deps = deps

    @property
    def query_text(self) -> str:
        return "default_db.keyword_position_from_api"

    async def fetch_rows(
        self,
        nmids: frozenset[int],
        position_first_available: date,
        cutoff: PackageCutoff,
    ) -> list[RawPositionRow]:
        return [
            r
            for r in self._deps.position_raw
            if r.nmid in nmids and r.stat_date >= position_first_available
        ]


class FakeBidProbe:
    def __init__(self, deps: FakeKeywordDeps) -> None:
        self._deps = deps

    async def probe(
        self, adv_ids: frozenset[int], cutoff: PackageCutoff | None = None
    ) -> BidDecisionAvailability:
        if self._deps.bid_decision_probe_result is not None:
            return self._deps.bid_decision_probe_result
        return BidDecisionAvailability(
            status=self._deps.bid_decision_status,
            present_columns=frozenset(
                {
                    "adv_id",
                    "nmid",
                    "norm_query",
                    "cpm_curr",
                    "decision_time",
                    "version",
                    "final_bid",
                    "stats_max_timestamp",
                    "decision_source",
                }
            ),
        )

    async def is_available(
        self, adv_ids: frozenset[int], cutoff: PackageCutoff | None = None
    ) -> bool:
        return self._deps.bid_decision_status == BidDecisionSourceStatus.AVAILABLE


class FakeBidDecisionReader:
    def __init__(self, deps: FakeKeywordDeps) -> None:
        self._deps = deps

    async def fetch_latest_decisions(
        self,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> list[RawBidDecisionRow]:
        return [r for r in self._deps.bid_decision_raw if r.adv_id in adv_ids]

    async def fetch_timeline(
        self,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> list[RawBidDecisionRow]:
        timeline = self._deps.bid_decision_timeline or self._deps.bid_decision_raw
        return [r for r in timeline if r.adv_id in adv_ids]


class FakePolicyReader:
    def __init__(self, deps: FakeKeywordDeps) -> None:
        self._deps = deps

    async def load_policies(
        self, shop_id: str, adv_setting_ids: frozenset[int]
    ) -> dict[int, CampaignPolicySnapshot]:
        return {
            adv_id: policy
            for adv_id, policy in self._deps.policies.items()
            if adv_id in adv_setting_ids
        }


class FakeQueryPolicyReader:
    def __init__(self, deps: FakeKeywordDeps) -> None:
        self._deps = deps

    async def load_query_policies(
        self, shop_id: str, adv_setting_ids: frozenset[int]
    ) -> dict[tuple[int, str], KeywordQueryPolicySnapshot]:
        return {
            key: policy
            for key, policy in self._deps.query_policies.items()
            if key[0] in adv_setting_ids
        }


def make_scope_row(
    *,
    shop_id: str = SHOP_ID,
    adv_setting_id: int = 101,
    auto_adv_id: int = 111,
    search_adv_id: int | None = 222,
    main_nmid: int = 500,
    rebound_auto: frozenset[int] | None = None,
    rebound_search: frozenset[int] | None = None,
) -> KeywordScopeRow:
    return KeywordScopeRow(
        shop_id=shop_id,
        adv_setting_id=adv_setting_id,
        auto_adv_id=auto_adv_id,
        search_adv_id=search_adv_id,
        main_nmid=main_nmid,
        rebound_auto_adv_ids=rebound_auto or frozenset(),
        rebound_search_adv_ids=rebound_search or frozenset(),
    )


def make_daily_raw(
    *,
    adv_id: int = 111,
    nmid: int = 500,
    norm_query: str = "query",
    stat_date: date = date(2026, 1, 3),
    views: int | None = 100,
    clicks: int | None = 10,
    spend: float | None = 50.0,
    avr_pos: float | None = 5.0,
    variants: int = 1,
    last_snapshot_ts: datetime | None = datetime(2026, 1, 3, 10, 0, 0),
) -> RawDailySnapshotRow:
    return RawDailySnapshotRow(
        adv_id=adv_id,
        nmid=nmid,
        norm_query=norm_query,
        stat_date=stat_date,
        last_snapshot_ts=last_snapshot_ts,
        snapshot_variants_at_max_ts=variants,
        views=views if variants == 1 else None,
        clicks=clicks if variants == 1 else None,
        add_to_cart=5 if variants == 1 else None,
        orders=2 if variants == 1 else None,
        spend=spend if variants == 1 else None,
        cpm=100.0 if variants == 1 else None,
        cpc=5.0 if variants == 1 else None,
        avr_pos=avr_pos if variants == 1 else None,
        ctr=0.1 if variants == 1 else None,
    )


def make_bid_decision_raw(
    *,
    adv_id: int = 111,
    nmid: int = 500,
    norm_query: str = "query",
    cpm_curr: float = 155.0,
    variants: int = 1,
    decision_time: datetime | None = None,
    stats_max_timestamp: datetime | None = None,
) -> RawBidDecisionRow:
    default_decision_time = datetime(2026, 1, 3, 11, 0, 0)
    default_stats_ts = datetime(2026, 1, 3, 10, 30, 0)
    return RawBidDecisionRow(
        adv_id=adv_id,
        nmid=nmid,
        norm_query=norm_query,
        cpm_curr=cpm_curr if variants == 1 else None,
        final_bid=cpm_curr if variants == 1 else None,
        decision_time=(
            decision_time if decision_time is not None else default_decision_time
        )
        if variants == 1
        else None,
        stats_max_timestamp=(
            stats_max_timestamp
            if stats_max_timestamp is not None
            else default_stats_ts
        )
        if variants == 1
        else None,
        decision_source="bidder" if variants == 1 else None,
        version=1,
        tuple_variants_at_max_version=variants,
    )


def make_position_raw(
    *,
    nmid: int = 500,
    text: str = "query",
    stat_date: date = date(2026, 1, 3),
    avr_position: float | None = 3.5,
    version: int = 1_700_000_000_000,
    variants: int = 1,
) -> RawPositionRow:
    return RawPositionRow(
        nmid=nmid,
        text=text,
        stat_date=stat_date,
        version=version,
        tuple_variants_at_max_version=variants,
        avr_position=avr_position if variants == 1 else None,
        total_views=100 if variants == 1 else None,
        orders=1 if variants == 1 else None,
    )


def build_fake_assembler(deps: FakeKeywordDeps) -> KeywordPerformanceAssembler:
    return KeywordPerformanceAssembler(
        scope_reader=FakeScopeReader(deps),
        bounds_reader=FakeBoundsReader(deps),
        daily_reader=FakeDailyReader(deps),
        position_reader=FakePositionReader(deps),
        bid_decision_probe=FakeBidProbe(deps),
        bid_decision_reader=FakeBidDecisionReader(deps),
        policy_reader=FakePolicyReader(deps),
        query_policy_reader=FakeQueryPolicyReader(deps),
    )


class NoOpKeywordAssembler:
    """Empty keyword assembly for legacy ExportService integration tests."""

    async def assemble(
        self,
        *,
        shop_id: str,
        manifest_shop_id: str,
        period: ExportPeriod,
        generated_at: str,
    ) -> KeywordAssemblyResult:
        from app.modules.ai_package_v1.domain.manifest import DomainPayload
        from app.modules.ai_package_v1.keyword_performance.domain.coverage_assembler import (
            build_coverage_json,
        )
        from app.modules.ai_package_v1.keyword_performance.domain.cutoff import (
            PackageCutoff,
        )
        from app.modules.ai_package_v1.keyword_performance.domain.data_map_builder import (
            build_data_map,
        )
        from app.modules.ai_package_v1.keyword_performance.export.dataset_cards import (
            COVERAGE_LOGICAL,
            DATA_MAP_LOGICAL,
            KEYWORD_CHANGES_LOGICAL,
            KEYWORD_CURRENT_LOGICAL,
            KEYWORD_DAILY_LOGICAL,
            KEYWORD_DECISIONS_LOGICAL,
            KEYWORD_POSITIONS_LOGICAL,
            KEYWORD_POSITION_CURRENT_LOGICAL,
            KEYWORD_POSITION_WINDOWS_LOGICAL,
            KEYWORD_WINDOWS_LOGICAL,
            build_coverage_card,
            build_data_map_card,
            build_keyword_changes_card,
            build_keyword_current_card,
            build_keyword_daily_card,
            build_keyword_decisions_card,
            build_keyword_position_current_card,
            build_keyword_position_windows_card,
            build_keyword_positions_card,
            build_keyword_windows_card,
        )
        from app.modules.ai_package_v1.keyword_performance.export.payload_encode import (
            encode_json_document,
        )
        from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
            BidDecisionAvailability,
            BidDecisionSourceStatus,
        )
        from app.modules.ai_package_v1.keyword_performance.scope.dto import (
            KeywordExportScope,
        )

        cutoff = PackageCutoff.from_generated_at(generated_at)
        empty_scope = KeywordExportScope(
            rows=(),
            assignments=(),
            all_adv_ids=frozenset(),
            all_nmids=frozenset(),
            reason_codes=frozenset({"NO_DATA"}),
        )
        data_map = build_data_map(
            cutoff=cutoff,
            daily_first=None,
            daily_last=None,
            position_first=None,
            position_last=None,
            export_period_note="noop test assembler",
        )
        coverage = build_coverage_json(
            scope=empty_scope,
            cutoff=cutoff,
            daily_first=None,
            daily_last=None,
            position_first=None,
            position_last=None,
            daily_rows=[],
            position_rows=[],
            bid_decision=BidDecisionAvailability(
                status=BidDecisionSourceStatus.UNSUPPORTED
            ),
            reason_codes=frozenset({"NO_DATA"}),
        )
        payloads = (
            DomainPayload(KEYWORD_DAILY_LOGICAL, "keyword_daily", b""),
            DomainPayload(KEYWORD_WINDOWS_LOGICAL, "keyword_windows", b""),
            DomainPayload(KEYWORD_CURRENT_LOGICAL, "keyword_current_state", b""),
            DomainPayload(KEYWORD_CHANGES_LOGICAL, "keyword_changes", b""),
            DomainPayload(KEYWORD_POSITIONS_LOGICAL, "keyword_positions", b""),
            DomainPayload(KEYWORD_POSITION_WINDOWS_LOGICAL, "keyword_position_windows", b""),
            DomainPayload(KEYWORD_POSITION_CURRENT_LOGICAL, "keyword_position_current", b""),
            DomainPayload(KEYWORD_DECISIONS_LOGICAL, "keyword_decisions", b""),
            DomainPayload(DATA_MAP_LOGICAL, "DATA_MAP", encode_json_document(data_map)),
            DomainPayload(
                COVERAGE_LOGICAL, "keyword_coverage", encode_json_document(coverage)
            ),
        )
        cards = (
            build_keyword_daily_card(period, row_count=0),
            build_keyword_windows_card(period, row_count=0),
            build_keyword_current_card(period, row_count=0),
            build_keyword_changes_card(period, row_count=0),
            build_keyword_positions_card(period, row_count=0),
            build_keyword_position_windows_card(period, row_count=0),
            build_keyword_position_current_card(period, row_count=0),
            build_keyword_decisions_card(period, row_count=0),
            build_data_map_card(period),
            build_coverage_card(period),
        )
        return KeywordAssemblyResult(payloads=payloads, cards=cards)


@pytest.fixture
def fake_deps() -> FakeKeywordDeps:
    row = make_scope_row()
    deps = FakeKeywordDeps(
        scope_rows=[row],
        overlap={
            111: [(SHOP_ID, 101)],
            222: [(SHOP_ID, 101)],
        },
        daily_raw=[make_daily_raw()],
    )
    return deps

"""KeywordPerformanceAssembler: orchestrates scope → CH read → windows → payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.domain.manifest import DomainPayload
from app.modules.ai_package_v1.keyword_performance.domain.coverage_assembler import (
    build_coverage_json,
)
from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.domain.cutoff_guard import (
    effective_last_available,
    filter_bid_decision_rows,
    filter_daily_rows,
    filter_position_rows,
)
from app.modules.ai_package_v1.keyword_performance.domain.data_map_builder import (
    build_data_map,
)
from app.modules.ai_package_v1.keyword_performance.export.current_state import (
    compute_current_state,
)
from app.modules.ai_package_v1.keyword_performance.export.daily_assembler import (
    assemble_daily_rows,
)
from app.modules.ai_package_v1.keyword_performance.export.decision_assembler import (
    assemble_decision_rows,
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
    encode_jsonl,
)
from app.modules.ai_package_v1.keyword_performance.export.position_assembler import (
    assemble_position_rows,
)
from app.modules.ai_package_v1.keyword_performance.guards.forbidden_sources import (
    assert_forbidden_sources_not_loaded,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
    BidDecisionAvailability,
    BidDecisionSourceStatus,
    ChBidDecisionProbe,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_reader import (
    ChBidDecisionReader,
    RawBidDecisionRow,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader import (
    ChKeywordBoundsReader,
    SourceBounds,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_daily_reader import (
    ChKeywordDailyReader,
    RawDailySnapshotRow,
)
from app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_position_reader import (
    ChKeywordPositionReader,
    RawPositionRow,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_keyword_policy_reader import (
    PgKeywordPolicyReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.pg_keyword_query_policy_reader import (
    PgKeywordQueryPolicyReader,
)
from app.modules.ai_package_v1.keyword_performance.readers.reader_protocols import (
    BidDecisionProbeProtocol,
    BidDecisionReaderProtocol,
    BoundsReaderProtocol,
    DailyReaderProtocol,
    KeywordPolicyReaderProtocol,
    KeywordQueryPolicyReaderProtocol,
    PositionReaderProtocol,
    ScopeReaderProtocol,
)
from app.modules.ai_package_v1.keyword_performance.scope.adv_id_collector import (
    collect_keyword_export_scope,
)
from app.modules.ai_package_v1.keyword_performance.scope.keyword_export_scope_reader import (
    KeywordExportScopeReader,
)
from app.modules.ai_package_v1.keyword_performance.windows.engine import (
    compute_changes,
    compute_windows,
)
from app.modules.ai_package_v1.keyword_performance.windows.position_engine import (
    compute_position_latest,
    compute_position_windows,
)
from app.modules.ai_package_v1.domain.dataset_card import DatasetCard


class KeywordAssemblerProtocol(Protocol):
    """Seam for ExportService keyword pipeline injection."""

    async def assemble(
        self,
        *,
        shop_id: str,
        manifest_shop_id: str,
        period: ExportPeriod,
        generated_at: str,
    ) -> KeywordAssemblyResult:
        ...


@dataclass(frozen=True, slots=True)
class KeywordAssemblyResult:
    """Keyword payloads + manifest cards."""

    payloads: tuple[DomainPayload, ...]
    cards: tuple[DatasetCard, ...]


def _decisions_by_key(
    rows: list[RawBidDecisionRow],
) -> dict[tuple[int, int, str], RawBidDecisionRow]:
    """Index latest decisions; ambiguous rows kept with null metrics."""
    result: dict[tuple[int, int, str], RawBidDecisionRow] = {}
    for row in rows:
        key = (row.adv_id, row.nmid, row.norm_query)
        existing = result.get(key)
        if existing is None:
            result[key] = row
            continue
        if row.tuple_variants_at_max_version > 1:
            result[key] = row
    return result


class KeywordPerformanceAssembler:
    """Read-only keyword pipeline L3–L7 for ExportService."""

    def __init__(
        self,
        *,
        scope_reader: ScopeReaderProtocol | None = None,
        bounds_reader: BoundsReaderProtocol | None = None,
        daily_reader: DailyReaderProtocol | None = None,
        position_reader: PositionReaderProtocol | None = None,
        bid_decision_probe: BidDecisionProbeProtocol | None = None,
        bid_decision_reader: BidDecisionReaderProtocol | None = None,
        policy_reader: KeywordPolicyReaderProtocol | None = None,
        query_policy_reader: KeywordQueryPolicyReaderProtocol | None = None,
    ) -> None:
        self._scope_reader = scope_reader or KeywordExportScopeReader()
        self._bounds_reader = bounds_reader or ChKeywordBoundsReader()
        self._daily_reader = daily_reader or ChKeywordDailyReader()
        self._position_reader = position_reader or ChKeywordPositionReader()
        self._bid_decision_probe = bid_decision_probe or ChBidDecisionProbe()
        self._bid_decision_reader = bid_decision_reader or ChBidDecisionReader()
        self._policy_reader = policy_reader or PgKeywordPolicyReader()
        self._query_policy_reader = query_policy_reader or PgKeywordQueryPolicyReader()

    async def assemble(
        self,
        *,
        shop_id: str,
        manifest_shop_id: str,
        period: ExportPeriod,
        generated_at: str,
    ) -> KeywordAssemblyResult:
        """Run full keyword export pipeline."""
        assert_forbidden_sources_not_loaded()
        cutoff = PackageCutoff.from_generated_at(generated_at)
        scope_rows, rebound_unavailable = await self._scope_reader.load_keyword_scope(
            shop_id
        )
        all_adv: frozenset[int] = frozenset()
        for row in scope_rows:
            all_adv = all_adv | row.all_adv_ids
        overlap = await self._scope_reader.load_global_adv_id_overlap(all_adv)
        scope = collect_keyword_export_scope(
            scope_rows, overlap, rebound_unavailable=rebound_unavailable
        )
        trusted_adv_ids = frozenset(
            a.adv_id
            for a in scope.assignments
            if not a.foreign_shop and not a.ambiguous_ownership
        )
        trusted_nmids = scope.all_nmids

        bid_availability = await self._probe_bid_decision_log(trusted_adv_ids, cutoff)

        daily_bounds_raw = await self._bounds_reader.fetch_daily_bounds(
            trusted_adv_ids, cutoff
        )
        position_bounds_raw = await self._bounds_reader.fetch_position_bounds(
            trusted_nmids, cutoff
        )

        first_available = daily_bounds_raw.first_available or cutoff.package_cutoff_date
        raw_daily: list[RawDailySnapshotRow] = []
        if trusted_adv_ids and daily_bounds_raw.first_available is not None:
            fetched_daily = await self._daily_reader.fetch_rows(
                trusted_adv_ids, first_available, cutoff
            )
            raw_daily = filter_daily_rows(fetched_daily, cutoff)
        daily_rows = assemble_daily_rows(
            raw_daily, manifest_shop_id=manifest_shop_id, scope=scope
        )
        daily_last = effective_last_available(
            ch_last=daily_bounds_raw.last_available,
            observed_dates=tuple(r.stat_date for r in raw_daily),
            cutoff=cutoff,
        )
        daily_bounds = SourceBounds(
            first_available=daily_bounds_raw.first_available,
            last_available=daily_last,
        )

        raw_positions: list[RawPositionRow] = []
        if trusted_nmids and position_bounds_raw.first_available is not None:
            fetched_positions = await self._position_reader.fetch_rows(
                trusted_nmids,
                position_bounds_raw.first_available,
                cutoff,
            )
            raw_positions = filter_position_rows(fetched_positions, cutoff)
        position_last = effective_last_available(
            ch_last=position_bounds_raw.last_available,
            observed_dates=tuple(r.stat_date for r in raw_positions),
            cutoff=cutoff,
        )
        position_bounds = SourceBounds(
            first_available=position_bounds_raw.first_available,
            last_available=position_last,
        )
        daily_norm_queries = frozenset(
            (r.nmid, r.date, r.norm_query) for r in daily_rows
        )
        position_rows = assemble_position_rows(
            raw_positions,
            manifest_shop_id=manifest_shop_id,
            daily_norm_queries=daily_norm_queries,
        )
        position_windows = compute_position_windows(
            position_rows,
            cutoff,
            position_bounds.first_available,
            position_bounds.last_available,
        )
        position_latest = compute_position_latest(position_rows)

        windows = compute_windows(
            daily_rows,
            cutoff,
            daily_bounds.first_available,
            daily_bounds.last_available,
        )
        changes = compute_changes(windows, daily_rows, cutoff)

        decisions: dict[tuple[int, int, str], RawBidDecisionRow] = {}
        decision_timeline_rows: list[RawBidDecisionRow] = []
        if bid_availability.status in (
            BidDecisionSourceStatus.AVAILABLE,
            BidDecisionSourceStatus.AVAILABLE_EMPTY,
        ):
            if bid_availability.status == BidDecisionSourceStatus.AVAILABLE:
                decision_rows = filter_bid_decision_rows(
                    await self._bid_decision_reader.fetch_latest_decisions(
                        trusted_adv_ids,
                        cutoff,
                    ),
                    cutoff,
                )
                decisions = _decisions_by_key(decision_rows)
                decision_timeline_rows = filter_bid_decision_rows(
                    await self._bid_decision_reader.fetch_timeline(
                        trusted_adv_ids, cutoff
                    ),
                    cutoff,
                )
        decision_rows_export = assemble_decision_rows(
            decision_timeline_rows,
            manifest_shop_id=manifest_shop_id,
        )

        active_setting_ids = frozenset(
            a.adv_setting_id
            for a in scope.assignments
            if not a.foreign_shop
            and not a.ambiguous_ownership
            and a.leg_role in ("AUTO", "SEARCH")
        )
        campaign_policies = await self._policy_reader.load_policies(
            shop_id, active_setting_ids
        )
        query_policies = await self._query_policy_reader.load_query_policies(
            shop_id, active_setting_ids
        )
        current = compute_current_state(
            daily_rows,
            cutoff=cutoff,
            decisions=decisions,
            campaign_policies=campaign_policies,
            query_policies=query_policies,
        )

        reason_codes = set(scope.reason_codes)
        if bid_availability.status == BidDecisionSourceStatus.UNSUPPORTED:
            reason_codes.add("UNSUPPORTED")
        elif bid_availability.status == BidDecisionSourceStatus.FAILED:
            reason_codes.add("SOURCE_ERROR")
        if trusted_nmids and position_bounds.first_available is None:
            reason_codes.add("POSITION_SOURCE_UNAVAILABLE")

        data_map = build_data_map(
            cutoff=cutoff,
            daily_first=daily_bounds.first_available,
            daily_last=daily_bounds.last_available,
            position_first=position_bounds.first_available,
            position_last=position_bounds.last_available,
            export_period_note=(
                f"manifest.period {period.start.isoformat()}..{period.end.isoformat()} "
                "applies to legacy datasets only; keyword history uses keyword_history_bounds"
            ),
        )
        coverage = build_coverage_json(
            scope=scope,
            cutoff=cutoff,
            daily_first=daily_bounds.first_available,
            daily_last=daily_bounds.last_available,
            position_first=position_bounds.first_available,
            position_last=position_bounds.last_available,
            daily_rows=daily_rows,
            position_rows=position_rows,
            bid_decision=bid_availability,
            reason_codes=frozenset(reason_codes),
        )

        payloads = (
            DomainPayload(
                logical_name=KEYWORD_DAILY_LOGICAL,
                dataset_id="keyword_daily",
                content=encode_jsonl(daily_rows),
            ),
            DomainPayload(
                logical_name=KEYWORD_WINDOWS_LOGICAL,
                dataset_id="keyword_windows",
                content=encode_jsonl(windows),
            ),
            DomainPayload(
                logical_name=KEYWORD_CURRENT_LOGICAL,
                dataset_id="keyword_current_state",
                content=encode_jsonl(current),
            ),
            DomainPayload(
                logical_name=KEYWORD_CHANGES_LOGICAL,
                dataset_id="keyword_changes",
                content=encode_jsonl(changes),
            ),
            DomainPayload(
                logical_name=KEYWORD_POSITIONS_LOGICAL,
                dataset_id="keyword_positions",
                content=encode_jsonl(position_rows),
            ),
            DomainPayload(
                logical_name=KEYWORD_POSITION_WINDOWS_LOGICAL,
                dataset_id="keyword_position_windows",
                content=encode_jsonl(position_windows),
            ),
            DomainPayload(
                logical_name=KEYWORD_POSITION_CURRENT_LOGICAL,
                dataset_id="keyword_position_current",
                content=encode_jsonl(position_latest),
            ),
            DomainPayload(
                logical_name=KEYWORD_DECISIONS_LOGICAL,
                dataset_id="keyword_decisions",
                content=encode_jsonl(decision_rows_export),
            ),
            DomainPayload(
                logical_name=DATA_MAP_LOGICAL,
                dataset_id="DATA_MAP",
                content=encode_json_document(data_map),
            ),
            DomainPayload(
                logical_name=COVERAGE_LOGICAL,
                dataset_id="keyword_coverage",
                content=encode_json_document(coverage),
            ),
        )
        cards = (
            build_keyword_daily_card(period, row_count=len(daily_rows)),
            build_keyword_windows_card(period, row_count=len(windows)),
            build_keyword_current_card(period, row_count=len(current)),
            build_keyword_changes_card(period, row_count=len(changes)),
            build_keyword_positions_card(period, row_count=len(position_rows)),
            build_keyword_position_windows_card(
                period, row_count=len(position_windows)
            ),
            build_keyword_position_current_card(period, row_count=len(position_latest)),
            build_keyword_decisions_card(period, row_count=len(decision_rows_export)),
            build_data_map_card(period),
            build_coverage_card(period),
        )
        return KeywordAssemblyResult(payloads=payloads, cards=cards)

    async def _probe_bid_decision_log(
        self, adv_ids: frozenset[int], cutoff: PackageCutoff
    ) -> BidDecisionAvailability:
        """Read-only availability probe via injected or default CH reader."""
        return await self._bid_decision_probe.probe(adv_ids, cutoff)

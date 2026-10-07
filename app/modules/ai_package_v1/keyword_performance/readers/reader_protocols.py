"""Protocol seams for keyword performance assembler dependency injection."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from app.modules.ai_package_v1.keyword_performance.domain.cutoff import PackageCutoff
from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
    BidDecisionAvailability,
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


class ScopeReaderProtocol(Protocol):
    """Read-only keyword export scope from PG inventory + rebound Redis."""

    async def load_keyword_scope(
        self, shop_id: str
    ) -> tuple[list[KeywordScopeRow], bool]:
        ...

    async def load_global_adv_id_overlap(
        self,
        adv_ids: frozenset[int],
        session: object = None,
    ) -> dict[int, list[tuple[str, int]]]:
        ...


class BoundsReaderProtocol(Protocol):
    """CH bounds probes for daily and position sources."""

    async def fetch_daily_bounds(
        self, adv_ids: frozenset[int], cutoff: PackageCutoff
    ) -> SourceBounds:
        ...

    async def fetch_position_bounds(
        self, nmids: frozenset[int], cutoff: PackageCutoff
    ) -> SourceBounds:
        ...


class DailyReaderProtocol(Protocol):
    """Bounded daily fact fetch from clusters_adv_stats."""

    @property
    def query_text(self) -> str:
        ...

    async def fetch_rows(
        self,
        adv_ids: frozenset[int],
        first_available: date,
        cutoff: PackageCutoff,
    ) -> list[RawDailySnapshotRow]:
        ...


class PositionReaderProtocol(Protocol):
    """Position API stream reader."""

    @property
    def query_text(self) -> str:
        ...

    async def fetch_rows(
        self,
        nmids: frozenset[int],
        position_first_available: date,
        cutoff: PackageCutoff,
    ) -> list[RawPositionRow]:
        ...


class BidDecisionProbeProtocol(Protocol):
    """Read-only bid_decision_log schema and scoped presence probe."""

    async def probe(
        self, adv_ids: frozenset[int], cutoff: PackageCutoff | None = None
    ) -> BidDecisionAvailability:
        ...


class BidDecisionReaderProtocol(Protocol):
    """Read bid_decision_log rows (source-derived DECISION classification)."""

    async def fetch_latest_decisions(
        self,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> list[RawBidDecisionRow]:
        ...

    async def fetch_timeline(
        self,
        adv_ids: frozenset[int],
        cutoff: PackageCutoff,
    ) -> list[RawBidDecisionRow]:
        ...


class KeywordPolicyReaderProtocol(Protocol):
    """PG AdvSetting campaign policy for current-state enrichment."""

    async def load_policies(
        self, shop_id: str, adv_setting_ids: frozenset[int]
    ) -> dict[int, CampaignPolicySnapshot]:
        ...


class KeywordQueryPolicyReaderProtocol(Protocol):
    """PG KeywordSetting per-query policy."""

    async def load_query_policies(
        self, shop_id: str, adv_setting_ids: frozenset[int]
    ) -> dict[tuple[int, str], KeywordQueryPolicySnapshot]:
        ...

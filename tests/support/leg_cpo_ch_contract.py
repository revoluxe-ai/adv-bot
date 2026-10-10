"""Shared ContractCase для leg-CPO CH thin ends (GAP-STUB-CH).

Golden request/return shapes согласованы с ``tests/support/leg_cpo_ch_seed.py`` и
authored CH boundary tests
(``test_leg_cpo_ch_external_gap_seams``, ``test_get_stats_by_adv_ids_last_days_keeps_legs_separate``).
Executable source для scenario stub assertions и ``stub_contract`` parity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.wb_stat_manager.leg_cpo import (
    LegCpoSnapshot,
    build_leg_cpo_snapshot,
)
from tests.support.leg_cpo_ch_seed import (
    LEG_CPO_AUTO_ADV_ID,
    LEG_CPO_FIXED_DAYS,
    LEG_CPO_FIXED_NOW,
    LEG_CPO_SEARCH_ADV_ID,
    resolve_leg_cpo_window,
)

CONTRACT_ID = "leg-cpo-ch-boundary-v1"

# Production CH read thin-end: positional args ``(adv_ids, start_date, end_date)``.
GET_STATS_REQUIRED_POSITIONAL: tuple[str, ...] = ("adv_ids", "start_date", "end_date")

# Production loader thin-end: keyword-only ``auto_adv_id``, ``search_adv_id``, optional window.
LOAD_SNAPSHOT_REQUIRED_KWONLY: frozenset[str] = frozenset(
    {"auto_adv_id", "search_adv_id"}
)
LOAD_SNAPSHOTS_REQUIRED_KWONLY: frozenset[str] = frozenset({"complex_advs"})


@dataclass(frozen=True)
class LegCpoChContractCase:
    """Golden paired Auto/Search economics из leg_cpo_ch_seed window."""

    case_id: str
    auto_adv_id: int
    search_adv_id: int
    auto_spend: float
    auto_orders: int
    search_spend: float
    search_orders: int
    now: datetime
    days: int

    @property
    def expected_auto_cpo(self) -> float:
        """CPO Auto leg из golden spend/orders."""
        return self.auto_spend / max(self.auto_orders, 1)

    @property
    def expected_search_cpo(self) -> float:
        """CPO Search leg из golden spend/orders."""
        return self.search_spend / max(self.search_orders, 1)

    def window(self) -> tuple[datetime, datetime]:
        """Inclusive observation window как у production ``resolve_leg_cpo_window``."""
        return resolve_leg_cpo_window(now=self.now, days=self.days)

    def adv_ids(self) -> list[int]:
        """Exact adv_id list для ``get_stats_by_adv_ids_last_days``."""
        return [self.auto_adv_id, self.search_adv_id]

    def get_stats_request(self) -> tuple[list[int], datetime, datetime]:
        """Golden request tuple для CH stats read."""
        start_date, end_date = self.window()
        return self.adv_ids(), start_date, end_date

    def load_snapshot_kwargs(self) -> dict[str, Any]:
        """Golden kwargs для ``load_leg_cpo_snapshot``."""
        return {
            "auto_adv_id": self.auto_adv_id,
            "search_adv_id": self.search_adv_id,
            "now": self.now,
            "days": self.days,
        }


GOLDEN_PAIR_CASE = LegCpoChContractCase(
    case_id="paired_auto_search_seed_window",
    auto_adv_id=LEG_CPO_AUTO_ADV_ID,
    search_adv_id=LEG_CPO_SEARCH_ADV_ID,
    auto_spend=600.0,
    auto_orders=2,
    search_spend=300.0,
    search_orders=3,
    now=LEG_CPO_FIXED_NOW,
    days=LEG_CPO_FIXED_DAYS,
)

LEG_CPO_CH_CONTRACT_CASES: tuple[LegCpoChContractCase, ...] = (GOLDEN_PAIR_CASE,)


def golden_stats_by_adv_id(
    case: LegCpoChContractCase = GOLDEN_PAIR_CASE,
) -> dict[int, SmallFullAdvStat]:
    """Golden CH return shape: per-adv spend/orders без смешивания ног."""
    return {
        case.auto_adv_id: SmallFullAdvStat(
            views=200,
            clicks=20,
            spend=case.auto_spend,
            added_to_cart=4,
            orders=case.auto_orders,
            sum_price=2200.0,
        ),
        case.search_adv_id: SmallFullAdvStat(
            views=170,
            clicks=17,
            spend=case.search_spend,
            added_to_cart=4,
            orders=case.search_orders,
            sum_price=1700.0,
        ),
    }


def golden_leg_cpo_snapshot(
    case: LegCpoChContractCase = GOLDEN_PAIR_CASE,
) -> LegCpoSnapshot:
    """Golden ``LegCpoSnapshot`` как после ``load_leg_cpo_snapshot`` на seed rows."""
    start_date, end_date = case.window()
    return build_leg_cpo_snapshot(
        auto_adv_id=case.auto_adv_id,
        search_adv_id=case.search_adv_id,
        stats_by_adv_id=golden_stats_by_adv_id(case),
        start_date=start_date,
        end_date=end_date,
    )


def assert_get_stats_request_matches_case(
    adv_ids: list[int],
    start_date: datetime,
    end_date: datetime,
    case: LegCpoChContractCase = GOLDEN_PAIR_CASE,
) -> None:
    """Executable parity: CH stats read request == ContractCase."""
    expected_ids, expected_start, expected_end = case.get_stats_request()
    assert adv_ids == expected_ids
    assert start_date == expected_start
    assert end_date == expected_end


def assert_load_snapshot_kwargs_match_case(
    kwargs: dict[str, Any],
    case: LegCpoChContractCase = GOLDEN_PAIR_CASE,
) -> None:
    """Executable parity: loader kwargs == ContractCase."""
    missing = LOAD_SNAPSHOT_REQUIRED_KWONLY - set(kwargs)
    assert not missing, f"load_leg_cpo_snapshot kwargs missing {sorted(missing)}"
    expected = case.load_snapshot_kwargs()
    for key in LOAD_SNAPSHOT_REQUIRED_KWONLY:
        assert kwargs[key] == expected[key]
    if "now" in kwargs:
        assert kwargs["now"] == expected["now"]
    if "days" in kwargs:
        assert kwargs["days"] == expected["days"]


def assert_snapshot_matches_case(
    snapshot: LegCpoSnapshot,
    case: LegCpoChContractCase = GOLDEN_PAIR_CASE,
) -> None:
    """Executable parity: snapshot fields == ContractCase golden economics."""
    start_date, end_date = case.window()
    assert snapshot.auto_adv_id == case.auto_adv_id
    assert snapshot.search_adv_id == case.search_adv_id
    assert snapshot.auto_cpo == case.expected_auto_cpo
    assert snapshot.search_cpo == case.expected_search_cpo
    assert snapshot.start_date == start_date
    assert snapshot.end_date == end_date


@dataclass
class RecordingLegCpoSnapshotLoader:
    """Thin-end fake для ``load_leg_cpo_snapshot`` с записью kwargs."""

    case: LegCpoChContractCase = GOLDEN_PAIR_CASE
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def load_leg_cpo_snapshot(self, **kwargs: Any) -> LegCpoSnapshot:
        """Сигнатура как production ``load_leg_cpo_snapshot`` (keyword-only)."""
        self.calls.append(dict(kwargs))
        return golden_leg_cpo_snapshot(self.case)

    def assert_matches_case(self, case: LegCpoChContractCase | None = None) -> None:
        """Scenario stub: один вызов с ContractCase kwargs и golden return."""
        active = case or self.case
        assert len(self.calls) == 1, "expected exactly one load_leg_cpo_snapshot call"
        assert_load_snapshot_kwargs_match_case(self.calls[0], active)
        assert_snapshot_matches_case(golden_leg_cpo_snapshot(active), active)


@dataclass
class RecordingGetStatsByAdvIds:
    """Thin-end fake для ``get_stats_by_adv_ids_last_days`` с записью request."""

    case: LegCpoChContractCase = GOLDEN_PAIR_CASE
    calls: list[tuple[list[int], datetime, datetime]] = field(default_factory=list)

    async def __call__(
        self,
        adv_ids: list[int],
        start_date: datetime,
        end_date: datetime,
    ) -> dict[int, SmallFullAdvStat]:
        """Сигнатура как production ``get_stats_by_adv_ids_last_days``."""
        self.calls.append((list(adv_ids), start_date, end_date))
        return golden_stats_by_adv_id(self.case)

    def assert_matches_case(self, case: LegCpoChContractCase | None = None) -> None:
        """Scenario stub: один CH read с ContractCase request/return."""
        active = case or self.case
        assert len(self.calls) == 1, "expected exactly one get_stats_by_adv_ids_last_days call"
        adv_ids, start_date, end_date = self.calls[0]
        assert_get_stats_request_matches_case(adv_ids, start_date, end_date, active)
        stats = golden_stats_by_adv_id(active)
        assert stats[active.auto_adv_id].spend == active.auto_spend
        assert stats[active.search_adv_id].spend == active.search_spend


@dataclass
class RecordingLegCpoSnapshotsLoader:
    """Thin-end fake для batch ``load_leg_cpo_snapshots``."""

    case: LegCpoChContractCase = GOLDEN_PAIR_CASE
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def load_leg_cpo_snapshots(self, **kwargs: Any) -> dict[int, LegCpoSnapshot]:
        """Сигнатура как production ``load_leg_cpo_snapshots`` (keyword-only)."""
        self.calls.append(dict(kwargs))
        return {self.case.auto_adv_id: golden_leg_cpo_snapshot(self.case)}

    def assert_matches_case(self, case: LegCpoChContractCase | None = None) -> None:
        """Scenario stub: batch loader возвращает golden snapshot keyed by auto adv_id."""
        active = case or self.case
        assert len(self.calls) == 1, "expected exactly one load_leg_cpo_snapshots call"
        kwargs = self.calls[0]
        missing = LOAD_SNAPSHOTS_REQUIRED_KWONLY - set(kwargs)
        assert not missing, f"load_leg_cpo_snapshots kwargs missing {sorted(missing)}"
        snapshots = {active.auto_adv_id: golden_leg_cpo_snapshot(active)}
        assert snapshots[active.auto_adv_id].search_cpo == active.expected_search_cpo

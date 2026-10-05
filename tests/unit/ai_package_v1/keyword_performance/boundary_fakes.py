"""Production-boundary fakes for default ExportService / KeywordPerformanceAssembler tests.

Patches only ``get_clickhouse_client``, ``default_pg_session_factory``, and Redis
rebound at real factory seams — not assembler injection or NoOp bypass.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
from datetime import date
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe import (
    ChBidDecisionProbe,
)


class FakeClickHouseClient:
    """Routes CH SQL by table/fragment at the client boundary."""

    def __init__(self) -> None:
        self.query = AsyncMock(side_effect=self._query)
        self.insert = AsyncMock(side_effect=self._insert)

    async def _insert(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("CH insert forbidden on read-only keyword export path")

    async def _query(
        self, sql: str, parameters: dict[str, Any] | None = None
    ) -> MagicMock:
        _ = parameters
        if "system.columns" in sql and "bid_decision_log" in sql:
            cols = [(c,) for c in ChBidDecisionProbe().required_columns]
            return MagicMock(result_rows=cols)
        if "bid_decision_log" in sql:
            return MagicMock(result_rows=[])
        if "keyword_position_bounds" in sql or (
            "keyword_position_from_api" in sql and "MIN" in sql
        ):
            return MagicMock(result_rows=[(date(2026, 1, 1), date(2026, 1, 5))])
        if "keyword_history_bounds" in sql or "clusters_adv_stats" in sql and "MIN" in sql:
            return MagicMock(result_rows=[(date(2026, 1, 1), date(2026, 1, 5))])
        if "keyword_daily_from_clusters" in sql or (
            "clusters_adv_stats" in sql and "norm_query" in sql
        ):
            return MagicMock(result_rows=[])
        if "keyword_position_from_api" in sql:
            return MagicMock(result_rows=[])
        return MagicMock(result_rows=[])


@asynccontextmanager
async def _fake_ch_client_cm() -> AsyncGenerator[FakeClickHouseClient, None]:
    yield FakeClickHouseClient()


def _fake_adv_setting(*, shop_id: str = "1") -> SimpleNamespace:
    return SimpleNamespace(
        id=101,
        adv_id=111,
        search_adv_id=222,
        nmids=[500],
        wb_cabinet=SimpleNamespace(shop_id=shop_id),
        bidder_active=True,
        max_cpm=300.0,
        active_status="active",
        strategy=SimpleNamespace(value="MIN_CPO"),
        min_target_position=5,
        target_position_mode=SimpleNamespace(value="MIN_CPA"),
    )


class FakePgSession:
    async def __aenter__(self) -> FakePgSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        raise AssertionError("PG commit forbidden on read-only keyword export path")

    async def execute(self, *args: object, **kwargs: object) -> MagicMock:
        def _empty_rows() -> list[object]:
            return []

        return MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=_empty_rows))
        )


def fake_pg_session_maker(**kwargs: object) -> MagicMock:
    _ = kwargs
    maker = MagicMock()
    maker.return_value = FakePgSession()
    return maker


# Backward-compatible aliases for production_keyword_boundary internals.
_FakeSession = FakePgSession
_fake_session_maker = fake_pg_session_maker


_CH_PATCH_TARGETS = (
    "app.utils.click_house.client.get_clickhouse_client",
    "app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_probe.get_clickhouse_client",
    "app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_bounds_reader.get_clickhouse_client",
    "app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_daily_reader.get_clickhouse_client",
    "app.modules.ai_package_v1.keyword_performance.readers.ch_keyword_position_reader.get_clickhouse_client",
    "app.modules.ai_package_v1.keyword_performance.readers.ch_bid_decision_reader.get_clickhouse_client",
)


@contextmanager
def production_keyword_boundary(
    *,
    shop_id: str = "1",
    inventory: list[SimpleNamespace] | None = None,
):
    """Patch production I/O seams for default keyword pipeline tests."""
    adv_rows = inventory or [_fake_adv_setting(shop_id=shop_id)]

    async def _load_inventory(_shop_id: str) -> list[SimpleNamespace]:
        matched: list[SimpleNamespace] = []
        for row in adv_rows:
            if getattr(row.wb_cabinet, "shop_id", None) == _shop_id:
                matched.append(row)
        return matched

    async def _rebound(_adv_setting_id: int) -> tuple[set[int], set[int]]:
        return set(), set()

    async def _overlap(
        adv_ids: frozenset[int], session: object = None
    ) -> dict[int, list[tuple[str, int]]]:
        _ = session
        return {adv_id: [(shop_id, 101)] for adv_id in adv_ids}

    patchers = [
        patch(target, side_effect=lambda: _fake_ch_client_cm())
        for target in _CH_PATCH_TARGETS
    ]
    for patcher in patchers:
        patcher.start()
    try:
        with (
            patch(
                "app.modules.ai_package_v1.keyword_performance.readers.pg_session_adapter.default_pg_session_factory",
                side_effect=_fake_session_maker,
            ),
            patch(
                "app.modules.ai_package_v1.scope.pg_adv_setting_inventory_reader.PgAdvSettingInventoryReader.load_inventory",
                side_effect=_load_inventory,
            ),
            patch(
                "app.modules.ai_package_v1.keyword_performance.scope.keyword_export_scope_reader.get_rebound_wb_adv_ids",
                side_effect=_rebound,
            ),
            patch(
                "app.modules.ai_package_v1.keyword_performance.readers.pg_adv_id_overlap_reader.PgAdvIdOverlapReader.load_overlap",
                side_effect=_overlap,
            ),
            patch(
                "app.modules.ai_package_v1.keyword_performance.readers.pg_keyword_query_policy_reader.PgKeywordQueryPolicyReader.load_query_policies",
                AsyncMock(return_value={}),
            ),
            patch(
                "app.modules.ai_package_v1.keyword_performance.readers.pg_keyword_policy_reader.PgKeywordPolicyReader.load_policies",
                AsyncMock(return_value={}),
            ),
            patch("redis.asyncio.Redis.set", MagicMock()) as redis_set,
        ):
            yield redis_set
    finally:
        for patcher in reversed(patchers):
            patcher.stop()

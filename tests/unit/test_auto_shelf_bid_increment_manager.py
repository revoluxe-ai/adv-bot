from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_increment_manager import (
    AutoShelfBidIncrementManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.dto import (
    AutoShelfBidSnapshot,
    AutoShelfRawStat,
)


pytestmark = pytest.mark.unit


def _build_manager() -> tuple[AutoShelfBidIncrementManager, MagicMock, MagicMock, MagicMock]:
    repository = MagicMock()
    writer = MagicMock()
    writer.insert_interval = AsyncMock()
    lock_manager = MagicMock()
    lock_manager.acquire = AsyncMock(return_value=True)
    lock_manager.release = AsyncMock(return_value=None)
    manager = AutoShelfBidIncrementManager(
        redis_client=MagicMock(),
        wb_manager_hub=MagicMock(),
        repository=repository,
        writer=writer,
        lock_manager=lock_manager,
    )
    state_manager = MagicMock()
    state_manager.get = AsyncMock()
    state_manager.persist = AsyncMock()
    state_manager.mark_resync_required = AsyncMock()
    state_manager.is_resync_required = AsyncMock(return_value=False)
    state_manager.clear_resync_required = AsyncMock()
    manager._last_state_manager = state_manager
    return manager, repository, writer, state_manager


def _build_adv(nmids: list[int]) -> SimpleNamespace:
    return SimpleNamespace(
        adv_id=111,
        auto_adv_id=222,
        shop_id="5fd8c93d-3f59-4de8-b413-7d4c90f96313",
        nmids=nmids,
    )


def _build_snapshot(
    nmid: int,
    impressions: int,
    clicks: int,
    carts: int,
    orders: int,
    spend: float,
    *,
    bid_minor: int = 1300,
    price_minor: int | None = None,
    price_currency: str | None = "RUB",
) -> AutoShelfBidSnapshot:
    now = datetime.now(ZoneInfo("Europe/Moscow")).replace(microsecond=0)
    return AutoShelfBidSnapshot(
        nmid=nmid,
        src_ts=now,
        bucket_start=now.replace(minute=0, second=0),
        version=1,
        mode="main",
        bid_minor=bid_minor,
        currency="RUB",
        price_minor=price_minor,
        price_currency=price_currency or "RUB",
        impressions=impressions,
        clicks=clicks,
        carts=carts,
        orders=orders,
        spend=spend,
    )


@pytest.mark.asyncio
async def test_single_nmid_guard_skips_no_nmids() -> None:
    manager, repository, writer, state_manager = _build_manager()
    await manager.update(_build_adv([]))
    repository.fetch_total_auto_stat.assert_not_called()
    writer.insert_interval.assert_not_called()
    state_manager.persist.assert_not_called()


@pytest.mark.asyncio
async def test_single_nmid_guard_skips_multi_nmids() -> None:
    manager, repository, writer, state_manager = _build_manager()
    await manager.update(_build_adv([1, 2]))
    repository.fetch_total_auto_stat.assert_not_called()
    writer.insert_interval.assert_not_called()
    state_manager.persist.assert_not_called()


@pytest.mark.asyncio
async def test_first_snapshot_persists_only_prev() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(100, 10, 3, 1, 50.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(20, 2, 1, 0, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1200)
    repository.get_current_mode = AsyncMock(return_value="main")
    state_manager.get.return_value = (None, "none")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_not_called()
    state_manager.persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_positive_delta_inserts_interval_and_persists_prev() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(130, 13, 4, 2, 60.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(30, 3, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(123, impressions=90, clicks=8, carts=2, orders=0, spend=40.0)
    state_manager.get.return_value = (prev, "redis")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_awaited_once()
    state_manager.persist.assert_awaited_once()
    inserted_row = writer.insert_interval.await_args.args[0]
    assert inserted_row.nmid == 123
    assert inserted_row.delta_impressions == 10
    assert inserted_row.delta_clicks == 2
    assert inserted_row.delta_carts == 1
    assert inserted_row.delta_orders == 1
    assert inserted_row.delta_spend == 10.0
    assert inserted_row.mode == "main"
    assert inserted_row.bid_minor == 1300
    assert inserted_row.currency == "RUB"


@pytest.mark.asyncio
async def test_insert_success_then_persist_fail_marks_resync_and_next_tick_keeps_single_interval() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(130, 13, 4, 2, 60.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(30, 3, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(123, impressions=90, clicks=8, carts=2, orders=0, spend=40.0)
    state_manager.get.return_value = (prev, "redis")
    state_manager.persist = AsyncMock(side_effect=[RuntimeError("persist failed"), None])
    state_manager.is_resync_required = AsyncMock(side_effect=[False, True])

    await manager.update(_build_adv([123]))
    await manager.update(_build_adv([123]))

    # Первый тик: interval вставлен, persist упал.
    # Второй тик: resync-ветка только выравнивает prev, новый interval не пишет.
    writer.insert_interval.assert_awaited_once()
    state_manager.mark_resync_required.assert_awaited_once_with(123)
    state_manager.clear_resync_required.assert_awaited_once_with(123)


@pytest.mark.asyncio
async def test_zero_delta_skips_interval_but_persists_prev() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(100, 10, 3, 1, 50.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(20, 2, 1, 0, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1200)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(
        123,
        impressions=80,
        clicks=8,
        carts=2,
        orders=1,
        spend=40.0,
        bid_minor=1200,
    )
    state_manager.get.return_value = (prev, "redis")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_not_awaited()
    state_manager.persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_negative_recommendations_skips_all_persist_and_insert() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(10, 1, 0, 0, 5.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(20, 2, 0, 0, 6.0))

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_not_called()
    state_manager.persist.assert_not_called()
    state_manager.mark_resync_required.assert_awaited_once_with(123)


@pytest.mark.asyncio
async def test_resync_required_persists_current_snapshot_without_interval() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(130, 13, 4, 2, 60.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(30, 3, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(123, impressions=90, clicks=8, carts=2, orders=0, spend=40.0)
    state_manager.get.return_value = (prev, "redis")
    state_manager.is_resync_required = AsyncMock(return_value=True)

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_not_awaited()
    state_manager.persist.assert_awaited_once()
    state_manager.clear_resync_required.assert_awaited_once_with(123)


@pytest.mark.asyncio
async def test_missing_keyword_stat_persists_first_snapshot_as_shelf_total() -> None:
    """Полочная РК без keyword-статы: пустой keyword = ноль, shelf = total."""
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(100, 10, 3, 1, 50.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=None)
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1200)
    repository.get_current_mode = AsyncMock(return_value="main")
    state_manager.get.return_value = (None, "none")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_not_called()
    state_manager.persist.assert_awaited_once()
    state_manager.mark_resync_required.assert_not_called()


@pytest.mark.asyncio
async def test_missing_keyword_stat_inserts_interval_on_positive_delta() -> None:
    """При keyword_stat=None и положительной shelf-дельте пишем interval."""
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(130, 13, 4, 2, 60.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=None)
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(123, impressions=90, clicks=8, carts=2, orders=0, spend=40.0)
    state_manager.get.return_value = (prev, "redis")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_awaited_once()
    state_manager.persist.assert_awaited_once()
    inserted_row = writer.insert_interval.await_args.args[0]
    # shelf = total (keyword=0): 130 - 90 prev = 40
    assert inserted_row.delta_impressions == 40


@pytest.mark.asyncio
async def test_missing_bid_skips_interval_and_prev() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(100, 10, 3, 1, 50.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(20, 2, 1, 0, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=None)

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_not_called()
    state_manager.persist.assert_not_called()


@pytest.mark.asyncio
async def test_price_is_not_fetched_and_non_blocking_for_interval_insert() -> None:
    # v1: price не читается из repository (см. README «Для ревью» п.2).
    # Мок fetch_current_price_minor — guard: даже если метод вернут, менеджер его не вызывает.
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(130, 13, 4, 2, 60.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(30, 3, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    repository.fetch_current_price_minor = AsyncMock(side_effect=RuntimeError("permission denied"))
    prev = _build_snapshot(123, impressions=90, clicks=8, carts=2, orders=0, spend=40.0)
    state_manager.get.return_value = (prev, "redis")

    await manager.update(_build_adv([123]))

    repository.fetch_current_price_minor.assert_not_called()
    writer.insert_interval.assert_awaited_once()
    state_manager.persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_negative_delta_skips_interval_and_persists_prev() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(120, 12, 5, 2, 50.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(20, 2, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(123, impressions=150, clicks=20, carts=7, orders=5, spend=70.0)
    state_manager.get.return_value = (prev, "redis")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_not_awaited()
    state_manager.persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_change_by_bid_flushes_boundary_to_prev_context() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(130, 13, 4, 2, 60.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(30, 3, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(
        123,
        impressions=90,
        clicks=8,
        carts=2,
        orders=0,
        spend=40.0,
        price_minor=None,
        price_currency="RUB",
    )
    prev = prev.model_copy(update={"bid_minor": 1200})
    state_manager.get.return_value = (prev, "redis")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_awaited_once()
    state_manager.persist.assert_awaited_once()
    inserted_row = writer.insert_interval.await_args.args[0]
    assert inserted_row.bid_minor == 1200
    assert inserted_row.mode == "main"
    assert inserted_row.delta_impressions == 10
    assert inserted_row.delta_carts == 1
    assert inserted_row.delta_spend == 10.0


@pytest.mark.asyncio
async def test_boundary_flush_then_persist_fail_marks_resync_and_prevents_second_boundary_interval() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        side_effect=[
            AutoShelfRawStat(130, 13, 4, 2, 60.0),
            AutoShelfRawStat(140, 14, 5, 2, 70.0),
        ]
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(30, 3, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(123, impressions=90, clicks=8, carts=2, orders=0, spend=40.0)
    prev = prev.model_copy(update={"bid_minor": 1200})
    state_manager.get.return_value = (prev, "redis")
    state_manager.persist = AsyncMock(side_effect=[RuntimeError("persist failed"), None])
    state_manager.is_resync_required = AsyncMock(side_effect=[False, True])

    await manager.update(_build_adv([123]))
    await manager.update(_build_adv([123]))

    # 1-й тик: boundary interval вставлен, persist упал.
    # 2-й тик: resync-only, без повторного boundary flush.
    writer.insert_interval.assert_awaited_once()
    state_manager.mark_resync_required.assert_awaited_once_with(123)
    state_manager.clear_resync_required.assert_awaited_once_with(123)


@pytest.mark.asyncio
async def test_price_unknown_does_not_create_context_change_by_itself() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(130, 13, 4, 2, 60.0)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(30, 3, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(
        123,
        impressions=90,
        clicks=8,
        carts=2,
        orders=0,
        spend=40.0,
        price_minor=None,
        price_currency="RUB",
    )
    state_manager.get.return_value = (prev, "redis")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_awaited_once()
    state_manager.persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_negative_delta_spend_with_epsilon_skips_interval_and_persists_prev() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(120, 12, 5, 2, 49.999999998)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(20, 2, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(123, impressions=100, clicks=10, carts=4, orders=1, spend=40.0)
    state_manager.get.return_value = (prev, "redis")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_not_awaited()
    state_manager.persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_small_negative_spend_within_epsilon_treated_as_zero_delta() -> None:
    manager, repository, writer, state_manager = _build_manager()
    repository.fetch_total_auto_stat = AsyncMock(
        return_value=AutoShelfRawStat(120, 12, 5, 2, 49.9999999995)
    )
    repository.fetch_keyword_stat = AsyncMock(return_value=AutoShelfRawStat(20, 2, 1, 1, 10.0))
    repository.fetch_current_auto_common_bid = AsyncMock(return_value=1300)
    repository.get_current_mode = AsyncMock(return_value="main")
    prev = _build_snapshot(123, impressions=100, clicks=10, carts=4, orders=1, spend=40.0)
    state_manager.get.return_value = (prev, "redis")

    await manager.update(_build_adv([123]))

    writer.insert_interval.assert_not_awaited()
    state_manager.persist.assert_awaited_once()


def test_clickhouse_ddl_contains_required_contract() -> None:
    from pathlib import Path

    ddl = Path(
        "scripts/clickhouse_migrations/004_create_auto_shelf_bid_increment_tables.sql"
    ).read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS default_db.auto_shelf_bid_intervals" in ddl
    assert "CREATE TABLE IF NOT EXISTS default_db.auto_shelf_bid_prev" in ddl
    assert "PARTITION BY toYYYYMM(event_date)" in ddl
    assert "bid_minor Int64" in ddl
    assert "price_minor Nullable(Int64)" in ddl
    assert "delta_spend Float64" in ddl
    ddl_lower = ddl.lower()
    assert "delta_revenue" not in ddl_lower
    assert "\n    revenue " not in ddl_lower


def test_validation_sql_contains_known_plus_unknown_wildcard_filter() -> None:
    from pathlib import Path

    known_sql = Path(
        "app/modules/shop_runner/service_manager/services/auto_shelf_bid_increment_manager/sql/validate_auto_shelf_bid_intervals_by_bid_price.sql"
    ).read_text(encoding="utf-8")
    assert "nmid = %(nmid)s" in known_sql
    assert "(price_minor = %(current_price_minor)s AND price_currency = %(current_price_currency)s)" in known_sql
    assert "OR price_minor IS NULL" in known_sql
    assert "OR price_currency IS NULL" in known_sql


def test_validation_sql_unknown_mode_has_no_price_filter() -> None:
    from pathlib import Path

    unknown_sql = Path(
        "app/modules/shop_runner/service_manager/services/auto_shelf_bid_increment_manager/sql/validate_auto_shelf_bid_intervals_by_bid_price_unknown.sql"
    ).read_text(encoding="utf-8")
    assert "nmid = %(nmid)s" in unknown_sql
    assert "current_price_minor" not in unknown_sql
    assert "current_price_currency" not in unknown_sql
    where_block = unknown_sql.split("GROUP BY")[0]
    assert "price_minor =" not in where_block
    assert "price_currency =" not in where_block


def test_interval_insert_sql_is_idempotent_by_event_id() -> None:
    from pathlib import Path

    sql = Path(
        "app/modules/shop_runner/service_manager/services/auto_shelf_bid_increment_manager/sql/insert_auto_shelf_bid_interval.sql"
    ).read_text(encoding="utf-8")
    assert "WHERE NOT EXISTS" in sql
    assert "event_date = %(event_date)s" in sql
    assert "event_id = %(event_id)s" in sql


def test_validation_sql_uses_event_id_dedup_pattern() -> None:
    from pathlib import Path

    known_sql = Path(
        "app/modules/shop_runner/service_manager/services/auto_shelf_bid_increment_manager/sql/validate_auto_shelf_bid_intervals_by_bid_price.sql"
    ).read_text(encoding="utf-8")
    unknown_sql = Path(
        "app/modules/shop_runner/service_manager/services/auto_shelf_bid_increment_manager/sql/validate_auto_shelf_bid_intervals_by_bid_price_unknown.sql"
    ).read_text(encoding="utf-8")
    dedup_checks = (
        "GROUP BY event_date, event_id",
        "argMax(delta_impressions, version)",
        "argMax(delta_spend, version)",
    )
    for expected in dedup_checks:
        assert expected in known_sql
        assert expected in unknown_sql


def test_sum_dedup_sql_exists_for_auto_shelf_analytics() -> None:
    from pathlib import Path

    sql = Path(
        "app/modules/shop_runner/service_manager/services/auto_shelf_bid_increment_manager/sql/sum_auto_shelf_bid_interval_deltas_dedup.sql"
    ).read_text(encoding="utf-8")
    assert "GROUP BY event_date, event_id" in sql
    assert "argMax(delta_impressions, version)" in sql
    assert "argMax(delta_spend, version)" in sql


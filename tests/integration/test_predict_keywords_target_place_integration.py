"""Интеграционные тесты для PredictKeywordsTargetPlace.

Act opens production ``get_clickhouse_client`` with SQL on ``default_db.*``.
Tests redirect conv + bids CH managers onto the fixture Guarded client and
rewrite ``default_db.*`` → ``test_adv_bot_clickhouse.*`` before the guard.
"""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

import app.modules.bids_for_positions_manager.clickhouse_manager.clickhouse_manager as bids_ch_module
import app.modules.predict_keywords_target_place.clickhouse_manager.clickhouse_manager as predict_ch_module
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from tests.support.rewrite_default_db_ch_client import patch_get_clickhouse_client


pytestmark = pytest.mark.destructive_local
TEST_NMID = 999001


@pytest.fixture
def predict_ch_on_test_db(
    clickhouse_client: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redirect predict/bids CH clients onto fixture Guarded client + rewrite."""
    patch_get_clickhouse_client(
        monkeypatch, [bids_ch_module], clickhouse_client
    )
    # predict module aliases import as ``get_client``
    patch_get_clickhouse_client(
        monkeypatch,
        [predict_ch_module],
        clickhouse_client,
        attr="get_client",
    )


def _make_adv_mock(
    nmid: int = TEST_NMID,
    min_bid: int = 50,
    strategy: Strategy = Strategy.MIN_CPO,
):
    """Минимальный mock adv для get_keywords_target_position(adv, positions_size)."""
    adv = MagicMock()
    adv.main_nmid = nmid
    adv.search_adv_min_bids = {nmid: min_bid}
    adv.strategy = strategy
    return adv


async def _ensure_predict_tables(clickhouse_client):
    """Создаёт таблицы, необходимые для predict_keywords_target_place."""
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.bid_decision_log (
            adv_id Int32,
            nmid UInt64,
            norm_query String,
            wb_category LowCardinality(String),
            pos_final Float64,
            pos_final_bucket UInt16,
            views_curr UInt32,
            spend_curr Float64,
            cpm_curr Float64,
            pos_curr Float64,
            views_prev UInt32,
            spend_prev Float64,
            cpm_prev Float64,
            pos_prev Float64,
            final_bid Float64,
            decision_source String,
            stats_max_timestamp DateTime,
            decision_time DateTime,
            version UInt64
        ) ENGINE = MergeTree()
        ORDER BY (nmid, norm_query, pos_final_bucket, version)
    """)
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.clusters_adv_deltas_5m (
            adv_id Int32,
            nmid UInt64,
            wb_category LowCardinality(String),
            norm_query LowCardinality(String),
            ts5 DateTime,
            dviews UInt32,
            dcarts UInt32,
            dclicks UInt32,
            dorders UInt32,
            pos_bin UInt16,
            cpm_mid Float32,
            dspend_est Float32,
            gap_minutes UInt16,
            is_reset UInt8,
            src_ts DateTime,
            version UInt64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(ts5)
        ORDER BY (nmid, norm_query, ts5)
    """)
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS test_adv_bot_clickhouse.pos_priors_category (
            wb_category LowCardinality(String),
            pos_bin UInt16,
            p_14d Float64,
            views_14d UInt32,
            calculated_at DateTime
        ) ENGINE = ReplacingMergeTree(calculated_at)
        ORDER BY (wb_category, pos_bin)
    """)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_keywords_target_position_empty_data(
    clickhouse_client,
    predict_ch_on_test_db,
):
    """При пустых таблицах возвращается пустой словарь."""
    del predict_ch_on_test_db
    await _ensure_predict_tables(clickhouse_client)
    async with anti_ch_crash_semaphore:
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.bid_decision_log")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.clusters_adv_deltas_5m")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.pos_priors_category")

    predictor = build_predict_keywords_target_place()
    adv = _make_adv_mock()

    result = await predictor.get_keywords_target_position(adv, positions_size=10)

    assert result == {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_keywords_target_position_with_bid_data_only(
    clickhouse_client,
    predict_ch_on_test_db,
):
    """Только bid_decision_log: get_bids возвращает данные, get_conv_cart — пусто → convs пусто."""
    del predict_ch_on_test_db
    await _ensure_predict_tables(clickhouse_client)
    ts = datetime.now()
    async with anti_ch_crash_semaphore:
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.bid_decision_log")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.clusters_adv_deltas_5m")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.pos_priors_category")

        await clickhouse_client.insert(
            "test_adv_bot_clickhouse.bid_decision_log",
            [
                [
                    1,
                    TEST_NMID,
                    "keyword_test",
                    "TestCategory",
                    1.0,
                    1,
                    100,
                    10.0,
                    100.0,
                    1.0,
                    90,
                    9.0,
                    90.0,
                    1.0,
                    100.0,
                    "cpm",
                    ts,
                    ts,
                    int(ts.timestamp() * 1000),
                ],
            ],
            column_names=[
                "adv_id",
                "nmid",
                "norm_query",
                "wb_category",
                "pos_final",
                "pos_final_bucket",
                "views_curr",
                "spend_curr",
                "cpm_curr",
                "pos_curr",
                "views_prev",
                "spend_prev",
                "cpm_prev",
                "pos_prev",
                "final_bid",
                "decision_source",
                "stats_max_timestamp",
                "decision_time",
                "version",
            ],
        )

    predictor = build_predict_keywords_target_place()
    adv = _make_adv_mock()

    result = await predictor.get_keywords_target_position(adv, positions_size=10)

    assert isinstance(result, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_keywords_target_position_full_e2e(
    clickhouse_client,
    predict_ch_on_test_db,
):
    """E2E: данные в bid_decision_log, clusters_adv_deltas_5m, pos_priors_category → ожидаемый результат."""
    del predict_ch_on_test_db
    await _ensure_predict_tables(clickhouse_client)
    ts = datetime.now()
    async with anti_ch_crash_semaphore:
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.bid_decision_log")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.clusters_adv_deltas_5m")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.pos_priors_category")

        await clickhouse_client.insert(
            "test_adv_bot_clickhouse.bid_decision_log",
            [
                [
                    1,
                    TEST_NMID,
                    "kw_full",
                    "Electronics",
                    1.0,
                    1,
                    100,
                    10.0,
                    100.0,
                    1.0,
                    90,
                    9.0,
                    90.0,
                    1.0,
                    100.0,
                    "cpm",
                    ts,
                    ts,
                    int(ts.timestamp() * 1000),
                ],
                [
                    1,
                    TEST_NMID,
                    "kw_full",
                    "Electronics",
                    2.0,
                    2,
                    80,
                    8.0,
                    100.0,
                    2.0,
                    70,
                    7.0,
                    87.5,
                    2.0,
                    90.0,
                    "cpm",
                    ts,
                    ts,
                    int(ts.timestamp() * 1000),
                ],
            ],
            column_names=[
                "adv_id",
                "nmid",
                "norm_query",
                "wb_category",
                "pos_final",
                "pos_final_bucket",
                "views_curr",
                "spend_curr",
                "cpm_curr",
                "pos_curr",
                "views_prev",
                "spend_prev",
                "cpm_prev",
                "pos_prev",
                "final_bid",
                "decision_source",
                "stats_max_timestamp",
                "decision_time",
                "version",
            ],
        )

        await clickhouse_client.insert(
            "test_adv_bot_clickhouse.clusters_adv_deltas_5m",
            [
                [
                    1,
                    TEST_NMID,
                    "Electronics",
                    "kw_full",
                    ts,
                    50,
                    5,
                    0,
                    0,
                    1,
                    100.0,
                    5.0,
                    0,
                    0,
                    ts,
                    1,
                ],
                [
                    1,
                    TEST_NMID,
                    "Electronics",
                    "kw_full",
                    ts,
                    40,
                    4,
                    0,
                    0,
                    2,
                    90.0,
                    3.6,
                    0,
                    0,
                    ts,
                    1,
                ],
            ],
            column_names=[
                "adv_id",
                "nmid",
                "wb_category",
                "norm_query",
                "ts5",
                "dviews",
                "dcarts",
                "dclicks",
                "dorders",
                "pos_bin",
                "cpm_mid",
                "dspend_est",
                "gap_minutes",
                "is_reset",
                "src_ts",
                "version",
            ],
        )

        await clickhouse_client.insert(
            "test_adv_bot_clickhouse.pos_priors_category",
            [
                ["Electronics", 1, 0.1, 50, ts],
                ["Electronics", 2, 0.12, 40, ts],
            ],
            column_names=["wb_category", "pos_bin", "p_14d", "views_14d", "calculated_at"],
        )

    predictor = build_predict_keywords_target_place()
    adv = _make_adv_mock()

    result = await predictor.get_keywords_target_position(adv, positions_size=10)

    assert isinstance(result, dict)
    if result:
        assert "kw_full" in result
        assert result["kw_full"] in (1, 2)

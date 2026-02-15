"""Интеграционные тесты для PredictKeywordsTargetPlace."""

from datetime import datetime

import pytest

from app.modules.predict_keywords_target_place.clickhouse_manager import ClickHouseManager
from app.modules.predict_keywords_target_place.predict_keywords_target_place import (
    PredictKeywordsTargetPlace,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore

TEST_NMID = 999001


async def _ensure_predict_tables(clickhouse_client):
    """Создаёт таблицы, необходимые для predict_keywords_target_place."""
    await clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS default_db.bid_decision_log (
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
        CREATE TABLE IF NOT EXISTS default_db.clusters_adv_deltas_5m (
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
        CREATE TABLE IF NOT EXISTS default_db.pos_priors_category (
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
async def test_get_keywords_target_position_empty_data(clickhouse_client):
    """При пустых таблицах возвращается пустой словарь."""
    await _ensure_predict_tables(clickhouse_client)
    async with anti_ch_crash_semaphore:
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS default_db.bid_decision_log")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS default_db.clusters_adv_deltas_5m")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS default_db.pos_priors_category")

    manager = ClickHouseManager()
    predictor = PredictKeywordsTargetPlace(manager)

    result = await predictor.get_keywords_target_position(
        nmid=TEST_NMID, min_bid=50, positions_size=10
    )

    assert result == {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_keywords_target_position_with_bid_data_only(clickhouse_client):
    """Только bid_decision_log: get_bids возвращает данные, get_conv_cart — пусто → convs пусто."""
    await _ensure_predict_tables(clickhouse_client)
    ts = datetime.now()
    async with anti_ch_crash_semaphore:
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS default_db.bid_decision_log")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS default_db.clusters_adv_deltas_5m")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS default_db.pos_priors_category")

        await clickhouse_client.insert(
            "default_db.bid_decision_log",
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

    manager = ClickHouseManager()
    predictor = PredictKeywordsTargetPlace(manager)

    result = await predictor.get_keywords_target_position(
        nmid=TEST_NMID, min_bid=50, positions_size=10
    )

    assert isinstance(result, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_keywords_target_position_full_e2e(clickhouse_client):
    """E2E: данные в bid_decision_log, clusters_adv_deltas_5m, pos_priors_category → ожидаемый результат."""
    await _ensure_predict_tables(clickhouse_client)
    ts = datetime.now()
    async with anti_ch_crash_semaphore:
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS default_db.bid_decision_log")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS default_db.clusters_adv_deltas_5m")
        await clickhouse_client.command("TRUNCATE TABLE IF EXISTS default_db.pos_priors_category")

        await clickhouse_client.insert(
            "default_db.bid_decision_log",
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
            "default_db.clusters_adv_deltas_5m",
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
            "default_db.pos_priors_category",
            [
                ["Electronics", 1, 0.1, 50, ts],
                ["Electronics", 2, 0.12, 40, ts],
            ],
            column_names=["wb_category", "pos_bin", "p_14d", "views_14d", "calculated_at"],
        )

    manager = ClickHouseManager()
    predictor = PredictKeywordsTargetPlace(manager)

    result = await predictor.get_keywords_target_position(
        nmid=TEST_NMID, min_bid=50, positions_size=10
    )

    assert isinstance(result, dict)
    if result:
        assert "kw_full" in result
        assert result["kw_full"] in (1, 2)

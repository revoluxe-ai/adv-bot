"""Bootstrap disposable PG schema for A/B Hold live verification (§19.5 / §22.7.3).

Минимальный stub ``advsetting`` (без PG ENUM / FK-графа) для Alembic epoch
upgrade/downgrade и raw/ORM concurrency против disposable ``TEST_DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def sync_url(db_url: str) -> str:
    """Нормализовать URL к sync ``postgresql://`` для Alembic/DDL."""
    if db_url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + db_url.removeprefix("postgresql+asyncpg://")
    return db_url


def async_url(db_url: str) -> str:
    """Нормализовать URL к ``postgresql+asyncpg://``."""
    if db_url.startswith("postgresql+asyncpg://"):
        return db_url
    if db_url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + db_url.removeprefix("postgresql://")
    return db_url


_PRE_EPOCH_DDL = """
DROP TABLE IF EXISTS advsetting CASCADE;
DROP TABLE IF EXISTS wbcabinet CASCADE;
DROP TABLE IF EXISTS alembic_version CASCADE;

CREATE TABLE wbcabinet (
    id SERIAL PRIMARY KEY
);

-- Stub: VARCHAR вместо PG ENUM, без FK — достаточно для epoch migration + ORM SELECT.
CREATE TABLE advsetting (
    id SERIAL PRIMARY KEY,
    adv_id BIGINT,
    name VARCHAR NOT NULL DEFAULT 'live-pg',
    wb_cabinet_id INTEGER NOT NULL DEFAULT 1,
    active_status VARCHAR,
    bot_active BOOLEAN DEFAULT false,
    nmids JSONB,
    black_phrases JSONB NOT NULL DEFAULT '[]'::jsonb,
    relevant_phrases JSONB NOT NULL DEFAULT '[]'::jsonb,
    pass_days INTEGER,
    boost FLOAT,
    type INTEGER,
    wb_bid_type VARCHAR,
    wb_placement_search BOOLEAN,
    wb_placement_recommendations BOOLEAN,
    hard_min_ctr FLOAT,
    max_cpc FLOAT,
    min_views_for_ml_predict INTEGER,
    parsing_active BOOLEAN,
    last_update TIMESTAMP,
    bidder_active BOOLEAN,
    max_cpm INTEGER,
    max_place INTEGER,
    use_incremental_stats BOOLEAN NOT NULL DEFAULT true,
    use_cluster_stats_in_freshness BOOLEAN,
    min_block_position INTEGER,
    clusters_mode BOOLEAN,
    target_ctr_mode BOOLEAN,
    hide_small_query_keywords BOOLEAN,
    bidder_coroutine_type VARCHAR(21),
    target_ctr_mode_strategy VARCHAR,
    new_auto_min_ctr_mode BOOLEAN,
    reset_place BOOLEAN,
    _search_adv_id INTEGER,
    bidder_step INTEGER,
    exponent_predict_ctr FLOAT,
    auction_boost_all_phrase_mode BOOLEAN,
    plan_for_sales_for_day INTEGER,
    target_price_for_order FLOAT,
    max_price_for_order INTEGER,
    substitute_fact_cpo_for_max BOOLEAN,
    cpm INTEGER,
    bidder_for_auto BOOLEAN,
    auto_update_white_list BOOLEAN,
    auto_budget_watchdog_enabled BOOLEAN,
    auto_update_target_place BOOLEAN,
    auto_update_exponent BOOLEAN,
    rec_system_mode BOOLEAN,
    auto_shelf_bid_control_enabled BOOLEAN,
    auto_shelf_bid_control_strategy VARCHAR(13),
    hide_zero_views_keywords BOOLEAN,
    max_balance_adding_for_day INTEGER,
    auto_budget_daily_limit INTEGER,
    search_auto_budget_daily_limit INTEGER,
    use_common_budget BOOLEAN,
    common_budget_daily_limit INTEGER,
    auto_adv_target_status BOOLEAN,
    auction_adv_target_status BOOLEAN,
    auto_add_only_relevant_phrase BOOLEAN,
    orders_source_for_auto_mode VARCHAR(16),
    predict_ctr_mode VARCHAR(2),
    sales_predict_method VARCHAR(12),
    automatic_version INTEGER,
    aggressiveness INTEGER,
    keyword_calibration_max_step INTEGER,
    card_ab_hold_mode VARCHAR(32) DEFAULT 'off' NOT NULL,
    card_ab_hold_allowed_phrases_snapshot JSONB DEFAULT '[]'::jsonb NOT NULL,
    card_ab_hold_degraded BOOLEAN DEFAULT false NOT NULL,
    bidder_mode VARCHAR(15),
    updater_common_bid_in_search_adv_active_status BOOLEAN,
    white_list_mode VARCHAR(22),
    individual_keywords_target_place_mode BOOLEAN,
    min_target_position INTEGER,
    target_position_mode VARCHAR(22),
    strategy VARCHAR(8),
    auto_update_strategy BOOLEAN,
    auto_common_budget BOOLEAN
);

INSERT INTO wbcabinet (id) VALUES (1);
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
INSERT INTO alembic_version (version_num) VALUES ('c9d0e1f2a3b4');
"""


def create_pre_epoch_advsetting_schema(db_url: str) -> None:
    """Создать stub schema на уровне parent revision ``c9d0e1f2a3b4``."""
    engine = create_engine(sync_url(db_url))
    with engine.begin() as conn:
        for stmt in _PRE_EPOCH_DDL.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    engine.dispose()


def run_epoch_migration_upgrade_downgrade(db_url: str) -> None:
    """Выполнить upgrade/downgrade ``d0e1f2a3b4c5`` через Alembic Operations.

    Не зависит от ``alembic_/env.py`` URL (settings/.env): работает только с
    переданным disposable ``db_url``.
    """
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from alembic_.versions.d0e1f2a3b4c5_add_card_ab_hold_epoch_lifecycle_fields import (
        downgrade as epoch_downgrade,
        upgrade as epoch_upgrade,
    )

    engine = create_engine(sync_url(db_url))
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            epoch_upgrade()
        conn.execute(text("UPDATE alembic_version SET version_num = 'd0e1f2a3b4c5'"))
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            epoch_downgrade()
        conn.execute(text("UPDATE alembic_version SET version_num = 'c9d0e1f2a3b4'"))
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            epoch_upgrade()
        conn.execute(text("UPDATE alembic_version SET version_num = 'd0e1f2a3b4c5'"))
    engine.dispose()


def ensure_post_epoch_schema_for_orm(db_url: str) -> None:
    """Гарантировать post-epoch ``advsetting`` + ``wbcabinet`` для live concurrency."""
    create_pre_epoch_advsetting_schema(db_url)
    run_epoch_migration_upgrade_downgrade(db_url)


def assert_epoch_columns_present(db_url: str) -> list[str]:
    """Вернуть список epoch-колонок, реально присутствующих в ``advsetting``."""
    engine = create_engine(sync_url(db_url))
    expected = [
        "card_ab_hold_phase",
        "card_ab_hold_warmup_started_at",
        "card_ab_hold_warmup_duration_hours",
        "card_ab_hold_generation",
        "card_ab_hold_wb_sync_idempotency_key",
        "card_ab_hold_pending_intent_json",
        "card_ab_hold_sync_status",
        "card_ab_hold_confirmed_keywords_json",
        "card_ab_hold_confirmed_target_places_json",
        "card_ab_hold_confirmed_auto_participation",
        "card_ab_hold_confirmed_auto_bid",
    ]
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'advsetting'"
            )
        ).fetchall()
    present = {str(r[0]) for r in rows}
    missing = [c for c in expected if c not in present]
    if missing:
        raise AssertionError(f"epoch columns missing after upgrade: {missing}")
    engine.dispose()
    return expected


def insert_ready_for_intent_row(
    db_url: str,
    *,
    adv_setting_id: int = 42,
    adv_id: int = 9001,
) -> int:
    """Вставить строку со всеми confirms для ``create_pending_intent_for_generation``."""
    engine = create_engine(sync_url(db_url))
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM advsetting WHERE id = :id"), {"id": adv_setting_id})
        conn.execute(
            text(
                """
                INSERT INTO advsetting (
                    id, adv_id, name, wb_cabinet_id,
                    black_phrases, relevant_phrases, use_incremental_stats,
                    card_ab_hold_mode, card_ab_hold_phase,
                    card_ab_hold_generation, card_ab_hold_sync_status,
                    card_ab_hold_confirmed_keywords_json,
                    card_ab_hold_confirmed_target_places_json,
                    card_ab_hold_confirmed_auto_participation,
                    card_ab_hold_confirmed_auto_bid,
                    card_ab_hold_pending_intent_json,
                    card_ab_hold_wb_sync_idempotency_key,
                    card_ab_hold_degraded,
                    card_ab_hold_warmup_duration_hours
                ) VALUES (
                    :id, :adv_id, 'live-pg', 1,
                    '[]'::jsonb, '[]'::jsonb, true,
                    'pending_setup', 'awaiting_auto_bid_confirm',
                    0, 'none',
                    CAST(:kw AS jsonb),
                    CAST(:tp AS jsonb),
                    true,
                    100.0,
                    NULL,
                    NULL,
                    false,
                    24
                )
                """
            ),
            {
                "id": adv_setting_id,
                "adv_id": adv_id,
                "kw": '["alpha"]',
                "tp": '{"alpha": 5}',
            },
        )
    engine.dispose()
    return adv_setting_id


@contextmanager
def patched_async_session_maker(db_url: str) -> Iterator[None]:
    """Подменить ``epoch_write.sm`` на disposable async engine."""
    from unittest.mock import patch

    engine = create_async_engine(async_url(db_url), pool_size=8, max_overflow=0)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def sm_factory(*, read_only: bool = False) -> AsyncIterator[AsyncSession]:
        _ = read_only
        session = maker()
        try:
            yield session
        finally:
            await session.close()

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        sm_factory,
    ):
        yield
    engine.sync_engine.dispose()

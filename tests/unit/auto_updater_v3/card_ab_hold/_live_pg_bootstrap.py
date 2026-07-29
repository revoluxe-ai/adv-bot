"""Bootstrap disposable PG schema for A/B Hold live verification (§19.5 / §22.7.3).

Минимальный stub ``advsetting`` / ``keywordsetting`` (без полного FK-графа) для
Alembic epoch upgrade/downgrade и ORM writers против disposable
``TEST_DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import ExitStack, asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_CARD_AB_HOLD_SM_TARGETS: tuple[str, ...] = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.epoch_write.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.setup_apply.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.epoch_pipelines.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.telegram.handlers.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.telegram.confirm_handlers.sm",
)


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


_KEYWORDSETTING_DDL = """
DROP TABLE IF EXISTS keywordsetting CASCADE;
DROP TYPE IF EXISTS keywordstrategymode CASCADE;
CREATE TYPE keywordstrategymode AS ENUM (
    'OFF', 'MIN_CPA', 'OPTIMUM', 'MAX_CONVERSION'
);
CREATE TABLE keywordsetting (
    id SERIAL PRIMARY KEY,
    text VARCHAR NOT NULL,
    adv_setting_id INTEGER NOT NULL REFERENCES advsetting(id),
    hard_status INTEGER DEFAULT 1,
    strategy_mode keywordstrategymode NOT NULL DEFAULT 'MIN_CPA',
    target_place INTEGER,
    predict_ctr FLOAT,
    added_clicks INTEGER DEFAULT 0,
    added_views INTEGER DEFAULT 0,
    auto_block BOOLEAN,
    relevant BOOLEAN DEFAULT false
);
"""


def ensure_keywordsetting_stub(db_url: str) -> None:
    """Создать stub ``keywordsetting`` после post-epoch ``advsetting``."""
    engine = create_engine(sync_url(db_url))
    with engine.begin() as conn:
        for stmt in _KEYWORDSETTING_DDL.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    engine.dispose()


def ensure_post_epoch_schema_for_orm(db_url: str) -> None:
    """Гарантировать post-epoch ``advsetting`` + ``keywordsetting`` для live ORM."""
    create_pre_epoch_advsetting_schema(db_url)
    run_epoch_migration_upgrade_downgrade(db_url)
    ensure_keywordsetting_stub(db_url)


def insert_adv_row(
    db_url: str,
    *,
    adv_setting_id: int,
    adv_id: int,
    mode: str = "off",
    phase: str | None = None,
    bot_active: bool = True,
    extra: dict[str, Any] | None = None,
) -> int:
    """Вставить минимальную строку ``advsetting`` для live PG writers.

    ``extra`` может переопределить стандартные epoch-колонки (generation, JSON, …).
    """
    import json

    extras = dict(extra or {})
    engine = create_engine(sync_url(db_url))
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM keywordsetting WHERE adv_setting_id = :id"),
            {"id": adv_setting_id},
        )
        conn.execute(
            text("DELETE FROM advsetting WHERE id = :id"),
            {"id": adv_setting_id},
        )
        base: dict[str, Any] = {
            "id": adv_setting_id,
            "adv_id": adv_id,
            "card_ab_hold_mode": mode,
            "card_ab_hold_phase": phase,
            "card_ab_hold_generation": 0,
            "card_ab_hold_sync_status": "none",
            "bot_active": bot_active,
            "card_ab_hold_allowed_phrases_snapshot": [],
            "card_ab_hold_confirmed_keywords_json": None,
            "card_ab_hold_confirmed_target_places_json": None,
            "card_ab_hold_pending_intent_json": None,
            "card_ab_hold_warmup_duration_hours": 24,
        }
        base.update(extras)
        jsonb_cols = {
            "card_ab_hold_allowed_phrases_snapshot",
            "card_ab_hold_confirmed_keywords_json",
            "card_ab_hold_confirmed_target_places_json",
            "card_ab_hold_pending_intent_json",
        }
        params: dict[str, Any] = {
            "id": base["id"],
            "adv_id": base["adv_id"],
            "mode": base["card_ab_hold_mode"],
            "phase": base["card_ab_hold_phase"],
            "generation": base["card_ab_hold_generation"],
            "sync_status": base["card_ab_hold_sync_status"],
            "bot_active": base["bot_active"],
            "warmup_hours": base["card_ab_hold_warmup_duration_hours"],
        }
        for col in jsonb_cols:
            val = base.get(col)
            params[col] = None if val is None else json.dumps(val)
        conn.execute(
            text(
                """
                INSERT INTO advsetting (
                    id, adv_id, name, wb_cabinet_id,
                    black_phrases, relevant_phrases, use_incremental_stats,
                    card_ab_hold_mode, card_ab_hold_phase,
                    card_ab_hold_generation, card_ab_hold_sync_status,
                    card_ab_hold_degraded, card_ab_hold_warmup_duration_hours,
                    bot_active, card_ab_hold_allowed_phrases_snapshot,
                    card_ab_hold_confirmed_keywords_json,
                    card_ab_hold_confirmed_target_places_json,
                    card_ab_hold_pending_intent_json
                ) VALUES (
                    :id, :adv_id, 'live-pg', 1,
                    '[]'::jsonb, '[]'::jsonb, true,
                    :mode, :phase, :generation, :sync_status,
                    false, :warmup_hours, :bot_active,
                    CAST(:card_ab_hold_allowed_phrases_snapshot AS jsonb),
                    CAST(:card_ab_hold_confirmed_keywords_json AS jsonb),
                    CAST(:card_ab_hold_confirmed_target_places_json AS jsonb),
                    CAST(:card_ab_hold_pending_intent_json AS jsonb)
                )
                """
            ),
            params,
        )
    engine.dispose()
    return adv_setting_id


def insert_keyword_row(
    db_url: str,
    *,
    keyword_id: int,
    adv_setting_id: int,
    text_value: str,
    hard_status: int = 2,
    strategy_mode: str = "MIN_CPA",
    target_place: int | None = 7,
) -> int:
    """Вставить stub ``keywordsetting`` для TP / FAIL→OFF writers."""
    engine = create_engine(sync_url(db_url))
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM keywordsetting WHERE id = :id"),
            {"id": keyword_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO keywordsetting (
                    id, text, adv_setting_id, hard_status, strategy_mode, target_place
                ) VALUES (
                    :id, :text, :adv_setting_id, :hard_status,
                    CAST(:strategy_mode AS keywordstrategymode), :target_place
                )
                """
            ),
            {
                "id": keyword_id,
                "text": text_value,
                "adv_setting_id": adv_setting_id,
                "hard_status": hard_status,
                "strategy_mode": strategy_mode,
                "target_place": target_place,
            },
        )
    engine.dispose()
    return keyword_id


def fetch_adv_epoch_row(db_url: str, adv_setting_id: int) -> Any:
    """Re-read durable epoch columns from live PG."""
    engine = create_engine(sync_url(db_url))
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT card_ab_hold_mode, card_ab_hold_phase,
                       card_ab_hold_warmup_started_at,
                       card_ab_hold_warmup_duration_hours,
                       card_ab_hold_generation,
                       card_ab_hold_confirmed_keywords_json,
                       card_ab_hold_confirmed_target_places_json,
                       card_ab_hold_confirmed_auto_participation,
                       card_ab_hold_confirmed_auto_bid,
                       card_ab_hold_pending_intent_json,
                       card_ab_hold_sync_status,
                       card_ab_hold_wb_sync_idempotency_key,
                       card_ab_hold_allowed_phrases_snapshot
                FROM advsetting WHERE id = :id
                """
            ),
            {"id": adv_setting_id},
        ).one()
    engine.dispose()
    return row


def fetch_keyword_row(db_url: str, keyword_id: int) -> Any:
    """Re-read keywordsetting hard_status / strategy_mode / target_place."""
    engine = create_engine(sync_url(db_url))
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT hard_status, strategy_mode::text, target_place
                FROM keywordsetting WHERE id = :id
                """
            ),
            {"id": keyword_id},
        ).one()
    engine.dispose()
    return row


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
        conn.execute(
            text("DELETE FROM keywordsetting WHERE adv_setting_id = :id"),
            {"id": adv_setting_id},
        )
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
def patched_async_session_maker(
    db_url: str,
    *,
    targets: Sequence[str] | None = None,
) -> Iterator[None]:
    """Подменить ``sm`` card_ab_hold writers на disposable async engine.

    Args:
        db_url: disposable Postgres URL.
        targets: module paths to patch; default — все A/B Hold PG writers.
    """
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

    patch_targets = tuple(targets) if targets is not None else _CARD_AB_HOLD_SM_TARGETS
    with ExitStack() as stack:
        for target in patch_targets:
            stack.enter_context(patch(target, sm_factory))
        yield
    engine.sync_engine.dispose()

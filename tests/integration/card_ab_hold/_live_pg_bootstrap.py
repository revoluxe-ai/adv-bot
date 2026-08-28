"""Bootstrap disposable PG schema for A/B Hold live verification (§19.5 / §22.7.3).

Минимальный stub ``advsetting`` / ``keywordsetting`` / ``wbcabinet`` (без полного
FK-графа) для Alembic epoch upgrade/downgrade и ORM writers против disposable
``TEST_DATABASE_URL``.

``wbcabinet`` stub MUST включать mapped-колонки ORM ``WBCabinet`` (как минимум
``shop_id``): ``AdvSetting.wb_cabinet`` — ``lazy="joined"``, иначе SELECT
AdvSetting падает с ``UndefinedColumn``.

ORM-complete post-epoch bootstrap ALSO applies emergency latch/educated
(``f2a3b4c5d6e7``): mapped on ``AdvSetting``, иначе ``SELECT … FOR UPDATE`` →
``UndefinedColumn`` на ``card_ab_hold_emergency_latch``.

Fail-closed: каждый ``create_engine`` / ``create_async_engine`` идёт только после
``validate_destructive_test_database_url``. DDL выполняется в уникальной schema
на run (``ab_hold_<uuid>``) — cleanup ``DROP SCHEMA … CASCADE``, без DROP
production-таблиц в ``public``.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import ExitStack, asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tests.support.destructive_pg_dsn import validate_destructive_test_database_url

_CARD_AB_HOLD_SM_TARGETS: tuple[str, ...] = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.epoch_write.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.setup_apply.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.epoch_pipelines.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.hold_guards.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.telegram.handlers.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.telegram.confirm_handlers.sm",
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.telegram.emergency_handlers.sm",
)

# Активная schema для текущего bootstrap-контекста (search_path).
_active_schema: str | None = None


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


def _attach_search_path(engine: Engine, schema: str) -> None:
    """На каждый connect выставлять search_path в disposable schema."""

    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.close()


def create_validated_sync_engine(db_url: str) -> Engine:
    """``create_engine`` только после fail-closed DSN validation."""
    validate_destructive_test_database_url(db_url)
    engine = create_engine(sync_url(db_url))
    if _active_schema:
        _attach_search_path(engine, _active_schema)
    return engine


def create_validated_async_engine(db_url: str, **kwargs: Any) -> AsyncEngine:
    """``create_async_engine`` только после fail-closed DSN validation."""
    validate_destructive_test_database_url(db_url)
    engine = create_async_engine(async_url(db_url), **kwargs)
    if _active_schema:
        _attach_search_path(engine.sync_engine, _active_schema)
    return engine


@contextmanager
def disposable_ab_hold_schema(db_url: str) -> Iterator[str]:
    """Создать уникальную schema, выставить search_path, cleanup CASCADE.

    Yields:
        Имя schema (``ab_hold_<hex>``).
    """
    global _active_schema
    validate_destructive_test_database_url(db_url)
    schema = f"ab_hold_{uuid.uuid4().hex[:12]}"
    engine = create_validated_sync_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine.dispose()
    previous = _active_schema
    _active_schema = schema
    try:
        yield schema
    finally:
        _active_schema = previous
        engine = create_validated_sync_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


_PRE_EPOCH_DDL = """
DROP TABLE IF EXISTS wbusercabinet CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;
DROP TABLE IF EXISTS advsetting CASCADE;
DROP TABLE IF EXISTS wbcabinet CASCADE;
DROP TABLE IF EXISTS alembic_version CASCADE;

-- Stub wbcabinet: колонки под ORM WBCabinet (AdvSetting.wb_cabinet lazy=joined).
-- Без shop_id/прочих mapped columns ORM SELECT AdvSetting → UndefinedColumn.
CREATE TABLE wbcabinet (
    id SERIAL PRIMARY KEY,
    shop_id VARCHAR NOT NULL UNIQUE,
    active BOOLEAN DEFAULT true,
    expiration_time TIMESTAMP NOT NULL DEFAULT (now() + interval '7 days'),
    expiration_alarm_days_pass INTEGER,
    demo BOOLEAN DEFAULT true,
    balance FLOAT NOT NULL DEFAULT 0,
    bonus FLOAT NOT NULL DEFAULT 0,
    default_max_cpm INTEGER NOT NULL DEFAULT 400,
    balance_went_negative_at TIMESTAMPTZ
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
    auto_update_minus_phrases BOOLEAN DEFAULT false,
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

INSERT INTO wbcabinet (id, shop_id, active, demo, balance, bonus, default_max_cpm)
VALUES (1, 'live_pg_stub_shop', true, true, 0, 0, 400);
CREATE TABLE "user" (
    id INTEGER PRIMARY KEY,
    user_telegram_id BIGINT UNIQUE,
    username VARCHAR,
    email VARCHAR,
    password_hash VARCHAR,
    adv_updater_user_chat_id BIGINT,
    passed_gate BOOLEAN NOT NULL DEFAULT false
);
CREATE TABLE wbusercabinet (
    id INTEGER PRIMARY KEY,
    wb_cabinet_id INTEGER NOT NULL REFERENCES wbcabinet(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    name VARCHAR(255) NOT NULL,
    UNIQUE (wb_cabinet_id, user_id)
);
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
INSERT INTO alembic_version (version_num) VALUES ('c9d0e1f2a3b4');
"""


def create_pre_epoch_advsetting_schema(db_url: str) -> None:
    """Создать stub schema на уровне parent revision ``c9d0e1f2a3b4``."""
    engine = create_validated_sync_engine(db_url)
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

    engine = create_validated_sync_engine(db_url)
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
    engine = create_validated_sync_engine(db_url)
    with engine.begin() as conn:
        for stmt in _KEYWORDSETTING_DDL.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    engine.dispose()


def ensure_post_epoch_schema_for_orm(db_url: str) -> None:
    """Гарантировать ORM-complete disposable ``advsetting`` + ``keywordsetting``.

    Включает epoch ``d0e1f2a3b4c5`` и emergency ``f2a3b4c5d6e7``: ORM
    ``AdvSetting`` мапит ``card_ab_hold_emergency_latch`` /
    ``card_ab_hold_emergency_educated``, иначе SELECT → ``UndefinedColumn``.
    """
    create_pre_epoch_advsetting_schema(db_url)
    run_epoch_migration_upgrade_downgrade(db_url)
    ensure_emergency_latch_columns(db_url)
    ensure_keywordsetting_stub(db_url)


def ensure_emergency_latch_columns(db_url: str) -> None:
    """Применить ``f2a3b4c5d6e7`` (emergency latch + educated) на disposable schema.

    Вызывать после epoch upgrade (parent revision ``d0e1f2a3b4c5``).
    Не трогает production ``public``.
    """
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from alembic_.versions.f2a3b4c5d6e7_add_card_ab_hold_emergency_latch import (
        upgrade as emergency_upgrade,
    )

    engine = create_validated_sync_engine(db_url)
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            emergency_upgrade()
        conn.execute(text("UPDATE alembic_version SET version_num = 'f2a3b4c5d6e7'"))
    engine.dispose()


def ensure_post_epoch_with_emergency_schema_for_orm(db_url: str) -> None:
    """Alias: ``ensure_post_epoch_schema_for_orm`` уже ORM-complete (emergency)."""
    ensure_post_epoch_schema_for_orm(db_url)


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
    engine = create_validated_sync_engine(db_url)
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
    engine = create_validated_sync_engine(db_url)
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


def insert_user_cabinet_relation(
    db_url: str,
    *,
    user_id: int,
    telegram_id: int,
    cabinet_id: int = 1,
    relation_id: int | None = None,
) -> int:
    """Создать disposable relation ``Telegram user → WB cabinet`` для gate tests.

    Args:
        db_url: validated disposable PostgreSQL DSN.
        user_id: stable test ``user.id``.
        telegram_id: identity, которую передаёт ``CallbackQuery.from_user.id``.
        cabinet_id: existing disposable ``wbcabinet.id``.
        relation_id: optional stable ``wbusercabinet.id``.

    Returns:
        ID созданной связи.
    """
    relation_pk = relation_id if relation_id is not None else user_id
    engine = create_validated_sync_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM wbusercabinet WHERE id = :relation_id"),
            {"relation_id": relation_pk},
        )
        conn.execute(
            text('DELETE FROM "user" WHERE id = :user_id'),
            {"user_id": user_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO "user" (id, user_telegram_id, username)
                VALUES (:user_id, :telegram_id, :username)
                """
            ),
            {
                "user_id": user_id,
                "telegram_id": telegram_id,
                "username": f"live-user-{user_id}",
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO wbusercabinet (id, wb_cabinet_id, user_id, name)
                VALUES (:relation_id, :cabinet_id, :user_id, :name)
                """
            ),
            {
                "relation_id": relation_pk,
                "cabinet_id": cabinet_id,
                "user_id": user_id,
                "name": f"live-cabinet-{cabinet_id}",
            },
        )
    engine.dispose()
    return relation_pk


def fetch_adv_epoch_row(db_url: str, adv_setting_id: int) -> Any:
    """Re-read durable epoch columns from live PG."""
    engine = create_validated_sync_engine(db_url)
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


def fetch_adv_degraded_flag(db_url: str, adv_setting_id: int) -> bool:
    """Re-read durable ``card_ab_hold_degraded`` for live PG writer evidence."""
    engine = create_validated_sync_engine(db_url)
    with engine.connect() as conn:
        value = conn.execute(
            text(
                """
                SELECT card_ab_hold_degraded
                FROM advsetting WHERE id = :id
                """
            ),
            {"id": adv_setting_id},
        ).scalar_one()
    engine.dispose()
    return bool(value)


def fetch_emergency_educated_flag(db_url: str, adv_setting_id: int) -> bool:
    """Re-read durable ``card_ab_hold_emergency_educated`` after educate ACK."""
    engine = create_validated_sync_engine(db_url)
    with engine.connect() as conn:
        value = conn.execute(
            text(
                """
                SELECT card_ab_hold_emergency_educated
                FROM advsetting WHERE id = :id
                """
            ),
            {"id": adv_setting_id},
        ).scalar_one()
    engine.dispose()
    return bool(value)


def fetch_emergency_latch_row(db_url: str, adv_setting_id: int) -> Any:
    """Re-read Emergency latch + pause-intent columns после kill-switch.

    Returns:
        ``(latch, auto_adv_target_status, auction_adv_target_status, mode)``.
    """
    engine = create_validated_sync_engine(db_url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT card_ab_hold_emergency_latch,
                       auto_adv_target_status,
                       auction_adv_target_status,
                       card_ab_hold_mode
                FROM advsetting WHERE id = :id
                """
            ),
            {"id": adv_setting_id},
        ).one()
    engine.dispose()
    return row


def fetch_keyword_row(db_url: str, keyword_id: int) -> Any:
    """Re-read keywordsetting hard_status / strategy_mode / target_place."""
    engine = create_validated_sync_engine(db_url)
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
    engine = create_validated_sync_engine(db_url)
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
    engine = create_validated_sync_engine(db_url)
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


@asynccontextmanager
async def patched_async_session_maker(
    db_url: str,
    *,
    targets: Sequence[str] | None = None,
) -> AsyncIterator[None]:
    """Подменить ``sm`` card_ab_hold writers на disposable async engine.

    Args:
        db_url: disposable Postgres URL.
        targets: module paths to patch; default — все A/B Hold PG writers.

    Lifecycle: always ``await engine.dispose()`` on exit (async cleanup only).
    """
    from unittest.mock import patch

    engine = create_validated_async_engine(db_url, pool_size=8, max_overflow=0)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def sm_factory(*, read_only: bool = False) -> AsyncIterator[AsyncSession]:
        _ = read_only
        session = maker()
        try:
            if _active_schema is None:
                raise RuntimeError("disposable A/B Hold schema is not active")
            await session.execute(text(f'SET search_path TO "{_active_schema}"'))
            yield session
        finally:
            await session.close()

    patch_targets = tuple(targets) if targets is not None else _CARD_AB_HOLD_SM_TARGETS
    with ExitStack() as stack:
        for target in patch_targets:
            stack.enter_context(patch(target, sm_factory))
        try:
            yield
        finally:
            await engine.dispose()

"""
Stub schema + Expand path for CI ephemeral PostgreSQL migration gates.

Historical upgrade-from-empty is not CI-safe; gates stamp baseline ``8c541a39b7e2``
then upgrade to repository head. Stubs must satisfy ALTER TABLE dependencies on
the supported ancestor path, including ``user`` for MCP connection FK.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.engine import Engine

EPHEMERAL_BASELINE_REVISION = "8c541a39b7e2"

AD_CONTROL_TABLES: tuple[str, ...] = (
    "adcontrolslotmutationledger",
    "adcontrolshopfeaturerow",
    "adcontrolcampaignfeaturerow",
)


def apply_ephemeral_baseline_stubs(engine: Engine) -> None:
    """Minimum tables required for stamp baseline → head Expand upgrades."""
    statements: Sequence[str] = (
        "CREATE TABLE IF NOT EXISTS advsetting (id SERIAL PRIMARY KEY)",
        'CREATE TABLE IF NOT EXISTS "user" (id SERIAL PRIMARY KEY)',
        (
            "CREATE TABLE IF NOT EXISTS auto_shelf_bid_control_settings "
            "(id BIGSERIAL PRIMARY KEY)"
        ),
        (
            "CREATE TABLE IF NOT EXISTS auto_shelf_bid_control_state "
            "(id BIGSERIAL PRIMARY KEY)"
        ),
        "CREATE TABLE IF NOT EXISTS wbautobudgettopup (id SERIAL PRIMARY KEY)",
    )
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def assert_ad_control_tables_present(engine: Engine) -> None:
    """Verify Slice B persistence tables exist after Expand upgrade."""
    with engine.connect() as conn:
        for table in AD_CONTROL_TABLES:
            exists = conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = :name
                    )
                    """
                ),
                {"name": table},
            ).scalar_one()
            if not exists:
                raise AssertionError(f"missing table after upgrade: {table}")


def repository_head_revision() -> str:
    """Single Alembic head revision id (fail if not exactly one)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"expected exactly one repository head, got {heads}")
    return heads[0]

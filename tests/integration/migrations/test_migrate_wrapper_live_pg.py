"""Live PostgreSQL evidence for the guarded migration wrapper."""

from __future__ import annotations

import json

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.pool import NullPool

from app.db.migrate import MigrationOutcome, run_migration
from tests.support.destructive_pg_dsn import require_validated_live_pg_dsn_or_skip

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]


def test_run_migration_uses_live_pg_identity_lock_and_noop_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Migration entrypoint проходит real PG checks and re-reads current head."""
    db_url = require_validated_live_pg_dsn_or_skip()
    sync_url = make_url(db_url).set(drivername="postgresql+psycopg2")
    engine = create_engine(sync_url, poolclass=NullPool)
    try:
        script = ScriptDirectory.from_config(Config("alembic.ini"))
        heads = tuple(script.get_heads())
        if len(heads) != 1:
            pytest.skip("live migration evidence requires one Alembic head")

        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalars().all()
        current = tuple(str(value) for value in rows)
        if current != heads:
            pytest.skip(f"live database is not at current head: {current!r} != {heads!r}")

        monkeypatch.setenv("DATABASE_URL", str(sync_url))
        monkeypatch.setenv("EXPECTED_TARGET_REVISION", heads[0])
        monkeypatch.setenv(
            "EXPECTED_CURRENT_REVISION_SETS",
            json.dumps([list(heads)]),
        )
        monkeypatch.delenv("MIGRATION_RECEIPT_STATE", raising=False)
        monkeypatch.delenv("MIGRATION_BACKFILL_KIND", raising=False)

        result = run_migration(engine)

        assert result.outcome is MigrationOutcome.SUCCESS_NOOP
        assert result.database_heads == heads
        with engine.connect() as connection:
            persisted = tuple(
                str(value)
                for value in connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalars()
            )
        assert persisted == heads
    finally:
        engine.dispose()

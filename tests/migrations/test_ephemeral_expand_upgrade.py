"""Live ephemeral PG: baseline stub → stamp → upgrade → ad-control DDL proof."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.db.migration_ephemeral_baseline import (
    EPHEMERAL_BASELINE_REVISION,
    apply_ephemeral_baseline_stubs,
    assert_ad_control_tables_present,
    repository_head_revision,
)

pytestmark = pytest.mark.integration


def _ephemeral_url() -> str | None:
    return os.environ.get("MIGRATION_EPHEMERAL_PG_URL") or os.environ.get("DATABASE_URL")


@pytest.mark.skipif(
    _ephemeral_url() is None,
    reason="set MIGRATION_EPHEMERAL_PG_URL or DATABASE_URL for ephemeral expand test",
)
def test_ephemeral_expand_reaches_head_with_ad_control_tables() -> None:
    """Mirrors migration-gates Expand path (not a substitute for the workflow job)."""
    url = _ephemeral_url()
    assert url is not None
    head = repository_head_revision()
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        apply_ephemeral_baseline_stubs(engine)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url)
        command.stamp(config, EPHEMERAL_BASELINE_REVISION)
        command.upgrade(config, head)
        with engine.connect() as conn:
            current = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert current == head
        assert_ad_control_tables_present(engine)
    finally:
        engine.dispose()

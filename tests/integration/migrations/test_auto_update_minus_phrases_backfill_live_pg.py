"""Live PG tests spec stage-landing-readiness for classifier backfill."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

from app.db.auto_update_minus_phrases_backfill import (
    apply_auto_update_minus_phrases_backfill,
    preview_auto_update_minus_phrases,
)
from tests.support.destructive_pg_dsn import require_validated_live_pg_dsn_or_skip

pytestmark = pytest.mark.destructive_local


def test_live_backfill_classifies_paid_state_and_retries_idempotently() -> None:
    """Spec stage-landing-readiness: live PG доказывает classifier и retry."""
    db_url = require_validated_live_pg_dsn_or_skip()
    # TEST_DATABASE_URL may use asyncpg for the application fixtures; this test
    # exercises the synchronous Connection seam used by the migration Job.
    sync_url = make_url(db_url).set(drivername="postgresql+psycopg2")
    engine = create_engine(sync_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TEMP TABLE advsetting (
                        id SERIAL PRIMARY KEY,
                        bot_active BOOLEAN NOT NULL,
                        auto_update_minus_phrases BOOLEAN DEFAULT false
                    ) ON COMMIT DROP
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO advsetting (bot_active, auto_update_minus_phrases)
                    VALUES (true, NULL), (false, NULL), (true, false)
                    """
                )
            )

            preview = preview_auto_update_minus_phrases(connection)
            result = apply_auto_update_minus_phrases_backfill(connection)
            retry = apply_auto_update_minus_phrases_backfill(connection)
            rows = connection.execute(
                text(
                    """
                    SELECT bot_active, auto_update_minus_phrases
                    FROM advsetting
                    ORDER BY id
                    """
                )
            ).fetchall()

        assert preview.total_records == 3
        assert preview.null_records == 2
        assert preview.expected_enabled_records == 2
        assert result.updated_records == 3
        assert result.incompatible_records == 0
        assert retry.updated_records == 0
        assert rows == [(True, True), (False, False), (True, True)]
    finally:
        engine.dispose()

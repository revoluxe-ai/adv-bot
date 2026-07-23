"""Live PG concurrency / idempotency for ``create_pending_intent_for_generation``.

Requires ``TEST_DATABASE_URL`` (disposable Postgres). Validates real
``SELECT … FOR UPDATE`` serialization + unique idempotency key (§22.7.3).
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import create_engine, text

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    build_wb_sync_idempotency_key,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    create_pending_intent_for_generation,
)
from tests.unit.auto_updater_v3.card_ab_hold._live_pg_bootstrap import (
    ensure_post_epoch_schema_for_orm,
    insert_ready_for_intent_row,
    patched_async_session_maker,
    sync_url,
)

_HAS_LIVE_PG = bool(os.getenv("TEST_DATABASE_URL"))


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_LIVE_PG, reason="TEST_DATABASE_URL not set")
async def test_live_pg_concurrent_generation_only_one_wins() -> None:
    """Два параллельных вызова на реальном PG: ровно один intent (§22.7.3)."""
    db_url = os.environ["TEST_DATABASE_URL"]
    ensure_post_epoch_schema_for_orm(db_url)
    adv_setting_id = insert_ready_for_intent_row(db_url, adv_setting_id=42, adv_id=9001)

    with patched_async_session_maker(db_url):
        results = await asyncio.gather(
            create_pending_intent_for_generation(adv_setting_id, adv_id=9001),
            create_pending_intent_for_generation(adv_setting_id, adv_id=9001),
        )

    assert sorted(results) == [False, True]

    engine = create_engine(sync_url(db_url))
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT card_ab_hold_generation, "
                "card_ab_hold_wb_sync_idempotency_key, "
                "card_ab_hold_pending_intent_json->>'generation' "
                "FROM advsetting WHERE id = :id"
            ),
            {"id": adv_setting_id},
        ).one()
    engine.dispose()
    assert int(row[0]) == 1
    assert row[1] == build_wb_sync_idempotency_key(9001, 1)
    assert int(row[2]) == 1


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_LIVE_PG, reason="TEST_DATABASE_URL not set")
async def test_live_pg_duplicate_intent_retry_idempotent() -> None:
    """Повтор после победы на реальном PG: generation/key без bump."""
    db_url = os.environ["TEST_DATABASE_URL"]
    ensure_post_epoch_schema_for_orm(db_url)
    adv_setting_id = insert_ready_for_intent_row(db_url, adv_setting_id=43, adv_id=8002)

    with patched_async_session_maker(db_url):
        first = await create_pending_intent_for_generation(adv_setting_id, adv_id=8002)
        second = await create_pending_intent_for_generation(adv_setting_id, adv_id=8002)

    assert first is True
    assert second is False

    engine = create_engine(sync_url(db_url))
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT card_ab_hold_generation, card_ab_hold_wb_sync_idempotency_key "
                "FROM advsetting WHERE id = :id"
            ),
            {"id": adv_setting_id},
        ).one()
    engine.dispose()
    assert int(row[0]) == 1
    assert row[1] == build_wb_sync_idempotency_key(8002, 1)

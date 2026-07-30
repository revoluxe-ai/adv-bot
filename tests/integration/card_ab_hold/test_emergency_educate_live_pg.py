"""Live PG coverage for Emergency educate ACK seam (PG WRITE).

Requires validated ``TEST_DATABASE_URL`` + ``ALLOW_DESTRUCTIVE_TEST_DB=1``.
Доказывает durable ``card_ab_hold_emergency_educated`` через production
``acknowledge_emergency_education_in_session`` + SQL re-select — не session mock.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.emergency_handlers import (
    acknowledge_emergency_education_in_session,
)
from tests.integration.card_ab_hold._live_pg_bootstrap import (
    create_validated_async_engine,
    disposable_ab_hold_schema,
    ensure_post_epoch_with_emergency_schema_for_orm,
    fetch_emergency_educated_flag,
    insert_adv_row,
)
from tests.support.destructive_pg_dsn import require_validated_live_pg_dsn_or_skip


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_acknowledge_emergency_education_persists_educated() -> None:
    """WRITE session + child seam → re-read educated=True из disposable PG."""
    db_url = require_validated_live_pg_dsn_or_skip()
    with disposable_ab_hold_schema(db_url):
        ensure_post_epoch_with_emergency_schema_for_orm(db_url)
        adv_setting_id = insert_adv_row(
            db_url,
            adv_setting_id=77,
            adv_id=7701,
            mode=CardAbHoldMode.ACTIVE.value,
            bot_active=True,
        )

        engine = create_validated_async_engine(db_url)
        maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        try:
            async with maker() as session:
                outcome = await acknowledge_emergency_education_in_session(
                    session,
                    adv_setting_original_id=adv_setting_id,
                )
                assert outcome.kind == "ok"
                assert outcome.adv is not None
                assert outcome.adv.card_ab_hold_emergency_educated is True
                await session.commit()
        finally:
            await engine.dispose()

        assert fetch_emergency_educated_flag(db_url, adv_setting_id) is True

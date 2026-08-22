"""Live PG coverage for Emergency kill-switch seam (PG WRITE).

Requires validated ``TEST_DATABASE_URL`` + ``ALLOW_DESTRUCTIVE_TEST_DB=1``.
Доказывает durable latch + pause-intent + BLACK_LIST keywords через
``apply_ab_hold_emergency_in_session`` + SQL re-select — не session mock.
Hold mode MUST NOT сбрасываться в OFF.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.client_bot import const as client_bot_const
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.emergency import (
    apply_ab_hold_emergency_in_session,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from tests.integration.card_ab_hold._live_pg_bootstrap import (
    create_validated_async_engine,
    disposable_ab_hold_schema,
    ensure_post_epoch_with_emergency_schema_for_orm,
    fetch_emergency_latch_row,
    fetch_keyword_row,
    insert_adv_row,
    insert_keyword_row,
)
from tests.support.destructive_pg_dsn import require_validated_live_pg_dsn_or_skip


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_live_pg_apply_ab_hold_emergency_persists_latch_and_block_all() -> None:
    """WRITE session + child seam → re-read latch/pause/keywords из disposable PG."""
    db_url = require_validated_live_pg_dsn_or_skip()
    with disposable_ab_hold_schema(db_url):
        ensure_post_epoch_with_emergency_schema_for_orm(db_url)
        adv_setting_id = insert_adv_row(
            db_url,
            adv_setting_id=78,
            adv_id=7801,
            mode=CardAbHoldMode.ACTIVE.value,
            bot_active=True,
        )
        keyword_id = insert_keyword_row(
            db_url,
            keyword_id=78001,
            adv_setting_id=adv_setting_id,
            text_value="emergency-block",
            hard_status=2,
            strategy_mode=KeywordStrategyMode.MIN_CPA.name,
            target_place=4,
        )

        engine = create_validated_async_engine(db_url)
        maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        try:
            async with maker() as session:
                result = await apply_ab_hold_emergency_in_session(
                    session,
                    adv_setting_id=adv_setting_id,
                )
                assert result.status == "ok"
                assert result.latch_set is True
                assert result.keywords_blocked >= 1
                await session.commit()
        finally:
            await engine.dispose()

        latch_row = fetch_emergency_latch_row(db_url, adv_setting_id)
        assert latch_row[0] is True
        assert latch_row[1] is False
        assert latch_row[2] is False
        assert latch_row[3] == CardAbHoldMode.ACTIVE.value

        kw = fetch_keyword_row(db_url, keyword_id)
        assert kw[0] == client_bot_const.BLACK_LIST
        assert kw[1] == KeywordStrategyMode.OFF.name

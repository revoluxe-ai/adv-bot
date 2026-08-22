"""Integration: notify_empty_keywords_pause PURE_READ cabinets via live PG.

Evidence: injectable session_maker → production get_wb_user_cabinets_for_shop
на живой async_session; assert по re-select persisted cabinets + telegram id.
Live pytest — только после AUTHORIZE_ONE_LIVE_RUN (close-external-gap).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.messages import (
    build_empty_keywords_pause_message,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.notify import (
    notify_empty_keywords_pause,
)
from app.modules.token_monitoring.services.notification_manager import (
    get_wb_user_cabinets_for_shop,
)
from app.utils.db.models import User

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


class CapturingSessionMaker:
    """Передаёт live async_session и фиксирует read_only polarity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.read_only_calls: list[bool] = []

    def __call__(self, *, read_only: bool) -> CapturingSessionMaker:
        self.read_only_calls.append(read_only)
        return self

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.destructive_local
async def test_notify_empty_keywords_pause_reads_cabinets_from_pg(
    async_session: AsyncSession,
) -> None:
    """Seed cabinets → notify via injectable sm(read_only=True) → re-select PG."""
    shop_id = f"ekp_notify_{uuid.uuid4().hex[:12]}"
    telegram_id = 6_100_001 + (uuid.uuid4().int % 10_000)

    user = User(
        user_telegram_id=telegram_id,
        username=f"ekp_user_{telegram_id}",
        passed_gate=True,
    )
    async_session.add(user)
    await async_session.flush()

    wb_cabinet = WBCabinet(
        shop_id=shop_id,
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        default_max_cpm=500,
    )
    async_session.add(wb_cabinet)
    await async_session.flush()

    wb_user_cabinet = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=wb_cabinet.id,
        name="EKP Notify Cabinet",
    )
    async_session.add(wb_user_cabinet)
    await async_session.flush()

    # Persisted re-read (store evidence, not only mock args).
    persisted = await get_wb_user_cabinets_for_shop(async_session, shop_id)
    assert len(persisted) == 1
    assert persisted[0].user is not None
    assert int(persisted[0].user.user_telegram_id) == telegram_id

    stmt = (
        select(WBUserCabinet)
        .options(selectinload(WBUserCabinet.user))
        .where(WBUserCabinet.id == wb_user_cabinet.id)
    )
    row = (await async_session.execute(stmt)).scalar_one()
    assert row.user is not None
    assert int(row.user.user_telegram_id) == telegram_id

    sm = CapturingSessionMaker(async_session)
    intent = MagicMock()
    intent.mark_notified = AsyncMock(return_value=True)
    sender = MagicMock()
    sender.send_message = AsyncMock(return_value=True)

    adv_id = 91_001
    campaign_name = "EKP Pause Campaign"
    await notify_empty_keywords_pause(
        shop_id=shop_id,
        adv_id=adv_id,
        campaign_name=campaign_name,
        notification_sender=sender,
        intent_manager=intent,
        session_maker=sm,
    )

    assert sm.read_only_calls == [True]
    expected_text = build_empty_keywords_pause_message(
        campaign_name=campaign_name,
        adv_id=adv_id,
        include_support_link=True,
    )
    sender.send_message.assert_awaited_once_with(
        telegram_id,
        expected_text,
        disable_web_page_preview=True,
    )

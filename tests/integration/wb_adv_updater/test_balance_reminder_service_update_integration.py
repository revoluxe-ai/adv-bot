from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.billing.event_manager.dto.event_type import EventType
from app.modules.billing.event_manager.event_manager import BillingEventManager
from app.modules.billing.event_manager.models import BillingEvent
from app.modules.common_slaves.wildberries.models import AdvSetting,WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.wb_adv_updater.modules.balance_exp_informer.models import BalanceReminder
from app.modules.wb_adv_updater.modules.balance_exp_informer.service import BalanceReminderService
from app.utils.db.models import User



pytestmark = pytest.mark.destructive_local
@pytest.mark.integration
@pytest.mark.asyncio
async def test_balance_reminder_service_update_creates_sent_reminder_and_event(
    async_engine,
    postgres_session,
) -> None:
    """Integration test: ensure BalanceReminderService.update writes balancereminder and event."""
    fixed_date = date(2026, 1, 5)

    user = User(user_telegram_id=123456789, username="test_reminder_user")
    wb_cabinet = WBCabinet(
        shop_id="test-shop-balance",
        expiration_time=(datetime.now(timezone.utc) + timedelta(days=7)).replace(
            tzinfo=None
        ),
        balance=0.0,
        bonus=0.0,
        active=True,
        demo=True,
    )
    wb_user_cabinet = WBUserCabinet(user=user, wb_cabinet=wb_cabinet, name="test-cabinet")
    adv_setting = AdvSetting(
        name="test-adv-setting",
        wb_cabinet=wb_cabinet,
        bot_active=True,
        active_status="started",
        adv_id=42,
    )

    postgres_session.add_all([user, wb_cabinet, wb_user_cabinet, adv_setting])
    await postgres_session.flush()
    await postgres_session.commit()

    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)

    with patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.service.Pricer.get_price_for_day_for_shop",
        new_callable=AsyncMock,
    ) as mock_get_price, patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.service.get_cabinet_balance",
        new_callable=AsyncMock,
    ) as mock_get_balance, patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.service.get_notification_sender",
    ) as mock_get_sender, patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.service.send_chunk",
        new_callable=AsyncMock,
    ) as mock_send_chunk, patch(
        "app.modules.wb_adv_updater.modules.balance_exp_informer.service.billing_today",
        return_value=fixed_date,
    ):
        mock_get_price.return_value = 100.0
        mock_get_balance.return_value = (0.0, 0.0)
        mock_get_sender.return_value = MagicMock()

        service = BalanceReminderService(
            session_factory=session_factory,
            event_manager=BillingEventManager(session_factory=session_factory),
        )
        await service.update()

    reminder_result = await postgres_session.execute(select(BalanceReminder))
    reminders = reminder_result.scalars().all()
    assert len(reminders) == 1
    reminder = reminders[0]
    assert reminder.status == "sent"
    assert reminder.sent_at is not None
    assert reminder.day == fixed_date
    assert reminder.user_id == user.id
    assert reminder.wb_cabinet_id == wb_cabinet.id

    event_result = await postgres_session.execute(
        select(BillingEvent).where(
            BillingEvent.event_type == EventType.BALANCE_REMINDER_SENT.value,
            BillingEvent.source == "balance_exp_informer",
        )
    )
    events = event_result.scalars().all()
    assert len(events) == 1
    event = events[0]
    assert event.user_id == user.id
    assert event.shop_id == wb_cabinet.shop_id
    assert event.user_telegram_id == user.user_telegram_id


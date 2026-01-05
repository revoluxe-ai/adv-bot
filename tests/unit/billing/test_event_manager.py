import pytest
from unittest.mock import AsyncMock

from app.modules.billing.event_manager.dto.event_type import EventType
from app.modules.billing.event_manager.event_manager import BillingEventManager
from app.modules.wb_adv_updater.modules.balance_exp_informer.dto import ReminderItem


class DummySessionContext:
    def __init__(self, session: AsyncMock) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncMock:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return False


@pytest.mark.asyncio
async def test_emit_commits_when_session_created() -> None:
    session = AsyncMock()
    session.commit = AsyncMock()
    manager = BillingEventManager(session_factory=lambda: DummySessionContext(session))
    manager._insert = AsyncMock()

    await manager.emit(
        event_type=EventType.ADD_BALANCE_CLICK,
        source="unit_test",
        user_telegram_id=1,
    )

    manager._insert.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_emit_does_not_commit_external_session() -> None:
    session = AsyncMock()
    session.commit = AsyncMock()
    manager = BillingEventManager()
    manager._insert = AsyncMock()

    await manager.emit(
        event_type=EventType.OFFERTA_SHOWN,
        source="unit_test",
        user_telegram_id=1,
        wb_cabinet_id=2,
        session=session,
    )

    manager._insert.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_emit_balance_reminder_sent_payloads_data() -> None:
    session = AsyncMock()
    manager = BillingEventManager()
    manager._insert = AsyncMock()

    reminder_item = ReminderItem(
        reminder_id=1,
        wb_cabinet_id=2,
        shop_id="shop-id",
        shop_name="Shop name",
        level=3,
        balance=42.0,
        avg_daily_spend=7.0,
        days_left=6.0,
    )

    await manager.emit_balance_reminder_sent(
        user_id=10,
        user_telegram_id=11,
        shop_id=reminder_item.shop_id,
        reminder_item=reminder_item,
        correlation_id="cid",
        session=session,
    )

    manager._insert.assert_awaited_once()
    values = manager._insert.await_args.args[1]
    assert values["event_type"] == EventType.BALANCE_REMINDER_SENT.value
    assert values["shop_id"] == reminder_item.shop_id
    assert values["payload"]["reminder_id"] == reminder_item.reminder_id
    assert values["correlation_id"] == "cid"


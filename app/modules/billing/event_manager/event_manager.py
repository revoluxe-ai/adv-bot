from __future__ import annotations

from typing import AsyncContextManager, Callable, Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.event_manager.dto import convertor
from app.modules.billing.event_manager.dto.event_type import EventType
from app.modules.billing.event_manager.models import BillingEvent
from app.modules.wb_adv_updater.modules.balance_exp_informer.dto import ReminderItem
from app.utils.db.session_maker import get_async_session_maker as sm

SessionFactory = Callable[..., AsyncContextManager[AsyncSession]]


class BillingEventManager:
    _SOURCE_CLIENT_BOT = "client_bot"
    _SOURCE_BALANCE_INFORMER = "balance_exp_informer"

    def __init__(self, session_factory: SessionFactory = sm):
        self._session_factory = session_factory

    @staticmethod
    def _build_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
        return payload.copy() if payload is not None else None

    async def emit(
        self,
        *,
        event_type: EventType,
        source: str,
        user_id: int | None = None,
        user_telegram_id: int | None = None,
        wb_cabinet_id: int | None = None,
        shop_id: str | None = None,
        amount: float | None = None,
        bonus_amount: float | None = None,
        currency: str = "RUB",
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        values = {
            "event_type": event_type.value,
            "source": source,
            "user_id": user_id,
            "user_telegram_id": user_telegram_id,
            "wb_cabinet_id": wb_cabinet_id,
            "shop_id": shop_id,
            "amount": amount,
            "bonus_amount": bonus_amount,
            "currency": currency.upper(),
            "correlation_id": correlation_id,
            "payload": self._build_payload(payload),
        }
        if session is None:
            async with self._session_factory() as session_ctx:
                await self._insert(session_ctx, values)
                await session_ctx.commit()
        else:
            await self._insert(session, values)

    async def _insert(self, session: AsyncSession, values: dict[str, Any]) -> None:
        await session.execute(insert(BillingEvent).values(**values))

    async def emit_add_balance_click(
        self,
        *,
        user_telegram_id: int,
        wb_cabinet_id: int | None,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        await self.emit(
            event_type=EventType.ADD_BALANCE_CLICK,
            source=self._SOURCE_CLIENT_BOT,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            correlation_id=correlation_id,
            payload=payload,
            session=session,
        )

    async def emit_offerta_shown(
        self,
        *,
        user_telegram_id: int,
        wb_cabinet_id: int | None,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        await self.emit(
            event_type=EventType.OFFERTA_SHOWN,
            source=self._SOURCE_CLIENT_BOT,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            correlation_id=correlation_id,
            payload=payload,
            session=session,
        )

    async def emit_offerta_confirm_click(
        self,
        *,
        user_telegram_id: int,
        wb_cabinet_id: int,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        await self.emit(
            event_type=EventType.OFFERTA_CONFIRM_CLICK,
            source=self._SOURCE_CLIENT_BOT,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            correlation_id=correlation_id,
            payload=payload,
            session=session,
        )

    async def emit_amount_prompt_shown(
        self,
        *,
        user_telegram_id: int,
        wb_cabinet_id: int,
        correlation_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        await self.emit(
            event_type=EventType.AMOUNT_PROMPT_SHOWN,
            source=self._SOURCE_CLIENT_BOT,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            correlation_id=correlation_id,
            session=session,
        )

    async def emit_amount_input(
        self,
        *,
        user_telegram_id: int,
        wb_cabinet_id: int,
        amount_text: str,
        is_valid: bool,
        parsed_amount: float | None,
        correlation_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        event_type = (
            EventType.AMOUNT_INPUT_RECEIVED if is_valid else EventType.AMOUNT_INPUT_INVALID
        )
        payload = {
            "text": amount_text,
            "is_valid": is_valid,
            "parsed_amount": parsed_amount,
        }
        await self.emit(
            event_type=event_type,
            source=self._SOURCE_CLIENT_BOT,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            correlation_id=correlation_id,
            payload=payload,
            session=session,
        )

    async def emit_invoice_sent(
        self,
        *,
        user_telegram_id: int,
        wb_cabinet_id: int,
        amount: float,
        currency: str,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        details = {"amount": amount, "currency": currency}
        if payload:
            details.update(payload)
        await self.emit(
            event_type=EventType.INVOICE_SENT,
            source=self._SOURCE_CLIENT_BOT,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            amount=amount,
            currency=currency,
            correlation_id=correlation_id,
            payload=details,
            session=session,
        )

    async def emit_pre_checkout_ok(
        self,
        *,
        user_telegram_id: int,
        wb_cabinet_id: int,
        correlation_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        await self.emit(
            event_type=EventType.PRE_CHECKOUT_OK,
            source=self._SOURCE_CLIENT_BOT,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            correlation_id=correlation_id,
            session=session,
        )

    async def emit_successful_payment_received(
        self,
        *,
        user_id: int,
        user_telegram_id: int,
        wb_cabinet_id: int,
        amount: float,
        currency: str,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        await self.emit(
            event_type=EventType.SUCCESSFUL_PAYMENT_RECEIVED,
            source=self._SOURCE_CLIENT_BOT,
            user_id=user_id,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            amount=amount,
            currency=currency,
            correlation_id=correlation_id,
            payload=payload,
            session=session,
        )

    async def emit_balance_topup_applied(
        self,
        *,
        user_id: int,
        user_telegram_id: int,
        wb_cabinet_id: int,
        amount: float,
        bonus_amount: float,
        correlation_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        await self.emit(
            event_type=EventType.BALANCE_TOPUP_APPLIED,
            source=self._SOURCE_CLIENT_BOT,
            user_id=user_id,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            amount=amount,
            bonus_amount=bonus_amount,
            correlation_id=correlation_id,
            session=session,
        )

    async def emit_balance_reminder_sent(
        self,
        *,
        user_id: int,
        user_telegram_id: int,
        shop_id: str,
        reminder_item: ReminderItem,
        correlation_id: str | None = None,
        session: AsyncSession,
    ) -> None:
        payload = convertor.build_balance_reminder_payload(reminder_item)
        await self.emit(
            event_type=EventType.BALANCE_REMINDER_SENT,
            source=self._SOURCE_BALANCE_INFORMER,
            user_id=user_id,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=reminder_item.wb_cabinet_id,
            shop_id=shop_id,
            correlation_id=correlation_id,
            payload=payload,
            session=session,
        )

    async def emit_balance_reminder_failed(
        self,
        *,
        user_id: int,
        user_telegram_id: int | None,
        shop_id: str | None,
        reminder_ids: list[int],
        error: str,
        correlation_id: str | None = None,
        session: AsyncSession,
    ) -> None:
        await self.emit(
            event_type=EventType.BALANCE_REMINDER_FAILED,
            source=self._SOURCE_BALANCE_INFORMER,
            user_id=user_id,
            user_telegram_id=user_telegram_id,
            shop_id=shop_id,
            payload={"reminder_ids": reminder_ids, "error": error},
            correlation_id=correlation_id,
            session=session,
        )

    async def emit_add_balance_context_lost(
        self,
        *,
        user_telegram_id: int,
        wb_cabinet_id: int | None = None,
        reason: str,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        details = {"reason": reason}
        if payload:
            details.update(payload)
        await self.emit(
            event_type=EventType.ADD_BALANCE_CONTEXT_LOST,
            source=self._SOURCE_CLIENT_BOT,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            correlation_id=correlation_id,
            payload=details,
            session=session,
        )

    async def emit_error_event(
        self,
        *,
        where: str,
        error: str,
        user_telegram_id: int | None = None,
        wb_cabinet_id: int | None = None,
        correlation_id: str | None = None,
        session: AsyncSession | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        details = {"where": where, "error": error}
        if payload:
            details.update(payload)
        await self.emit(
            event_type=EventType.ERROR,
            source=self._SOURCE_CLIENT_BOT,
            user_telegram_id=user_telegram_id,
            wb_cabinet_id=wb_cabinet_id,
            correlation_id=correlation_id,
            payload=details,
            session=session,
        )

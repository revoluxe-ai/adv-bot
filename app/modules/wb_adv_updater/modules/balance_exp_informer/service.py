from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timezone, timedelta
from typing import Any, AsyncIterator, Iterable

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.bot import get_bot
from app.modules.balance_manager.balance_service import get_cabinet_balance
from app.modules.billing.pricer.pricer import Pricer
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.modules.wb_adv_updater.modules.balance_exp_informer.dto import ReminderItem
from app.modules.wb_adv_updater.modules.balance_exp_informer.levels import (
    BalanceLevel,
    pick_level,
)
from app.modules.wb_adv_updater.modules.balance_exp_informer.message_builder import (
    build_message,
    chunk,
    sort_items,
)
from app.modules.wb_adv_updater.modules.balance_exp_informer.models import BalanceReminder
from app.modules.wb_adv_updater.modules.balance_exp_informer.sender import send_chunk
from app.modules.wb_adv_updater.modules.balance_exp_informer.time import billing_today
from app.utils.db.models import User

MAX_CHUNKS_PER_USER = 12
BATCH_SIZE = 10


async def iter_user_cabinets_batches(
    session: AsyncSession,
    batch_size: int = BATCH_SIZE,
) -> AsyncIterator[list[tuple[int, int, int, str, str]]]:
    """
    Yield батчи:
      (user_id, chat_id, wb_cabinet_id, shop_id, shop_name)

    ВАЖНО: keyset pagination по WBUserCabinet.id (уникальный ключ),
    иначе можно пропустить строки.
    """
    last_link_id = 0

    while True:
        stmt = (
            select(
                WBUserCabinet.id.label("link_id"),
                User.id.label("user_id"),
                User.user_telegram_id.label("chat_id"),
                WBCabinet.id.label("wb_cabinet_id"),
                WBCabinet.shop_id.label("shop_id"),
                WBUserCabinet.name.label("shop_name"),
            )
            .select_from(WBUserCabinet)
            .join(User, User.id == WBUserCabinet.user_id)
            .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id)
            .where(
                WBUserCabinet.id > last_link_id,
                # чтобы не создавать pending тем, кому нельзя отправить вообще
                User.user_telegram_id.is_not(None),
                WBCabinet.adv_settings.any(AdvSetting.bot_active.is_(True)),
            )
            .order_by(WBUserCabinet.id)
            .limit(batch_size)
        )

        result = await session.execute(stmt)
        rows = list(result.all())
        if not rows:
            break

        batch: list[tuple[int, int, int, str, str]] = []
        for row in rows:
            shop_name = (row.shop_name or "").strip()
            if not shop_name:
                shop_name = f"Кабинет {int(row.wb_cabinet_id)}"

            batch.append(
                (
                    int(row.user_id),
                    int(row.chat_id),
                    int(row.wb_cabinet_id),
                    str(row.shop_id),
                    shop_name,
                )
            )

        last_link_id = int(rows[-1].link_id)
        yield batch


class BalanceReminderService:
    def __init__(self, session_factory: Any):
        self._session_factory = session_factory
        self._logger = logging.getLogger(__name__)
        self._pricer = Pricer()

    async def update(self) -> None:
        today: date = billing_today()

        users_total: set[int] = set()
        cabinets_total = 0
        cabinets_in_zone_total = 0
        pending_created_total = 0
        messages_sent_total = 0
        send_errors_total = 0
        users_skipped_no_telegram_total = 0

        async with self._session_factory() as session:
            pending_created, cabinets_processed, in_zone, processed_users = (
                await self._create_pending(session, today)
            )
            pending_created_total += pending_created
            cabinets_total += cabinets_processed
            cabinets_in_zone_total += in_zone
            users_total.update(processed_users)

            due = await self._select_due_reminders(session, today)
            due_to_send_total = sum(len(items) for _, items in due.values())

            bot = get_bot()
            for _user_id, (chat_id, items) in due.items():
                items_sorted = sort_items(items)
                chunks = chunk(items_sorted)[:MAX_CHUNKS_PER_USER]
                for reminder_chunk in chunks:
                    text, keyboard = build_message(reminder_chunk)
                    reminder_ids = [it.reminder_id for it in reminder_chunk]
                    try:
                        await send_chunk(bot, chat_id, text, keyboard)
                        await self._mark_sent(session, reminder_ids)
                        messages_sent_total += 1
                    except Exception as exc:
                        send_errors_total += 1
                        await self._mark_failed(session, reminder_ids)
                        self._logger.error(
                            "Failed to send balance reminder chunk", exc_info=exc
                        )
                        break

            await session.commit()

        self._logger.info(
            "Balance informer run: users=%s, cabinets=%s, in_zone=%s, pending_created=%s, due=%s, messages=%s, errors=%s, skipped_no_telegram=%s",
            len(users_total),
            cabinets_total,
            cabinets_in_zone_total,
            pending_created_total,
            due_to_send_total,
            messages_sent_total,
            send_errors_total,
            users_skipped_no_telegram_total,
        )

    async def _create_pending(self, session: AsyncSession, today: date) -> tuple[int, int, int, set[int]]:
        pending_created = 0
        cabinets_processed = 0
        in_zone = 0
        processed_users: set[int] = set()

        # кеш цены по shop_id на время запуска
        price_cache: dict[str, float] = {}

        async for batch in iter_user_cabinets_batches(session, batch_size=BATCH_SIZE):
            for user_id, _chat_id, wb_cabinet_id, shop_id, shop_name in batch:
                processed_users.add(user_id)
                cabinets_processed += 1

                avg_daily_spend = price_cache.get(shop_id)
                if avg_daily_spend is None:
                    avg_daily_spend = await self._pricer.get_price_for_day_for_shop(session, shop_id)
                    price_cache[shop_id] = avg_daily_spend

                if avg_daily_spend <= 0:
                    continue

                balance, bonus = await get_cabinet_balance(wb_cabinet_id)
                total_balance = balance + bonus
                days_left = total_balance / avg_daily_spend

                level = pick_level(days_left)
                if level is None:
                    continue

                in_zone += 1
                payload = {
                    "balance": total_balance,
                    "avg_daily_spend": avg_daily_spend,
                    "days_left": days_left,
                    "shop_name": shop_name,
                }

                inserted = await self._try_create_pending(
                    session=session,
                    wb_cabinet_id=wb_cabinet_id,
                    user_id=user_id,
                    day=today,
                    level=level,
                    payload=payload,
                )
                if inserted:
                    pending_created += 1

        return pending_created, cabinets_processed, in_zone, processed_users

    @staticmethod
    async def _try_create_pending(
        session: AsyncSession,
        wb_cabinet_id: int,
        user_id: int,
        day: date,
        level: BalanceLevel,
        payload: dict[str, Any],
    ) -> bool:
        stmt = (
            pg_insert(BalanceReminder)
            .values(
                wb_cabinet_id=wb_cabinet_id,
                user_id=user_id,
                day=day,
                level=int(level),
                status="pending",
                attempts=0,
                payload=payload,
                created_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing(
                index_elements=[
                    BalanceReminder.wb_cabinet_id,
                    BalanceReminder.day,
                    BalanceReminder.level,
                ]
            )
            .returning(BalanceReminder.id)
        )
        result = await session.execute(stmt)
        inserted = result.scalar_one_or_none()
        return bool(inserted)

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    async def _select_due_reminders(
        session: AsyncSession, today: date
    ) -> dict[int, tuple[int, list[ReminderItem]]]:
        now = datetime.now(timezone.utc)

        stmt = (
            select(
                BalanceReminder,
                User.user_telegram_id,
            )
            .select_from(BalanceReminder)
            .join(User, User.id == BalanceReminder.user_id)
            .where(
                BalanceReminder.status.in_(("pending", "failed")),
                BalanceReminder.attempts < 3,
                BalanceReminder.day <= today,
                or_(
                    BalanceReminder.last_attempt_at.is_(None),
                    BalanceReminder.last_attempt_at < now - timedelta(minutes=30),
                ),
            )
        )

        result = await session.execute(stmt)
        rows = result.all()

        items_map: dict[int, list[ReminderItem]] = defaultdict(list)
        chat_map: dict[int, int] = {}

        for reminder, telegram_id in rows:
            # telegram_id может быть None на старых данных/в редких случаях.
            # Мы такие записи пропускаем, т.к. отправить всё равно некуда.
            if telegram_id is None:
                continue

            payload: dict[str, Any] = reminder.payload or {}

            shop_name = (payload.get("shop_name") or "").strip()
            if not shop_name:
                shop_name = f"Кабинет {reminder.wb_cabinet_id}"

            item = ReminderItem(
                reminder_id=reminder.id,
                wb_cabinet_id=reminder.wb_cabinet_id,
                shop_name=shop_name,
                level=reminder.level,
                balance=BalanceReminderService._to_float(payload.get("balance")),
                avg_daily_spend=BalanceReminderService._to_float(
                    payload.get("avg_daily_spend")
                ),
                days_left=BalanceReminderService._to_float(payload.get("days_left")),
            )

            items_map[reminder.user_id].append(item)
            chat_map.setdefault(reminder.user_id, int(telegram_id))

        return {
            user_id: (chat_map[user_id], items)
            for user_id, items in items_map.items()
            if user_id in chat_map
        }

    @staticmethod
    async def _mark_sent(session: AsyncSession, reminder_ids: Iterable[int]) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(BalanceReminder)
            .where(BalanceReminder.id.in_(reminder_ids))
            .values(status="sent", sent_at=now, last_attempt_at=now)
        )
        await session.execute(stmt)

    @staticmethod
    async def _mark_failed(session: AsyncSession, reminder_ids: Iterable[int]) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(BalanceReminder)
            .where(BalanceReminder.id.in_(reminder_ids))
            .values(
                status="failed",
                attempts=BalanceReminder.attempts + 1,
                last_attempt_at=now,
            )
        )
        await session.execute(stmt)

    @staticmethod
    async def _mark_failed_permanent(session: AsyncSession, reminder_ids: Iterable[int]) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(BalanceReminder)
            .where(BalanceReminder.id.in_(reminder_ids))
            .values(
                status="failed",
                attempts=3,
                last_attempt_at=now,
            )
        )
        await session.execute(stmt)
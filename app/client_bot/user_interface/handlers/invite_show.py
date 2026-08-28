"""Partner page handler shown from the existing invite entry point."""

from __future__ import annotations

import datetime
import random
import string
from datetime import UTC, timedelta
from decimal import Decimal

from aiogram import Bot, Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot import const
from app.client_bot.user_interface.views.callbacks import InviteShow
from app.modules.partner_program.partner_stats import PartnerStats, get_partner_stats
from app.utils.db.models import Invite, InviteStatus, User
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker

INVITE_TTL = timedelta(hours=24)
INVITE_COOLDOWN_DAYS = 0
CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_PART_LEN = 4
CODE_PARTS = 2


def _generate_invite_code() -> str:
    """Generate an invite code in the ``AB12-CD34`` format."""
    parts = [
        "".join(random.choices(CODE_ALPHABET, k=CODE_PART_LEN))
        for _ in range(CODE_PARTS)
    ]
    return "-".join(parts)


def _format_money(amount: Decimal) -> str:
    """Format Decimal money for compact partner-page output."""
    normalized = amount.quantize(Decimal("0.01"))
    if normalized == normalized.quantize(Decimal("1")):
        return f"{normalized.quantize(Decimal('1'))} ₽"
    return f"{normalized} ₽"


def _build_partner_keyboard() -> InlineKeyboardMarkup:
    """Return the partner page keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Запросить выплату",
                    url=const.PARTNER_PAYOUT_REQUEST_URL,
                )
            ]
        ]
    )


def _build_partner_page_text(
    *,
    invite_code: str,
    expires_at: datetime.datetime,
    stats: PartnerStats,
) -> str:
    """Render the compact partner page."""
    expires_str = expires_at.strftime("%d.%m.%Y %H:%M")
    return (
        "Инвайты / партнёрка\n\n"
        f"Ваш инвайт: {invite_code}\n"
        f"Действителен до: {expires_str}\n\n"
        f"Создано инвайтов: {stats.invite_count}\n"
        f"Использовано: {stats.used_invite_count}\n"
        f"Пришло пользователей: {stats.invited_users_count}\n"
        f"Платных пользователей: {stats.paid_users_count}\n\n"
        f"Оплаты приглашённых: {_format_money(stats.clients_paid_sum)}\n"
        f"Ваши 15%: {_format_money(stats.earned_amount)}\n"
        f"Выплачено: {_format_money(stats.paid_out_amount)}\n"
        f"К выплате: {_format_money(stats.available_to_payout)}"
    )


async def _resolve_active_invite(
    *,
    session: AsyncSession,
    user: User,
    now_utc: datetime.datetime,
) -> Invite | None:
    """Return an active invite for the user, creating one if needed."""
    active_stmt = select(Invite).where(
        Invite.issued_to_user_id == user.id,
        Invite.status == InviteStatus.ACTIVE,
    )
    active_result = await session.execute(active_stmt)
    active_invite = active_result.scalar_one_or_none()

    if active_invite is not None:
        if active_invite.expires_at >= now_utc:
            return active_invite
        await session.execute(
            update(Invite)
            .where(Invite.id == active_invite.id)
            .values(status=InviteStatus.EXPIRED)
        )
        await session.commit()

    last_issued = user.last_invite_issued_at
    if last_issued is not None:
        next_issue_at = last_issued + timedelta(days=INVITE_COOLDOWN_DAYS)
        if now_utc < next_issue_at:
            refresh_stmt = select(Invite).where(
                Invite.issued_to_user_id == user.id,
                Invite.status == InviteStatus.ACTIVE,
            )
            refresh_result = await session.execute(refresh_stmt)
            return refresh_result.scalar_one_or_none()

    for _ in range(10):
        code = _generate_invite_code()
        expires_at = now_utc + INVITE_TTL
        try:
            invite = Invite(
                code=code,
                issued_to_user_id=user.id,
                issued_at=now_utc,
                expires_at=expires_at,
                status=InviteStatus.ACTIVE,
            )
            session.add(invite)
            await session.execute(
                update(User).where(User.id == user.id).values(last_invite_issued_at=now_utc)
            )
            await session.commit()
            return invite
        except IntegrityError:
            await session.rollback()
            continue
    return None


async def load_user_by_telegram_id_in_session(
    session: AsyncSession,
    telegram_id: int,
) -> User | None:
    """Load ``User`` by telegram id within an existing session.

    Caller opens ``sm(read_only=False)`` (invite page may create invite) and
    passes the session here.
    """
    user_stmt = select(User).where(User.user_telegram_id == telegram_id)
    user_result = await session.execute(user_stmt)
    return user_result.scalar_one_or_none()


@router.callback_query(InviteShow.filter())
async def invite_show_handler(
    callback: types.CallbackQuery,
    bot: Bot,
) -> None:
    """Open the partner page from the existing invite entry point.

    Parent WRITE seam: ``sm(read_only=False)`` →
    :func:`load_user_by_telegram_id_in_session` +
    :func:`_resolve_active_invite`.
    """
    if callback.message is None:
        return

    chat_id = callback.message.chat.id
    telegram_id = callback.from_user.id
    now_utc = datetime.datetime.now(UTC).replace(tzinfo=None)

    async with _sm(read_only=False) as session:
        user = await load_user_by_telegram_id_in_session(session, telegram_id)
        if user is None:
            await bot.send_message(chat_id, "Пользователь не найден.")
            return

        active_invite = await _resolve_active_invite(
            session=session,
            user=user,
            now_utc=now_utc,
        )
        if active_invite is None:
            await bot.send_message(
                chat_id,
                "Не удалось сгенерировать уникальный код. Попробуйте позже.",
            )
            return

    stats = await get_partner_stats(user.id)
    await bot.send_message(
        chat_id,
        _build_partner_page_text(
            invite_code=active_invite.code,
            expires_at=active_invite.expires_at,
            stats=stats,
        ),
        reply_markup=_build_partner_keyboard(),
    )

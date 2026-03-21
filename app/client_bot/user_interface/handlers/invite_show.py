"""Обработчик «Показать инвайт» для пользователей с passed_gate."""

import datetime
import random
import string
from datetime import UTC, timedelta

from aiogram import Bot, Router, types
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.client_bot.user_interface.views.callbacks import InviteShow
from app.utils.db.models import Invite, InviteStatus, User
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker

# Срок действия выданного инвайта (не дольше 24 часов с момента выдачи).
INVITE_TTL = timedelta(hours=24)
INVITE_COOLDOWN_DAYS = 0
CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_PART_LEN = 4
CODE_PARTS = 2


def _generate_invite_code() -> str:
    """Генерирует код формата AB12-CD34."""
    parts = [
        "".join(random.choices(CODE_ALPHABET, k=CODE_PART_LEN))
        for _ in range(CODE_PARTS)
    ]
    return "-".join(parts)


@router.callback_query(InviteShow.filter())
async def invite_show_handler(
    callback: types.CallbackQuery,
    bot: Bot,
) -> None:
    """Показать текущий инвайт или выдать новый (с учётом TTL и кулдауна)."""
    if callback.message is None:
        return None
    chat_id = callback.message.chat.id
    telegram_id = callback.from_user.id
    now_utc = datetime.datetime.now(UTC).replace(tzinfo=None)

    async with _sm(read_only=False) as session:
        user_stmt = select(User).where(User.user_telegram_id == telegram_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            _ = await bot.send_message(
                chat_id,
                "Пользователь не найден.",
            )
            return

        # Активный инвайт пользователя
        active_stmt = (
            select(Invite)
            .where(
                Invite.issued_to_user_id == user.id,
                Invite.status == InviteStatus.ACTIVE,
            )
        )
        active_result = await session.execute(active_stmt)
        active_invite = active_result.scalar_one_or_none()

        if active_invite is not None:
            if active_invite.expires_at >= now_utc:
                expires_str = active_invite.expires_at.strftime("%d.%m.%Y %H:%M")
                _ = await bot.send_message(
                    chat_id,
                    (
                        f"Ваш инвайт: {active_invite.code}\n"
                        f"Действителен до {expires_str}."
                    ),
                )
                return
            # Истёк — переводим в EXPIRED и продолжаем
            _ = await session.execute(
                update(Invite)
                .where(Invite.id == active_invite.id)
                .values(status=InviteStatus.EXPIRED)
            )
            await session.commit()

        # Активного нет: проверяем кулдаун
        last_issued = user.last_invite_issued_at
        if last_issued is not None:
            next_issue_at = last_issued + timedelta(days=INVITE_COOLDOWN_DAYS)
            if now_utc < next_issue_at:
                next_str = next_issue_at.strftime("%d.%m.%Y %H:%M")
                _ = await bot.send_message(
                    chat_id,
                    f"Новый инвайт будет доступен после {next_str}.",
                )
                return

        # Выдаём новый инвайт
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
                _ = await session.execute(
                    update(User)
                    .where(User.id == user.id)
                    .values(last_invite_issued_at=now_utc)
                )
                await session.commit()
                expires_str = expires_at.strftime("%d.%m.%Y %H:%M")
                _ = await bot.send_message(
                    chat_id,
                    (
                        f"Ваш инвайт: {code}\n"
                        f"Действителен до {expires_str}."
                    ),
                )
                return
            except IntegrityError:
                await session.rollback()
                continue

        _ = await bot.send_message(
            chat_id,
            "Не удалось сгенерировать уникальный код. Попробуйте позже.",
        )
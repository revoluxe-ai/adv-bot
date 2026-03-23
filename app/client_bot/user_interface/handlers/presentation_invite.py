"""Общая логика активации инвайта для заявки на презентацию (без открытия полного доступа)."""

import datetime
from datetime import UTC

from sqlalchemy import select, update

from app.utils.db.models import Invite, InviteStatus
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker


def normalize_invite_code(raw: str) -> str:
    """Trim, upper, keep dashes."""
    return raw.strip().upper()


async def redeem_invite_for_presentation(
    *,
    telegram_id: int,
    user_db_id: int,
    code: str,
) -> tuple[bool, str]:
    """Атомарно списывает инвайт (ACTIVE -> USED). Не выставляет passed_gate.

    Returns:
        (True, "") при успехе
        (False, reason_for_user) при ошибке
    """
    code = normalize_invite_code(code)
    if not code:
        return False, "Введите непустой инвайт-код."

    now_utc = datetime.datetime.now(UTC).replace(tzinfo=None)

    async with _sm(read_only=False) as session:
        invite_stmt = select(Invite).where(Invite.code == code)
        invite_result = await session.execute(invite_stmt)
        invite = invite_result.scalar_one_or_none()

        if invite is None:
            return False, "Неверный инвайт-код."

        if invite.status != InviteStatus.ACTIVE:
            return False, "Этот инвайт уже использован или отозван."

        if invite.expires_at < now_utc:
            invite.status = InviteStatus.EXPIRED
            session.add(invite)
            await session.commit()
            return False, "Срок действия инвайт-кода истёк."

        update_invite_stmt = (
            update(Invite)
            .where(
                Invite.code == code,
                Invite.status == InviteStatus.ACTIVE,
                Invite.expires_at >= now_utc,
            )
            .values(
                status=InviteStatus.USED,
                used_by_user_id=user_db_id,
                used_at=now_utc,
            )
        )
        result = await session.execute(update_invite_stmt)
        rowcount = getattr(result, "rowcount", 0)
        if rowcount != 1:
            return False, "Этот инвайт уже использован или истёк."

        await session.commit()

    return True, ""

"""Create users registered via web form."""

from __future__ import annotations

import logging
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.db.models import User
from app.web.passwords import hash_password

logger = logging.getLogger(__name__)

_MAX_PLACEHOLDER_ATTEMPTS = 64


class EmailAlreadyRegisteredError(Exception):
    """Raised when normalized email is already used."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def _allocate_web_placeholder_telegram_id(session: AsyncSession) -> int:
    """Telegram user ids are positive; web-only users get unique negative 63-bit ids."""
    for _ in range(_MAX_PLACEHOLDER_ATTEMPTS):
        candidate = -(secrets.randbelow(2**63 - 1) + 1)
        exists = await session.scalar(
            select(User.id).where(User.user_telegram_id == candidate)
        )
        if exists is None:
            return candidate
    msg = "Could not allocate unique placeholder telegram id for web user"
    logger.error(msg)
    raise RuntimeError(msg)


async def register_web_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User:
    """Persist a new User with email + password_hash and a synthetic telegram id."""
    normalized = normalize_email(email)
    existing = await session.scalar(select(User.id).where(User.email == normalized))
    if existing is not None:
        raise EmailAlreadyRegisteredError()

    placeholder_tid = await _allocate_web_placeholder_telegram_id(session)
    user = User(
        user_telegram_id=placeholder_tid,
        username=None,
        email=normalized,
        password_hash=hash_password(password),
        wb_tokens=[],
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

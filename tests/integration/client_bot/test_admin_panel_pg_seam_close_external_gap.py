"""Integration coverage for admin_panel PG WRITE ``*_in_session`` seams.

Exercises injectable children with live ``async_session`` and re-reads
persisted User rows from PostgreSQL. Marked destructive_local; do not run
without ``AUTHORIZE_ONE_LIVE_RUN`` + independent re-audit.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.client_bot.user_interface.handlers.admin_panel import (
    grant_user_gate_in_session,
    reset_user_access_in_session,
)
from app.utils.db.models import User
from app.utils.db.passed_gate_reason import PassedGateReason

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


async def _make_user(
    async_session,
    *,
    telegram_id: int,
    username: str,
    passed_gate: bool = False,
    phone: str | None = None,
) -> User:
    """Create a persisted Telegram user for admin seam tests."""
    user = User(
        user_telegram_id=telegram_id,
        username=username,
        passed_gate=passed_gate,
        phone=phone,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_grant_user_gate_in_session_persists_passed_gate(
    async_session,
) -> None:
    """WRITE seam sets passed_gate + reason; re-select proves persistence."""
    telegram_id = 880011001
    user = await _make_user(
        async_session,
        telegram_id=telegram_id,
        username="admin_grant_target",
        passed_gate=False,
    )
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    updated = await grant_user_gate_in_session(
        async_session, telegram_id, now_utc=now_utc
    )
    assert updated is not None
    assert updated.id == user.id

    reread = await async_session.scalar(
        select(User).where(User.user_telegram_id == telegram_id)
    )
    assert reread is not None
    assert reread.passed_gate is True
    assert reread.passed_gate_at == now_utc
    assert reread.passed_gate_reason == PassedGateReason.ADMIN_MANUAL


@pytest.mark.asyncio
async def test_reset_user_access_in_session_clears_gate_and_phone(
    async_session,
) -> None:
    """WRITE seam clears gate/phone; re-select proves persistence."""
    telegram_id = 880011002
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    user = await _make_user(
        async_session,
        telegram_id=telegram_id,
        username="admin_reset_target",
        passed_gate=True,
        phone="+79990001122",
    )
    user.passed_gate_at = now_utc
    user.passed_gate_reason = PassedGateReason.ADMIN_MANUAL
    await async_session.commit()

    updated = await reset_user_access_in_session(async_session, telegram_id)
    assert updated is not None
    assert updated.id == user.id

    reread = await async_session.scalar(
        select(User).where(User.user_telegram_id == telegram_id)
    )
    assert reread is not None
    assert reread.passed_gate is False
    assert reread.passed_gate_at is None
    assert reread.passed_gate_reason is None
    assert reread.phone is None


@pytest.mark.asyncio
async def test_grant_user_gate_in_session_returns_none_when_missing(
    async_session,
) -> None:
    """Missing Telegram ID yields None without inventing a user row."""
    missing_id = 880011099
    result = await grant_user_gate_in_session(
        async_session,
        missing_id,
        now_utc=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    assert result is None
    assert (
        await async_session.scalar(
            select(User).where(User.user_telegram_id == missing_id)
        )
        is None
    )

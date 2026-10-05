"""Адаптер PG session factory для keyword performance readers."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.ai_package_v1.scope.pg_adv_setting_inventory_reader import (
    SessionMakerProtocol,
)
from app.utils.db.session_maker import read_only_session_maker, read_write_session_maker


def default_pg_session_factory(
    read_only: bool = False, **kwargs: object
) -> async_sessionmaker[AsyncSession]:
    """Возвращает read-only или read-write async sessionmaker (SessionMakerProtocol)."""
    _ = kwargs
    if read_only:
        return cast(async_sessionmaker[AsyncSession], read_only_session_maker)
    return cast(async_sessionmaker[AsyncSession], read_write_session_maker)


def as_session_maker_protocol(
    session_maker: SessionMakerProtocol
    | Callable[..., async_sessionmaker[AsyncSession]],
) -> SessionMakerProtocol:
    """Приводит callable к SessionMakerProtocol без type: ignore."""
    return session_maker

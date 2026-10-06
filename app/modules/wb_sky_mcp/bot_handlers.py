"""Хендлеры бота для согласия MCP. Обычный ``/start`` сюда не попадает.

Вход — только payload ``mcp_`` внутри ``start_registration``. Команда
``/chatgpt`` объясняет поток и показывает отключение, но не выпускает токен.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import CallbackQuery, Message

from app.client_bot.utils import create_user
from app.modules.wb_sky_mcp.bot_ui import (
    CANCEL_PREFIX,
    CONFIRM_PREFIX,
    DISCONNECT_PREFIX,
    cancel_text,
    connections_keyboard,
    connections_text,
    consent_keyboard,
    consent_text,
    disabled_text,
    disconnected_text,
    explain_text,
    expired_text,
    return_keyboard,
    return_text,
)
from app.modules.wb_sky_mcp.config import load_mcp_config
from app.modules.wb_sky_mcp.errors import McpError
from app.modules.wb_sky_mcp.runtime import get_mcp_broker
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router()
_sm = get_async_session_maker


class _CallbackPrefix(BaseFilter):
    """Совпадение callback_data по короткому префиксу MCP."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    async def __call__(self, query: CallbackQuery) -> bool:
        return bool(query.data and query.data.startswith(self.prefix))


def mcp_txn_id_from_start(text: str | None) -> str | None:
    """Вернуть id транзакции, если это ``/start mcp_<id>``.

    Любой другой ``/start`` возвращает None и остаётся прежним меню.
    """
    if text is None:
        return None
    parts = text.strip().split(maxsplit=1)
    if len(parts) != 2:
        return None
    command = parts[0].split("@", 1)[0].lower()
    if command != "/start":
        return None
    payload = parts[1].strip()
    prefix = "mcp_"
    if not payload.startswith(prefix):
        return None
    txn_id = payload[len(prefix) :]
    if not txn_id or any(char.isspace() for char in txn_id):
        return None
    return txn_id


async def present_mcp_start(message: Message, txn_id: str) -> None:
    """Показать согласие. Открытие ссылки не подтверждает транзакцию."""
    if not load_mcp_config().enabled:
        _ = await message.answer(disabled_text())
        return
    try:
        _view = await get_mcp_broker().inspect_start(txn_id)
    except McpError:
        logger.info("mcp start rejected")
        _ = await message.answer(expired_text())
        return
    _ = await message.answer(consent_text(), reply_markup=consent_keyboard(txn_id))


async def _bind_principal(telegram_user_id: int, username: str | None) -> int:
    """Найти или создать User тем же ``create_user``, что и обычный /start."""
    async with _sm(read_only=False) as session:
        stmt = select(User).where(User.user_telegram_id == telegram_user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            user = await create_user(session, telegram_user_id, username=username)
        return int(user.id)


@router.callback_query(_CallbackPrefix(CONFIRM_PREFIX))
async def confirm_mcp(query: CallbackQuery) -> None:
    """Кнопка подтверждения. Пишет User.id, не telegram id."""
    if query.data is None or not isinstance(query.message, Message):
        return
    txn_id = query.data[len(CONFIRM_PREFIX) :]
    try:
        view = await get_mcp_broker().confirm(
            txn_id,
            telegram_user_id=query.from_user.id,
            username=query.from_user.username,
            bind_principal=_bind_principal,
        )
    except McpError:
        logger.info("mcp confirm rejected")
        _ = await query.answer()
        _ = await query.message.answer(expired_text())
        return
    _ = await query.answer()
    _ = await query.message.answer(
        return_text(), reply_markup=return_keyboard(view.complete_url)
    )


@router.callback_query(_CallbackPrefix(CANCEL_PREFIX))
async def cancel_mcp(query: CallbackQuery) -> None:
    """Кнопка отмены. Код не выпускается; клиент получает error URL.

    Ссылка — уже собранный broker completion с ``error=access_denied``.
    Текст отмены не заменяет эту ссылку.
    """
    if query.data is None or not isinstance(query.message, Message):
        return
    txn_id = query.data[len(CANCEL_PREFIX) :]
    try:
        complete_url = await get_mcp_broker().cancel(txn_id)
    except McpError:
        logger.info("mcp cancel rejected")
        _ = await query.answer()
        _ = await query.message.answer(expired_text())
        return
    _ = await query.answer()
    _ = await query.message.answer(
        cancel_text(), reply_markup=return_keyboard(complete_url)
    )


@router.message(Command("chatgpt"))
async def chatgpt_menu(message: Message) -> None:
    """Список подключений. Команда не создаёт bearer."""
    if message.from_user is None:
        return
    if not load_mcp_config().enabled:
        _ = await message.answer(disabled_text())
        return
    try:
        principal_id = await _bind_principal(
            message.from_user.id, message.from_user.username
        )
        rows = await get_mcp_broker().list_connections(principal_id)
    except McpError:
        logger.info("mcp list rejected")
        _ = await message.answer(expired_text())
        return
    _ = await message.answer(
        explain_text() + "\n\n" + connections_text(rows),
        reply_markup=connections_keyboard(rows),
    )


@router.callback_query(_CallbackPrefix(DISCONNECT_PREFIX))
async def disconnect_mcp(query: CallbackQuery) -> None:
    """Отключить выбранное подключение текущего пользователя."""
    if query.data is None or not isinstance(query.message, Message):
        return
    connection_id = query.data[len(DISCONNECT_PREFIX) :]
    try:
        principal_id = await _bind_principal(
            query.from_user.id, query.from_user.username
        )
        _state = await get_mcp_broker().disconnect(
            user_id=principal_id, connection_id=connection_id
        )
    except McpError:
        logger.info("mcp disconnect rejected")
        _ = await query.answer()
        _ = await query.message.answer(expired_text())
        return
    _ = await query.answer()
    _ = await query.message.answer(disconnected_text())

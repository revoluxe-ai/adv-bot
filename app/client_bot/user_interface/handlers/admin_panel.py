"""Admin panel handlers for gate access and user-access reset operations.

PG WRITE для grant/reset выполняется в injectable ``*_in_session`` children;
handlers открывают ``sm(read_only=False)`` и передают session вниз.
"""

from __future__ import annotations

import datetime
from datetime import UTC

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.admin_access import IsBotAdminFilter
from app.client_bot.middlewars.channel_subscription import SUBSCRIPTION_CACHE_PREFIX
from app.client_bot.user_interface.states import AdminGrantGate, AdminResetUserAccess
from app.client_bot.user_interface.views import callbacks
from app.modules.admin_user_balance.callbacks import AdminUserBalance
from app.modules.cabinet_bonus_manager.callbacks import AdminBonus, AdminPanel
from app.core.di.app_container import AppContainer
from app.utils.db.models import User
from app.utils.db.passed_gate_reason import PassedGateReason
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker


async def grant_user_gate_in_session(
    session: AsyncSession,
    telegram_id: int,
    *,
    now_utc: datetime.datetime,
) -> User | None:
    """WRITE: открыть invite-gate пользователю по Telegram ID (admin grant).

    Caller открывает ``sm(read_only=False)`` и передаёт session сюда.
    При успехе выполняет ``commit``.

    Args:
        session: injectable async session.
        telegram_id: Telegram ID целевого пользователя.
        now_utc: значение для ``passed_gate_at`` (naive UTC).

    Returns:
        Строка ``User`` после update, либо ``None`` если пользователь не найден.
    """
    stmt = select(User).where(User.user_telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        return None
    _ = await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            passed_gate=True,
            passed_gate_at=now_utc,
            passed_gate_reason=PassedGateReason.ADMIN_MANUAL,
        )
    )
    await session.commit()
    return user


async def reset_user_access_in_session(
    session: AsyncSession,
    telegram_id: int,
) -> User | None:
    """WRITE: сбросить gate/phone поля пользователя по Telegram ID.

    Caller открывает ``sm(read_only=False)`` и передаёт session сюда.
    Очистку Redis-кэша подписки выполняет handler после этого seam.

    Args:
        session: injectable async session.
        telegram_id: Telegram ID целевого пользователя.

    Returns:
        Строка ``User``, либо ``None`` если пользователь не найден.
    """
    stmt = select(User).where(User.user_telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        return None
    _ = await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            passed_gate=False,
            passed_gate_at=None,
            passed_gate_reason=None,
            phone=None,
        )
    )
    await session.commit()
    return user


def _build_admin_keyboard() -> InlineKeyboardMarkup:
    """Return the admin panel keyboard with the user-access reset action."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Пополнение кабинетов",
                    callback_data=AdminBonus(action="menu").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Пополнение пользователей",
                    callback_data=AdminUserBalance(action="menu").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Открыть гейт по Telegram ID",
                    callback_data=AdminPanel(action="grant_gate").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="♻️ Сбросить пользователя",
                    callback_data=AdminPanel(action="reset_user_access").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=callbacks.Start().pack(),
                )
            ],
        ]
    )


def _build_cancel_keyboard() -> InlineKeyboardMarkup:
    """Return a one-button keyboard that closes the admin sub-flow."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=AdminPanel(action="menu").pack(),
                )
            ]
        ]
    )


def _build_subscription_cache_key(telegram_id: int) -> str:
    """Build the Redis key used for support-channel subscription cache."""
    return f"{SUBSCRIPTION_CACHE_PREFIX}:{telegram_id}"


@router.callback_query(
    AdminPanel.filter(F.action == "menu"),
    IsBotAdminFilter(),
)
async def show_admin_panel(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    """Show the administrator action menu."""
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Выберите действие:",
            reply_markup=_build_admin_keyboard(),
        )


@router.callback_query(
    AdminPanel.filter(F.action == "grant_gate"),
    IsBotAdminFilter(),
)
async def admin_grant_gate_start(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    """Ask for a Telegram ID to open the invite gate manually."""
    await state.set_state(AdminGrantGate.waiting_telegram_id)
    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        "Введите Telegram ID пользователя (только цифры), которому открыть доступ к боту "
        "(passed_gate).\n\n"
        "Пользователь должен уже быть в базе: хотя бы один раз нажать /start.",
        reply_markup=_build_cancel_keyboard(),
    )


@router.message(
    StateFilter(AdminGrantGate.waiting_telegram_id),
    F.text,
    IsBotAdminFilter(),
)
async def admin_grant_gate_process(
    message: types.Message,
    state: FSMContext,
) -> None:
    """Open the invite gate for the user identified by Telegram ID."""
    raw = (message.text or "").strip()
    if raw.startswith("/"):
        if raw.split()[0].lower().startswith("/cancel"):
            await state.clear()
            _ = await message.answer(
                "Отменено.",
                reply_markup=_build_admin_keyboard(),
            )
        return
    if not raw.isdigit():
        _ = await message.answer("Нужен числовой Telegram ID, например 123456789.")
        return

    telegram_id = int(raw)
    if telegram_id <= 0:
        _ = await message.answer("Некорректный Telegram ID.")
        return

    now_utc = datetime.datetime.now(UTC).replace(tzinfo=None)

    async with _sm(read_only=False) as session:
        user = await grant_user_gate_in_session(
            session, telegram_id, now_utc=now_utc
        )
    if user is None:
        _ = await message.answer(
            "Пользователь с таким Telegram ID не найден. "
            "Пусть сначала нажмёт /start в боте.",
        )
        return

    await state.clear()
    uname_disp = f"@{user.username}" if user.username else "(без username)"
    _ = await message.answer(
        f"Гейт открыт для Telegram ID `{telegram_id}` {uname_disp}.",
        reply_markup=_build_admin_keyboard(),
        parse_mode="Markdown",
    )


@router.callback_query(
    AdminPanel.filter(F.action == "reset_user_access"),
    IsBotAdminFilter(),
)
async def admin_reset_user_access_start(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    """Ask for a Telegram ID to reset access-related user data."""
    await state.set_state(AdminResetUserAccess.waiting_telegram_id)
    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        "Введите Telegram ID пользователя, которому нужно сбросить доступ.\n\n"
        "Будут очищены:\n"
        "• passed_gate\n"
        "• причина и дата открытия гейта\n"
        "• телефон в базе\n"
        "• Redis-кэш проверки подписки",
        reply_markup=_build_cancel_keyboard(),
    )


@router.message(
    StateFilter(AdminResetUserAccess.waiting_telegram_id),
    F.text,
    IsBotAdminFilter(),
)
async def admin_reset_user_access_process(
    message: types.Message,
    state: FSMContext,
) -> None:
    """Reset access-related state for a user identified by Telegram ID."""
    raw = (message.text or "").strip()
    if raw.startswith("/"):
        if raw.split()[0].lower().startswith("/cancel"):
            await state.clear()
            _ = await message.answer(
                "Отменено.",
                reply_markup=_build_admin_keyboard(),
            )
        return
    if not raw.isdigit():
        _ = await message.answer("Нужен числовой Telegram ID, например 123456789.")
        return

    telegram_id = int(raw)
    if telegram_id <= 0:
        _ = await message.answer("Некорректный Telegram ID.")
        return

    async with _sm(read_only=False) as session:
        user = await reset_user_access_in_session(session, telegram_id)
    if user is None:
        _ = await message.answer(
            "Пользователь с таким Telegram ID не найден. "
            "Пусть сначала нажмёт /start в боте.",
        )
        return

    redis_client = AppContainer().redis_client_wrapper()
    await redis_client.delete(_build_subscription_cache_key(telegram_id))

    await state.clear()
    uname_disp = f"@{user.username}" if user.username else "(без username)"
    _ = await message.answer(
        f"Доступ пользователя Telegram ID `{telegram_id}` {uname_disp} сброшен.\n"
        "Гейт закрыт, телефон очищен, кэш подписки удалён.",
        reply_markup=_build_admin_keyboard(),
        parse_mode="Markdown",
    )

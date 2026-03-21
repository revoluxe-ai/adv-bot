"""Обработчик входа в панель администратора: выбор действий и открытие гейта по Telegram ID."""

import datetime
from datetime import UTC

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select, update

from app.client_bot.admin_access import IsBotAdminFilter
from app.client_bot.user_interface.states import AdminGrantGate
from app.client_bot.user_interface.views.keyboards import get_admin_keyboard
from app.modules.cabinet_bonus_manager.callbacks import AdminPanel
from app.utils.db.models import User
from app.utils.db.passed_gate_reason import PassedGateReason
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker


@router.callback_query(
    AdminPanel.filter(F.action == "menu"),
    IsBotAdminFilter(),
)
async def show_admin_panel(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать экран выбора: пополнение кабинетов / пользователей / гейт."""
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            "Выберите действие:",
            reply_markup=get_admin_keyboard(),
        )


@router.callback_query(
    AdminPanel.filter(F.action == "grant_gate"),
    IsBotAdminFilter(),
)
async def admin_grant_gate_start(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    """Запрос Telegram ID пользователя для открытия гейта."""
    await state.set_state(AdminGrantGate.waiting_telegram_id)
    await callback.answer()
    if callback.message is None:
        return
    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=AdminPanel(action="menu").pack(),
                )
            ]
        ]
    )
    await callback.message.edit_text(
        "Введите **Telegram ID** пользователя (только цифры), которому открыть доступ к боту "
        "(passed_gate).\n\n"
        "Пользователь должен уже быть в базе (хотя бы раз нажал /start).",
        reply_markup=cancel_kb,
        parse_mode="Markdown",
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
    """Открыть гейт по введённому Telegram ID."""
    raw = (message.text or "").strip()
    if raw.startswith("/"):
        if raw.split()[0].lower().startswith("/cancel"):
            await state.clear()
            _ = await message.answer(
                "Отменено.",
                reply_markup=get_admin_keyboard(),
            )
        return
    if not raw.isdigit():
        _ = await message.answer("Нужен числовой Telegram ID (например 123456789).")
        return
    telegram_id = int(raw)
    if telegram_id <= 0:
        _ = await message.answer("Некорректный ID.")
        return

    now_utc = datetime.datetime.now(UTC).replace(tzinfo=None)

    async with _sm(read_only=False) as session:
        stmt = select(User).where(User.user_telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            _ = await message.answer(
                "Пользователь с таким Telegram ID не найден. "
                "Пусть сначала нажмёт /start в боте.",
            )
            return
        uname = user.username
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

    await state.clear()
    uname_disp = f"@{uname}" if uname else "(без username)"
    _ = await message.answer(
        f"Гейт открыт для Telegram ID `{telegram_id}` {uname_disp}.",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown",
    )

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from aiogram import Bot, F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.client_bot.admin_access import IsBotAdminFilter
from app.client_bot.presentation_booking_service import (
    create_booking,
    create_slot,
    deactivate_slot,
    format_slot_for_human,
    get_slot,
    list_available_slots,
    list_slots_for_admin,
    presentation_manager_confirm_url,
    utc_naive_to_msk,
)
from app.client_bot.support_notify import notify_presentation_booking
from app.client_bot.user_interface.states import AdminPresentationSlots
from app.client_bot.user_interface.views import callbacks
from app.modules.cabinet_bonus_manager.callbacks import AdminPanel
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router()

_SLOT_INPUT_RE = re.compile(
    r"^\s*(?P<date>\d{2}\.\d{2}\.\d{4})\s+(?P<time>\d{2}:\d{2})(?:\s+(?P<dur>\d{1,3}))?\s*$"
)


async def _build_admin_slots_markup() -> InlineKeyboardMarkup:
    slots = await list_slots_for_admin()
    builder = InlineKeyboardBuilder()

    for slot in slots:
        badge = "записан" if slot.is_booked else "свободен"
        active = "активен" if slot.is_active else "выкл"
        if slot.is_active:
            builder.row(
                InlineKeyboardButton(
                    text=f"Отключить #{slot.slot_id} ({active}, {badge})",
                    callback_data=callbacks.PresentationSlotsAdmin(
                        action="deactivate", slot_id=slot.slot_id
                    ).pack(),
                )
            )

    builder.row(
        InlineKeyboardButton(
            text="Создать слот",
            callback_data=callbacks.PresentationSlotsAdmin(action="create").pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Обновить",
            callback_data=callbacks.PresentationSlotsAdmin(action="menu").pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Назад в админку",
            callback_data=AdminPanel(action="menu").pack(),
        )
    )
    return builder.as_markup()


async def _admin_slots_text() -> str:
    slots = await list_slots_for_admin()
    if not slots:
        return "Слотов пока нет. Создайте первый слот для записи на презентацию."
    lines = ["Ближайшие слоты презентации:"]
    for slot in slots:
        status = "записан" if slot.is_booked else "свободен"
        active = "активен" if slot.is_active else "отключен"
        lines.append(f"#{slot.slot_id} {format_slot_for_human(slot)} · {status} · {active}")
    return "\n".join(lines)


def _parse_slot_input(text: str) -> tuple[datetime, int] | None:
    match = _SLOT_INPUT_RE.match(text)
    if not match:
        return None
    date_s = match.group("date")
    time_s = match.group("time")
    dur_s = match.group("dur")
    duration = int(dur_s) if dur_s else 60
    if duration < 15 or duration > 240:
        return None
    start_local = datetime.strptime(f"{date_s} {time_s}", "%d.%m.%Y %H:%M")
    start_local = start_local.replace(tzinfo=timezone(timedelta(hours=3)))
    start_utc = start_local.astimezone(UTC).replace(tzinfo=None)
    if start_utc <= datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5):
        return None
    return start_utc, duration


async def _user_is_gate_not_passed(telegram_id: int) -> bool:
    async with sm(read_only=True) as session:
        user = (
            (
                await session.execute(
                    select(User).where(User.user_telegram_id == telegram_id).limit(1)
                )
            )
            .scalars()
            .first()
        )
    if user is None:
        return False
    return not user.passed_gate


@router.callback_query(AdminPanel.filter(F.action == "presentation_slots_menu"), IsBotAdminFilter())
@router.callback_query(
    callbacks.PresentationSlotsAdmin.filter(F.action == "menu"), IsBotAdminFilter()
)
async def admin_slots_menu(
    callback: types.CallbackQuery,
) -> None:
    if callback.message is None:
        return
    await callback.message.edit_text(
        await _admin_slots_text(),
        reply_markup=await _build_admin_slots_markup(),
    )
    await callback.answer()


@router.callback_query(
    callbacks.PresentationSlotsAdmin.filter(F.action == "create"), IsBotAdminFilter()
)
async def admin_slots_create_start(
    callback: types.CallbackQuery, state: FSMContext
) -> None:
    if callback.message is None:
        return
    await state.set_state(AdminPresentationSlots.waiting_for_slot_input)
    await callback.message.edit_text(
        "Отправьте слот в формате:\n"
        "`ДД.ММ.ГГГГ ЧЧ:ММ [длительность_мин]`\n\n"
        "Пример: `11.04.2026 14:30 60`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Отмена",
                        callback_data=callbacks.PresentationSlotsAdmin(
                            action="menu"
                        ).pack(),
                    )
                ]
            ]
        ),
    )
    await callback.answer()


@router.message(StateFilter(AdminPresentationSlots.waiting_for_slot_input), IsBotAdminFilter(), F.text)
async def admin_slots_create_finish(
    message: types.Message, state: FSMContext
) -> None:
    assert message.from_user
    assert message.text
    parsed = _parse_slot_input(message.text)
    if parsed is None:
        await message.answer(
            "Не удалось распознать формат. Используйте:\n"
            "`ДД.ММ.ГГГГ ЧЧ:ММ [длительность_мин]`\n"
            "Пример: `11.04.2026 14:30 60`",
            parse_mode="Markdown",
        )
        return

    start_utc, duration = parsed
    slot = await create_slot(
        start_at_utc=start_utc,
        duration_minutes=duration,
        admin_telegram_id=message.from_user.id,
    )
    await state.clear()
    start_msk = utc_naive_to_msk(slot.start_at)
    await message.answer(
        f"Слот создан: #{slot.id} {start_msk:%d.%m.%Y %H:%M} МСК, {slot.duration_minutes} мин."
    )
    await message.answer(
        await _admin_slots_text(),
        reply_markup=await _build_admin_slots_markup(),
    )


@router.callback_query(
    callbacks.PresentationSlotsAdmin.filter(F.action == "deactivate"), IsBotAdminFilter()
)
async def admin_slots_deactivate(
    callback: types.CallbackQuery, callback_data: callbacks.PresentationSlotsAdmin
) -> None:
    slot_id = callback_data.slot_id
    if slot_id is None:
        await callback.answer("Не найден slot_id", show_alert=True)
        return
    changed = await deactivate_slot(slot_id)
    await callback.answer("Слот отключен" if changed else "Слот уже отключен")
    if callback.message is None:
        return
    await callback.message.edit_text(
        await _admin_slots_text(),
        reply_markup=await _build_admin_slots_markup(),
    )


@router.callback_query(callbacks.PresentationBooking.filter(F.action == "menu"))
async def booking_menu(callback: types.CallbackQuery) -> None:
    if callback.message is None or callback.from_user is None:
        return
    if not await _user_is_gate_not_passed(callback.from_user.id):
        await callback.answer("Запись доступна только на входе до прохождения гейта.", show_alert=True)
        return
    slots = await list_available_slots()
    builder = InlineKeyboardBuilder()
    if slots:
        for slot in slots:
            builder.row(
                InlineKeyboardButton(
                    text=format_slot_for_human(slot),
                    callback_data=callbacks.PresentationBooking(
                        action="pick", slot_id=slot.slot_id
                    ).pack(),
                )
            )
        text = "Выберите свободный слот для презентации:"
    else:
        text = (
            "Пока нет свободных слотов для презентации.\n"
            "Нажмите «Обновить» или попробуйте позже."
        )
    builder.row(
        InlineKeyboardButton(
            text="Обновить",
            callback_data=callbacks.PresentationBooking(action="menu").pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=callbacks.Start().pack(),
        )
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(callbacks.PresentationBooking.filter(F.action == "pick"))
async def booking_pick_slot(
    callback: types.CallbackQuery, callback_data: callbacks.PresentationBooking
) -> None:
    if callback.message is None:
        return
    slot_id = callback_data.slot_id
    if slot_id is None:
        await callback.answer("Слот не найден", show_alert=True)
        return
    slot = await get_slot(slot_id)
    if slot is None or not slot.is_active or slot.is_booked:
        await callback.answer("Слот больше недоступен", show_alert=True)
        await booking_menu(callback)
        return
    text = f"Запись на презентацию:\n{format_slot_for_human(slot)}"
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Записаться на этот слот",
                    callback_data=callbacks.PresentationBooking(
                        action="confirm", slot_id=slot.slot_id
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад к слотам",
                    callback_data=callbacks.PresentationBooking(action="menu").pack(),
                )
            ],
        ]
    )
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(callbacks.PresentationBooking.filter(F.action == "confirm"))
async def booking_confirm(
    callback: types.CallbackQuery,
    callback_data: callbacks.PresentationBooking,
    bot: Bot,
) -> None:
    if callback.message is None or callback.from_user is None:
        return
    slot_id = callback_data.slot_id
    if slot_id is None:
        await callback.answer("Слот не найден", show_alert=True)
        return
    result = await create_booking(slot_id, callback.from_user.id)
    if result != "ok":
        await callback.answer("Слот уже занят или недоступен.", show_alert=True)
        await booking_menu(callback)
        return
    slot = await get_slot(slot_id)
    if slot is None:
        await callback.answer("Запись создана, но слот не найден.", show_alert=True)
        return

    slot_human = format_slot_for_human(slot)
    await notify_presentation_booking(
        bot,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        slot_text=slot_human,
    )
    manager_url = presentation_manager_confirm_url(slot_human)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Связаться с менеджером",
                    url=manager_url,
                )
            ]
        ]
    )
    await callback.message.edit_text(
        "Вы записаны на презентацию.\n"
        f"Слот: {slot_human}\n\n"
        "Нажмите кнопку ниже, чтобы связаться с менеджером.",
        reply_markup=keyboard,
    )
    await callback.answer("Запись подтверждена")

"""Admin panel handlers: gate/reset seams, partner stats and payouts.

PG WRITE для grant/reset выполняется в injectable ``*_in_session`` children;
handlers открывают ``sm(read_only=False)`` и передают session вниз.
Partner list/detail/payout — отдельные admin-flow поверх ``partner_stats``.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal, InvalidOperation

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.admin_access import IsBotAdminFilter
from app.client_bot.middlewars.channel_subscription import SUBSCRIPTION_CACHE_PREFIX
from app.client_bot.user_interface.states import (
    AdminGrantGate,
    AdminPartnerList,
    AdminPartnerPayout,
    AdminResetUserAccess,
)
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import PartnerAdminAction
from app.core.di.app_container import AppContainer
from app.modules.admin_user_balance.callbacks import AdminUserBalance
from app.modules.cabinet_bonus_manager.callbacks import AdminBonus, AdminPanel
from app.modules.partner_program.partner_stats import (
    PartnerAdminStatsRow,
    create_partner_payout,
    get_partner_stats,
    list_partner_stats,
)
from app.utils.db.models import User
from app.utils.db.passed_gate_reason import PassedGateReason
from app.utils.db.session_maker import get_async_session_maker

router = Router()
_sm = get_async_session_maker

_PARTNER_LIST_PAGE_SIZE = 8
_PARTNER_STATE_PREFIX = "client_bot:partner_admin_state"
_SORT_INVITED = "invited_desc"
_SORT_EARNED = "earned_desc"
_SORT_PAID_OUT = "paid_out_desc"
_DEFAULT_SORT = _SORT_INVITED


@dataclass(slots=True)
class _PartnerAdminListState:
    """Persisted admin UI state for the partner list screen."""

    page: int = 1
    sort_key: str = _DEFAULT_SORT
    filter_value: str | None = None
    selected_partner_user_id: int | None = None


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


def _format_money(amount: Decimal) -> str:
    """Format Decimal money for compact admin messages."""
    normalized = amount.quantize(Decimal("0.01"))
    if normalized == normalized.quantize(Decimal("1")):
        return f"{normalized.quantize(Decimal('1'))}₽"
    return f"{normalized}₽"


def _partner_display_name(row: PartnerAdminStatsRow) -> str:
    """Build a compact partner label for list rows."""
    if row.username:
        return f"@{row.username}"
    if row.user_telegram_id is not None:
        return f"tg:{row.user_telegram_id}"
    return f"ID {row.partner_user_id}"


def _build_admin_keyboard() -> InlineKeyboardMarkup:
    """Return the admin panel keyboard with partner statistics actions."""
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
                    text="📊 Статистика партнёров",
                    callback_data=PartnerAdminAction(action="list").pack(),
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
    """Return a one-button keyboard that closes the current admin sub-flow."""
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


def _build_partner_state_key(admin_telegram_id: int) -> str:
    """Build the Redis key for persisted admin partner-list state."""
    return f"{_PARTNER_STATE_PREFIX}:{admin_telegram_id}"


async def _load_partner_list_state(admin_telegram_id: int) -> _PartnerAdminListState:
    """Load persisted list state from Redis or return defaults."""
    redis_client = AppContainer().redis_client_wrapper()
    raw = await redis_client.get(_build_partner_state_key(admin_telegram_id))
    if not raw:
        return _PartnerAdminListState()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return _PartnerAdminListState()
    return _PartnerAdminListState(
        page=max(1, int(payload.get("page", 1))),
        sort_key=str(payload.get("sort_key", _DEFAULT_SORT)),
        filter_value=(
            str(payload["filter_value"]) if payload.get("filter_value") is not None else None
        ),
        selected_partner_user_id=(
            int(payload["selected_partner_user_id"])
            if payload.get("selected_partner_user_id") is not None
            else None
        ),
    )


async def _save_partner_list_state(
    admin_telegram_id: int,
    state: _PartnerAdminListState,
) -> None:
    """Persist admin partner-list state to Redis."""
    payload = json.dumps(
        {
            "page": state.page,
            "sort_key": state.sort_key,
            "filter_value": state.filter_value,
            "selected_partner_user_id": state.selected_partner_user_id,
        },
        ensure_ascii=False,
    )
    redis_client = AppContainer().redis_client_wrapper()
    await redis_client.set(_build_partner_state_key(admin_telegram_id), payload)


def _apply_partner_filter(
    rows: list[PartnerAdminStatsRow],
    filter_value: str | None,
) -> list[PartnerAdminStatsRow]:
    """Filter partners by internal user id or telegram id."""
    if not filter_value:
        return rows
    value = filter_value.strip()
    if not value:
        return rows
    if value.isdigit():
        numeric = int(value)
        return [
            row
            for row in rows
            if row.partner_user_id == numeric or row.user_telegram_id == numeric
        ]
    lowered = value.lower()
    return [
        row
        for row in rows
        if row.username is not None and lowered in row.username.lower()
    ]


def _apply_partner_sort(
    rows: list[PartnerAdminStatsRow],
    sort_key: str,
) -> list[PartnerAdminStatsRow]:
    """Sort partner rows for the admin list."""
    if sort_key == _SORT_EARNED:
        return sorted(
            rows,
            key=lambda row: (row.earned_amount, row.partner_user_id),
            reverse=True,
        )
    if sort_key == _SORT_PAID_OUT:
        return sorted(
            rows,
            key=lambda row: (row.paid_out_amount, row.partner_user_id),
            reverse=True,
        )
    return sorted(
        rows,
        key=lambda row: (row.invited_users_count, row.partner_user_id),
        reverse=True,
    )


def _slice_partner_rows(
    rows: list[PartnerAdminStatsRow],
    page: int,
) -> tuple[list[PartnerAdminStatsRow], int]:
    """Paginate the filtered/sorted partner rows."""
    total_pages = max(1, (len(rows) + _PARTNER_LIST_PAGE_SIZE - 1) // _PARTNER_LIST_PAGE_SIZE)
    current_page = min(max(1, page), total_pages)
    start = (current_page - 1) * _PARTNER_LIST_PAGE_SIZE
    end = start + _PARTNER_LIST_PAGE_SIZE
    return rows[start:end], total_pages


def _build_partner_list_text(
    all_rows: list[PartnerAdminStatsRow],
    filtered_rows: list[PartnerAdminStatsRow],
    state: _PartnerAdminListState,
    *,
    total_pages: int,
) -> str:
    """Render the summary-only admin partner statistics page."""
    total_partners = len(filtered_rows)
    total_invited = sum(row.invited_users_count for row in filtered_rows)
    total_paid_users = sum(row.paid_users_count for row in filtered_rows)
    total_paid_sum = sum((row.clients_paid_sum for row in filtered_rows), Decimal("0.00"))
    total_earned = sum((row.earned_amount for row in filtered_rows), Decimal("0.00"))
    total_paid_out = sum((row.paid_out_amount for row in filtered_rows), Decimal("0.00"))
    total_available = sum(
        (row.available_to_payout for row in filtered_rows),
        Decimal("0.00"),
    )
    lines = [
        "Статистика партнёров",
        "",
        f"Всего партнёров: {total_partners}",
        f"Всего приглашённых пользователей: {total_invited}",
        f"Всего платных пользователей: {total_paid_users}",
        f"Всего оплат приглашённых: {_format_money(total_paid_sum)}",
        f"Всего заработано партнёрами: {_format_money(total_earned)}",
        f"Всего выплачено: {_format_money(total_paid_out)}",
        f"Всего к выплате: {_format_money(total_available)}",
        "",
        "Введите User.id или Telegram ID для фильтра.",
        f"Сортировка: {_sort_label(state.sort_key)}",
        f"Страница: {state.page}/{total_pages}",
    ]
    if state.filter_value:
        lines.append(f"Фильтр: {state.filter_value}")
    if not filtered_rows:
        lines.append("")
        lines.append("Партнёры не найдены")
    return "\n".join(lines)


def _partner_button_text(row: PartnerAdminStatsRow) -> str:
    """Return the compact partner button label."""
    return (
        f"{_partner_display_name(row)} | ID {row.partner_user_id} — "
        f"{row.invited_users_count} / {row.paid_users_count} / "
        f"{_format_money(row.available_to_payout)}"
    )[:64]


def _sort_label(sort_key: str) -> str:
    """Return a human-readable sort label."""
    if sort_key == _SORT_EARNED:
        return "по заработку ↓"
    if sort_key == _SORT_PAID_OUT:
        return "по выплатам ↓"
    return "по привлечению ↓"


def _build_partner_list_keyboard(
    rows: list[PartnerAdminStatsRow],
    state: _PartnerAdminListState,
    *,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Return partner list buttons, sort controls, and pagination."""
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="Привлечение ↓",
                callback_data=PartnerAdminAction(
                    action="sort",
                    sort_key=_SORT_INVITED,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="Заработок ↓",
                callback_data=PartnerAdminAction(
                    action="sort",
                    sort_key=_SORT_EARNED,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="Выплаты ↓",
                callback_data=PartnerAdminAction(
                    action="sort",
                    sort_key=_SORT_PAID_OUT,
                ).pack(),
            ),
        ]
    )
    for row in rows:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=_partner_button_text(row),
                    callback_data=PartnerAdminAction(
                        action="detail",
                        partner_user_id=row.partner_user_id,
                    ).pack(),
                )
            ]
        )
    pager_row: list[InlineKeyboardButton] = []
    if state.page > 1:
        pager_row.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=PartnerAdminAction(
                    action="page",
                    page=state.page - 1,
                ).pack(),
            )
        )
    if state.page < total_pages:
        pager_row.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=PartnerAdminAction(
                    action="page",
                    page=state.page + 1,
                ).pack(),
            )
        )
    if pager_row:
        inline_keyboard.append(pager_row)
    action_row = [
        InlineKeyboardButton(
            text="Сбросить фильтр",
            callback_data=PartnerAdminAction(action="clear_filter").pack(),
        ),
        InlineKeyboardButton(
            text="Назад",
            callback_data=AdminPanel(action="menu").pack(),
        ),
    ]
    inline_keyboard.append(action_row)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def _get_partner_row(partner_user_id: int) -> PartnerAdminStatsRow:
    """Load one partner row from the aggregated admin list."""
    rows = await list_partner_stats()
    for row in rows:
        if row.partner_user_id == partner_user_id:
            return row
    raise RuntimeError(f"Partner user {partner_user_id} was not found.")


async def _build_partner_detail_text(partner_user_id: int) -> str:
    """Render a detailed admin card for one partner."""
    row = await _get_partner_row(partner_user_id)
    stats = await get_partner_stats(partner_user_id)
    return (
        "Карточка партнёра\n\n"
        f"username: {row.username or '—'}\n"
        f"User.id: {row.partner_user_id}\n"
        f"telegram_id: {row.user_telegram_id or '—'}\n"
        f"phone: {row.phone or '—'}\n\n"
        f"invite_count: {stats.invite_count}\n"
        f"used_invite_count: {stats.used_invite_count}\n"
        f"invited_users_count: {stats.invited_users_count}\n"
        f"paid_users_count: {stats.paid_users_count}\n\n"
        f"clients_paid_sum: {_format_money(stats.clients_paid_sum)}\n"
        f"earned_amount: {_format_money(stats.earned_amount)}\n"
        f"paid_out_amount: {_format_money(stats.paid_out_amount)}\n"
        f"available_to_payout: {_format_money(stats.available_to_payout)}"
    )


def _build_partner_detail_keyboard(partner_user_id: int) -> InlineKeyboardMarkup:
    """Return the partner detail action keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сделать выплату",
                    callback_data=PartnerAdminAction(
                        action="payout",
                        partner_user_id=partner_user_id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад к списку",
                    callback_data=PartnerAdminAction(action="list").pack(),
                )
            ],
        ]
    )


async def get_admin_user_db_id_in_session(
    session: AsyncSession,
    admin_telegram_id: int,
) -> int:
    """Resolve internal ``User.id`` for an admin telegram id in an open session.

    Caller opens ``sm(read_only=True)`` and passes the session here.
    """
    stmt = select(User.id).where(User.user_telegram_id == admin_telegram_id)
    result = await session.execute(stmt)
    admin_user_id = result.scalar_one_or_none()
    if admin_user_id is None:
        raise RuntimeError(
            f"Admin user with telegram_id {admin_telegram_id} was not found."
        )
    return int(admin_user_id)


async def _get_admin_user_db_id(admin_telegram_id: int) -> int:
    """Resolve the internal ``User.id`` for the admin performing the payout.

    Parent PURE_READ seam: ``sm(read_only=True)`` →
    :func:`get_admin_user_db_id_in_session`.
    """
    async with _sm(read_only=True) as session:
        return await get_admin_user_db_id_in_session(session, admin_telegram_id)


async def _render_partner_list(
    callback: types.CallbackQuery,
    admin_telegram_id: int,
    state: FSMContext,
) -> None:
    """Load rows, apply filter/sort/pagination, and render the admin list."""
    if not isinstance(callback.message, Message):
        return
    stored_state = await _load_partner_list_state(admin_telegram_id)
    rows = await list_partner_stats()
    filtered_rows = _apply_partner_filter(rows, stored_state.filter_value)
    sorted_rows = _apply_partner_sort(filtered_rows, stored_state.sort_key)
    paged_rows, total_pages = _slice_partner_rows(sorted_rows, stored_state.page)
    stored_state.page = min(max(1, stored_state.page), total_pages)
    await _save_partner_list_state(admin_telegram_id, stored_state)
    await state.set_state(AdminPartnerList.waiting_filter)
    await callback.message.edit_text(
        _build_partner_list_text(rows, filtered_rows, stored_state, total_pages=total_pages),
        reply_markup=_build_partner_list_keyboard(
            paged_rows,
            stored_state,
            total_pages=total_pages,
        ),
    )


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
    PartnerAdminAction.filter(F.action == "list"),
    IsBotAdminFilter(),
)
async def show_partner_stats_list(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    """Show the admin list of partner statistics."""
    stored_state = await _load_partner_list_state(callback.from_user.id)
    stored_state.selected_partner_user_id = None
    await _save_partner_list_state(callback.from_user.id, stored_state)
    await _render_partner_list(callback, callback.from_user.id, state)


@router.callback_query(
    PartnerAdminAction.filter(F.action == "sort"),
    IsBotAdminFilter(),
)
async def sort_partner_stats_list(
    callback: types.CallbackQuery,
    callback_data: PartnerAdminAction,
    state: FSMContext,
) -> None:
    """Change sort mode and rerender the partner list."""
    stored_state = await _load_partner_list_state(callback.from_user.id)
    stored_state.sort_key = callback_data.sort_key or _DEFAULT_SORT
    stored_state.page = 1
    await _save_partner_list_state(callback.from_user.id, stored_state)
    await _render_partner_list(callback, callback.from_user.id, state)


@router.callback_query(
    PartnerAdminAction.filter(F.action == "page"),
    IsBotAdminFilter(),
)
async def paginate_partner_stats_list(
    callback: types.CallbackQuery,
    callback_data: PartnerAdminAction,
    state: FSMContext,
) -> None:
    """Change page and rerender the partner list."""
    stored_state = await _load_partner_list_state(callback.from_user.id)
    stored_state.page = max(1, callback_data.page or 1)
    await _save_partner_list_state(callback.from_user.id, stored_state)
    await _render_partner_list(callback, callback.from_user.id, state)


@router.callback_query(
    PartnerAdminAction.filter(F.action == "clear_filter"),
    IsBotAdminFilter(),
)
async def clear_partner_stats_filter(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    """Clear the persisted list filter and rerender the partner list."""
    stored_state = await _load_partner_list_state(callback.from_user.id)
    stored_state.filter_value = None
    stored_state.page = 1
    await _save_partner_list_state(callback.from_user.id, stored_state)
    await _render_partner_list(callback, callback.from_user.id, state)


@router.message(
    StateFilter(AdminPartnerList.waiting_filter),
    F.text,
    IsBotAdminFilter(),
)
async def filter_partner_stats_list(
    message: types.Message,
    state: FSMContext,
) -> None:
    """Apply an ID filter to the partner list and rerender it."""
    if message.from_user is None:
        return
    raw = (message.text or "").strip()
    if raw.startswith("/"):
        return
    stored_state = await _load_partner_list_state(message.from_user.id)
    stored_state.filter_value = raw or None
    stored_state.page = 1
    await _save_partner_list_state(message.from_user.id, stored_state)
    rows = await list_partner_stats()
    filtered_rows = _apply_partner_filter(rows, stored_state.filter_value)
    sorted_rows = _apply_partner_sort(filtered_rows, stored_state.sort_key)
    paged_rows, total_pages = _slice_partner_rows(sorted_rows, stored_state.page)
    await message.answer(
        _build_partner_list_text(rows, filtered_rows, stored_state, total_pages=total_pages),
        reply_markup=_build_partner_list_keyboard(
            paged_rows,
            stored_state,
            total_pages=total_pages,
        ),
    )


@router.callback_query(
    PartnerAdminAction.filter(F.action == "detail"),
    IsBotAdminFilter(),
)
async def show_partner_detail(
    callback: types.CallbackQuery,
    callback_data: PartnerAdminAction,
) -> None:
    """Show the detailed admin card for one partner."""
    if (
        not isinstance(callback.message, Message)
        or callback_data.partner_user_id is None
    ):
        return
    stored_state = await _load_partner_list_state(callback.from_user.id)
    stored_state.selected_partner_user_id = callback_data.partner_user_id
    await _save_partner_list_state(callback.from_user.id, stored_state)
    await callback.message.edit_text(
        await _build_partner_detail_text(callback_data.partner_user_id),
        reply_markup=_build_partner_detail_keyboard(callback_data.partner_user_id),
    )


@router.callback_query(
    PartnerAdminAction.filter(F.action == "payout"),
    IsBotAdminFilter(),
)
async def start_partner_payout(
    callback: types.CallbackQuery,
    callback_data: PartnerAdminAction,
    state: FSMContext,
) -> None:
    """Start the partner payout flow and ask the admin for the amount."""
    if (
        not isinstance(callback.message, Message)
        or callback_data.partner_user_id is None
    ):
        return
    stats = await get_partner_stats(callback_data.partner_user_id)
    stored_state = await _load_partner_list_state(callback.from_user.id)
    stored_state.selected_partner_user_id = callback_data.partner_user_id
    await _save_partner_list_state(callback.from_user.id, stored_state)
    await state.update_data(partner_user_id=callback_data.partner_user_id)
    await state.set_state(AdminPartnerPayout.waiting_amount)
    await callback.message.edit_text(
        (
            f"Введите сумму выплаты для партнёра {callback_data.partner_user_id}.\n\n"
            f"Доступно к выплате: {_format_money(stats.available_to_payout)}"
        ),
        reply_markup=_build_cancel_keyboard(),
    )


@router.message(
    StateFilter(AdminPartnerPayout.waiting_amount),
    F.text,
    IsBotAdminFilter(),
)
async def process_partner_payout_amount(
    message: types.Message,
    state: FSMContext,
) -> None:
    """Create a partner payout from the admin-provided amount."""
    if message.from_user is None:
        return
    raw = (message.text or "").strip().replace(",", ".")
    if raw.startswith("/"):
        if raw.split()[0].lower().startswith("/cancel"):
            await state.clear()
            _ = await message.answer(
                "Отменено.",
                reply_markup=_build_admin_keyboard(),
            )
        return

    try:
        Decimal(raw)
    except InvalidOperation:
        _ = await message.answer(
            "Сумма выплаты должна быть числом.",
            reply_markup=_build_cancel_keyboard(),
        )
        return

    state_data = await state.get_data()
    partner_user_id = state_data.get("partner_user_id")
    if not isinstance(partner_user_id, int):
        raise RuntimeError("Partner user id was not saved in the payout state.")

    admin_user_id = await _get_admin_user_db_id(message.from_user.id)
    try:
        _ = await create_partner_payout(
            partner_user_id=partner_user_id,
            admin_user_id=admin_user_id,
            amount=raw,
        )
    except ValueError as exc:
        _ = await message.answer(str(exc), reply_markup=_build_cancel_keyboard())
        return

    await state.clear()
    _ = await message.answer(
        await _build_partner_detail_text(partner_user_id),
        reply_markup=_build_partner_detail_keyboard(partner_user_id),
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

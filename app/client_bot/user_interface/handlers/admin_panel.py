"""Обработчик входа в панель администратора: показ выбора (кабинеты / пользователи)."""

from aiogram import F, Router, types

from app.client_bot.const import ADMINS
from app.client_bot.user_interface.views.keyboards import get_admin_keyboard
from app.modules.cabinet_bonus_manager.callbacks import AdminPanel

router = Router()


@router.callback_query(
    AdminPanel.filter(F.action == "menu"),
    F.from_user.id.in_(ADMINS),
)
async def show_admin_panel(
    callback: types.CallbackQuery,
    callback_data: AdminPanel,
) -> None:
    """Показать экран выбора: пополнение кабинетов или пользователей."""
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            "Выберите действие:",
            reply_markup=get_admin_keyboard(),
        )

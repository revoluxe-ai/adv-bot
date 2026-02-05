"""
Сцена пополнения личного баланса пользователей администратором.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, SceneRegistry, SceneWizard, on
from aiogram.types import CallbackQuery, Message

from app.client_bot.const import ADMINS
from app.client_bot.user_interface.views.keyboards import get_admin_keyboard
from app.modules.admin_user_balance.callbacks import AdminUserBalance
from app.modules.admin_user_balance.keyboards import (
    get_confirm_keyboard,
    get_user_balance_keyboard,
)
from app.modules.balance_manager.exceptions import InvalidAmountError, UserNotFoundError
from app.modules.balance_manager.user_balance_service import (
    add_user_balance,
    add_user_bonus,
    get_user_balance,
)

logger = logging.getLogger(__name__)

OPERATION_NAMES = {"add_balance": "пополнение баланса", "add_bonus": "начисление бонусов"}


class UserBalanceScene(Scene, state="user_balance_scene"):
    """Сцена для пополнения баланса пользователей администратором."""

    def __init__(self, wizard: SceneWizard):
        super().__init__(wizard)
        self.state_context: FSMContext | None = None

    @on.message.enter()
    async def enter_scene(self, message: Message, state: FSMContext) -> None:
        """Вход в сцену по команде."""
        logger.info("Вход в сцену пополнения баланса пользователей")
        self.state_context = state
        await state.update_data(action="menu")
        await message.answer("Введите telegram_id пользователя:")

    @on.callback_query.enter(AdminUserBalance.filter(F.action == "menu"))
    async def enter_scene_from_callback(
        self, callback: CallbackQuery, bot: Bot, state: FSMContext
    ) -> None:
        """Вход в сцену через callback из панели админа."""
        logger.info("Вход в сцену пополнения баланса пользователей через callback")
        self.state_context = state
        await state.update_data(action="menu")
        if callback.message:
            await callback.message.edit_text("Введите telegram_id пользователя:")
        else:
            await bot.send_message(
                callback.from_user.id, "Введите telegram_id пользователя:"
            )
        return

    @on.message(Command("start"))
    async def handle_start_command(self, message: Message, state: FSMContext) -> None:
        """Выход из сцены по /start (глобальный обработчик покажет список магазинов)."""
        await state.clear()
        await self.wizard.exit()

    @on.message(F.text)
    async def process_message(self, message: Message, state: FSMContext) -> None:
        """Обработка ввода: telegram_id, сумма, комментарий."""
        data = await state.get_data()
        action = data.get("action")

        if action == "menu":
            raw = message.text.strip()
            if not raw or not raw.lstrip("-").isdigit():
                await message.answer(
                    "Введите корректный telegram_id (целое число):"
                )
                return
            user_telegram_id = int(raw)
            try:
                balance, bonus = await get_user_balance(user_telegram_id)
            except UserNotFoundError:
                await message.answer(
                    f"Пользователь с telegram_id {user_telegram_id} не найден. "
                    "Введите другой telegram_id:"
                )
                return
            await state.update_data(
                user_telegram_id=user_telegram_id,
                current_balance=balance,
                current_bonus=bonus,
            )
            await message.answer(
                f"👤 Пользователь: {user_telegram_id}\n"
                f"💰 Баланс: {balance:.0f} руб.\n"
                f"🎁 Бонусы: {bonus:.0f} руб.\n\n"
                f"Выберите действие:",
                reply_markup=get_user_balance_keyboard(),
            )
            return

        if action == "amount":
            try:
                amount = float(message.text.strip().replace(",", "."))
                if amount <= 0:
                    raise ValueError("Сумма должна быть положительной")
            except ValueError:
                await message.answer("Введите корректную сумму (положительное число):")
                return
            operation = data.get("operation")
            await state.update_data(amount=amount, action="description")
            op_name = OPERATION_NAMES.get(operation, operation)
            await message.answer(
                f"Операция: {op_name}\nСумма: {amount:.0f} руб.\n\n"
                "Введите комментарий (или «-» чтобы пропустить):"
            )
            return

        if action == "description":
            description = message.text.strip()
            if description == "-":
                description = None
            await state.update_data(description=description, action="confirm")
            data = await state.get_data()
            user_telegram_id = data["user_telegram_id"]
            amount = data["amount"]
            operation = data["operation"]
            op_name = OPERATION_NAMES.get(operation, operation)
            balance = data.get("current_balance", 0)
            bonus = data.get("current_bonus", 0)
            confirm_text = (
                f"👤 Пользователь: {user_telegram_id}\n"
                f"💰 Текущий баланс: {balance:.0f} руб. | Бонусы: {bonus:.0f} руб.\n\n"
                f"Операция: {op_name}\n"
                f"Сумма: {amount:.0f} руб.\n"
                f"Комментарий: {description or '—'}\n\n"
                "Подтвердите операцию:"
            )
            await message.answer(
                confirm_text,
                reply_markup=get_confirm_keyboard(operation),
            )
            return

    @on.callback_query(AdminUserBalance.filter(F.action.in_(["add_balance", "add_bonus"])))
    async def process_add_callback(
        self,
        callback: CallbackQuery,
        callback_data: AdminUserBalance,
        state: FSMContext,
    ) -> None:
        """Переход к вводу суммы для пополнения баланса или бонусов."""
        await callback.answer()
        self.state_context = state
        await state.update_data(operation=callback_data.action, action="amount")
        data = await state.get_data()
        balance = data.get("current_balance", 0)
        bonus = data.get("current_bonus", 0)
        user_telegram_id = data.get("user_telegram_id")
        op_name = OPERATION_NAMES.get(callback_data.action, callback_data.action)
        if callback.message:
            await callback.message.edit_text(
                f"👤 Пользователь: {user_telegram_id}\n"
                f"💰 Баланс: {balance:.0f} руб. | Бонусы: {bonus:.0f} руб.\n\n"
                f"Введите сумму для {op_name}:"
            )

    @on.callback_query(AdminUserBalance.filter(F.action == "menu"))
    async def back_to_telegram_id(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Возврат к вводу telegram_id (другой пользователь)."""
        await callback.answer()
        self.state_context = state
        await state.update_data(action="menu")
        if callback.message:
            await callback.message.edit_text("Введите telegram_id пользователя:")

    @on.callback_query(AdminUserBalance.filter(F.action == "confirm"))
    async def process_confirm(
        self,
        callback: CallbackQuery,
        callback_data: AdminUserBalance,
        state: FSMContext,
    ) -> None:
        """Подтверждение: вызов сервиса и вывод результата."""
        await callback.answer()
        data = await state.get_data()
        user_telegram_id = data.get("user_telegram_id")
        amount = data.get("amount")
        description = data.get("description")
        operation = callback_data.operation
        if not user_telegram_id or amount is None or not operation:
            if callback.message:
                await callback.message.edit_text(
                    "❌ Ошибка: недостаточно данных. Начните заново.",
                    reply_markup=get_user_balance_keyboard(),
                )
            return
        admin_tg_id = callback.from_user.id if callback.from_user else 0
        admin_note = f"Пополнение администратором (tg:{admin_tg_id})."
        full_description = f"{admin_note} {description}" if description else admin_note
        try:
            if operation == "add_balance":
                await add_user_balance(
                    user_telegram_id, amount, full_description
                )
                operation_text = (
                    f"✅ Баланс пользователя {user_telegram_id} пополнен на {amount:.0f} руб."
                )
            elif operation == "add_bonus":
                await add_user_bonus(
                    user_telegram_id, amount, full_description
                )
                operation_text = (
                    f"✅ Пользователю {user_telegram_id} начислено бонусов: {amount:.0f} руб."
                )
            else:
                if callback.message:
                    await callback.message.edit_text(
                        "❌ Неизвестная операция.",
                        reply_markup=get_user_balance_keyboard(),
                    )
                return
        except UserNotFoundError:
            if callback.message:
                await callback.message.edit_text(
                    f"❌ Пользователь с telegram_id {user_telegram_id} не найден.",
                    reply_markup=get_user_balance_keyboard(),
                )
            return
        except InvalidAmountError as e:
            if callback.message:
                await callback.message.edit_text(
                    f"❌ Ошибка: {e}",
                    reply_markup=get_user_balance_keyboard(),
                )
            return
        new_balance, new_bonus = await get_user_balance(user_telegram_id)
        await state.update_data(
            current_balance=new_balance,
            current_bonus=new_bonus,
            action="menu",
        )
        if callback.message:
            await callback.message.edit_text(
                f"{operation_text}\n\n"
                f"💰 Баланс: {new_balance:.0f} руб. | Бонусы: {new_bonus:.0f} руб.\n\n"
                "Выберите действие или введите другой telegram_id:",
                reply_markup=get_user_balance_keyboard(),
            )

    @on.callback_query(AdminUserBalance.filter(F.action == "cancel"))
    async def process_cancel(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Отмена: возврат к меню пользователя (баланс + кнопки)."""
        await callback.answer()
        self.state_context = state
        data = await state.get_data()
        await state.update_data(action="menu")
        user_telegram_id = data.get("user_telegram_id")
        balance = data.get("current_balance", 0)
        bonus = data.get("current_bonus", 0)
        if callback.message:
            await callback.message.edit_text(
                f"👤 Пользователь: {user_telegram_id}\n"
                f"💰 Баланс: {balance:.0f} руб.\n"
                f"🎁 Бонусы: {bonus:.0f} руб.\n\n"
                "Операция отменена. Выберите действие:",
                reply_markup=get_user_balance_keyboard(),
            )

    @on.callback_query(AdminUserBalance.filter(F.action == "back"))
    async def process_exit(self, callback: CallbackQuery) -> None:
        """Выход в главное меню администратора."""
        await callback.answer()
        logger.info("Выход из сцены пополнения баланса пользователей")
        if callback.message:
            await callback.message.edit_text(
                "Вы вернулись в главное меню администратора",
                reply_markup=get_admin_keyboard(),
            )
        await self.wizard.exit()


def register_user_balance_scene(
    router: Router, scene_registry: SceneRegistry | None = None
) -> None:
    """Регистрирует сцену пополнения баланса пользователей в роутере.
    Если scene_registry передан, сцена в него не добавляется (должна быть добавлена снаружи).
    """
    if scene_registry is None:
        scene_registry = SceneRegistry(router)
        scene_registry.add(UserBalanceScene)

    router.message.register(
        UserBalanceScene.as_handler(),
        Command("user_balance_menu"),
        F.from_user.id.in_(ADMINS),
    )
    router.callback_query.register(
        UserBalanceScene.as_handler(),
        AdminUserBalance.filter(F.action == "menu"),
        F.from_user.id.in_(ADMINS),
    )
    logger.info("Сцена пополнения баланса пользователей зарегистрирована")

"""
Сцены для модуля управления бонусами кабинетов.
Обеспечивает изоляцию интерфейса управления бонусами от основной части приложения.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, SceneRegistry, SceneWizard, on
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.client_bot.const import ADMINS
from app.modules.cabinet_bonus_manager.bonus_service import (
    add_balance,
    add_bonus,
    get_cabinet_by_id,
    get_wb_cabinet_by_shop_id,
    reset_balance,
    reset_bonus,
    subtract_balance,
    subtract_bonus,
    subtract_total_with_bonus_priority,
)
from app.modules.cabinet_bonus_manager.callbacks import AdminBonus
from app.modules.cabinet_bonus_manager.keyboards import (
    get_confirm_keyboard,
    get_shop_bonus_keyboard,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)

# Словарь для хранения операций, обрабатываемых менеджером состояний
OPERATIONS = {
    "add": "добавление бонусов",
    "subtract": "снятие бонусов",
    "reset": "обнуление бонусов",
    "add_balance": "пополнение баланса",
    "subtract_balance": "снятие баланса",
    "reset_balance": "обнуление баланса",
    "subtract_priority": "списание (сначала бонусы, затем баланс)",
}


class BonusScene(Scene, state="bonus_scene"):
    """Сцена для управления бонусами кабинетов"""

    def __init__(self, wizard: SceneWizard):
        """
        Инициализация сцены бонусов

        Args:
            wizard: Объект SceneWizard для управления сценой
        """
        super().__init__(wizard)
        self.state_context: FSMContext | None = None  # Будет установлен в enter методах

    @on.message.enter()
    async def enter_scene(self, message: Message, state: FSMContext) -> None:
        """Вход в сцену управления бонусами"""
        logger.info("Вход в сцену управления бонусами")
        self.state_context: FSMContext = state  # Сохраняем контекст состояния

        await message.answer("Введите shop_id кабинета для управления бонусами:")
        await state.update_data(action="menu")

    @on.callback_query.enter(AdminBonus.filter(F.action == "menu"))
    async def enter_scene_from_callback(
        self, callback: CallbackQuery, bot: Bot, state: FSMContext
    ) -> None:
        """Вход в сцену управления бонусами через callback"""
        logger.info("Вход в сцену управления бонусами через callback")
        self.state_context = state  # Сохраняем контекст состояния

        await state.update_data(action="menu")
        await bot.send_message(
            callback.from_user.id, "Введите shop_id кабинета для управления бонусами:"
        )
        return

    async def wizard_exit(self, with_data=True) -> None:
        """
        Расширенный метод выхода из сцены с опциональным сохранением данных

        Args:
            with_data: Флаг, указывающий, нужно ли сохранять данные о кабинете
        """
        # Проверяем, что state_context инициализирован
        if not self.state_context:
            logger.warning(
                "state_context не инициализирован, использую стандартный выход"
            )
            await self.wizard.exit()

        # Если нужно сохранить данные, создаем их копию перед выходом
        if with_data:
            assert self.state_context is not None
            data = await self.state_context.get_data()
            # Временно сохраняем важные данные в хранилище
            tmp_data = {}
            for key in ["shop_id", "current_bonus", "current_balance"]:
                if key in data:
                    tmp_data[key] = data[key]

            # Выходим из сцены
            await self.wizard.exit()

            # Возвращаем важные данные в хранилище
            if tmp_data:
                logger.info(f"Сохраняем данные после выхода из сцены: {tmp_data}")
                await self.state_context.update_data(tmp_data)
        else:
            # Просто выходим без сохранения данных
            await self.wizard.exit()

    @on.message(Command("start"))
    async def handle_start_command(self, message: Message, state: FSMContext) -> None:
        """
        Обработка команды /start - выход из сцены и возврат в основное меню
        ВАЖНО: НЕ использовать return, чтобы позволить глобальному обработчику
        продолжить работу и показать список магазинов
        """
        # Сохраняем текущее содержимое для логирования
        await state.clear()
        # Выходим из сцены без отправки сообщения
        # Здесь правильно использовать выход из сцены, так как команда /start
        # должна вернуть пользователя к начальному экрану бота
        await self.wizard.exit()

        # ВАЖНО: НЕ используем return, чтобы позволить глобальному обработчику показать список магазинов
        # НЕ отправляем сообщения, чтобы избежать дублирования с глобальным обработчиком
        logger.info(
            f"Пользователь {message.from_user.id}"
            f" успешно вышел из сцены бонусов,"
            f" управление передано глобальному обработчику"
        )

    @on.message(F.text)
    async def process_shop_id(self, message: Message, state: FSMContext):
        """Обработка введенного shop_id"""
        data = await state.get_data()
        action = data.get("action")

        if action == "menu":
            shop_id = str(message.text.strip())  # Преобразуем в строку
            if not shop_id:
                await message.answer("Некорректный shop_id. Введите shop_id кабинета:")
                return

            # Проверяем существование кабинета и получаем информацию о нем
            cabinet = await get_wb_cabinet_by_shop_id(shop_id)
            if cabinet is None:
                await message.answer(
                    f"Кабинет с shop_id {shop_id} не найден. Попробуйте еще раз:"
                )
                return

            wb_cabinet_original_id = cabinet.id
            await state.update_data(wb_cabinet_original_id=wb_cabinet_original_id)

            # Безопасно получаем значения баланса и бонусов
            current_bonus = 0
            current_balance = 0
            if hasattr(cabinet, "calculated_bonus"):
                current_bonus = (
                    cabinet.calculated_bonus
                    if cabinet.calculated_bonus is not None
                    else 0
                )
            if hasattr(cabinet, "calculated_balance"):
                current_balance = (
                    cabinet.calculated_balance
                    if cabinet.calculated_balance is not None
                    else 0
                )

            # Сохраняем информацию о кабинете
            await state.update_data(
                shop_id=shop_id,
                cabinet_id=cabinet.id,
                wb_cabinet_original_id=cabinet.id,
                current_bonus=current_bonus,
                current_balance=current_balance,
            )

            # Отображаем информацию и кнопки для управления бонусами данного магазина
            await message.answer(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance:.0f} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus:.0f} руб.\n\n"
                f"Выберите операцию:",
                reply_markup=get_shop_bonus_keyboard(cabinet.id),
            )
        elif action == "amount":
            # Обработка ввода суммы
            try:
                amount = float(message.text.strip())
                if amount <= 0:
                    raise ValueError("Сумма должна быть положительной")
            except ValueError:
                await message.answer("Введите корректную сумму (положительное число):")
                return

            # Сохраняем сумму
            await state.update_data(amount=amount)

            # Получаем данные из хранилища
            data = await state.get_data()
            operation = data.get("operation")
            current_bonus = data.get("current_bonus", 0)
            current_balance = data.get("current_balance", 0)
            shop_id = data.get("shop_id")

            # Локальные проверки на достаточность средств
            if operation == "subtract" and amount > current_bonus:
                await message.answer(
                    f"Недостаточно бонусов для снятия. Текущий баланс бонусов: {current_bonus} руб.\n"
                    f"Введите меньшую сумму:"
                )
                return
            if operation == "subtract_balance" and amount > current_balance:
                await message.answer(
                    f"Недостаточно баланса для снятия. Текущий баланс: {current_balance} руб.\n"
                    f"Введите меньшую сумму:"
                )
                return
            # Переходим к вводу описания
            await state.update_data(action="description")
            await message.answer(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance:.0f} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
                f"Указанная сумма: {amount:.0f} руб.\n"
                f"Введите комментарий для операции:"
            )
        elif action == "description":
            # Обработка ввода описания
            description = message.text.strip()
            if description == "-":
                description = None

            # Сохраняем описание
            await state.update_data(description=description)

            # Получаем данные из хранилища для формирования сообщения
            data = await state.get_data()
            operation = data.get("operation")
            shop_id: str = data.get("shop_id")
            wb_cabinet_original_id: int = data.get("wb_cabinet_original_id")
            current_bonus = data.get("current_bonus", 0)
            current_balance = data.get("current_balance", 0)
            amount = data.get("amount")

            # Формируем сообщение для подтверждения
            if operation == "reset":
                confirm_message = (
                    f"🏪 Магазин: {shop_id}\n"
                    f"💰 Текущий баланс: {current_balance} руб.\n"
                    f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
                    f"Вы собираетесь ОБНУЛИТЬ все бонусы этого кабинета!\n"
                    f"Описание: {description or 'Не указано'}\n\n"
                    f"Подтвердите операцию:"
                )
            elif operation == "reset_balance":
                confirm_message = (
                    f"🏪 Магазин: {shop_id}\n"
                    f"💰 Текущий баланс: {current_balance} руб.\n"
                    f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
                    f"Вы собираетесь ОБНУЛИТЬ весь баланс этого кабинета!\n"
                    f"Описание: {description or 'Не указано'}\n\n"
                    f"Подтвердите операцию:"
                )
            else:
                operation_name = OPERATIONS.get(operation, "операция")
                confirm_message = (
                    f"🏪 Магазин: {shop_id}\n"
                    f"💰 Текущий баланс: {current_balance:.0f} руб.\n"
                    f"🎁 Текущие бонусы: {current_bonus:.0f} руб.\n\n"
                    f"Операция: {operation_name.upper()}\n"
                    f"Сумма: {amount} руб.\n"
                    f"Описание: {description or 'Не указано'}\n\n"
                    f"Подтвердите операцию:"
                )

            # Устанавливаем действие на подтверждение и показываем кнопки
            await state.update_data(action="confirm")
            await message.answer(
                confirm_message,
                reply_markup=get_confirm_keyboard(
                    wb_cabinet_original_id=wb_cabinet_original_id,
                    operation=operation,
                    amount=amount,
                ),
            )

        elif action == "check_bonus":
            shop_id = str(message.text.strip())  # Преобразуем в строку
            if not shop_id:
                await message.answer("Некорректный shop_id. Введите shop_id кабинета:")
                return

            # Проверяем существование кабинета и получаем информацию о нем
            cabinet = await get_wb_cabinet_by_shop_id(shop_id)
            if cabinet is None:
                await message.answer(
                    f"Кабинет с shop_id {shop_id} не найден. Попробуйте еще раз:"
                )
                return

            # Безопасно получаем значения баланса и бонусов
            current_bonus = 0
            current_balance = 0
            if hasattr(cabinet, "calculated_bonus"):
                current_bonus = (
                    cabinet.calculated_bonus
                    if cabinet.calculated_bonus is not None
                    else 0
                )
            if hasattr(cabinet, "calculated_balance"):
                current_balance = (
                    cabinet.calculated_balance
                    if cabinet.calculated_balance is not None
                    else 0
                )

            # Обновляем данные о кабинете в хранилище
            await state.update_data(
                shop_id=shop_id,
                cabinet_id=cabinet.id,  # Сохраняем cabinet_id
                wb_cabinet_original_id=cabinet.id,  # Сохраняем оригинальный id кабинета
                current_bonus=current_bonus,
                current_balance=current_balance,
                action="menu",  # Переходим в меню операций
            )

            # Отображаем информацию о бонусах и балансе кабинета с кнопками управления
            await message.answer(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance:.0f} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus:.0f} руб.\n\n"
                f"Выберите операцию:",
                reply_markup=get_shop_bonus_keyboard(
                    cabinet.id
                ),  # Используем cabinet.id
            )

    @on.callback_query(
        AdminBonus.filter(
            F.action.in_(
                [
                    "add",
                    "subtract",
                    "reset",
                    "add_balance",
                    "subtract_balance",
                    "reset_balance",
                    "subtract_priority",
                ]
            )
        )
    )
    async def process_shop_bonus_callback(
        self, callback: CallbackQuery, callback_data: AdminBonus, state: FSMContext
    ):
        """Обработчик действий с бонусами конкретного магазина"""
        logger.info(f"Обработка callback бонусов: {callback_data.action}")

        data = await state.get_data()
        current_bonus = data.get("current_bonus", 0)
        current_balance = data.get("current_balance", 0)
        shop_id = data.get("shop_id")

        self.state_context = state

        await state.update_data(operation=callback_data.action)

        if callback_data.action in ("reset", "reset_balance"):
            await state.update_data(action="description")
            reset_subject = (
                "бонусов" if callback_data.action == "reset" else "баланса"
            )
            await callback.message.edit_text(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance:.0f} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus:.0f} руб.\n\n"
                f"Введите описание операции обнуления {reset_subject}:"
            )
        else:
            await state.update_data(action="amount")
            operation_name = {
                "add": "пополнения бонусов",
                "subtract": "списания бонусов",
                "add_balance": "пополнения баланса",
                "subtract_balance": "списания баланса",
                "subtract_priority": "списания (сначала бонусы, затем баланс)",
            }.get(callback_data.action, "операции")
            await callback.message.edit_text(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance:.0f} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus:.0f} руб.\n\n"
                f"Введите сумму для {operation_name}:"
            )

    @on.callback_query(AdminBonus.filter(F.action == "menu"))
    async def bonus_menu_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик возврата в главное меню бонусов"""
        await callback.answer()
        await state.clear()
        await state.update_data(action="menu")
        await callback.message.edit_text(
            "Введите shop_id кабинета для управления бонусами:"
        )

    @on.callback_query(AdminBonus.filter(F.action == "confirm"))
    async def process_confirm_callback(
        self, callback: CallbackQuery, callback_data: AdminBonus, state: FSMContext
    ):
        """Обработчик подтверждения операции с бонусами"""
        data = await state.get_data()
        shop_id = data.get("shop_id")
        if not shop_id:
            await callback.message.edit_text(
                "❌ Ошибка: не найден shop_id. Попробуйте еще раз."
            )

        description = data.get("description")
        wb_cabinet_original_id = callback_data.wb_cabinet_original_id
        admin_tg_id = callback.from_user.id if callback.from_user else None
        admin_note = (
            f"Операция администратором (tg:{admin_tg_id})."
            if admin_tg_id is not None
            else "Операция администратором."
        )
        full_description = (
            f"{admin_note} {description}".strip()
            if description
            else admin_note
        )
        admin_user_id: int | None = None
        if admin_tg_id is not None:
            async with get_async_session_maker() as session:
                stmt = select(User.id).where(User.user_telegram_id == admin_tg_id)
                result_stmt = await session.execute(stmt)
                admin_user_id = result_stmt.scalar_one_or_none()
        try:
            operation = callback_data.operation
            if operation == "add":
                result = await add_bonus(
                    wb_cabinet_original_id,
                    callback_data.amount,
                    admin_user_id,
                    full_description,
                )
                operation_text = (
                    f"✅ Бонусы успешно добавлены в кабинет {shop_id}"
                    f" \nСумма: {callback_data.amount} руб."
                )
            elif operation == "add_balance":
                result = await add_balance(
                    wb_cabinet_original_id,
                    callback_data.amount,
                    admin_user_id,
                    full_description,
                )
                operation_text = (
                    f"✅ Баланс успешно пополнен для кабинета {shop_id}\n"
                    f"Сумма: {callback_data.amount} руб."
                )
            elif operation == "subtract":
                result = await subtract_bonus(
                    wb_cabinet_original_id,
                    callback_data.amount,
                    admin_user_id,
                    full_description,
                )
                operation_text = (
                    f"✅ Бонусы успешно списаны с кабинета {shop_id}!\n"
                    f"Сумма: {callback_data.amount} руб."
                )
            elif operation == "subtract_balance":
                result = await subtract_balance(
                    wb_cabinet_original_id,
                    callback_data.amount,
                    admin_user_id,
                    full_description,
                )
                operation_text = (
                    f"✅ Баланс успешно списан с кабинета {shop_id}!\n"
                    f"Сумма: {callback_data.amount} руб."
                )
            elif operation == "reset":
                result = await reset_bonus(
                    wb_cabinet_original_id, admin_user_id, full_description
                )
                operation_text = f"✅ Бонусы кабинета {shop_id} успешно обнулены!"
            elif operation == "reset_balance":
                result = await reset_balance(
                    wb_cabinet_original_id, admin_user_id, full_description
                )
                operation_text = f"✅ Баланс кабинета {shop_id} успешно обнулен!"
            elif operation == "subtract_priority":
                result, bonus_spent, balance_spent = (
                    await subtract_total_with_bonus_priority(
                        wb_cabinet_original_id,
                        callback_data.amount,
                        admin_user_id,
                        full_description,
                    )
                )
                operation_text = (
                    f"✅ Списание выполнено для кабинета {shop_id}.\n"
                    f"Всего: {callback_data.amount} руб.\n"
                    f"Из бонусов: {bonus_spent:.0f} руб.\n"
                    f"С баланса: {balance_spent:.0f} руб."
                )
            else:
                raise ValueError(f"Неизвестная операция: {operation}")

            if result:
                cabinet = await get_cabinet_by_id(wb_cabinet_original_id)
                new_bonus = cabinet.calculated_bonus if cabinet else 0
                new_balance = cabinet.calculated_balance if cabinet else 0

                self.state_context = state

                await state.update_data(
                    action="menu",
                    shop_id=shop_id,
                    wb_cabinet_original_id=wb_cabinet_original_id,
                    current_bonus=new_bonus,
                    current_balance=new_balance,
                )

                logger.info(f"Обновляем состояние после операции {operation}")

                await callback.message.edit_text(
                    f"{operation_text}\n"
                    f"💰 Текущий баланс: {new_balance:.0f} руб.\n"
                    f"🎁 Текущие бонусы: {new_bonus:.0f} руб.\n\n"
                    f"Для продолжения работы с этим кабинетом используйте кнопки ниже:",
                    reply_markup=get_shop_bonus_keyboard(wb_cabinet_original_id),
                )
            else:
                await callback.message.edit_text(
                    "❌ Не удалось выполнить операцию. Попробуйте еще раз.",
                    reply_markup=get_shop_bonus_keyboard(wb_cabinet_original_id),
                )

        except Exception as e:
            logger.error(f"Ошибка при выполнении операции с бонусами: {e}")
            raise e

    @on.callback_query(AdminBonus.filter(F.action == "cancel"))
    async def process_cancel_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик отмены операции"""
        logger.info("Отмена операции")

        self.state_context = state

        data = await state.get_data()
        shop_id = data.get("shop_id")
        current_bonus = data.get("current_bonus")
        current_balance = data.get("current_balance")
        wb_cabinet_original_id = data.get("wb_cabinet_original_id")

        await state.update_data(action="menu")

        await callback.message.edit_text(
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс: {current_balance:.0f} руб.\n"
            f"🎁 Текущие бонусы: {current_bonus:.0f} руб.\n\n"
            f"Операция отменена. Выберите действие:",
            reply_markup=get_shop_bonus_keyboard(wb_cabinet_original_id),
        )

    @on.callback_query(AdminBonus.filter(F.action == "back"))
    async def process_exit_button(self, callback: CallbackQuery):
        """Обработчик нажатия на кнопку 'Назад' для выхода из меню управления бонусами"""
        await callback.answer()

        logger.info(f"Пользователь {callback.from_user.id} выходит из сцены бонусов")

        from app.client_bot.user_interface.views.keyboards import get_admin_keyboard

        await callback.message.edit_text(
            "Вы вернулись в главное меню администратора",
            reply_markup=get_admin_keyboard(),
        )

        await self.wizard.exit()

    @on.message(Command("check_bonus"))
    async def cmd_check_bonus(self, message: Message, state: FSMContext):
        """Обработчик команды проверки бонусов кабинета"""
        await state.update_data(action="check_bonus")
        await message.answer("Введите shop_id кабинета для проверки бонусов:")


def register_bonus_scene(router: Router, scene_registry: SceneRegistry | None = None):
    """Регистрирует сцену для управления бонусами в указанном роутере.
    Если scene_registry передан, сцена в него не добавляется (должна быть добавлена снаружи).
    """
    if scene_registry is None:
        scene_registry = SceneRegistry(router)
        scene_registry.add(BonusScene)

    router.message.register(
        BonusScene.as_handler(), Command("bonus_menu"), F.from_user.id.in_(ADMINS)
    )
    router.message.register(
        BonusScene.as_handler(), Command("check_bonus"), F.from_user.id.in_(ADMINS)
    )

    # Регистрируем только один обработчик для входа через callback
    router.callback_query.register(
        BonusScene.as_handler(),
        AdminBonus.filter(F.action == "menu"),
        F.from_user.id.in_(ADMINS),
    )

    logger.info("Сцена управления бонусами успешно зарегистрирована")

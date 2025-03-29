"""
Изолированный роутер для модуля управления бонусами кабинетов.
Позволяет отделить обработчики этого модуля от основной части приложения,
обеспечивая более чистую архитектуру.
"""
import logging
from aiogram import Router, types, Bot, F
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.filters.callback_data import CallbackData
from sqlalchemy import select

from app.client_bot.const import ADMINS
from app.modules.cabinet_bonus_manager.state_manager import BonusManagerStateGroup
from app.modules.cabinet_bonus_manager.bonus_service import (
    add_bonus, subtract_bonus, reset_bonus, get_wb_cabinet
)
from app.modules.cabinet_bonus_manager.keyboards import (
    get_bonus_admin_keyboard, get_confirm_keyboard, get_shop_bonus_keyboard
)
from app.utils.db.models import User
# Импортируем AdminBonus для обратной совместимости
from app.client_bot.user_interface.views.callbacks import AdminBonus

logger = logging.getLogger(__name__)

# Создаем изолированный роутер
bonus_router = Router(name="cabinet_bonus_isolated")

# Определяем класс для колбеков этого модуля


class BonusCallback(CallbackData, prefix="bonus_isolated"):
    """Класс для обработки колбеков в изолированном модуле бонусов"""
    action: str
    shop_id: str = None
    amount: float = None
    operation: str = None

# Словарь для хранения операций, обрабатываемых менеджером состояний
OPERATIONS = {
    "add": "добавление",
    "subtract": "снятие",
    "reset": "обнуление"
}

# Обработчик команды /start - высокий приоритет для выхода из любого состояния модуля


@bonus_router.message(CommandStart())
async def handle_start_command(message: types.Message, state: FSMContext):
    """
    Обработка команды /start - очищает состояние модуля бонусов 
    и позволяет показать пользователю список его магазинов.
    
    ВАЖНО ДЛЯ РАЗРАБОТЧИКОВ:
    При создании модулей с состояниями всегда добавляйте обработчик команды /start с высоким приоритетом,
    который очищает состояния модуля и передает управление основному обработчику.
    
    В проекте команда /start должна возвращать пользователя к списку его магазинов
    через вызов функции ShopChoice, это обеспечивается глобальным обработчиком.
    
    CommandStart() должен стоять перед любыми обработчиками с StateFilter,
    чтобы работать независимо от текущего состояния.
    """
    # Проверяем, находится ли пользователь в одном из состояний модуля
    current_state = await state.get_state()
    
    # Очищаем все возможные состояния, связанные с модулем бонусов
    if current_state:
        # Очищаем обычное состояние
        await state.clear()
        logger.info(f"Пользователь {message.from_user.id} вышел из модуля бонусов по команде /start")
        
    # ВАЖНО: НЕ используем return, чтобы глобальный обработчик мог продолжить работу
    # ВАЖНО: НЕ отправляем никаких сообщений, чтобы не конфликтовать с глобальным обработчиком


# Команда /bonus_help - показывает справку по командам управления бонусами
@bonus_router.message(Command("bonus_help"), F.from_user.id.in_(ADMINS))
async def cmd_bonus_help(message: types.Message):
    help_text = (
        "🔹 Команды управления бонусами кабинетов:\n\n"
        "/bonus_menu - Открыть меню управления бонусами\n"
        "/check_bonus - Проверить текущий баланс бонусов кабинета\n\n"
        "Для доступа к этим командам вы должны быть в списке администраторов."
    )
    await message.answer(help_text)

@bonus_router.message(Command("bonus_menu"), F.from_user.id.in_(ADMINS))
async def cmd_bonus_menu(message: types.Message, state: FSMContext):
    """Запрашивает shop_id для работы с бонусами"""
    # Очищаем предыдущие данные и устанавливаем новое состояние
    await state.clear()
    await state.set_state(BonusManagerStateGroup.waiting_for_shop_id)
    
    await message.answer("Введите shop_id кабинета для управления бонусами:")

# Обработчик callback для BonusCallback с action=menu
@bonus_router.callback_query(BonusCallback.filter(F.action == "menu"), F.from_user.id.in_(ADMINS))
async def admin_bonus_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показывает меню управления бонусами по коллбеку"""
    # Отвечаем на callback
    await callback.answer()
    
    # Очищаем предыдущие данные и устанавливаем новое состояние
    await state.clear()
    await state.set_state(BonusManagerStateGroup.waiting_for_shop_id)
    
    await callback.message.edit_text("Введите shop_id кабинета для управления бонусами:")

# Обработчик ввода shop_id
@bonus_router.message(StateFilter(BonusManagerStateGroup.waiting_for_shop_id))
async def process_shop_id(message: types.Message, state: FSMContext):
    shop_id = message.text.strip()
    if not shop_id:
        await message.answer("Некорректный shop_id. Введите shop_id кабинета:")
        return

    # Проверяем существование кабинета и получаем информацию о нем
    cabinet = await get_wb_cabinet(shop_id)
    if cabinet is None:
        await message.answer(f"Кабинет с shop_id {shop_id} не найден. Попробуйте еще раз:")
        return

    # Сохраняем информацию о кабинете в хранилище
    await state.update_data({
        "shop_id": shop_id, 
        "current_bonus": cabinet.calculated_bonus,
        "current_balance": cabinet.calculated_balance
    })
    
    # Отображаем информацию и кнопки для управления бонусами данного магазина
    await message.answer(
        f"🏪 Магазин: {shop_id}\n"
        f"💰 Текущий баланс: {cabinet.calculated_balance} руб.\n"
        f"🎁 Текущие бонусы: {cabinet.calculated_bonus} руб.\n\n"
        f"Выберите операцию:",
        reply_markup=get_shop_bonus_keyboard(shop_id)
    )

# Обработчик колбеков операций с магазином
@bonus_router.callback_query(F.data.startswith("shop_bonus_"), F.from_user.id.in_(ADMINS))
async def process_shop_bonus_callback(callback: types.CallbackQuery, state: FSMContext):
    # Отвечаем на callback
    await callback.answer()
    
    # Парсим данные из callback_data
    parts = callback.data.split("_")
    operation = parts[2]  # add, subtract или reset
    shop_id = parts[3]    # shop_id магазина
    
    # Получаем данные из состояния
    data = await state.get_data()
    current_bonus = data.get("current_bonus")
    current_balance = data.get("current_balance")
    
    # Обновляем информацию о текущей операции
    await state.update_data(operation=operation)
    
    if operation == "reset":
        # Для обнуления сразу переходим к описанию
        await state.set_state(BonusManagerStateGroup.waiting_for_description)
        await callback.message.edit_text(
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс: {current_balance} руб.\n"
            f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
            f"Введите описание операции обнуления:"
        )
    else:
        # Для добавления или снятия запрашиваем сумму
        await state.set_state(BonusManagerStateGroup.waiting_for_amount)
        operation_name = "пополнения" if operation == "add" else "списания"
        await callback.message.edit_text(
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс: {current_balance} руб.\n"
            f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
            f"Введите сумму для {operation_name} бонусов:"
        )

# Обработчик возврата в главное меню бонусов
@bonus_router.callback_query(F.data == "bonus_menu", F.from_user.id.in_(ADMINS))
async def bonus_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(BonusManagerStateGroup.waiting_for_shop_id)
    await callback.message.edit_text("Введите shop_id кабинета для управления бонусами:")

# Обработчик ввода суммы
@bonus_router.message(StateFilter(BonusManagerStateGroup.waiting_for_amount))
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
    except ValueError:
        await message.answer("Введите корректную сумму (положительное число):")
        return

    # Сохраняем сумму в состоянии
    await state.update_data(amount=amount)
    
    # Получаем данные из состояния
    data = await state.get_data()
    operation = data.get("operation")
    current_bonus = data.get("current_bonus")
    current_balance = data.get("current_balance")
    shop_id = data.get("shop_id")

    # Проверяем достаточно ли бонусов для subtract
    if operation == "subtract" and amount > current_bonus:
        await message.answer(
            f"Недостаточно бонусов для снятия. Текущий баланс бонусов: {current_bonus} руб.\n"
            f"Введите меньшую сумму:"
        )
        return

    # Переходим к вводу описания
    await state.set_state(BonusManagerStateGroup.waiting_for_description)
    await message.answer(
        f"🏪 Магазин: {shop_id}\n"
        f"💰 Текущий баланс: {current_balance} руб.\n"
        f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
        f"Введите описание операции:"
    )

# Обработчик ввода описания
@bonus_router.message(StateFilter(BonusManagerStateGroup.waiting_for_description))
async def process_description(message: types.Message, state: FSMContext):
    description = message.text.strip()
    if description == "-":
        description = None

    # Сохраняем описание в состоянии
    await state.update_data(description=description)
    
    # Получаем данные из состояния
    data = await state.get_data()
    operation = data.get("operation")
    shop_id = data.get("shop_id")
    current_bonus = data.get("current_bonus")
    current_balance = data.get("current_balance")
    
    # Формируем сообщение для подтверждения
    if operation == "reset":
        confirm_message = (
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс: {current_balance} руб.\n"
            f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
            f"Подтвердите обнуление бонусов:\n"
            f"Описание: {description or 'Не указано'}"
        )
        # Клавиатура для подтверждения обнуления
        keyboard = get_confirm_keyboard(operation, shop_id)
    else:
        amount = data.get("amount")
        operation_name = "пополнения" if operation == "add" else "списания"
        new_balance = current_bonus + amount if operation == "add" else current_bonus - amount
        
        confirm_message = (
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс: {current_balance} руб.\n"
            f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
            f"Подтвердите операцию {operation_name} бонусов:\n"
            f"Сумма: {amount} руб.\n"
            f"Новый баланс будет: {new_balance} руб.\n"
            f"Описание: {description or 'Не указано'}"
        )
        # Клавиатура для подтверждения с суммой
        keyboard = get_confirm_keyboard(operation, shop_id, amount)
    
    await state.set_state(BonusManagerStateGroup.waiting_for_confirm)
    await message.answer(confirm_message, reply_markup=keyboard)


# Обработчик колбека для подтверждения/отмены операции
@bonus_router.callback_query(F.data.startswith("bonus_confirm_"), F.from_user.id.in_(ADMINS))
async def process_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
    # Отвечаем на callback
    await callback.answer()
    
    # Парсим данные из callback_data
    parts = callback.data.split("_")
    operation = parts[2]
    shop_id = parts[3]
    amount = float(parts[4]) if len(parts) > 4 else None
    
    admin_user_id = callback.from_user.id
    data = await state.get_data()
    description = data.get("description")
    
    try:
        # Выполняем операцию в зависимости от типа
        result = False
        if operation == "add":
            result = await add_bonus(shop_id, amount, admin_user_id, description)
            operation_text = f"Бонусы в размере {amount} руб. успешно добавлены"
        elif operation == "subtract":
            result = await subtract_bonus(shop_id, amount, admin_user_id, description)
            operation_text = f"Бонусы в размере {amount} руб. успешно сняты"
        elif operation == "reset":
            result = await reset_bonus(shop_id, admin_user_id, description)
            operation_text = "Бонусы успешно обнулены"
        
        if result:
            # Получаем обновленную информацию о кабинете
            cabinet = await get_wb_cabinet(shop_id)
            new_bonus = cabinet.calculated_bonus if cabinet else 0
            new_balance = cabinet.calculated_balance if cabinet else 0
            
            await callback.message.edit_text(
                f"✅ {operation_text} для магазина {shop_id}.\n"
                f"💰 Текущий баланс: {new_balance} руб.\n"
                f"🎁 Новый баланс бонусов: {new_bonus} руб.\n\n"
                f"Для продолжения работы с этим магазином используйте кнопки ниже:",
                reply_markup=get_shop_bonus_keyboard(shop_id)
            )
            # Обновляем данные о текущем балансе
            await state.update_data(current_bonus=new_bonus, current_balance=new_balance)
            # Очищаем состояние
            await state.set_state()
        else:
            await callback.message.edit_text(
                f"❌ Ошибка при выполнении операции для магазина {shop_id}.\n\n"
                f"Попробуйте еще раз:",
                reply_markup=get_shop_bonus_keyboard(shop_id)
            )
            await state.set_state()
            
    except Exception as e:
        logger.error(f"Ошибка при управлении бонусами: {e}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка: {str(e)}\n\n"
            f"Вернитесь в меню управления магазином:",
            reply_markup=get_shop_bonus_keyboard(shop_id)
        )
        await state.set_state()

# Обработчик колбека для отмены операции
@bonus_router.callback_query(F.data == "bonus_cancel", F.from_user.id.in_(ADMINS))
async def process_cancel_callback(callback: types.CallbackQuery, state: FSMContext) -> None:
    # Получаем данные о магазине
    data = await state.get_data()
    shop_id = data.get("shop_id")
    current_bonus = data.get("current_bonus")
    current_balance = data.get("current_balance")
    
    # Очищаем состояние ожидания подтверждения и возвращаемся к меню магазина
    await state.set_state()
    
    await callback.message.edit_text(
        f"🏪 Магазин: {shop_id}\n"
        f"💰 Текущий баланс: {current_balance} руб.\n"
        f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
        f"Операция отменена. Выберите действие:",
        reply_markup=get_shop_bonus_keyboard(shop_id)
    )

# Обработчик callback для кнопки "Назад"
@bonus_router.callback_query(F.data == "bonus_back", F.from_user.id.in_(ADMINS))
async def process_back_button(callback: types.CallbackQuery, state: FSMContext):

    # Очищаем все состояния и данные
    await state.clear()
    
    # Отправляем пользователя назад в главное меню
    from app.client_bot.user_interface.views.keyboards import get_admin_keyboard
    
    await callback.message.edit_text(
        "Вы вернулись в главное меню администратора",
        reply_markup=get_admin_keyboard()
    )

# Экспортируем объекты для обратной совместимости
# Это позволяет использовать импорты в старом коде без изменений
BonusAdminStates = BonusManagerStateGroup

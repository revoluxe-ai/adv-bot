"""
Обработчики команд администратора для управления бонусами кабинетов.
"""
import logging
from aiogram import Router, types, Bot, F
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from app.client_bot.const import ADMINS
from app.modules.cabinet_bonus_manager.bonus_service import (
    add_bonus, subtract_bonus, reset_bonus, get_wb_cabinet
)
from app.modules.cabinet_bonus_manager.keyboards import (
    get_bonus_admin_keyboard, get_confirm_keyboard, get_shop_bonus_keyboard
)
from app.utils.db.models import User
from app.client_bot.user_interface.views.callbacks import AdminBonus

logger = logging.getLogger(__name__)
router = Router()

# Определяем состояния для FSM (Finite State Machine)
class BonusAdminStates(StatesGroup):
    waiting_for_shop_id = State()  # Ожидание ввода shop_id
    waiting_for_amount = State()   # Ожидание ввода суммы
    waiting_for_description = State()  # Ожидание ввода описания операции
    waiting_for_confirm = State()  # Ожидание подтверждения операции

# Словарь для хранения операций, обрабатываемых FSM
OPERATIONS = {
    "add": "добавление",
    "subtract": "снятие",
    "reset": "обнуление"
}

# Фильтр для доступа только администраторам
def is_admin_filter(message: types.Message):
    return message.from_user.id in ADMINS

# Обработчик /start перенесен в isolated_router.py для централизованного управления
# Это позволяет избежать дублирования и конфликтов между обработчиками

# Команда /bonus_help - показывает справку по командам управления бонусами
@router.message(Command("bonus_help"), F.from_user.id.in_(ADMINS))
async def cmd_bonus_help(message: types.Message):
    help_text = (
        "🔹 Команды управления бонусами кабинетов:\n\n"
        "/bonus_menu - Открыть меню управления бонусами\n"
        "/check_bonus - Проверить текущий баланс бонусов кабинета\n\n"
        "Для доступа к этим командам вы должны быть в списке администраторов."
    )
    await message.answer(help_text)

@router.message(Command("bonus_menu"), F.from_user.id.in_(ADMINS))
async def cmd_bonus_menu(message: types.Message, state: FSMContext):
    """Запрашивает shop_id для работы с бонусами"""
    await state.clear()
    await state.set_state(BonusAdminStates.waiting_for_shop_id)
    await message.answer("Введите shop_id кабинета для управления бонусами:")

# Обработчик callback для вызова меню управления бонусами из админ-панели перенесен в bonus_scene.py
# @router.callback_query(AdminBonus.filter(F.action == "menu"), F.from_user.id.in_(ADMINS))
# async def admin_bonus_menu_callback(callback: types.CallbackQuery, callback_data: AdminBonus, state: FSMContext):
#     """Показывает меню управления бонусами по коллбеку из админ-панели"""
#     # Отвечаем на callback
#     await callback.answer()
#     
#     # Запрашиваем shop_id
#     await state.clear()
#     await state.set_state(BonusAdminStates.waiting_for_shop_id)
#     await callback.message.edit_text("Введите shop_id кабинета для управления бонусами:")

# Обработчик ввода shop_id
@router.message(StateFilter(BonusAdminStates.waiting_for_shop_id))
async def process_shop_id(message: types.Message, state: FSMContext):
    shop_id = message.text.strip()
    if not shop_id:
        await message.answer("Некорректный shop_id. Введите shop_id кабинета:")
        return

    # Проверяем существование кабинета и текущий баланс бонусов
    current_bonus = await get_wb_cabinet(shop_id)
    if current_bonus is None:
        await message.answer(f"Кабинет с shop_id {shop_id} не найден. Попробуйте еще раз:")
        return

    # Сохраняем информацию о кабинете
    await state.update_data(shop_id=shop_id, current_bonus=current_bonus)
    
    # Отображаем информацию и кнопки для управления бонусами данного магазина
    await message.answer(
        f"🏪 Магазин: {shop_id}\n"
        f"💰 Текущий баланс бонусов: {current_bonus} руб.\n\n"
        f"Выберите операцию:",
        reply_markup=get_shop_bonus_keyboard(shop_id)
    )

# Обработчик колбеков операций с магазином
@router.callback_query(F.data.startswith("shop_bonus_"), F.from_user.id.in_(ADMINS))
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
    
    # Обновляем информацию о текущей операции
    await state.update_data(operation=operation)
    
    if operation == "reset":
        # Для обнуления сразу переходим к описанию
        await state.set_state(BonusAdminStates.waiting_for_description)
        await callback.message.edit_text(
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс бонусов: {current_bonus} руб.\n\n"
            f"Введите описание операции обнуления (или отправьте '-' для пропуска):"
        )
    else:
        # Для добавления или снятия запрашиваем сумму
        await state.set_state(BonusAdminStates.waiting_for_amount)
        operation_name = "пополнения" if operation == "add" else "списания"
        await callback.message.edit_text(
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс бонусов: {current_bonus} руб.\n\n"
            f"Введите сумму для {operation_name} бонусов:"
        )

# Обработчик возврата в главное меню бонусов
@router.callback_query(F.data == "bonus_menu", F.from_user.id.in_(ADMINS))
async def bonus_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(BonusAdminStates.waiting_for_shop_id)
    await callback.message.edit_text("Введите shop_id кабинета для управления бонусами:")

# Обработчик ввода суммы
@router.message(StateFilter(BonusAdminStates.waiting_for_amount))
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
    except ValueError:
        await message.answer("Введите корректную сумму (положительное число):")
        return

    await state.update_data(amount=amount)
    data = await state.get_data()
    operation = data["operation"]
    current_bonus = data["current_bonus"]
    shop_id = data["shop_id"]

    # Проверяем достаточно ли бонусов для subtract
    if operation == "subtract" and amount > current_bonus:
        await message.answer(
            f"Недостаточно бонусов для снятия. Текущий баланс: {current_bonus} руб.\n"
            f"Введите меньшую сумму:"
        )
        return

    await state.set_state(BonusAdminStates.waiting_for_description)
    await message.answer(
        f"🏪 Магазин: {shop_id}\n"
        f"💰 Текущий баланс бонусов: {current_bonus} руб.\n\n"
        f"Введите описание операции (или отправьте '-' для пропуска):"
    )

# Обработчик ввода описания
@router.message(StateFilter(BonusAdminStates.waiting_for_description))
async def process_description(message: types.Message, state: FSMContext):
    description = message.text.strip()
    if description == "-":
        description = None

    await state.update_data(description=description)
    data = await state.get_data()

    # Формируем сообщение для подтверждения
    operation = data["operation"]
    shop_id = data["shop_id"]
    current_bonus = data["current_bonus"]
    
    if operation == "reset":
        confirm_message = (
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс бонусов: {current_bonus} руб.\n\n"
            f"Подтвердите обнуление бонусов:\n"
            f"Описание: {description or 'Не указано'}"
        )
        # Клавиатура для подтверждения обнуления
        keyboard = get_confirm_keyboard(operation, shop_id)
    else:
        amount = data["amount"]
        operation_name = "пополнения" if operation == "add" else "списания"
        new_balance = current_bonus + amount if operation == "add" else current_bonus - amount
        
        confirm_message = (
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс бонусов: {current_bonus} руб.\n\n"
            f"Подтвердите операцию {operation_name} бонусов:\n"
            f"Сумма: {amount} руб.\n"
            f"Новый баланс будет: {new_balance} руб.\n"
            f"Описание: {description or 'Не указано'}"
        )
        # Клавиатура для подтверждения с суммой
        keyboard = get_confirm_keyboard(operation, shop_id, amount)
    
    await state.set_state(BonusAdminStates.waiting_for_confirm)
    await message.answer(confirm_message, reply_markup=keyboard)

# Обработчик колбека для подтверждения/отмены операции
@router.callback_query(F.data.startswith("bonus_confirm_"), F.from_user.id.in_(ADMINS))
async def process_confirm_callback(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
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
            new_bonus = await get_wb_cabinet(shop_id)
            await callback.message.edit_text(
                f"✅ {operation_text} для магазина {shop_id}.\n"
                f"💰 Новый баланс бонусов: {new_bonus} руб.\n\n"
                f"Для продолжения работы с этим магазином используйте кнопки ниже:",
                reply_markup=get_shop_bonus_keyboard(shop_id)
            )
            # Обновляем данные о текущем балансе
            await state.update_data(current_bonus=new_bonus)
            # Сбрасываем состояние ожидания подтверждения
            await state.set_state(None)
        else:
            await callback.message.edit_text(
                f"❌ Ошибка при выполнении операции для магазина {shop_id}.\n\n"
                f"Попробуйте еще раз:",
                reply_markup=get_shop_bonus_keyboard(shop_id)
            )
            await state.set_state(None)
            
    except Exception as e:
        logger.error(f"Ошибка при управлении бонусами: {e}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка: {str(e)}\n\n"
            f"Вернитесь в меню управления магазином:",
            reply_markup=get_shop_bonus_keyboard(shop_id)
        )
        await state.set_state(None)

# Обработчик колбека для отмены операции
@router.callback_query(F.data == "bonus_cancel", F.from_user.id.in_(ADMINS))
async def process_cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    # Отвечаем на callback
    await callback.answer()
    
    # Получаем данные о магазине
    data = await state.get_data()
    shop_id = data.get("shop_id")
    current_bonus = data.get("current_bonus")
    
    # Очищаем состояние ожидания подтверждения и возвращаемся к меню магазина
    await state.set_state(None)
    
    await callback.message.edit_text(
        f"🏪 Магазин: {shop_id}\n"
        f"💰 Текущий баланс бонусов: {current_bonus} руб.\n\n"
        f"Операция отменена. Выберите действие:",
        reply_markup=get_shop_bonus_keyboard(shop_id)
    )

# Обработчик callback для кнопки "Назад"
@router.callback_query(F.data == "bonus_back", F.from_user.id.in_(ADMINS))
async def process_back_button(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку 'Назад' в меню управления бонусами"""
    # Отвечаем на callback
    await callback.answer()
    await state.clear()
    
    # Отправляем пользователя назад в главное меню
    from app.client_bot.user_interface.views.keyboards import get_admin_keyboard
    
    await callback.message.edit_text(
        "Вы вернулись в главное меню администратора",
        reply_markup=get_admin_keyboard()
    ) 
"""
Сцены для модуля управления бонусами кабинетов.
Обеспечивает изоляцию интерфейса управления бонусами от основной части приложения.
"""
import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, SceneRegistry, on, SceneWizard
from aiogram.fsm.storage.memory import SimpleEventIsolation


from app.client_bot.const import ADMINS
from app.modules.cabinet_bonus_manager.bonus_service import (
    add_bonus, subtract_bonus, reset_bonus, get_wb_cabinet
)
from app.modules.cabinet_bonus_manager.keyboards import (
    get_bonus_admin_keyboard, get_confirm_keyboard, get_shop_bonus_keyboard, get_back_to_menu_keyboard
)

from app.client_bot.user_interface.views.callbacks import AdminBonus

logger = logging.getLogger(__name__)

# Словарь для хранения операций, обрабатываемых менеджером состояний
OPERATIONS = {
    "add": "добавление",
    "subtract": "снятие",
    "reset": "обнуление"
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
        self.state_context = None  # Будет установлен в enter методах
    
    @on.message.enter()
    async def enter_scene(self, message: Message, state: FSMContext):
        """Вход в сцену управления бонусами"""
        logger.info("Вход в сцену управления бонусами")
        self.state_context = state  # Сохраняем контекст состояния
        await message.answer("Введите shop_id кабинета для управления бонусами:")
        await state.update_data(action="menu")
    
    @on.callback_query.enter(AdminBonus.filter(F.action == "menu"))
    async def enter_scene_from_callback(self, callback: CallbackQuery, state: FSMContext):
        """Вход в сцену управления бонусами через callback"""
        logger.info("Вход в сцену управления бонусами через callback")
        self.state_context = state  # Сохраняем контекст состояния
        await callback.answer()
        # Запрашиваем shop_id
        await state.update_data(action="menu")
        await callback.message.edit_text("Введите shop_id кабинета для управления бонусами:")
    
    async def wizard_exit(self, with_data=True):
        """
        Расширенный метод выхода из сцены с опциональным сохранением данных
        
        Args:
            with_data: Флаг, указывающий, нужно ли сохранять данные о кабинете
        """
        # Проверяем, что state_context инициализирован
        if not self.state_context:
            logger.warning("state_context не инициализирован, использую стандартный выход")
            await self.wizard.exit()
            return
            
        # Если нужно сохранить данные, создаем их копию перед выходом
        if with_data:
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
    async def handle_start_command(self, message: Message, state: FSMContext):
        """
        Обработка команды /start - выход из сцены и возврат в основное меню
        ВАЖНО: НЕ использовать return, чтобы позволить глобальному обработчику
        продолжить работу и показать список магазинов
        """
        logger.info(f"Получена команда /start внутри сцены бонусов - пользователь {message.from_user.id} выходит из сцены")
        
        # Сохраняем текущее содержимое для логирования
        data = await state.get_data()
        if data:
            logger.info(f"Очищаем данные сцены: {data}")
            
        # Выходим из сцены без отправки сообщения
        # Здесь правильно использовать выход из сцены, так как команда /start
        # должна вернуть пользователя к начальному экрану бота
        await self.wizard.exit()
        
        # ВАЖНО: НЕ используем return, чтобы позволить глобальному обработчику показать список магазинов
        # НЕ отправляем сообщения, чтобы избежать дублирования с глобальным обработчиком
        logger.info(f"Пользователь {message.from_user.id} успешно вышел из сцены бонусов, управление передано глобальному обработчику")
    

    @on.message(F.text)
    async def process_shop_id(self, message: Message, state: FSMContext):
        """Обработка введенного shop_id"""
        data = await state.get_data()
        action = data.get("action")
        
        if action == "menu":
            shop_id = message.text.strip()
            if not shop_id:
                await message.answer("Некорректный shop_id. Введите shop_id кабинета:")
                return

            # Проверяем существование кабинета и получаем информацию о нем
            cabinet = await get_wb_cabinet(shop_id)
            if cabinet is None:
                await message.answer(f"Кабинет с shop_id {shop_id} не найден. Попробуйте еще раз:")
                return

            # Безопасно получаем значения баланса и бонусов
            current_bonus = 0
            current_balance = 0
            if hasattr(cabinet, 'calculated_bonus'):
                current_bonus = cabinet.calculated_bonus if cabinet.calculated_bonus is not None else 0
            if hasattr(cabinet, 'calculated_balance'):
                current_balance = cabinet.calculated_balance if cabinet.calculated_balance is not None else 0
            
            # Сохраняем информацию о кабинете
            await state.update_data(
                shop_id=shop_id,
                current_bonus=current_bonus,
                current_balance=current_balance
            )
            
            # Отображаем информацию и кнопки для управления бонусами данного магазина
            await message.answer(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
                f"Выберите операцию:",
                reply_markup=get_shop_bonus_keyboard(shop_id)
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

            # Проверяем достаточно ли бонусов для subtract
            if operation == "subtract" and amount > current_bonus:
                await message.answer(
                    f"Недостаточно бонусов для снятия. Текущий баланс бонусов: {current_bonus} руб.\n"
                    f"Введите меньшую сумму:"
                )
                return

            # Переходим к вводу описания
            await state.update_data(action="description")
            await message.answer(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
                f"Введите описание операции (или отправьте '-' для пропуска):"
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
            shop_id = data.get("shop_id")
            current_bonus = data.get("current_bonus", 0)
            current_balance = data.get("current_balance", 0)
            
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
            else:
                amount = data.get("amount")
                operation_name = OPERATIONS.get(operation, "операция")
                confirm_message = (
                    f"🏪 Магазин: {shop_id}\n"
                    f"💰 Текущий баланс: {current_balance} руб.\n"
                    f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
                    f"Операция: {operation_name.upper()} бонусов\n"
                    f"Сумма: {amount} руб.\n"
                    f"Описание: {description or 'Не указано'}\n\n"
                    f"Подтвердите операцию:"
                )
            
            # Устанавливаем действие на подтверждение и показываем кнопки
            await state.update_data(action="confirm")
            await message.answer(confirm_message, reply_markup=get_confirm_keyboard())
        
        elif action == "check_bonus":
            shop_id = message.text.strip()
            if not shop_id:
                await message.answer("Некорректный shop_id. Введите shop_id кабинета:")
                return

            # Проверяем существование кабинета и получаем информацию о нем
            cabinet = await get_wb_cabinet(shop_id)
            if cabinet is None:
                await message.answer(f"Кабинет с shop_id {shop_id} не найден. Попробуйте еще раз:")
                return
            
            # Безопасно получаем значения баланса и бонусов
            current_bonus = 0
            current_balance = 0
            if hasattr(cabinet, 'calculated_bonus'):
                current_bonus = cabinet.calculated_bonus if cabinet.calculated_bonus is not None else 0
            if hasattr(cabinet, 'calculated_balance'):
                current_balance = cabinet.calculated_balance if cabinet.calculated_balance is not None else 0
            
            # Обновляем данные о кабинете в хранилище
            await state.update_data(
                shop_id=shop_id,
                current_bonus=current_bonus,
                current_balance=current_balance,
                action="menu"  # Переходим в меню операций
            )
            
            # Отображаем информацию о бонусах и балансе кабинета с кнопками управления
            await message.answer(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
                f"Выберите операцию:",
                reply_markup=get_shop_bonus_keyboard(shop_id)
            )

    @on.callback_query(F.data.startswith("shop_bonus_"))
    async def process_shop_bonus_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка колбеков операций с магазином"""
        # Отвечаем на callback
        await callback.answer()
        
        # Парсим данные из callback_data
        parts = callback.data.split("_")
        operation = parts[2]  # add, subtract или reset
        shop_id = parts[3]    # shop_id магазина
        
        # Получаем данные из хранилища с безопасными значениями по умолчанию
        data = await state.get_data()
        current_bonus = data.get("current_bonus", 0)
        current_balance = data.get("current_balance", 0)
        
        # Обновляем информацию о текущей операции
        await state.update_data(operation=operation)
        
        if operation == "reset":
            # Для обнуления сразу переходим к описанию
            await state.update_data(action="description")
            await callback.message.edit_text(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
                f"Введите описание операции обнуления (или отправьте '-' для пропуска):"
            )
        else:
            # Для добавления или снятия запрашиваем сумму
            await state.update_data(action="amount")
            operation_name = "пополнения" if operation == "add" else "списания"
            await callback.message.edit_text(
                f"🏪 Магазин: {shop_id}\n"
                f"💰 Текущий баланс: {current_balance} руб.\n"
                f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
                f"Введите сумму для {operation_name} бонусов:"
            )

    @on.callback_query(F.data == "bonus_menu")
    async def bonus_menu_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик возврата в главное меню бонусов"""
        await callback.answer()
        await state.clear()
        await state.update_data(action="menu")
        await callback.message.edit_text("Введите shop_id кабинета для управления бонусами:")

    @on.callback_query(F.data == "confirm_ok")
    async def process_confirm_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка подтверждения операции"""
        await callback.answer()
        
        # Получаем все необходимые данные из хранилища
        data = await state.get_data()
        shop_id = data.get("shop_id")
        operation = data.get("operation")
        description = data.get("description")
        
        result_message = ""
        
        try:
            if operation == "add":
                amount = data.get("amount")
                # Выполняем добавление бонусов
                await add_bonus(shop_id, amount, callback.from_user.id, description)
                result_message = f"✅ Бонусы успешно добавлены в кабинет {shop_id}!\nСумма: {amount} руб."
            
            elif operation == "subtract":
                amount = data.get("amount")
                # Выполняем снятие бонусов
                await subtract_bonus(shop_id, amount, callback.from_user.id, description)
                result_message = f"✅ Бонусы успешно списаны с кабинета {shop_id}!\nСумма: {amount} руб."
            
            elif operation == "reset":
                # Выполняем обнуление бонусов
                await reset_bonus(shop_id, callback.from_user.id, description)
                result_message = f"✅ Бонусы кабинета {shop_id} успешно обнулены!"
            
            # Получаем обновленную информацию о кабинете
            cabinet = await get_wb_cabinet(shop_id)
            if cabinet:
                # Безопасно получаем значения баланса и бонусов
                current_bonus = 0
                current_balance = 0
                if hasattr(cabinet, 'calculated_bonus'):
                    current_bonus = cabinet.calculated_bonus if cabinet.calculated_bonus is not None else 0
                if hasattr(cabinet, 'calculated_balance'):
                    current_balance = cabinet.calculated_balance if cabinet.calculated_balance is not None else 0
                
                # Обновляем данные о кабинете в хранилище
                await state.update_data(
                    shop_id=shop_id,
                    current_bonus=current_bonus,
                    current_balance=current_balance
                )
                
                result_message += f"\n\n🏪 Магазин: {shop_id}\n💰 Текущий баланс: {current_balance} руб.\n🎁 Текущие бонусы: {current_bonus} руб."
            
            # Добавляем инструкции по дальнейшим действиям
            result_message += "\n\nНажмите кнопку ниже для выполнения новой операции."
            
            # Возвращаем пользователя в меню операций с текущим магазином
            await state.update_data(action="menu")
            await callback.message.edit_text(
                result_message,
                reply_markup=get_shop_bonus_keyboard(shop_id)
            )
            
        except Exception as e:
            error_message = f"❌ Ошибка при выполнении операции: {str(e)}"
            logger.error(f"Ошибка при выполнении операции с бонусами: {e}", exc_info=True)
            await callback.message.edit_text(error_message)
            
            # Добавляем кнопку для возврата в меню
            await callback.message.edit_text(
                error_message,
                reply_markup=get_back_to_menu_keyboard()
            )

    @on.callback_query(F.data == "confirm_cancel")
    async def process_cancel_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка отмены операции"""
        await callback.answer()
        
        # Получаем данные о магазине
        data = await state.get_data()
        shop_id = data.get("shop_id")
        current_bonus = data.get("current_bonus", 0)
        current_balance = data.get("current_balance", 0)
        
        # Возвращаем пользователя в меню операций
        await state.update_data(action="menu")
        
        # Отмена операции и возврат к меню бонусов
        await callback.message.edit_text(
            f"Операция отменена.\n\n"
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс: {current_balance} руб.\n"
            f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
            f"Выберите операцию:",
            reply_markup=get_shop_bonus_keyboard(shop_id)
        )

    @on.callback_query(F.data == "back_to_shop_bonus")
    async def process_back_button(self, callback: CallbackQuery, state: FSMContext):
        """Обработка кнопки возврата к выбору операции"""
        await callback.answer()
        
        # Получаем данные из хранилища с безопасными значениями по умолчанию
        data = await state.get_data()
        shop_id = data.get("shop_id")
        current_bonus = data.get("current_bonus", 0)
        current_balance = data.get("current_balance", 0)
        
        # Сбрасываем действие на выбор операции
        await state.update_data(action="menu")
        
        # Отображаем информацию и кнопки для управления бонусами
        await callback.message.edit_text(
            f"🏪 Магазин: {shop_id}\n"
            f"💰 Текущий баланс: {current_balance} руб.\n"
            f"🎁 Текущие бонусы: {current_bonus} руб.\n\n"
            f"Выберите операцию:",
            reply_markup=get_shop_bonus_keyboard(shop_id)
        )

    @on.callback_query(F.data == "bonus_back")
    async def process_exit_button(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик нажатия на кнопку 'Назад' для выхода из меню управления бонусами"""
        # Отвечаем на callback
        await callback.answer()
        
        # Здесь мы действительно должны выйти из сцены, так как пользователь возвращается к админ-панели
        logger.info(f"Пользователь {callback.from_user.id} выходит из сцены бонусов")
        
        # Отправляем пользователя назад в главное меню
        from app.client_bot.user_interface.views.keyboards import get_admin_keyboard
        
        await callback.message.edit_text(
            "Вы вернулись в главное меню администратора",
            reply_markup=get_admin_keyboard()
        )
        
        # Это один из случаев, когда выход из сцены действительно необходим
        # так как мы переходим в другую часть приложения
        await self.wizard.exit()

    @on.message(Command("check_bonus"))
    async def cmd_check_bonus(self, message: Message, state: FSMContext):
        """Обработчик команды проверки бонусов кабинета"""
        await state.update_data(action="check_bonus")
        await message.answer("Введите shop_id кабинета для проверки бонусов:")


def register_bonus_scene(router: Router):
    """Регистрирует сцену для управления бонусами в указанном роутере"""
    # Создаем реестр сцен на роутере
    scene_registry = SceneRegistry(router)
    
    # Регистрируем сцену управления бонусами
    scene_registry.add(BonusScene)
    
    # Регистрируем обработчики входа в сцену через команды
    # Используем дополнительный параметр state=None для предотвращения конфликтов
    router.message.register(BonusScene.as_handler(), Command("bonus_menu"), F.from_user.id.in_(ADMINS))
    router.message.register(BonusScene.as_handler(state=None), Command("check_bonus"), F.from_user.id.in_(ADMINS))
    
    # Регистрируем обработчик для входа через callback от кнопки "Админ панель"
    router.callback_query.register(BonusScene.as_handler(), AdminBonus.filter(F.action == "menu"), F.from_user.id.in_(ADMINS))
    
    logger.info("Сцена управления бонусами успешно зарегистрирована")
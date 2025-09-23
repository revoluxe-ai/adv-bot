# Руководство по модификации телеграм-бота

Это руководство предназначено для облегчения процесса внесения изменений в телеграм-бота для рекламы на Wildberries. Здесь представлены типичные сценарии модификации с конкретными шагами и примерами кода.

## Содержание
1. [Добавление новой кнопки](#добавление-новой-кнопки)
2. [Создание нового обработчика](#создание-нового-обработчика)
3. [Модификация сообщений](#модификация-сообщений)
4. [Добавление нового состояния FSM](#добавление-нового-состояния-fsm)
5. [Создание новой клавиатуры](#создание-новой-клавиатуры)
6. [Добавление нового меню](#добавление-нового-меню)
7. [Создание нового модуля](#создание-нового-модуля)

## Добавление новой кнопки

### Шаг 1: Создание callback-класса
Добавьте новый класс для callback в файл `app/client_bot/user_interface/views/callbacks.py`:

```python
class NewFeatureCallback(CallbackData, prefix="new_feature"):
    action: str
    param_id: int = None
```

### Шаг 2: Добавление кнопки в клавиатуру
Найдите подходящую клавиатуру в файле `app/client_bot/user_interface/views/keyboards.py` и добавьте в неё новую кнопку:

```python
def get_some_keyboard(param_id: int):
    builder = InlineKeyboardBuilder()

    # Добавление существующих кнопок
    # ...

    # Добавление новой кнопки
    button = InlineKeyboardButton(
        text="Новая функция",
        callback_data=NewFeatureCallback(
            action="show",
            param_id=param_id
        ).pack()
    )
    builder.row(button)

    return builder.as_markup()
```

### Шаг 3: Создание обработчика для кнопки
Создайте обработчик в соответствующем файле в директории `app/client_bot/user_interface/handlers/`:

```python
@router.callback_query(NewFeatureCallback.filter(F.action == "show"))
async def process_new_feature(
    callback: types.CallbackQuery,
    callback_data: NewFeatureCallback,
    bot: aiogram.Bot,
    state: FSMContext
):
    # Ваш код для обработки нажатия на кнопку
    param_id = callback_data.param_id
    chat_id = callback.message.chat.id

    # Например, отправляем сообщение
    await bot.send_message(chat_id, f"Вы выбрали новую функцию с параметром {param_id}")
```

## Создание нового обработчика

### Шаг 1: Создайте новый файл обработчика
Если функционал достаточно большой, создайте новый файл в директории `app/client_bot/user_interface/handlers/`, например `new_feature.py`:

```python
from aiogram import Router, types
import aiogram
from aiogram.fsm.context import FSMContext
from ..views import callbacks, messages
from .. import states

router = Router()

@router.callback_query(callbacks.NewFeatureCallback.filter())
async def process_new_feature(
    callback: types.CallbackQuery,
    callback_data: callbacks.NewFeatureCallback,
    bot: aiogram.Bot,
    state: FSMContext
):
    # Код обработчика
    pass
```

### Шаг 2: Подключите роутер в common_routers.py
Добавьте импорт вашего нового обработчика в файл `app/client_bot/common_routers.py` и включите его роутер:

```python
from .user_interface.handlers import new_feature

# ...

common_router.include_routers(new_feature.router)
```

## Модификация сообщений

### Пример: Создание нового класса сообщения
Добавьте новый класс в файл `app/client_bot/user_interface/views/messages.py`:

```python
class NewFeatureMessage:
    def __init__(self, bot: Bot, chat_id: int, data: dict = None):
        self.bot = bot
        self.chat_id = chat_id
        self.data = data or {}

    async def __call__(self):
        text = (
            f"✅ Новая функция активирована!\n\n"
            f"Параметр: {self.data.get('param', 'не указан')}\n"
            f"Статус: {self.data.get('status', 'активный')}"
        )

        # Создаем клавиатуру с кнопками для этого сообщения
        keyboard = keyboards.get_new_feature_keyboard(
            param_id=self.data.get('param_id')
        )

        await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            reply_markup=keyboard
        )
```

### Использование нового сообщения в обработчике
```python
@router.callback_query(callbacks.SomeCallback.filter())
async def some_handler(
    callback: types.CallbackQuery,
    callback_data: callbacks.SomeCallback,
    bot: aiogram.Bot,
    state: FSMContext
):
    chat_id = callback.message.chat.id
    data = {
        "param": "значение",
        "status": "активный",
        "param_id": callback_data.id
    }

    await messages.NewFeatureMessage(bot, chat_id, data)()
```

## Добавление нового состояния FSM

### Шаг 1: Создание нового класса состояний
Добавьте новый класс в файл `app/client_bot/user_interface/states.py`:

```python
class NewFeatureState(StatesGroup):
    waiting_for_input = State()
    waiting_for_confirmation = State()
```

### Шаг 2: Использование состояний в обработчиках
```python
@router.callback_query(callbacks.NewFeatureCallback.filter(F.action == "start"))
async def start_new_feature_process(
    callback: types.CallbackQuery,
    callback_data: callbacks.NewFeatureCallback,
    bot: aiogram.Bot,
    state: FSMContext
):
    chat_id = callback.message.chat.id

    # Устанавливаем состояние
    await state.set_state(states.NewFeatureState.waiting_for_input)

    # Сохраняем данные в состоянии
    await state.update_data(param_id=callback_data.param_id)

    # Отправляем сообщение с инструкциями
    await bot.send_message(chat_id, "Введите значение для новой функции:")

@router.message(StateFilter(states.NewFeatureState.waiting_for_input))
async def process_new_feature_input(
    message: types.Message,
    bot: aiogram.Bot,
    state: FSMContext
):
    user_input = message.text
    chat_id = message.chat.id

    # Получаем данные из состояния
    state_data = await state.get_data()
    param_id = state_data.get("param_id")

    # Обрабатываем ввод пользователя
    # ...

    # Переходим к следующему состоянию
    await state.set_state(states.NewFeatureState.waiting_for_confirmation)
    await state.update_data(user_input=user_input)

    # Отправляем сообщение для подтверждения
    await bot.send_message(
        chat_id,
        f"Вы ввели: {user_input}. Подтвердите действие:",
        reply_markup=keyboards.get_confirmation_keyboard()
    )
```

## Создание новой клавиатуры

### Пример создания клавиатуры с кнопками и пагинацией
```python
def get_new_feature_keyboard(items: list, page: int = 1, items_per_page: int = 5):
    builder = InlineKeyboardBuilder()

    # Вычисляем границы текущей страницы
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(items))

    # Добавляем кнопки для элементов на текущей странице
    for i in range(start_idx, end_idx):
        item = items[i]
        button = InlineKeyboardButton(
            text=f"{item['name']}",
            callback_data=callbacks.ItemSelect(
                id=item["id"],
                action="select"
            ).pack()
        )
        builder.row(button)

    # Добавляем кнопки навигации, если есть больше страниц
    nav_buttons = []

    if page > 1:
        # Кнопка "Назад"
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=callbacks.Pagination(
                    action="prev",
                    page=page - 1
                ).pack()
            )
        )

    # Номер текущей страницы
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{page}/{(len(items) + items_per_page - 1) // items_per_page}",
            callback_data="ignore"
        )
    )

    if end_idx < len(items):
        # Кнопка "Вперед"
        nav_buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=callbacks.Pagination(
                    action="next",
                    page=page + 1
                ).pack()
            )
        )

    # Добавляем строку с кнопками навигации
    builder.row(*nav_buttons)

    # Добавляем кнопку "Назад в меню"
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад в меню",
            callback_data=callbacks.Navigation(
                action="back_to_menu"
            ).pack()
        )
    )

    return builder.as_markup()
```

## Добавление нового меню

### Шаг 1: Создание callback-классов для меню
```python
class NewMenuCallback(CallbackData, prefix="new_menu"):
    action: str
    item_id: int = None
```

### Шаг 2: Создание клавиатуры для меню
```python
def get_new_menu_keyboard():
    builder = InlineKeyboardBuilder()

    # Добавляем пункты меню
    builder.row(
        InlineKeyboardButton(
            text="Пункт 1",
            callback_data=NewMenuCallback(action="option_1").pack()
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Пункт 2",
            callback_data=NewMenuCallback(action="option_2").pack()
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Пункт 3",
            callback_data=NewMenuCallback(action="option_3").pack()
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=callbacks.Navigation(action="back").pack()
        )
    )

    return builder.as_markup()
```

### Шаг 3: Создание сообщения меню
```python
class NewMenuMessage:
    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id

    async def __call__(self):
        text = (
            "🔹 Новое меню\n\n"
            "Выберите одну из доступных опций:"
        )

        keyboard = keyboards.get_new_menu_keyboard()

        await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            reply_markup=keyboard
        )
```

### Шаг 4: Создание обработчиков для пунктов меню
```python
@router.callback_query(NewMenuCallback.filter(F.action == "option_1"))
async def process_menu_option_1(
    callback: types.CallbackQuery,
    callback_data: NewMenuCallback,
    bot: aiogram.Bot,
    state: FSMContext
):
    chat_id = callback.message.chat.id
    await bot.send_message(chat_id, "Вы выбрали пункт 1")

@router.callback_query(NewMenuCallback.filter(F.action == "option_2"))
async def process_menu_option_2(
    callback: types.CallbackQuery,
    callback_data: NewMenuCallback,
    bot: aiogram.Bot,
    state: FSMContext
):
    chat_id = callback.message.chat.id
    await bot.send_message(chat_id, "Вы выбрали пункт 2")

@router.callback_query(NewMenuCallback.filter(F.action == "option_3"))
async def process_menu_option_3(
    callback: types.CallbackQuery,
    callback_data: NewMenuCallback,
    bot: aiogram.Bot,
    state: FSMContext
):
    chat_id = callback.message.chat.id
    await bot.send_message(chat_id, "Вы выбрали пункт 3")
```

## Создание нового модуля

**ВАЖНО**: Новая функциональность разрабатывается преимущественно в виде модулей в директории `app/modules/`.

### Шаг 1: Создание структуры модуля
Создайте новую директорию для вашего модуля в папке `app/modules/`, например:

```
app/
  modules/
    my_new_feature/
      __init__.py
      models.py
      service.py
      repository.py
      telegram/
        __init__.py
        callbacks.py
        handlers/
          __init__.py
          main_handler.py
```

### Шаг 2: Создание моделей данных
В файле `models.py` определите модели данных, которые будут использоваться модулем:

```python
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.utils.db.models import BaseTable

class MyNewFeatureSettings(BaseTable):
    __tablename__ = 'my_new_feature_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    adv_setting_id = Column(Integer, ForeignKey('adv_settings.id'))

    adv_setting = relationship("AdvSetting", back_populates="my_new_feature_settings")
```

### Шаг 3: Создание сервисного класса
В файле `service.py` реализуйте бизнес-логику вашего модуля:

```python
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import MyNewFeatureSettings

class MyNewFeatureService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_settings_by_adv_id(self, adv_id: int) -> Optional[MyNewFeatureSettings]:
        stmt = select(MyNewFeatureSettings).where(MyNewFeatureSettings.adv_setting_id == adv_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_settings(self, name: str, adv_id: int) -> MyNewFeatureSettings:
        settings = MyNewFeatureSettings(
            name=name,
            adv_setting_id=adv_id
        )
        self.session.add(settings)
        await self.session.commit()
        await self.session.refresh(settings)
        return settings

    async def update_settings(self, settings_id: int, is_active: bool) -> Optional[MyNewFeatureSettings]:
        stmt = select(MyNewFeatureSettings).where(MyNewFeatureSettings.id == settings_id)
        result = await self.session.execute(stmt)
        settings = result.scalar_one_or_none()

        if settings:
            settings.is_active = is_active
            await self.session.commit()
            await self.session.refresh(settings)

        return settings
```

### Шаг 4: Создание callback-классов для Telegram
В файле `telegram/callbacks.py` создайте классы для обработки колбэков:

```python
from aiogram.filters.callback_data import CallbackData

class MyNewFeatureCallback(CallbackData, prefix="my_new_feature"):
    action: str
    settings_id: int = None
    adv_id: int = None
```

### Шаг 5: Создание обработчиков для Telegram
В файле `telegram/handlers/main_handler.py` создайте обработчики для колбэков:

```python
from aiogram import Router, F, types
import aiogram
from aiogram.fsm.context import FSMContext
from app.utils.db.session_maker import get_async_session_maker
from ... import service
from ..callbacks import MyNewFeatureCallback

router = Router()
sm = get_async_session_maker

@router.callback_query(MyNewFeatureCallback.filter(F.action == "view"))
async def view_settings(
    callback: types.CallbackQuery,
    callback_data: MyNewFeatureCallback,
    bot: aiogram.Bot,
    state: FSMContext
):
    chat_id = callback.message.chat.id
    adv_id = callback_data.adv_id

    async with sm() as session:
        service_obj = service.MyNewFeatureService(session)
        settings = await service_obj.get_settings_by_adv_id(adv_id)

        if settings:
            status = "активно" if settings.is_active else "не активно"
            await bot.send_message(
                chat_id,
                f"Настройки функции:\n"
                f"Имя: {settings.name}\n"
                f"Статус: {status}"
            )
        else:
            await bot.send_message(
                chat_id,
                "Настройки не найдены. Создайте новые настройки."
            )

@router.callback_query(MyNewFeatureCallback.filter(F.action == "toggle"))
async def toggle_settings(
    callback: types.CallbackQuery,
    callback_data: MyNewFeatureCallback,
    bot: aiogram.Bot,
    state: FSMContext
):
    chat_id = callback.message.chat.id
    settings_id = callback_data.settings_id

    async with sm() as session:
        service_obj = service.MyNewFeatureService(session)
        settings = await service_obj.get_settings_by_id(settings_id)

        if settings:
            settings = await service_obj.update_settings(settings_id, not settings.is_active)
            status = "активно" if settings.is_active else "не активно"
            await bot.send_message(
                chat_id,
                f"Статус функции изменен на: {status}"
            )
        else:
            await bot.send_message(
                chat_id,
                "Настройки не найдены."
            )
```

### Шаг 6: Экспорт роутера в `__init__.py`
В файле `telegram/handlers/__init__.py`:

```python
from .main_handler import router
```

А в файле корневом `__init__.py` модуля:

```python
from .telegram.handlers import router
```

### Шаг 7: Подключение роутера модуля к основному боту
В файле `app/client_bot/common_routers.py` добавьте импорт вашего модуля и включите его роутер:

```python
from app.modules.my_new_feature import router as my_new_feature_router

# ...

common_router.include_routers(my_new_feature_router)
```

### Шаг 8: Интеграция модуля с интерфейсом
Для полной интеграции с пользовательским интерфейсом, добавьте кнопку для вашей функции в соответствующую клавиатуру в файле `app/client_bot/user_interface/views/keyboards.py`:

```python
from app.modules.my_new_feature.telegram.callbacks import MyNewFeatureCallback

# ...

def get_adv_setting_keyboard(adv_setting: AdvSetting):
    builder = InlineKeyboardBuilder()

    # Существующие кнопки
    # ...

    # Кнопка для новой функции
    builder.row(
        InlineKeyboardButton(
            text="Моя новая функция",
            callback_data=MyNewFeatureCallback(
                action="view",
                adv_id=adv_setting.id
            ).pack()
        )
    )

    return builder.as_markup()
```

### Шаг 9: Добавление миграции базы данных
Если ваш модуль добавляет новые таблицы в базу данных, создайте миграцию с помощью Alembic:

```bash
alembic revision --autogenerate -m "Add my_new_feature tables"
alembic upgrade head
```

### Пример полной интеграции модуля

Полная интеграция нового модуля включает в себя следующие компоненты:

1. **Модели данных** - для хранения информации в БД
2. **Сервисный слой** - для реализации бизнес-логики
3. **Колбэки Telegram** - для обработки взаимодействия с пользователем
4. **Обработчики** - для выполнения конкретных действий в ответ на действия пользователя
5. **Роутеры** - для регистрации обработчиков и их соединения с основным ботом
6. **UI интеграция** - добавление кнопок и сообщений в пользовательский интерфейс

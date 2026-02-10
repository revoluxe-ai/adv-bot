# Спецификация функционала онбординга: главное меню и страница «Мои магазины»

Документ описывает функционал, реализованный в рамках рефакторинга онбординга: разделение экрана после входа на **главное меню** и **страницу «Мои магазины»**, единообразный возврат «к списку магазинов» и отображение статусов магазинов.

---

## 1. Цели и контекст

### Зачем нужен рефакторинг

- **Раньше:** после `/start` пользователь сразу видел один экран с кнопками «Добавить магазин», «Показать инвайт», «Мой баланс» и списком всех магазинов. Кнопки «Вернуться к списку магазинов» и «К списку магазинов» в части мест вели на тот же экран через callback `Start`, в других — могли вести на тот же экран, но логика «главное» и «список магазинов» смешивалась.
- **Проблема:** после введения отдельного главного меню кнопка «Вернуться к списку магазинов» продолжала использовать `Start`, из‑за чего пользователь попадал в главное меню, а не в список магазинов.
- **Цель:** явно разделить два экрана и обеспечить, чтобы все кнопки «к списку магазинов» вели именно на страницу со списком магазинов, а в главное меню пользователь попадал только по `/start`, «Назад» с этой страницы или «Перейти в главное меню».

### Что сделано

1. Введены два уровня экранов: **главное меню (MainMenu)** и **страница «Мои магазины» (ShopsListPage)**.
2. Добавлен callback **ShowShopsList** для перехода на страницу «Мои магазины»; все кнопки возврата к списку магазинов переведены на него.
3. На странице «Мои магазины» добавлены: пагинация (по 20 магазинов), индикаторы статуса магазина (✅/❌), кнопка «Назад» в главное меню.
4. Сохранена обратная совместимость: класс **ShopChoice** оставлен как алиас `ShopsListPage` для мест, где после действия показывают список магазинов.

---

## 2. Два уровня экранов

### 2.1. Главное меню (MainMenu)

**Когда показывается**

- После команды `/start` (если пользователь прошёл гейт).
- После callback **Start** (кнопка «Назад» на странице «Мои магазины», кнопка «Перейти в главное меню» в рассылках и т.п.).
- После успешного прохождения гейта по инвайту (`gate.py`).
- После успешной регистрации в `start_registration_func.py`.

**Содержимое**

- Текст: приветственный блок из `get_main_text(user_telegram_id)` (описание бота, этапы, поддержка).
- Кнопки (сверху вниз):
  1. **Панель администратора** — только для `user_telegram_id in const.ADMINS`, callback `AdminPanel(action="menu")`.
  2. **Мои магазины** — callback `ShowShopsList()`.
  3. **Мой баланс** — callback `UserBalanceMenu()`.
  4. **Показать инвайт** — callback `InviteShow()`.

**Реализация**

- Класс: `MainMenu` (наследник `TextWithKeyboard`).
- Клавиатура: `get_main_menu_keyboard(user_telegram_id)`.
- Файл: `app/client_bot/user_interface/handlers/shop_choice_message.py`.

**Точки вызова MainMenu в коде**

- `app/client_bot/user_interface/handlers/start/start.py`: обработчик callback `Start` — `await MainMenu(bot, chat_id)()`.
- `app/client_bot/user_interface/handlers/start_registration_func.py`: после успешного входа — `await MainMenu(bot, chat_id)()`.
- `app/client_bot/user_interface/handlers/gate.py`: после успешного ввода инвайт-кода — `await MainMenu(bot, chat_id)()`.

---

### 2.2. Страница «Мои магазины» (ShopsListPage)

**Когда показывается**

- По нажатию «Мои магазины» в главном меню (callback `ShowShopsList`).
- По нажатию «Вернуться к списку магазинов» (меню магазина в `keyboards.py` и `shop_menu/message.py`).
- По нажатию «К списку магазинов» (например, с экрана оплаты в `keyboards.py`).
- После удаления кабинета в `shop_settings.py`.
- После успешного добавления кабинета в `start.py` (через `ShopChoice`, то есть ту же страницу).
- После успешной оплаты входа в `balance_manager/handlers.py` (через `ShopChoice`).

**Содержимое**

- Заголовок: константа `SHOPS_LIST_PAGE_TITLE` — пояснение «Нажмите "Добавить магазин" для начала использования», блок «Мои магазины», легенда «✅ — Магазин подключен», «❌ — Требуется замена токена».
- Кнопки:
  1. **➕Добавить магазин** — callback `ShopNew()`.
  2. Список кнопок магазинов на текущей странице (до 20): текст вида «Название магазина ✅» или «Название магазина ❌», callback `Shop(action="select", wb_user_cabinet_original_id=...)`.
  3. Пагинация (если нужно): **⬅️ Назад** — `ShopsListPaginator(page=page-1)`, **Вперёд ➡️** — `ShopsListPaginator(page=page+1)`.
  4. **Назад** — callback `Start()` (возврат в главное меню).

**Логика статуса магазина (✅/❌)**

- Магазин считается «подключённым» (✅), если:
  - у связанного `WBCabinet` установлено `active == True`, и
  - в множестве `shop_ids_with_active_tokens` есть `wb_cabinet.shop_id` (либо `shop_ids_with_active_tokens` не передано — тогда проверяется только `active`).
- Множество `shop_ids_with_active_tokens` формируется сервисом `get_shop_ids_with_complete_token_status(shop_ids)` (модуль `token_monitoring`): туда входят магазины, у которых есть валидный, не истёкший, не read-only токен с полным набором прав.
- Иначе показывается ❌ («Требуется замена токена»).

**Пагинация**

- Константа `SHOPS_PER_PAGE = 20`.
- Для страницы `page` отображаются магазины с индексами `(page-1)*20` по `page*20 - 1`.
- Кнопка «⬅️ Назад» показывается при `page > 1`, «Вперёд ➡️» — при `len(all_shops) > end_index`.

**Реализация**

- Класс: `ShopsListPage` (наследник `TextWithKeyboard`). Конструктор: `(bot, chat_id, all_shops, shop_ids_with_active_tokens=None, page=1)`.
- Клавиатура: `get_shops_list_keyboard(all_shops, user_telegram_id, shop_ids_with_active_tokens, page)`.
- Файл: `app/client_bot/user_interface/handlers/shop_choice_message.py`.

**Обратная совместимость**

- Класс `ShopChoice` объявлен как подкласс `ShopsListPage` без дополнительной логики; везде, где после действия нужно показать список магазинов, можно вызывать либо `ShopsListPage(...)`, либо `ShopChoice(...)` с теми же аргументами (в т.ч. `shop_ids_with_active_tokens`).

---

## 3. Callbacks и обработчики

### 3.1. Callbacks (callbacks.py)

| Класс                 | prefix           | Поля    | Назначение |
|------------------------|------------------|--------|------------|
| `Start`                | `start`          | —      | Возврат в главное меню (MainMenu). |
| `ShowShopsList`        | `shops_list`     | —      | Переход на страницу «Мои магазины» (ShopsListPage), страница 1. |
| `ShopsListPaginator`   | `shops_list_pg`  | `page` | Переключение страницы списка «Мои магазины». |

Файл: `app/client_bot/user_interface/views/callbacks.py`.

### 3.2. Обработчики (start.py)

- **Callback Start**  
  Зарегистрирован вручную: `router.callback_query.register(callback_start_registration, callbacks.Start.filter())`.  
  Очищает FSM, загружает пользователя с кабинетами; если не прошёл гейт — показывает гейт; иначе вызывает `MainMenu(bot, chat_id)()`.

- **Callback ShowShopsList**  
  Декоратор: `@router.callback_query(callbacks.ShowShopsList.filter())`, функция `show_shops_list`.  
  Очищает FSM, загружает пользователя с `wb_user_cabinets` и `wb_cabinet` (joinedload), собирает `shop_ids`, вызывает `get_shop_ids_with_complete_token_status(shop_ids)`, отображает `ShopsListPage(bot, chat_id, wb_user_cabinets, shop_ids_with_active_tokens)` (страница 1). Если пользователя нет или не прошёл гейт — показывает гейт.

- **Callback ShopsListPaginator**  
  Декоратор: `@router.callback_query(callbacks.ShopsListPaginator.filter())`, функция `shops_list_paginator`.  
  Аналогично загружает пользователя и магазины, нормализует `page` (не меньше 1), отображает `ShopsListPage(..., page=page)`.

Файл: `app/client_bot/user_interface/handlers/start/start.py`.

---

## 4. Где используются кнопки «к списку магазинов»

Все следующие кнопки должны вести на страницу «Мои магазины» (callback `ShowShopsList`), а не в главное меню:

| Место | Текст кнопки | Файл / функция |
|-------|----------------|--------------------------------|
| Меню магазина (альтернативная клавиатура) | Вернуться к списку магазинов | `views/keyboards.py` — `get_shop_menu_keyboard()` |
| Меню магазина (полное меню магазина)     | Вернуться к списку магазинов | `modules/shop_menu/message.py` — клавиатура `ShopMenu` |
| Экран оплаты                             | К списку магазинов           | `views/keyboards.py` — `get_payment_keyboard()` |

Проверка: во всех этих местах в `callback_data` используется `callbacks.ShowShopsList().pack()` (или импортированный `ShowShopsList().pack()` в `shop_menu/message.py`).

---

## 5. Зависимости и сервисы

- **Статусы токенов:** `app.modules.token_monitoring.services.get_shop_ids_with_complete_token_status(shop_ids: list[str]) -> set[str]`. Один запрос к БД по всем магазинам; возвращает множество `shop_id`, у которых есть «полный» токен (валидный, не истёкший, не read-only, все требуемые права).
- **Модели:** `User`, `WBUserCabinet`, `WBCabinet` (с полем `shop_id`, `active`). Для построения списка и статусов нужен `joinedload(WBUserCabinet.wb_cabinet)` при загрузке кабинетов пользователя.

---

## 6. Краткая схема переходов

```
/start (passed_gate)  ──►  MainMenu
       │
       ├── «Мои магазины» (ShowShopsList)  ──►  ShopsListPage (page=1)
       │         │
       │         ├── «➕Добавить магазин»  ──►  сценарий добавления  ──►  ShopsListPage
       │         ├── «[Магазин ✅/❌]»     ──►  меню магазина
       │         │         └── «Вернуться к списку магазинов»  ──►  ShopsListPage
       │         ├── «⬅️ Назад» / «Вперёд ➡️»  ──►  ShopsListPage (другая страница)
       │         └── «Назад» (Start)  ──►  MainMenu
       │
       └── «Мой баланс» / «Показать инвайт» / админка  — без смены на ShopsListPage

«К списку магазинов» (с оплаты и т.п.)  ──►  ShopsListPage
«Перейти в главное меню» (рассылки)     ──►  MainMenu  (Start)
```

---

## 7. Связанная документация и файлы

- **Краткая навигация:** [ONBOARDING_NAVIGATION.md](ONBOARDING_NAVIGATION.md).
- **Подробное описание кнопок и callbacks:** [BUTTONS_FUNCTIONALITY.md](BUTTONS_FUNCTIONALITY.md).
- **Справочник кнопок по экранам:** [BUTTONS_GUIDE.md](BUTTONS_GUIDE.md).

**Основные файлы реализации**

- `app/client_bot/user_interface/handlers/shop_choice_message.py` — классы `MainMenu`, `ShopsListPage`, `ShopChoice`, функции `get_main_menu_keyboard`, `get_shops_list_keyboard`, константы `SHOPS_LIST_PAGE_TITLE`, `SHOPS_PER_PAGE`.
- `app/client_bot/user_interface/handlers/start/start.py` — обработчики `callback_start_registration`, `show_shops_list`, `shops_list_paginator`, вызовы `MainMenu`/`ShopsListPage`/`ShopChoice`.
- `app/client_bot/user_interface/views/callbacks.py` — классы `Start`, `ShowShopsList`, `ShopsListPaginator`.
- `app/client_bot/user_interface/views/keyboards.py` — кнопки «Вернуться к списку магазинов», «К списку магазинов» с `ShowShopsList`.
- `app/modules/shop_menu/message.py` — кнопка «Вернуться к списку магазинов» с `ShowShopsList`.
- `app/modules/token_monitoring/services/token_info_service.py` — `get_shop_ids_with_complete_token_status`, батч-метод по магазинам.

Данная спецификация соответствует текущей реализации в ветке с рефакторингом онбординга.

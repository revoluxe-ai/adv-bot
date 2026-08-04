## 1. Tests-first (RED / contract)

- [x] 1.1 Обновить unit-тест «новый user на callback» → ожидание: `create_user` MUST NOT вызываться; при `invite_gate` — gate UI (spec: Callback Start is menu-return / Missing user non-write)
- [x] 1.2 Добавить paired write-gate: existing user path по-прежнему показывает MainMenu/gate/minimal, и `create_user` не вызывается (spec: menu-return without User creation)
- [x] 1.3 Добавить/уточнить missing-user без `invite_gate`: без create и без full MainMenu как зарегистрированный клиент (spec: Missing user without invite gate)
- [x] 1.4 Прогнать targeted RED: `poetry run pytest tests/client_bot/test_callback_start_registration.py -vv` — падает на текущем production с create_user

## 2. Production

- [x] 2.1 Убрать `create_user` из callback Start path; сохранить `sm(read_only=True)` (decision: callback-start-entry-write-path)
- [x] 2.2 При `user is None`: non-write outcome — gate при `invite_gate`, иначе early return без MainMenu (design #2; spec Missing user)
- [x] 2.3 Не менять routing для существующего User (minimal → gate → full MainMenu)

## 3. Verification

- [x] 3.1 Targeted GREEN: `poetry run pytest tests/client_bot/test_callback_start_registration.py -vv`
- [x] 3.2 Adjacent при необходимости: integration onboarding callbacks `-k callback_start_registration` (если падают — поправить только assertions под контракт, не возвращать create)

## Telegram UI / Message Safety

Gate text/keyboard уже существующие (`get_gate_message_text` / `get_gate_keyboard`); новых copy не вводим. Checklist на reuse:

- [x] 3.3 Подтвердить, что missing-user + invite_gate отправляет тот же gate payload (text + reply_markup), без сырого technical leak
- [x] 3.4 В unit assert'ах на gate path проверить наличие gate text и non-null keyboard (лимиты текста покрыты существующим gate surface; новых динамических placeholders нет)

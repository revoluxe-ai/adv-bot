# add-free-ui-bot-access-guards

Продуктовый контракт Free UI и access guards для границы free/paid.

## Intent (актуально)

1. **Free-бот по умолчанию** — после прохождения entry-gates клиент видит
   полный free MainMenu (магазины, токен, ручные/Excel сценарии), без
   dual onboarding «presentation-only».
2. **Entry-gates (сохраняются):**
   - invite gate — опционально (`INVITE_GATE`, default true);
   - подписка на канал — обязательна (middleware, fail-closed);
   - phone / прочие явные onboarding write — без изменения ownership.
3. **Paid** — только авто-управление / платные automation-возможности;
   не отдельное «закрытие» free UI.
4. **Legacy `PRESENTATION_ONLY_MODE`** — не форкает gate middleware и не
   переключает `/start` / Callback Start на minimal presentation menu.
   Default env: false. Явное `true` не рекомендуется.

См. `design.md` и `specs/free-client-entry/spec.md`.
Связанный living main spec: `openspec/specs/callback-start-menu-return/spec.md`.

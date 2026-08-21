## 1. Baseline and test seams

- [ ] 1.1 LEGACY_BASELINE: зафиксировать существующие entrypoints подтверждения, отключения и W3-рендеринга в targeted `card_ab_hold` тестах; старые assertions использовать только как характеристику до intentional change, не требовать сохранения устаревшего поведения после исправления.
- [x] 1.2 TARGET_REGRESSION: подготовить contract cases для связанного пользователя, чужого пользователя, положительной позиции, отсутствующей позиции, нулевой, отрицательной и non-finite позиции; каждый новый или изменённый тест снабдить русским docstring с указанием spec `card-ab-hold-mode`.

## 2. Callback actor gate

- [x] 2.1 TARGET_REGRESSION (S01): через реальный callback confirmation entrypoint доказать, что связанный с кабинетом Telegram-пользователь проходит actor/stale gates и продолжает существующий explicit-confirmation flow без изменения lifecycle.
- [x] 2.2 TARGET_REGRESSION (S02): через реальный confirmation callback доказать для чужого пользователя нейтральный отказ без изменения PG/FSM/Redis/lifecycle state и без раскрытия состояния чужой кампании; проверять состояние до и после, а не только отсутствие вызова mock.
- [x] 2.3 TARGET_REGRESSION (S03): покрыть оба disable entrypoint — прямой EXIT и confirm-flow EXIT — для чужого пользователя; доказать отсутствие database write, Redis cleanup, FSM reset, redraw чужого состояния и lifecycle transition.
- [x] 2.4 Реализовать общий actor/access gate в Telegram A/B Hold handlers до stale-check и до любого confirm/disable writer: загрузить `AdvSetting`, проверить текущий `query.from_user.id` через существующий `get_wb_user_cabinet_for_adv_and_telegram`, вернуть нейтральный отказ при отсутствии связи и не менять callback schema.
- [x] 2.5 FINAL_ACCEPTANCE: проверить paired allowed/foreign behavior для confirmation и disable, включая сохранение существующего авторизованного EXIT cleanup и actor-bound redraw только после успешного gate.

## 3. Positive factual-position candidate filtering

- [x] 3.1 TARGET_REGRESSION (S04, S07): через реальный W3 row-construction и render path доказать, что конечная положительная factual position остаётся confirmable, proposed target place вычисляется из неё, а factual position и target place отображаются отдельными полями даже при числовом совпадении.
- [x] 3.2 TARGET_REGRESSION (S05, S06): через реальный factual-position read boundary и W3 render path доказать, что missing, zero, negative и non-finite positions исключаются с конкретной причиной, не превращаются в factual position `0` и не создают proposed target place `0`.
- [x] 3.3 TARGET_REGRESSION (S08, S09): через реальный `on_tp_confirm_all` path доказать, что mixed valid/invalid набор сохраняет только положительные ключи, а полностью невалидный набор останавливает подтверждение до writer/phase transition и показывает причину пустого валидного набора. Live PG/runtime evidence authored and executed in `tests/integration/card_ab_hold/test_confirmation_boundaries_live.py` against the validated disposable test database.
- [x] 3.4 Реализовать чистый candidate validator/helper и подключить его к `_tp_rows_from_adv`/W3 render и confirmation flow: сохранять только finite factual positions `> 0`, формировать причины исключения, строить proposed `tp_map` только по оставшемуся набору и не добавлять implicit zero fallback.
- [x] 3.5 FINAL_ACCEPTANCE: проверить, что пользователь видит исключённые ключи и причины, подтверждает только оставшийся валидный набор, а положительный разрешённый flow сохраняет существующее поведение.

## 4. Durable target-place write boundary

- [x] 4.1 TARGET_REGRESSION: добавить paired tests для существующего epoch write-path под `SELECT ... FOR UPDATE`: положительный полный `tp_map` и UI-filtered subset проходят, а пустой, неположительный, нецелочисленный или содержащий чужой ключ payload отклоняется без PG update, commit или phase transition. Live PG write/rejection tests are authored and executed in `tests/integration/card_ab_hold/test_confirmation_boundaries_live.py` against the validated disposable test database.
- [x] 4.2 Реализовать финальную проверку durable payload в существующем `confirm_target_places`/session writer до `UPDATE`/`COMMIT`: `tp_map` обязан быть непустым, содержать только положительные целочисленные target places и покрывать именно оставшийся подтверждаемый keyword-set.
- [x] 4.3 TARGET_REGRESSION (S10, S11): доказать, что setup tick, activation retry и обычный drift factual position не пересчитывают и не перезаписывают уже подтверждённый target place текущей epoch.
- [ ] 4.4 FINAL_ACCEPTANCE (S12, S13): доказать, что валидное подтверждение сохраняет WARM_UP, generation, durable PG/Redis lifecycle и существующий retry flow, а hardening не авторизует unrelated V3/shared-defaults/Excel/bid/budget/WB writers.

## 5. Telegram rejection and exclusion UX safety

- [x] 5.1 TARGET_REGRESSION: подготовить worst-case tests для neutral foreign-callback rejection, empty-valid-set notification и списка исключённых ключей; проверить отсутствие раскрытия чужой кампании и отсутствие raw technical text.
- [x] 5.2 Обновить только необходимые Telegram error/render surfaces, чтобы они сообщали нейтральный отказ, причины исключения и отсутствие валидных ключей, сохраняя порядок `keyword-set → WARM_UP → factual position/proposed target → target confirm → Auto confirmations` и не обещая автоматическую фиксацию target place.
- [x] 5.3 Проверить Telegram payload limits по `openspec/policies/telegram_bot_api_limits.md` на worst-case shop/campaign/keyword names, Cyrillic, emoji, HTML escaping и dynamic exclusion reasons; измерять `callback_data` в UTF-8 bytes, проверить parse mode/escaping, keyboard callbacks и отсутствие технических placeholders.

## 6. Scenario-plan and final verification

- [ ] 6.1 FINAL_ACCEPTANCE: закрыть материализованный scenario plan `SCPV1-2032f579212ef33b` всеми сценариями S01–S13 и сохранить evidence roles `TARGET_REGRESSION`/`FINAL_ACCEPTANCE`; не считать chat-only evidence заменой durable scenario receipt.
- [x] 6.2 Запустить targeted unit/integration suites для `tests/unit/auto_updater_v3/card_ab_hold/test_w3_confirmed_flow.py`, actor/disable handlers, epoch write gates, Telegram payload limits и связанных scenario seams; проверить, что regression tests падают при удалении guarded conditions.
- [x] 6.3 Выполнить `poetry run pyright-strict` и `git diff --check`; проверить документацию на всех новых/изменённых Python-модулях, публичных методах и тестовых helper-функциях, а также подтвердить отсутствие миграций и изменений WARM_UP/generation/PG/Redis lifecycle.

## Telegram UI / Message Safety

- [x] 6.4 Проверить все изменённые Telegram message, callback answer, inline keyboard и checklist surfaces с worst-case dynamic data согласно `openspec/policies/telegram_bot_api_limits.md`.
- [x] 6.5 Проверить лимиты `sendMessage.text`, `answerCallbackQuery.text` и `callback_data` в UTF-8 bytes, корректность parse mode/escaping, наличие ожидаемых keyboard buttons и отсутствие утечки технических деталей или данных чужой кампании.

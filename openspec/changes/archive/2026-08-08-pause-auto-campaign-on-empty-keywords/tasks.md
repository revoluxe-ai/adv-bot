## 1. Characterization и tests-first (до production)

- [x] 1.1 Characterization: зафиксировать текущее поведение V3 apply при force-off последнего ключа (пауза РК сейчас НЕ вызывается) — baseline для `pause-on-empty-keywords`.
- [x] 1.2 Unit tests-first (decision): «выключать больше нечего» → pause как **следующий** шаг после завершения OFF (не current/concurrent с OFF) — positive (last key) и paired negative (≥1 ключ остаётся) по spec «Pause campaign after last keyword off by bot».
- [x] 1.2a Unit tests-first: упорядоченность OFF → затем pause (pause не в том же шаге, что OFF) — scenarios «Nothing left to turn off» / «Pause is not concurrent with keyword off».
- [x] 1.3 Unit tests-first: отдельный reason empty-keywords ≠ schedule/budget/cost/balance — по spec «Distinct pause reason for empty keywords».
- [x] 1.4 Unit/integration tests-first: цикл recheck resume→всё ещё empty→re-pause и resume→есть активный ключ→не держать empty-pause — по spec «Periodic recheck while paused for empty keywords».
- [x] 1.5 Tests-first 7d: pause и recheck cycle при статистике только ≤7 дней (без requirement >7d) — по spec «Seven-day statistics window compatibility»; тесты MUST падать если код требует историю старше 7 дней.
- [x] 1.6 Regression: empty-keywords pause не маскируется под `TIME_SCHEDULE` / budget reasons; удаление gate ломает тест.
- [x] 1.7 Paired orthogonality: freeze ≠ stop — empty-keywords pause не EXIT’ит A/B Hold в OFF (mock/minimal Hold state) по spec «Orthogonality to A/B Hold freeze».

## 2. Reason code и отображение

- [x] 2.1 Добавить `AutoReasonCode` для empty-keywords + parse/display в reason_display (короткий UI-label).
- [x] 2.2 Docstrings на русском со ссылкой на spec requirement для новых enum/хелперов.

## 3. Detect + pause write-path

- [x] 3.1 Реализовать post-apply детект «OFF завершён и выключать больше нечего» в V3 apply/tick seam (по `empty-keywords-pause-write-path`); OFF остаётся текущим шагом.
- [x] 3.2 Вызвать существующий pause adapter **следующим** шагом после OFF (не concurrent); записать empty-keywords reason/intent.
- [x] 3.3 Убедиться, что при непустом наборе (ещё есть что выключать) pause по empty-keywords не вызывается (paired с 1.2).
- [x] 3.4 Не менять keyword selection / bid / whitelist / minus логику за пределами хука.

## 4. Recheck / resume в activity-control

- [x] 4.1 Встроить empty-keywords intent в `ensure_campaigns_active` (или эквивалентный gate): периодический start/recheck без отмены более приоритетных pause reasons.
- [x] 4.2 После recheck: если ключей снова нет — pause с empty-keywords; если ключи есть и нет других blockers — не держать empty-pause.
- [x] 4.3 Recheck MUST NOT запрашивать/ждать статистику >7 дней (согласовано с design D3 и tests 1.5).

## 5. User notification

- [x] 5.1 Сообщение пользователю при входе в empty-keywords pause: причина + периодическая перепроверка; debounce once-per-enter.
- [x] 5.2 При упоминании поддержки использовать только `const.SUPPORT_LINK`.

## Telegram UI / Message Safety

- [x] T1 Identify every changed Telegram payload surface (текст паузы/перепроверки).
- [x] T2 Add/update tests with worst-case dynamic placeholder data (длинные названия РК/магазина).
- [x] T3 Assert Telegram Bot API limits from `openspec/policies/telegram_bot_api_limits.md`.
- [x] T4 Assert valid parse_mode / escaping.
- [x] T5 Assert callback_data length in UTF-8 bytes (если добавляются callback-кнопки).
- [x] T6 Assert no raw technical text leaks to user (internal reason enums не в сыром виде).

## 6. Проверка границ change

- [x] 6.1 Пройти targeted unit (+ нужные integration) для этого change; убедиться в отсутствии EVOLUTION_SCOPE_DRIFT (нет tariff/disconnect/comms/onboarding tasks в коде).
- [x] 6.2 Обновить `LINKED_CHANGES` на карточке звезды / proposal evidence только после verify (не расширять DoD).

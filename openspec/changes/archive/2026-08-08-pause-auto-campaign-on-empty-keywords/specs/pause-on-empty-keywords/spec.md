## ADDED Requirements

### Requirement: Pause campaign after last keyword off by bot

На paid автокампании с активным ботом выключение ключей — **текущий** шаг
автоматики. Когда после такого выключения выключать больше нечего (активных
ключей не остаётся), система MUST поставить рекламную кампанию на паузу на
Wildberries как **следующий** шаг — после завершения OFF, не в том же шаге,
что выключение ключа, и не вместо OFF. Остальная логика выбора и ставок
ключей MUST NOT меняться этим требованием за пределами этого упорядоченного
перехода к паузе. Это Paid automation write-path; Free MUST NOT получать это
поведение как бесплатный automation core.

#### Scenario: Nothing left to turn off → pause is next step

- **GIVEN** paid автокампания с ботом и ровно одним активным ключом
- **WHEN** автоматика завершает выключение этого последнего активного ключа (текущий шаг = OFF)
- **THEN** система ставит кампанию на паузу на Wildberries как следующий шаг после OFF, а не как часть текущего шага выключения ключа

#### Scenario: Pause is not concurrent with keyword off

- **GIVEN** paid автокампания с ботом, где автоматика выключает последний активный ключ
- **WHEN** выполняется текущий шаг выключения ключа
- **THEN** pause кампании MUST NOT считаться тем же текущим шагом, что OFF ключа

#### Scenario: Non-empty keyword set does not trigger empty-keywords pause

- **GIVEN** paid автокампания с ботом и двумя активными ключами
- **WHEN** автоматика выключает только один из них и остаётся хотя бы один активный ключ (выключать ещё есть что)
- **THEN** система MUST NOT ставить кампанию на паузу по причине empty-keywords

### Requirement: Distinct pause reason for empty keywords

Пауза из-за отсутствия активных ключей MUST иметь отдельную причину
активности, отличную от бюджета, лимитов расхода, расписания показов и
insufficient balance. Пользовательский интерфейс MUST показывать эту причину
так, чтобы её нельзя было спутать с паузой по расписанию или бюджету.

#### Scenario: Reason is not masked as schedule or budget

- **GIVEN** кампания поставлена на паузу из-за отсутствия активных ключей после действий бота
- **WHEN** пользователь или система читает причину паузы
- **THEN** причина идентифицируется как empty-keywords (или эквивалент «нет активных ключей»), а не как schedule/budget/cost/balance

### Requirement: Periodic recheck while paused for empty keywords

Пока кампания на паузе по причине empty-keywords, система MUST периодически
снова запускать кампанию и перепроверять возможность работы автоматики.
Если после перепроверки активных ключей снова нет, система MUST снова
поставить кампанию на паузу с той же причиной empty-keywords. Более
приоритетные причины паузы (расписание, бюджет, баланс) MUST NOT быть
тихо перезаписаны так, будто empty-keywords их отменяет.

#### Scenario: Recheck resumes then re-pauses when still empty

- **GIVEN** кампания на паузе по empty-keywords и интервал перепроверки наступил
- **WHEN** система выполняет перепроверку и активных ключей по-прежнему нет
- **THEN** кампания снова оказывается на паузе с причиной empty-keywords

#### Scenario: Recheck allows continue when keywords become active

- **GIVEN** кампания на паузе по empty-keywords
- **WHEN** система выполняет перепроверку и автоматика снова имеет хотя бы один активный ключ без нарушения других pause-правил
- **THEN** кампания MUST NOT оставаться на паузе исключительно из-за устаревшего empty-keywords состояния

### Requirement: Seven-day statistics window compatibility

Корректность паузы и периодической перепроверки MUST NOT зависеть от наличия
статистики старше семи дней. Триггер паузы MUST опираться на состояние
активных ключей. Перепроверка и решения автоматики о ключах MUST использовать
только доступное окно статистики не длиннее семи дней (текущий продуктовый
лимит). Отсутствие более длинной истории MUST NOT считаться дефектом,
блокирующим цикл pause→recheck.

#### Scenario: Pause without history older than seven days

- **GIVEN** у кампании доступна статистика не более чем за семь дней (или меньше)
- **WHEN** бот выключает последний активный ключ
- **THEN** система всё равно ставит кампанию на паузу по empty-keywords

#### Scenario: Recheck cycle without history older than seven days

- **GIVEN** кампания на паузе по empty-keywords и доступна статистика только в пределах семи дней
- **WHEN** наступает перепроверка
- **THEN** система выполняет цикл перепроверки без требования статистики старше семи дней

### Requirement: User notification on empty-keywords pause

При входе в паузу по empty-keywords система MUST уведомить пользователя
понятным сообщением: что кампания на паузе из-за отсутствия активных ключей
после работы бота, и что будет периодическая перепроверка. Сообщение MUST
укладываться в лимиты Telegram Bot API. Если указывается помощь поддержки,
MUST использоваться существующий `SUPPORT_LINK` администратора, без нового
канала поддержки в этом change.

#### Scenario: User is informed about pause and recheck

- **GIVEN** кампания впервые переходит в паузу по empty-keywords в данном эпизоде
- **WHEN** пауза применена
- **THEN** пользователь получает сообщение с причиной (нет активных ключей) и упоминанием периодической перепроверки

### Requirement: Orthogonality to A/B Hold freeze

Empty-keywords pause MUST оставаться ортогональным к A/B Hold freeze:
пауза кампании по empty-keywords MUST NOT реализовываться как нарушение
freeze через обычные keyword writers Hold, и MUST NOT трактоваться как
выход из Hold. Допустимо переиспользовать ordinary campaign activity-control
pause/start, согласованный с моделью «freeze ≠ stop».

#### Scenario: Empty-keywords pause does not exit Hold

- **GIVEN** кампания в A/B Hold non-OFF и бот (в рамках допустимого Hold safety/overspend path) приводит к отсутствию активных ключей либо срабатывает empty-keywords путь ортогонально
- **WHEN** применяется пауза по empty-keywords
- **THEN** режим A/B Hold MUST NOT автоматически переводиться в OFF только из-за этой паузы

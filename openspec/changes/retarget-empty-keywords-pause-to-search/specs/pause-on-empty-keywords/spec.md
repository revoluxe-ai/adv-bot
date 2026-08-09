## MODIFIED Requirements

### Requirement: Pause campaign after last keyword off by bot

На paid автокампании с активным ботом выключение ключей — **текущий** шаг
автоматики. Когда после такого выключения выключать больше нечего (активных
ключей не остаётся), система MUST поставить на паузу на Wildberries **ногу
Search** того же комплекта авто-настройки как **следующий** шаг — после
завершения OFF, не в том же шаге, что выключение ключа, и не вместо OFF.
Система MUST NOT ставить на паузу ногу Auto по причине empty-keywords.
Остальная логика выбора и ставок ключей MUST NOT меняться этим требованием
за пределами этого упорядоченного перехода к паузе Search. Это Paid
automation write-path; Free MUST NOT получать это поведение как бесплатный
automation core.

#### Scenario: Nothing left to turn off → Search pause is next step

- **GIVEN** paid авто-настройка с ботом, ногой Search и ровно одним активным ключом
- **WHEN** автоматика завершает выключение этого последнего активного ключа (текущий шаг = OFF)
- **THEN** система ставит ногу Search на паузу на Wildberries как следующий шаг после OFF, а не как часть текущего шага выключения ключа

#### Scenario: Auto leg is not paused for empty-keywords

- **GIVEN** paid авто-настройка с ботом, ногами Auto и Search, и срабатывает empty-keywords pause path
- **WHEN** система применяет паузу по причине empty-keywords
- **THEN** нога Auto MUST NOT быть поставлена на паузу этим path, а нога Search MUST быть на паузе (если Search присутствует и была активна)

#### Scenario: Pause is not concurrent with keyword off

- **GIVEN** paid автокампания с ботом, где автоматика выключает последний активный ключ
- **WHEN** выполняется текущий шаг выключения ключа
- **THEN** pause ноги Search MUST NOT считаться тем же текущим шагом, что OFF ключа

#### Scenario: Non-empty keyword set does not trigger empty-keywords pause

- **GIVEN** paid автокампания с ботом и двумя активными ключами
- **WHEN** автоматика выключает только один из них и остаётся хотя бы один активный ключ (выключать ещё есть что)
- **THEN** система MUST NOT ставить ногу Search на паузу по причине empty-keywords

### Requirement: Distinct pause reason for empty keywords

Пауза из-за отсутствия активных ключей MUST иметь отдельную причину
активности со значением empty-keywords (или эквивалент «нет активных ключей»),
отличную от бюджета, лимитов расхода, расписания показов и insufficient
balance. Причина MUST относиться к паузе **ноги Search** для этого path.
Пользовательский интерфейс MUST показывать эту причину так, чтобы её нельзя
было спутать с паузой по расписанию или бюджету.

#### Scenario: Reason is not masked as schedule or budget

- **GIVEN** нога Search поставлена на паузу из-за отсутствия активных ключей после действий бота
- **WHEN** пользователь или система читает причину паузы
- **THEN** причина идентифицируется как empty-keywords (или эквивалент «нет активных ключей»), а не как schedule/budget/cost/balance

### Requirement: Periodic recheck while paused for empty keywords

Пока нога Search на паузе по причине empty-keywords, система MUST периодически
снова запускать **ту же ногу Search** и перепроверять возможность работы
автоматики. Recheck MUST NOT считаться выполненным, если запущена только нога
Auto, а Search остаётся на паузе исключительно из-за empty-keywords. Если
после перепроверки активных ключей снова нет, система MUST снова поставить
ногу Search на паузу с той же причиной empty-keywords. Более приоритетные
причины паузы Search (расписание, бюджет, баланс) MUST NOT быть тихо
перезаписаны так, будто empty-keywords их отменяет.

#### Scenario: Recheck resumes Search then re-pauses when still empty

- **GIVEN** нога Search на паузе по empty-keywords и интервал перепроверки наступил
- **WHEN** система выполняет перепроверку и активных ключей по-прежнему нет
- **THEN** нога Search снова оказывается на паузе с причиной empty-keywords

#### Scenario: Recheck allows continue when keywords become active

- **GIVEN** нога Search на паузе по empty-keywords
- **WHEN** система выполняет перепроверку и автоматика снова имеет хотя бы один активный ключ без нарушения других pause-правил Search
- **THEN** нога Search MUST NOT оставаться на паузе исключительно из-за устаревшего empty-keywords состояния

#### Scenario: Auto-only start does not satisfy empty-keywords recheck

- **GIVEN** нога Search на паузе по empty-keywords
- **WHEN** система запускает только ногу Auto, не запуская Search
- **THEN** это MUST NOT считаться выполненной перепроверкой empty-keywords для ноги Search

## ADDED Requirements

### Requirement: Empty-keywords pause targets Search leg only

Для причины empty-keywords целевая сущность паузы и перепроверки — нога
Search комплекта. Система MUST использовать Search pause/start write-path и
MUST NOT использовать Auto pause write-path для этой причины. Отсутствие
ноги Search MUST NOT приводить к паузе Auto «вместо» Search.

#### Scenario: Wrong adapter Auto pause is forbidden

- **GIVEN** срабатывает empty-keywords pause path
- **WHEN** система выбирает WB pause adapter для этой причины
- **THEN** Auto pause adapter MUST NOT быть использован; MUST быть использован Search pause adapter при наличии Search

#### Scenario: Missing Search leg does not pause Auto

- **GIVEN** paid авто-настройка с ботом без ноги Search и empty-keywords условие выполнено
- **WHEN** система обрабатывает empty-keywords pause path
- **THEN** система MUST NOT ставить ногу Auto на паузу по причине empty-keywords

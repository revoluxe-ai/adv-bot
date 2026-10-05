## ADDED Requirements

### Requirement: Каждая рекламная нога имеет собственный фактический CPO

Система MUST рассчитывать фактический CPO Auto и Search как отдельные leg-level показатели, используя расходы и заказы соответствующей рекламной ноги за один и тот же согласованный observation window. Идентичность Auto/Search MUST соответствовать структурной связке кампании, а не WB marketing type.

#### Scenario: Auto и Search имеют разную экономику
- **GIVEN** у связки есть активные Auto и Search ноги
- **WHEN** их расходы и заказы дают разные значения CPO
- **THEN** система хранит/возвращает два независимых значения CPO Auto и CPO Search

#### Scenario: Search-нога отсутствует
- **GIVEN** у кампании нет связанной Search-ноги
- **WHEN** система собирает leg-level CPO
- **THEN** CPO Search недоступен и MUST NOT подменяться CPO Auto или общим CPO

### Requirement: Search automation использует только CPO Search

Любое leg-level решение, которое изменяет управление Search/ключами на основании фактического CPO, MUST использовать CPO Search и MUST NOT использовать общий CPO или CPO Auto как substitute/fallback.

#### Scenario: Auto плохой, Search хороший
- **GIVEN** CPO Auto превышает управляющий порог, а CPO Search не превышает его
- **WHEN** Search/keyword automation принимает CPO-зависимое решение
- **THEN** решение MUST оцениваться по CPO Search и MUST NOT ухудшать Search только из-за CPO Auto или общего CPO

#### Scenario: Search CPO недоступен
- **GIVEN** CPO Search нельзя надёжно вычислить
- **WHEN** Search/keyword automation доходит до CPO-зависимого решения
- **THEN** система MUST NOT использовать CPO Auto или общий CPO вместо Search CPO
- **AND** destructive Search action MUST NOT быть обоснован только экономикой другой ноги

### Requirement: Auto automation использует только CPO Auto

Любое leg-level решение Auto, которое зависит от фактического CPO, MUST использовать CPO Auto и MUST NOT использовать CPO Search или общий CPO как substitute/fallback.

#### Scenario: Search плохой, Auto хороший
- **GIVEN** CPO Search превышает управляющий порог, а CPO Auto не превышает его
- **WHEN** Auto automation принимает CPO-зависимое решение
- **THEN** решение MUST оцениваться по CPO Auto и MUST NOT ухудшать Auto только из-за CPO Search или общего CPO

#### Scenario: Auto CPO недоступен
- **GIVEN** CPO Auto нельзя надёжно вычислить
- **WHEN** Auto automation доходит до CPO-зависимого решения
- **THEN** система MUST NOT использовать CPO Search или общий CPO вместо Auto CPO

### Requirement: Общий CPO остаётся отдельной aggregate-метрикой

Система MAY сохранять общий CPO связки Auto + Search для plan/fact аналитики и других явно aggregate-сценариев, но MUST NOT выдавать его за CPO конкретной ноги.

#### Scenario: Aggregate CPO хуже обеих leg-level оценок
- **GIVEN** общий CPO связки отличается от CPO Auto и CPO Search
- **WHEN** система отображает или использует leg-level CPO
- **THEN** общий CPO MUST NOT подменять ни одно из leg-level значений

### Requirement: Интерфейс показывает CPO Auto и CPO Search отдельно

Paid UI кампании MUST показывать отдельные значения CPO Auto и CPO Search из того же leg-level economics snapshot, который доступен управляющим consumers. Недоступное значение MUST отображаться как недоступное, а не как значение другой ноги.

#### Scenario: Обе ноги имеют данные
- **GIVEN** доступны CPO Auto и CPO Search
- **WHEN** пользователь открывает интерфейс экономики/ключей связанной кампании
- **THEN** интерфейс показывает оба значения с явными подписями Auto и Search

#### Scenario: Одна нога не имеет данных
- **GIVEN** CPO одной ноги недоступен, а второй доступен
- **WHEN** пользователь открывает интерфейс
- **THEN** доступное значение показывается для своей ноги
- **AND** недоступная нога отображается без подстановки соседнего или общего CPO

### Requirement: Runtime и UI используют согласованную семантику CPO

Для одного и того же snapshot/window значение leg CPO, показанное пользователю, MUST соответствовать значению, передаваемому CPO-зависимому consumer этой ноги.

#### Scenario: Search CPO отображается и используется
- **GIVEN** Search CPO рассчитан для текущего observation window
- **WHEN** UI отображает Search CPO и Search automation выполняет CPO-зависимое решение
- **THEN** оба пути используют одну и ту же leg-level семантику и источник данных

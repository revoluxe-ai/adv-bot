<!--
Sync Impact Report
- Version change: 1.0.0 -> 1.1.0
- Modified principles:
  - Respect Existing Architecture -> Respect Existing Architecture
  - Keep Data Semantics Explicit -> Data Semantics
  - Read-Only Analytics -> Controlled State Changes
  - Separate Forecasts From Facts -> Safe Failure
  - Change Minimally And Test Proportionally -> Minimal, Backward-Compatible Change
- Added sections: None
- Removed sections: None
- Templates requiring updates: None
- Follow-up TODOs:
  - Future feature specification should define read-only predictor rules and forecast accuracy dependencies.
-->
# adv-bot Constitution

## Core Principles

### I. Respect Existing Architecture
Перед изменениями нужно изучить текущую реализацию и сохранять существующие
архитектурные границы, соглашения и публичные контракты проекта. Новое решение
должно вписываться в текущую структуру `app/`, `tests/` и `.specify/`, а не
перестраивать проект без необходимости.

### II. Data Semantics
Любые факты, агрегаты, целевые и прогнозные значения должны иметь явную
семантику и источник. Позиции можно использовать как пример, но нельзя
смешивать наблюдаемые значения с производными оценками без явного обозначения
типа данных, окна, метода и происхождения.

### III. Controlled State Changes
Изменения ставок, денег, кампаний, пользовательских настроек, БД и внешних
систем допустимы только при явном контракте и отдельном согласовании. Любая
функция, которая пишет состояние или вызывает внешнее действие, должна явно
обозначать свои side effects и границы ответственности.

### IV. Safe Failure
Отсутствие, конфликт или противоречивость данных не должны приводить к опасным
изменениям состояния. Ошибки должны быть наблюдаемыми, а поведение при
неполных данных должно быть безопасным по умолчанию, а не скрыто
компенсирующим.

### V. Minimal, Backward-Compatible Change
Изменения должны быть минимальными, обратно совместимыми и покрытыми тестами
пропорционально риску. Если поведение меняется, тесты должны подтверждать
сохранение контрактов и точность новых допущений.

## Governance

Конституция имеет приоритет над локальными привычками и разовыми правками.
Любое изменение принципов требует короткого обоснования, проверки влияния на
существующие контракты и обновления тестов или документации, если риск
изменения затрагивает поведение проекта.

Частные правила для read-only predictor, а также зависимости точности прогноза
от полноты данных, выносятся в будущую feature specification и не закрепляются
в этой конституции.

**Version**: 1.1.0 | **Ratified**: 2026-07-11 | **Last Amended**: 2026-07-11

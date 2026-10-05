# Owner Contract: campaign-settings-history

## Owner intent

История должна фиксировать изменения настроек рекламных кампаний WB Sky во времени так, чтобы при добавлении или изменении настройки разработчик не мог забыть включить её в history/Excel contract.

## Required semantics

- PostgreSQL остаётся authority текущих настроек.
- ClickHouse хранит только исторические snapshots и не становится authority для production settings writes.
- История фиксирует canonical normalized settings aggregate кампании, а не случайный набор колонок одной таблицы.
- Canonical aggregate охватывает текущие settings-owned sources: AdvSetting, KeywordSetting, AutoShelfBidControlSettings, AdvTimeSettings и AdvTimeWeekMask.
- Физический WB-state, plan/fact, статистика, расходы, transient runtime/decision state и operational diagnostics не являются настройками только потому, что лежат рядом в БД.
- Каждое candidate field в settings-owned source MUST иметь явную classification policy.
- Новое, удалённое или переименованное candidate field без обновлённой classification policy MUST fail closed на deterministic contract test.
- Silent ignore неизвестного settings-поля запрещён.
- History policy и Excel policy принадлежат одному field registry/contract; два независимых ручных whitelist запрещены.
- Для history field policy должна явно говорить include/exclude и причину exclusion.
- Для Excel field policy должна явно говорить editable/read-only/excluded.
- History snapshot пишется только если canonical hash изменился.
- Одинаковые последовательные состояния не создают дублирующие snapshots.
- Canonical payload имеет schema_version и deterministic normalization.
- Ориентир polling — один сбор примерно раз в 5 минут; точный scheduler cadence может быть конфигурацией, но изменение cadence не меняет семантику snapshots.
- Изменение contract shape/normalization, влияющее на интерпретацию payload, требует version bump.
- Старые snapshots должны оставаться интерпретируемыми по их schema_version.

## Out of scope

- AI/API/MCP write control plane.
- Изменение логики bidder/V3/ставок.
- История фактического WB-state.
- Клиентская аналитическая витрина history.
- Редизайн Telegram UI.

## Owner acceptance

Основной acceptance-инвариант: если завтра в settings-owned модели появится новое поле настройки, PR не должен пройти contract tests, пока это поле не получит явную history/Excel classification.

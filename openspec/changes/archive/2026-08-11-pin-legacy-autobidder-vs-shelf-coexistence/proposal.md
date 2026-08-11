## Evolution Context

```text
EVOLUTION_LINK: LINKED
STAR_ID: affordable-auto-pause-on-empty
INCREMENT_ID: INC-AUTO-COST-SHELF-COEXIST-01
KEEP: Pin/prove «управление ставкой для Авто» vs «управление ставкой в полках»; ON → старый игнорируется; characterization + paired regression; thin spec/design; proposed ADL ownership; no terminal retest; no bidder rewrite
HARD: EVOLUTION_SCOPE_DRIFT if artifacts/tasks include OUT_OF_SCOPE or FUTURE_INCREMENTS
FORWARD: do not mask future shelf-terminal under cost_rule_failed; freeze≠stop; Search empty-keywords orthogonal
```

## Why

В настройках РК рядом живут два способа автоматически менять ставку Авто: старый путь через **«Управление ставкой» → «Включить управление ставкой для Авто»** и новый — **«Управление ставкой в полках»**. Без явного контракта «кто пишет ставку» легко допустить конфликт двух модулей или смешать их с паузой по себестоимости. Сейчас нужно зафиксировать и доказать правило Owner: когда новый модуль включён, старый **игнорируется** — как фундамент перед будущей честной паузой «ставки в полках исчерпаны».

## What Changes

### Intent

Один результат: контракт сосуществования старого и нового модуля управления ставкой Авто зафиксирован в spec/design/decision и доказан characterization + paired regression (вкл/выкл нового модуля). Когда **«Управление ставкой в полках»** включено — старый путь **«управление ставкой для Авто»** не меняет ставку. Алгоритмы выбора ставки / plan_distance не переписываются.

### Current behavior

- В UI есть оба входа: главное меню РК → **«Управление ставкой»** → внутри этого подменю **«Включить/Выключить управление ставкой для Авто»**; и отдельно в главном меню РК → **«Управление ставкой в полках»** → внутри **«Включить/Выключить управление»**.
 - Поведение «новый включён → старый не пишет ставку» и различимость причин pause/start vs записи ставок **не** закреплены отдельной capability/spec как проверяемый контракт сосуществования.
- В registry нет accepted decision про ownership write-path «ставка для Авто» vs «ставка в полках» (**Architecture Decision Missing** до proposed decision в этом change).
- Контроль активности кампании (пауза/старт, в т.ч. `cost_rule_failed`) и Search empty-keywords — соседние контуры; не являются этим контрактом «кто пишет ставку».

### Desired behavior

- Когда **«Управление ставкой в полках»** **выключено** и **«управление ставкой для Авто»** **включено** — старый модуль MAY менять ставку Авто; новый MUST NOT менять ставку.
- Когда **«Управление ставкой в полках»** **включено** — новый модуль MAY менять ставку; старый модуль (**«управление ставкой для Авто»**) MUST NOT менять ставку (игнорируется).
- Запись ставки полками MUST NOT маскироваться под reason cost-паузы (`cost_rule_failed`); cost-пауза MUST NOT выдавать себя за действия «управления ставкой в полках».
- Будущая терминальная причина «полки исчерпаны» MUST NOT вводиться этим change и MUST NOT маскироваться под обычный `cost_rule_failed` (forward-compat).
- Контракт MUST быть проверяем paired scenarios (новый вкл / новый выкл).

### Scope in

- Thin capability/spec контракта сосуществования двух UI-модулей ставки Авто.
- Design + proposed architecture decision: ownership границ «кто пишет ставку Авто» (старый vs новый); ортогональность к контролю активности и к Search empty-keywords.
- Characterization и paired regression под правило «новый вкл → старый игнорируется» и обратный режим.
- Уточнение/минимальная правка поведения **только если** текущий runtime нарушает правило Owner (без rewrite selection / plan_distance).

### Scope out

- Терминальная пауза «ставки в полках исчерпаны» и отложенный перетест.
- Empty-keywords Search path.
- Fair Auto/Search billing, тариф 1000₽, communications, disconnect, onboarding.
- Retire updater v2.
- Перепись OLD_UPDATE / shelf bid selection / plan_distance math.
- Новый terminal Auto reason или DB latch под shelf-exhausted.
- Смена смысла кнопок «стандартный / кластерный биддер» и режима раскрутки РС (полок) как отдельный продукт.

### Risk

- High-risk зона: автоматическая запись ставок Auto; ошибка в gate «игнорировать старый» даст двойную запись ставки или отключит нужный legacy-путь при выключенных полках.
- Путаница с контролем активности / `cost_rule_failed` при слишком широком scope.

### Rollback idea

- Откатить только gate/tests/spec этого change; вернуть прежнее включение старого пути, если правка поведения оказалась ошибочной. Алгоритмы выбора ставки не затрагиваются → откат узкий.

## Capabilities

### New Capabilities

- `auto-bid-module-coexistence`: observable контракт взаимного исключения записи ставки Авто между UI-путями **«Управление ставкой» → «управление ставкой для Авто»** и **«Управление ставкой в полках»** (вкл/выкл); различимость записи ставки и cost-паузы; без terminal shelf pause.

### Modified Capabilities

- (нет) — `pause-on-empty-keywords` и прочие main specs не меняют requirements этим change (ортогональны).

## Impact

- Paid automation: shop-runner / activity вокруг Auto bid writers и флага управления ставкой в полках; UI-смысл двух кнопок меню РК как границы контракта.
- Architecture: потребуется proposed decision ownership write-path (сейчас **Architecture Decision Missing** в registry); без него change не apply-ready.
- Тесты: characterization + paired ON/OFF; без расширения в billing/empty-keywords/terminal shelf.
- Пользовательский paid-интерфейс кнопок не ломаем по смыслу: фиксируем правило, кто реально меняет ставку при вкл/выкл.

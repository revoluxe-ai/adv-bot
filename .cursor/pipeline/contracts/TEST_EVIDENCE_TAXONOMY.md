# Test Evidence Taxonomy

Единый словарь классов test evidence для OPSX-команд и project rules.

```text
CONTRACT_ID=OPSX_TEST_EVIDENCE_TAXONOMY_V1
```

## Принцип

Pytest marker, каталог теста и evidence class — разные измерения.

Например, тест под `tests/unit/` может быть `scenario_seam`, если он проходит
реальную production orchestration до тонкого внешнего конца. Это не делает его
live/store integration. `destructive_local` описывает способ исполнения, а не
полноту доказательства Spec Scenario.

Команды MUST указывать:

```text
TEST_ID:
PYTEST_MARKERS:
EVIDENCE_CLASS:
EXECUTION_CLASS:
PROVES:
DOES_NOT_PROVE:
```

## Evidence classes

### `unit_component`

Изолированная проверка decision/function/component logic.

Доказывает локальные вычисления и edge cases. Не доказывает runtime wiring,
store query, внешний adapter или полный Spec Scenario.

### `scenario_seam`

Проверка Spec Scenario через настоящий production entrypoint либо ближайший
runtime-reachable orchestration seam.

Обязательно:

- реальная causal/business logic выполняется;
- production input/state shape сохранена;
- guard/candidate/handler path достигается;
- mocks/fakes стоят только после проверяемой causal boundary;
- observable THEN и forbidden/allowed effects проверены;
- тест падает при удалении requirement или guard.

### `side_effect_proof` (`PA_SIDE_EFFECT_PROOF`)

Доказательство **this-run** внешнего эффекта (или forbidden sibling
non-effect) для Product Acceptance
(`.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md` pillar SIDE_EFFECT_PROOF).

Обязательно, когда acceptance scenario утверждает mutation наружу
(WB pause/start, paid notify send, billing write, эквивалент):

- в том же test run наблюдается вызов/adapter эффекта (methods_called /
  await assert / equivalent), **или**
- явно доказан forbidden non-effect на sibling target;

Запрещено считать PA-sufficient:

- только Redis intent / durable reason / latch без this-run mutation;
- OR-armed proxies (`intent_after OR pause_path_armed`), где GREEN возможен
  без this-run external call;
- «кампания уже была paused» как успех текущего arm-path без this-run call.

Маркер: `EVIDENCE_CLASS=side_effect_proof` (или `PROVES` includes
`PA_SIDE_EFFECT_PROOF`). Weak/missing ⇒ Product Acceptance FAIL pillar
`SIDE_EFFECT_PROOF`, не archive GO.

### `runtime_entrypoint`

Проверка реального runtime handler/scheduler/worker entrypoint с допустимыми
тонкими внешними stubs. Доказывает wiring выше orchestration seam.

### `boundary_adapter`

Проверка сериализации, request/response shape, exception mapping или transport
adapter без обязательного live store/network.

### `boundary_integration`

Проверка реального test provider/end:

- PG — live `async_session` либо production session-maker seam на test DB;
- CH — live test client;
- Redis — fakeredis либо declared boundary adapter согласно testing-rules;
- WB/HTTP — sandbox/live/recorded schema proof по отдельной policy;
- Telegram — real library/API shape contract без пользовательской отправки,
  если live явно не разрешён.

Boundary integration доказывает end contract, но сам по себе не доказывает
полный Spec Scenario.

### `stub_contract`

Executable parity между fake/stub из `scenario_seam` и реальным boundary:

- request shape;
- success return;
- relevant empty/failure responses;
- exception mapping;
- async/sync semantics;
- field types, enums, identity и optionality.

Сильное доказательство использует общий reviewed `ContractCase`, fixture,
schema или golden. Две вручную продублированные структуры без общего contract
source — `PARITY_WEAK`.

### `load_or_performance_measurement`

Измерительный тест нагрузки, latency, throughput, memory или concurrency.

Он требуется только по explicit performance requirement/report. Команда
`/opsx-performance-review` является read-only causal review и не считается
нагрузочным прогоном.

## Execution classes

### `fast_local`

Не требует Docker, live PG/CH, network или destructive fixtures.

### `destructive_local`

Тест с `@pytest.mark.destructive_local`, который может поднимать, reset-ить или
изменять локальную test infrastructure.

Это:

- opt-in execution class;
- не синоним `boundary_integration`;
- не доказательство полного Scenario;
- не production destructive action.

Один `-m integration` не должен молча выбирать `destructive_local`.

### `authorized_live`

Live/sandbox/network/destructive execution с отдельным owner contract и
одноразовой авторизацией. Наличие test code не доказывает, что этот тест был
исполнен.

## Store defaults

```text
PG/CH contract changed
→ boundary_integration required

Redis boundary
→ fakeredis/boundary_adapter may be sufficient

WB/HTTP destructive end
→ scenario_seam may stub transport after causal boundary
→ separate boundary proof required for stub_contract parity
```

Для PG session mode:

```text
WRITE            → sm(read_only=False)
PURE_READ        → sm(read_only=True)
READ_AFTER_WRITE → sm(read_only=False)
```

## Forbidden conflations

Запрещено:

- называть любой test с `AsyncMock` интеграционным;
- считать `destructive_local` полным Spec Scenario evidence;
- считать unit-mock proof для PG/CH;
- считать найденный, но не выполненный тест green evidence;
- считать `CACHE_HIT` / `SKIPPED_CACHED` (destructive selective cache)
  EXECUTED=YES green evidence для archive, Scenario certify или
  `authorized_live`;
- считать static performance review нагрузочным тестом;
- полностью mock-ать causal boundary проверяемого Scenario;
- автоматически обновлять golden/ContractCase текущим live output.

## Freshness

Executed evidence MUST быть связано с текущими:

```text
TEST_CONTENT_SHA:
CONTRACT_SHA:
PRODUCTION_BOUNDARY_SHA:
FAKE_SHA:                 # когда fake участвует
SCHEMA_SHA:               # когда store schema релевантна
WORKTREE_FINGERPRINT:
```

Несовпадение обязательного hash делает evidence stale, а не PASS.

`CACHE_HIT` / `SKIPPED_CACHED` из
`.cursor/static-check/contracts/destructive-selective-cache.md` — только
optimization receipt для `CACHE_MODE=dev`. Это не замена свежего
executed run для `/opsx-verify` archive, Scenario certify или
`authorized_live`. Перед archive/PR confidence используй `CACHE_OFF` /
`CACHE_FORCE` (или INTERIM `CACHE_DEGRADED` run-all).

## Ownership

- Spec Scenario — source observable behavior.
- Production DTO/interface/schema — source technical shape.
- Reviewed ContractCase — executable shared contract.
- Test writer — автор test-only ContractCase/fake/scenario tests.
- External-gap writer — автор production seam и PG/CH provider integration.
- Independent coverage auditor — владелец coverage verdict.
- `/opsx-verify` — владелец archive verdict.

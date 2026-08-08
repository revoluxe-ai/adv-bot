---
name: /opsx-spec-scenario-coverage
id: opsx-spec-scenario-coverage
category: Workflow
description: "Strict read-only audit: every OpenSpec Scenario maps to an executed production-flow test, required live/store end tests, and verified stub-contract parity."
argument-hint: "change=<change-id> [run=targeted|none] [scenario=<exact-title>]"
---

# /opsx-spec-scenario-coverage

Проверь **полноту и честность test evidence** для каждого Scenario текущего
OpenSpec change.

Команда отвечает на вопросы:

1. Для каждого ли Spec Scenario существует тест полного production-flow?
2. Проходит ли тест через реальную causal/business logic до тонких внешних
   концов, а не mock-ает проверяемое поведение?
3. Для каждого stubbed end существует ли отдельный boundary/store integration
   test, доказывающий реальный request/response contract?
4. Проверено ли, что stub в scenario-flow принимает и возвращает **ровно ту же
   форму**, которую доказывает boundary integration test?
5. Если Scenario включает и запись, и последующее чтение PG/CH, существуют ли
   отдельные integration tests для write-end и read-end?
6. Были ли требуемые тесты реально выполнены на текущем snapshot?

```text
COMMAND_MODE=READ_ONLY
PRODUCT_WRITE=FORBIDDEN
TEST_WRITE=FORBIDDEN
OPENSPEC_WRITE=FORBIDDEN
ARCHIVE_VERDICT_OWNER=/opsx-verify
```

## User input

```text
$ARGUMENTS
```

Required:

```text
change=<change-id>
```

Optional:

| Token | Meaning |
|---|---|
| `run=targeted` | Выполнить найденные targeted test ids (default) |
| `run=none` | Только inspect; execution evidence будет `NOT_EXECUTED`, поэтому полный PASS невозможен |
| `scenario=<exact-title>` | Узкий diagnostic audit одного Scenario; не является полным change PASS |

Если `change=` отсутствует или change не существует:

```text
STATUS: BLOCKED
REASON: CHANGE_REQUIRED_OR_NOT_FOUND
NEXT_ACTION: /opsx-spec-scenario-coverage change=<change-id>
```

Не выдумывай change id и не выбирай похожий change молча.

## Authority and relationship

Эта команда — отдельный строгий matrix-auditor.

Она:

- читает Spec Scenarios как source of required observable behavior;
- может читать additive `TEST_COVERAGE_PACKET` из `/opsx-invariant`;
- дополняет `/opsx-external-call-coverage`, но не заменяет его diff inventory;
- не пишет тесты (`/opsx-test`);
- не создаёт production seams (`/opsx-apply` или
  `/opsx-close-external-gap` по соответствующему packet);
- не выдаёт archive `GO` (`/opsx-verify`);
- не запускает live production, WB writes, migrations или destructive tests
  без их собственного authorization contract.

Пересечение с другими coverage-командами допустимо: эта команда владеет
только verdict по матрице **Spec Scenario × test evidence**.

## Canonical evidence classes

Если существует
`.cursor/pipeline/contracts/TEST_EVIDENCE_TAXONOMY.md`, он является SoT.
До его появления применяй следующие fail-closed определения вместе с
`.cursor/rules/testing-rules.mdc`.

### `unit_component`

Проверяет изолированную decision/function/component logic. Может использовать
mocks. Не доказывает production wiring, store query или полный Scenario-flow.

### `scenario_seam`

Главное доказательство Spec Scenario:

- начинает с production entrypoint либо ближайшего runtime-reachable
  orchestration entry;
- выполняет реальную causal/business logic Scenario;
- сохраняет production input/state shape;
- доходит до candidate/guard/handler/write-or-read adapter boundary;
- stub-ает только **thin destructive ends**, где уже нет проверяемой
  business logic: WB/HTTP transport, Telegram transport, внешний network,
  иногда injected PG/CH adapter после реальной orchestration boundary;
- проверяет observable outcome, allowed effect и forbidden effect;
- падает при удалении requirement/guard из Scenario.

`scenario_seam` может быть pytest unit по marker/path, но по evidence class это
не `unit_component`. Не называй его live/store integration.

### `boundary_integration`

Отдельный тест реального thin end / adapter contract:

- PG: live test `async_session` или production session-maker seam с корректным
  `read_only=` и test DB;
- CH: live test client/test store;
- Redis: fakeredis или declared boundary adapter может быть достаточен согласно
  testing-rules;
- WB/HTTP: authorized sandbox/live test, transport contract test, recorded
  schema test либо другой project-approved boundary proof;
- Telegram: real library/API shape contract без отправки пользователю, если
  policy не разрешает live.

Он доказывает end contract, но сам по себе не доказывает Spec Scenario.

### `destructive_local`

Тест, помеченный `@pytest.mark.destructive_local`, который может поднимать,
reset-ить или изменять локальную test infrastructure. Это opt-in execution
class, а не синоним Scenario integration и не production destructive action.

### `stub_contract`

Доказательство parity между stub из `scenario_seam` и реальным boundary:

- request shape stub-а совпадает с request shape boundary integration;
- return/success shape совпадает;
- failure/empty/error shapes совпадают, когда Scenario от них зависит;
- async/sync semantics и исключения совпадают;
- identity, field types, enums, optionality и ownership совпадают.

Одного `AsyncMock(return_value=True)` недостаточно, если реальный adapter
возвращает DTO/None/response или бросает иные исключения.

Предпочтительное сильное доказательство:

```text
shared contract fixture / golden schema
  consumed by scenario stub assertions
  AND consumed or produced by boundary integration test
```

Две вручную продублированные структуры без общего contract source —
`PARITY_WEAK`, не полный PASS.

### `load_or_performance_measurement`

Нагрузочные/measurement tests не требуются автоматически для каждого Scenario.
Они обязательны только при explicit spec/performance requirement или
`PERFORMANCE_REVIEW_REPORT`. `/opsx-performance-review` сам по себе является
read-only review, а не нагрузочным прогоном.

## Required evidence matrix

Построй одну строку на каждый `#### Scenario:` во всех delta specs change.
Не пропускай negative, sibling, failure, empty-state, retry, residual,
next-tick и idempotency scenarios.

```text
SCENARIO_EVIDENCE_ROW:
  SCENARIO_ID: <repo-relative spec path>::<exact heading>
  REQUIREMENT_CONTEXT:
  GIVEN_WHEN_THEN:
  PRODUCTION_ENTRYPOINT:
  CAUSAL_PATH:
  THIN_ENDS:
  REQUIRED_TESTS:
    SCENARIO_SEAM:
    BOUNDARY_INTEGRATION_WRITE:
    BOUNDARY_INTEGRATION_READ:
    BOUNDARY_INTEGRATION_OTHER:
    STUB_CONTRACT:
    UNIT_COMPONENT:
    LOAD_OR_PERFORMANCE:
  MAPPED_TEST_IDS:
  EXECUTION:
  ASSERTION_ADEQUACY:
  MOCK_PLACEMENT:
  STUB_PARITY:
  REALITY_CONSTRAINTS:
  GAPS:
  ROW_VERDICT:
```

### Baseline requirements per Scenario

Каждый behavioral Scenario MUST иметь:

1. минимум один `scenario_seam`;
2. реальный production causal path до всех значимых thin ends;
3. assertions на observable THEN, а не только mock call count;
4. paired allowed/forbidden evidence, если Scenario содержит gate;
5. execution evidence на текущем snapshot для полного PASS.

Unit tests могут быть дополнительными, но не заменяют `scenario_seam`.

### Split write/read rule

Если causal path Scenario:

- пишет в PG/CH и затем читает из PG/CH; или
- write и read принадлежат разным callables/session modes; или
- scenario outcome зависит от durable read-after-write,

требуй **два отдельных boundary integration test ids**:

```text
BOUNDARY_INTEGRATION_WRITE
BOUNDARY_INTEGRATION_READ
```

Write test обязан доказать настоящий write adapter/session mode и persisted
state. Read test обязан доказать настоящий query/selection/session mode и
returned production shape. Один test может запускать оба этапа только как
дополнительный flow evidence; он не отменяет отдельную диагностическую
атрибуцию write/read, если boundaries различны.

Для PG:

```text
WRITE                → sm(read_only=False)
PURE_READ            → sm(read_only=True)
READ_AFTER_WRITE     → sm(read_only=False)
```

### Stub parity rule

Для каждого thin end, заменённого stub/mock/fake в `scenario_seam`, требуй:

1. exact stub symbol/fixture path;
2. exact boundary integration test id для реального end;
3. shared contract fixture/schema/golden либо executable parity comparison;
4. request parity;
5. success return parity;
6. relevant failure/empty parity;
7. async and exception parity.

Если реального boundary integration test нет:

```text
STUB_PARITY=UNPROVEN
ROW_VERDICT=FAIL
```

Если оба теста есть, но формы сравниваются только глазами или по похожим
именам:

```text
STUB_PARITY=PARITY_WEAK
ROW_VERDICT=FAIL
```

Если Scenario не использует stub:

```text
STUB_PARITY=NOT_APPLICABLE
```

## Audit procedure

Следуй `.cursor/commands/opsx-source-resolution.md` и
`.cursor/commands/opsx-execution-preflight.md`.

### 1. Resolve exact change artifacts

Используй:

```text
openspec status --change <id> --json
```

Читай exact paths из `artifactPaths`; минимум:

- delta specs;
- design;
- tasks;
- optional decisions, только если нужны для write-path/ownership;
- optional materialized `TEST_COVERAGE_PACKET`.

Не делай unbounded dump `openspec/**`.

### 2. Enumerate all Spec Scenarios

Извлеки каждый exact `#### Scenario:` heading и GIVEN/WHEN/THEN. Сохрани
stable `SCENARIO_ID = <spec-path>::<exact-heading>`.

Сверь:

```text
SCENARIOS_TOTAL
SCENARIOS_AUDITED
SCENARIOS_SKIPPED
```

Полный change PASS требует:

```text
SCENARIOS_SKIPPED=0
```

### 3. Resolve production path

Для каждого Scenario найди:

- runtime entrypoint;
- causal/business boundary;
- guard/candidate/handler path;
- store/external/write/read ends;
- allowed and forbidden sibling paths.

Используй exact hints из design/tasks/packet сначала. Не считай test imports
доказательством runtime reachability.

Если production path нельзя доказать в bounded lookup:

```text
ROW_VERDICT=BLOCKED
GAP=PRODUCTION_PATH_UNRESOLVED
```

### 4. Map tests by evidence, not name

Ищи existing tests сначала по:

- exact symbols/entrypoints;
- requirement/scenario title or durable marker;
- adapter/store symbols;
- fixtures/fakes used by mapped scenario tests.

Для каждого mapped test прочитай body и assertion-defining fixtures.
Похожее имя, docstring или green status сами по себе не являются coverage.

Mapping confidence:

```text
EXACT   = durable scenario marker/id + adequate body
STRONG  = direct production path + assertions uniquely prove Scenario
WEAK    = name/import/mock-call similarity only
NONE
```

`WEAK` и `NONE` не дают PASS.

### 5. Inspect mock placement

FAIL, если:

- causal/business function Scenario полностью patched;
- pipeline stubbed так, что real guard/candidate не достигается;
- test заранее получает результат, который должна вычислить production logic;
- forbidden path проверяется только `assert_not_called()` без доказательства,
  что entity дошла до реального guard/candidate boundary;
- model/DTO fixture shape невозможна в production;
- async test вручную мутирует shared module dependency вокруг `await`.

### 6. Inspect each stub contract

Построй:

```text
STUB_CONTRACT_ROW:
  SCENARIO_ID:
  STUB_SYMBOL:
  SCENARIO_TEST_ID:
  REAL_BOUNDARY_SYMBOL:
  BOUNDARY_INTEGRATION_TEST_ID:
  SHARED_CONTRACT_SOURCE:
  REQUEST_PARITY:
  SUCCESS_RETURN_PARITY:
  FAILURE_EMPTY_PARITY:
  ASYNC_EXCEPTION_PARITY:
  VERDICT:
```

Нельзя использовать signature inspection alone как proof runtime payload.

### 7. Execute targeted evidence

При `run=targeted`:

1. запускай самый узкий mapped test id;
2. scenario tests без destructive marker — обычным targeted pytest;
3. `destructive_local`, live/sandbox/network tests не запускай без их точного
   opt-in/authorization contract;
4. отсутствие authorization → `EXECUTION=BLOCKED_AUTH`, не PASS и не
   «test missing»;
5. разделяй authored/found и executed evidence.

Все project test commands:

```text
poetry run pytest <exact-test-ids> -vv
```

Не запускай unrelated full suite.

### 8. Synthesize strict verdict

Row PASS разрешён только если:

```text
SCENARIO_SEAM_PRESENT=YES
SCENARIO_SEAM_ADEQUATE=YES
PRODUCTION_CAUSAL_PATH_EXECUTED=YES
REQUIRED_BOUNDARY_INTEGRATIONS_PRESENT=YES
ALL_USED_STUBS_HAVE_CONTRACT_PARITY=YES
REQUIRED_TESTS_EXECUTED_AND_GREEN=YES
REALITY_AND_MOCKING_CONSTRAINTS_SATISFIED=YES
```

Full PASS:

```text
SCENARIOS_TOTAL > 0
SCENARIOS_AUDITED = SCENARIOS_TOTAL
SCENARIOS_PASS = SCENARIOS_TOTAL
SCENARIOS_FAIL = 0
SCENARIOS_BLOCKED = 0
STUB_CONTRACTS_FAIL = 0
UNEXECUTED_REQUIRED_TESTS = 0
```

Не ослабляй verdict из-за того, что `/opsx-verify` legacy-compatible.

## Verdicts

Верни ровно один:

```text
STATUS: PASS
VERDICT: SCENARIO_TEST_COVERAGE_PASS
```

```text
STATUS: FAIL
VERDICT: SCENARIO_TEST_COVERAGE_FAIL
```

```text
STATUS: BLOCKED
VERDICT: SCENARIO_TEST_COVERAGE_UNKNOWN
```

Правила:

- `PASS`: каждая строка PASS и всё обязательное evidence executed green;
- `FAIL`: доказан хотя бы один missing/weak/mismatched test или stub contract;
- `BLOCKED`: аудит нельзя завершить из-за environment/auth/unresolved source;
  blocked нельзя представлять как PASS;
- узкий `scenario=` прогон возвращает `PASS_SCOPE=FOCUS_ONLY` и никогда не
  подтверждает полный change PASS.

## Gap routing

```text
MISSING_OR_WEAK_SCENARIO_TEST
MISSING_STUB_CONTRACT_TEST
TEST_ONLY_BOUNDARY_GAP
→ /opsx-test
```

```text
PG_CH_NO_INJECTABLE_SEAM
PG_CH_MISSING_PARENT_SESSION_HANDOFF
PRODUCTION_CAUSAL_PATH_UNTESTABLE
→ /opsx-close-external-gap
```

```text
SPEC_SCENARIO_AMBIGUOUS
WRITE_TARGET_AMBIGUOUS
→ /opsx-update <change-id>
```

Не исправляй gap внутри этой команды.

## Required output

```text
STATUS:
VERDICT:
MODE: READ_ONLY
CHANGE:
SNAPSHOT:
PASS_SCOPE: FULL_CHANGE | FOCUS_ONLY

SCENARIO_SUMMARY:
  SCENARIOS_TOTAL:
  SCENARIOS_AUDITED:
  SCENARIOS_PASS:
  SCENARIOS_FAIL:
  SCENARIOS_BLOCKED:
  SCENARIOS_SKIPPED:

EVIDENCE_SUMMARY:
  SCENARIO_SEAM_TESTS:
  UNIT_COMPONENT_TESTS:
  BOUNDARY_INTEGRATION_WRITE_TESTS:
  BOUNDARY_INTEGRATION_READ_TESTS:
  BOUNDARY_INTEGRATION_OTHER_TESTS:
  DESTRUCTIVE_LOCAL_TESTS:
  STUB_CONTRACTS_TOTAL:
  STUB_CONTRACTS_PASS:
  STUB_CONTRACTS_FAIL:
  REQUIRED_TESTS_EXECUTED:
  UNEXECUTED_REQUIRED_TESTS:

SCENARIO_MATRIX:
- <SCENARIO_EVIDENCE_ROW per exact Scenario>

STUB_CONTRACT_MATRIX:
- <STUB_CONTRACT_ROW per used stub>

TESTS_EXECUTED:
- TEST_ID:
  EVIDENCE_CLASS:
  RESULT:
  SNAPSHOT:

GAPS:
- GAP_ID:
  SCENARIO_ID:
  CLASS:
  EVIDENCE:
  REQUIRED_CLOSURE:
  NEXT_COMMAND:

OVERLAP_NOTES:
- EXTERNAL_CALL_COVERAGE:
- TEST_COVERAGE_PACKET:
- VERIFY:

SOURCE_RESOLUTION:
EXECUTION_PREFLIGHT:
FILES_CHANGED: none
COMMIT_PUSH_PR_ARCHIVE_DEPLOY: not_performed
NEXT_ACTION:
```

При FAIL `NEXT_ACTION` должен быть один основной executable handoff по
наиболее раннему blocking gap; остальные paths перечисли как `ALSO_OK`.

## Safety

- Never edit production, tests, OpenSpec artifacts, commands or policies.
- Never create/update durable report in v1; report is chat output.
- Never stage, commit, push, create PR, archive, deploy or run migrations.
- Never access production credentials, production DB, WB seller account or
  Kubernetes.
- Never run live/destructive tests without their own exact authorization.
- Never infer PASS from test existence, test name, collection or authored-only
  evidence.
- Never call another primary OPSX command from this audit.

## Self-review

- Every exact Spec Scenario has one matrix row.
- Every Scenario has an adequate scenario-seam or an explicit FAIL.
- Every thin-end stub has a boundary integration and executable parity proof.
- Write/read store boundaries have separately attributable integration tests.
- Unit, scenario-seam, boundary integration and destructive execution classes
  are not conflated.
- Required tests are distinguished as found vs executed.
- Focus PASS is not reported as full change PASS.
- No legacy compatibility rule weakened this command's strict verdict.
- Output includes one clear next action without performing fixes.

---
name: /opsx-spec-scenario-coverage
id: opsx-spec-scenario-coverage
category: Workflow
description: "READ_ONLY Spec Scenario coverage: mode=plan|audit|certify (required). Plan required evidence; audit matrix/gaps; certify with provider receipts."
argument-hint: "mode=plan|audit|certify change=<change-id> [run=targeted|none] [scenario=<exact-title>]"
---

# /opsx-spec-scenario-coverage

Проверь **полноту и честность test evidence** для каждого Scenario текущего
OpenSpec change. Lifecycle CLI modes (обязателен ровно один):

```text
mode=plan     → required-evidence matrix (SCENARIO_COVERAGE_PLAN); not PASS
mode=audit    → independent matrix + gaps + route packets
mode=certify  → full-change PASS only with fresh PROVIDER_EXECUTION_RECEIPT(s)
```

Authority: `.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md`.

Команда отвечает на вопросы (в `mode=audit` / `mode=certify`):

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
7. (`mode=certify`) Есть ли свежие provider receipts для обязательных PG/CH ends?

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

### Required tokens

```text
mode=plan | mode=audit | mode=certify
change=<change-id>
```

`mode=` **обязателен**. Нет silent default на `audit`. Missing / unknown /
wrong-place tokens → stop **before** any scenario work (см. Arg gate).

### Optional tokens (mode-scoped)

| Token | Allowed on | Meaning |
|---|---|---|
| `run=targeted` | `audit` only (default when omitted on audit) | Выполнить найденные targeted test ids |
| `run=none` | `audit` (and implicit on `plan`) | Только inspect; execution = `NOT_EXECUTED` → full PASS невозможен |
| `scenario=<exact-title>` | `audit` only | Узкий diagnostic; `PASS_SCOPE=FOCUS_ONLY`; не full-change PASS |

### Modes (CLI)

#### `mode=plan`

```text
INPUT:  apply_ready / planning artifacts (delta specs, design, tasks)
ACTION: build required-evidence matrix; do not claim tests exist or PASS
OUTPUT: SCENARIO_COVERAGE_PLAN (PLAN_STATUS=ready|provisional|blocked)
SUCCESS: PLAN_STATUS=ready (or provisional with explicit OPEN_QUESTIONS)
NEXT:   /opsx-apply   |   /opsx-update <change> if PLANNING_UPDATE / blocked
```

`mode=plan` **never** executes tests. Treat as `run=none`. Do not emit
full-change `SCENARIO_TEST_COVERAGE_REPORT VERDICT=PASS`.

**Product Acceptance / change spirit:** When
`PRODUCT_ACCEPTANCE_REQUIRED=true`, resolve lifecycle as follows (see
`.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md` and
`SCENARIO_TEST_COVERAGE.md`):

1. Prefer durable Derived Lifecycle in `design.md`
   (`LIFECYCLE_STATUS: DERIVED` + per-step SOURCE), verified against
   reviewed `owner-contract.md`.
2. If design lacks an explicit section but lifecycle is unambiguously
   derivable from owner-contract + decisions + specs without inventing
   semantics → treat as DERIVED for planning; note
   `PLANNING_LIFECYCLE_GAP` only when a known Owner transition was omitted
   from planning representation.
3. Build `LIFECYCLE_COVERAGE` (L* ↔ Spec Scenarios). Do **not** invent
   temporal steps from chat. Do **not** require
   `OWNER_LIFECYCLE_ECHO` / `CONFIRM_LIFECYCLE` on this primary path.
4. Missing Spec Scenario for a known L* → plan/gap
   `SPEC_SCENARIO_MISSING` / `SPEC_COVERAGE_GAP` with
   `REPAIR_TARGET: spec` / planning writer (`/opsx-continue` |
   `/opsx-ff` | `/opsx-update`) — **not** `NEEDS_OWNER` /
   `BLOCKED_NEEDS_OWNER_LIFECYCLE`.
5. Genuine unresolved product fork → `STATUS=BLOCKED`,
   `REASON=UNRESOLVED_PRODUCT_SEMANTICS`,
   `NEXT_ACTION=/opsx-owner-contract-review change=<change>`
   (no `CONFIRM_LIFECYCLE` contour).
6. **Legacy only** (no reviewed `owner-contract.md`): if durable
   `OWNER_LIFECYCLE_ECHO` / `CONFIRM_LIFECYCLE` missing →
   `STATUS=BLOCKED`, `REASON=BLOCKED_NEEDS_OWNER_LIFECYCLE`,
   `NEXT_ACTION=/opsx-update <change>` (or `/opsx-ff`).
7. Non-temporal Changes: do not force artificial 3–7 step lifecycle;
   remain usable without ceremony.

This command never writes OpenSpec artifacts.

#### `mode=audit`

```text
INPUT:  change specs + code/tests (+ optional writer packets / receipts as evidence)
ACTION: independent Spec Scenario × evidence matrix; gap dispositions; route packets
OUTPUT: SCENARIO_TEST_COVERAGE_REPORT + GAPS + ROUTE_PACKETS
        (+ INDEPENDENT_REAUDIT READY_FOR_ONE_AUTHORIZED_RUN when applicable)
SUCCESS: not required to proceed; FAIL routes to writers
NEXT:   /opsx-test | /opsx-close-external-gap | /opsx-update | re-audit
```

When `PRODUCT_ACCEPTANCE_REQUIRED=true`, each acceptance-relevant matrix row
MUST cite the matching Derived Lifecycle step (prefer design.md). Unmapped
rows → FAIL/BLOCKED for that scenario (cannot support PA LIFECYCLE PASS).
If Derived Lifecycle is missing and cannot be derived without invention →
`PLANNING_LIFECYCLE_GAP` or `UNRESOLVED_PRODUCT_SEMANTICS` (NEXT: planning
writer or `/opsx-owner-contract-review`). Do **not** emit
`BLOCKED_NEEDS_OWNER_LIFECYCLE` when a reviewed Owner Contract exists and
lifecycle is DERIVED / derivable. Legacy path (no owner-contract): missing
echo → `BLOCKED_NEEDS_OWNER_LIFECYCLE` (NEXT: `/opsx-update`).
Spec inventing unsupported behavior → `SEMANTIC_DRIFT` (not PASS).

#### `mode=certify`

```text
INPUT:  current worktree hashes + fresh PROVIDER_EXECUTION_RECEIPT(s) for required PG/CH
ACTION: full-change re-check; receipts must be present, PASS, and hash-fresh
OUTPUT: SCENARIO_TEST_COVERAGE_REPORT (PASS only if all rows + receipts OK)
SUCCESS: VERDICT=PASS, PASS_SCOPE=FULL_CHANGE
NEXT:   /opsx-verify mode=archive <change>   | recovery on FAIL/BLOCKED
```

`mode=certify` is **full-change only**. Missing/stale receipts →
`BLOCKED_NEEDS_PROVIDER_RECEIPT` (not PASS). Same PA echo-mapping rules as
`mode=audit` apply when `PRODUCT_ACCEPTANCE_REQUIRED=true`.

### Arg gate (fail-closed — run first)

Allowed tokens only: `mode=`, `change=`, `run=`, `scenario=`.

Stop immediately (no matrix work) when:

| Condition | STATUS | REASON | NEXT_ACTION |
|---|---|---|---|
| `mode=` absent | `BLOCKED` | `MODE_REQUIRED` | `/opsx-spec-scenario-coverage mode=plan\|audit\|certify change=<id>` |
| `mode=` not in `{plan,audit,certify}` | `BLOCKED` | `UNKNOWN_MODE` | same; list allowed modes |
| `change=` absent or change not found | `BLOCKED` | `CHANGE_REQUIRED_OR_NOT_FOUND` | `/opsx-spec-scenario-coverage mode=<mode> change=<change-id>` |
| unknown token present | `BLOCKED` | `UNKNOWN_ARG` | list allowed tokens; drop unknown |
| `base=` present | `BLOCKED` | `WRONG_COMMAND` | `/opsx-external-call-coverage base=<BASE>` |
| `AUTHORIZE_ONE_LIVE_RUN` (or live-auth synonym) | `BLOCKED` | `WRONG_COMMAND` | `/opsx-close-external-gap` + packet |
| `GO` / `AUTHORIZE_COMMAND_FIX` / writer apply tokens | `BLOCKED` | `WRONG_COMMAND` | this command is READ_ONLY auditor |
| `mode=plan` + `scenario=` | `BLOCKED` | `INVALID_ARG_COMBO` | drop `scenario=` or use `mode=audit` |
| `mode=certify` + `scenario=` | `BLOCKED` | `INVALID_ARG_COMBO` | certify is full-change only |
| `mode=plan` + `run=targeted` | `BLOCKED` | `INVALID_ARG_COMBO` | plan never executes tests |
| `mode=certify` + `run=none` implying skip receipt proof | `BLOCKED` | `INVALID_ARG_COMBO` | certify requires executed evidence + receipts |
| `mode=certify` without usable fresh receipt(s) when PG/CH required | `BLOCKED` | `NEEDS_PROVIDER_RECEIPT` | `/opsx-close-external-gap` certify/live path |

Не выдумывай change id и не выбирай похожий change молча.
Не подставляй `mode=audit`, если `mode=` не указан.

## Authority and relationship

Эта команда — отдельный строгий matrix-auditor / planner / certifier
(по `mode=`).

Она:

- читает Spec Scenarios как source of required observable behavior;
- может читать additive `TEST_COVERAGE_PACKET` из `/opsx-invariant`;
- дополняет `/opsx-external-call-coverage`, но не заменяет его diff inventory;
- не пишет тесты (`/opsx-test`);
- не создаёт production seams (`/opsx-apply` или
  `/opsx-close-external-gap` по соответствующему packet);
- не выдаёт archive `GO` (`/opsx-verify`);
- не запускает live production, WB writes, migrations или destructive tests
  без их собственного authorization contract;
- в `mode=plan` не утверждает существование tests и не выдаёт coverage PASS;
- в `mode=certify` не выдаёт PASS без свежих `PROVIDER_EXECUTION_RECEIPT`.

Пересечение с другими coverage-командами допустимо: эта команда владеет
только verdict по матрице **Spec Scenario × test evidence** (и plan/certify
фазами того же контракта).

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
next-tick, idempotency и (когда применимо) steady-state / already-true
reconcile scenarios.

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

### Steady-state / already-true reconcile (mandatory when applicable)

Authority:
`.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md` →
**Steady-state / already-true reconcile (mandatory)**.

When Spec, design, or an accepted decision implies an invariant that must hold
on observe / reconcile / deploy (not only after a producer event):

1. The change MUST include at least one Spec Scenario with
   `GIVEN` already-true precondition (no fresh producer event),
   `WHEN` periodic / ensure / reconcile entrypoint,
   `THEN` the same allowed effect as the post-event transition path
   (+ forbidden sibling if gated).
2. Encoding **only** post-event transition producers for that invariant is
   FAIL_CLOSED:
   - `mode=plan` → `OPEN_QUESTIONS` (or provisional/blocked plan) naming the gap;
   - `mode=audit` / `mode=certify` → gap class
     `MISSING_STEADY_STATE_RECONCILE_SCENARIO` → FAIL (not PASS).
3. Do not treat transition-producer Scenario alone as covering deploy-safe /
   already-true reconcile.

Non-normative class note: ROOT-001 empty-keywords — empty keywords + Search
STARTED + bot on must arm Search EMPTY_KEYWORDS pause without prior V3 intent.

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

Только `mode=audit`. `mode=plan` never executes. `mode=certify` may re-run
required evidence only when receipts/hashes demand execution proof — never as
a substitute for missing `PROVIDER_EXECUTION_RECEIPT`.

При `run=targeted` (audit):

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
MISSING_STEADY_STATE_RECONCILE_SCENARIO   # Spec omits already-true / reconcile Scenario
SPEC_SCENARIO_MISSING / SPEC_COVERAGE_GAP # Lifecycle known; Spec Scenario absent
PLANNING_LIFECYCLE_GAP                   # Owner semantics known; design omitted L*
SEMANTIC_DRIFT                           # Spec invents unsupported behavior
→ /opsx-update <change-id>   |   /opsx-continue | /opsx-ff (planning writer)
```

```text
UNRESOLVED_PRODUCT_SEMANTICS             # Owner Contract leaves material fork open
→ /opsx-owner-contract-review change=<change-id>
  (NOT CONFIRM_LIFECYCLE; NOT NEEDS_OWNER via scenario-coverage inventing meaning)
```

```text
MISSING_STEADY_STATE_RECONCILE_SCENARIO   # Spec has Scenario; evidence missing/weak
→ /opsx-test
```

Не исправляй gap внутри этой команды.

### FAIL → pasteable ROUTE_PACKETS (mandatory)

На `STATUS: FAIL` в `mode=audit` (и на `mode=certify` FAIL с TEST_ONLY gaps)
прозаический `GAPS:` + `NEXT_ACTION: /opsx-test` **недостаточны**.

Если есть хотя бы один gap с disposition `TEST_ONLY`
(`MISSING_OR_WEAK_SCENARIO_TEST`, `MISSING_STUB_CONTRACT_TEST`,
`TEST_ONLY_BOUNDARY_GAP`):

1. Required output MUST включать блок `ROUTE_PACKETS:` с полным fenced
   `SCENARIO_TEST_ONLY_PACKET` (schema из
   `.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md`).
2. Packet MUST содержать: `SCHEMA_VERSION: 1`, `SOURCE`, `CHANGE_ID`,
   `SOURCE_SPEC_SHA`, `WORKTREE_FINGERPRINT`, непустые `ITEMS`.
3. Для **каждого** stubbed thin end, который блокирует FAIL-row (не только
   первого gap), item MUST заполнять `REQUIRED_ARTIFACTS`:
   `CONTRACT_CASES`, `FAKE_OR_STUB`, `SCENARIO_SEAM_TEST`,
   `STUB_CONTRACT_TEST`, `BOUNDARY_ADAPTER_TEST` (что применимо).
4. `NEXT_ACTION` = `/opsx-test` **и** Owner должен иметь возможность
   вставить весь packet в args следующего `/opsx-test` без реконструкции
   из матрицы.
5. FAIL без такого pasteable TEST_ONLY packet при наличии TEST_ONLY gaps =
   **невалидный handoff** (self-review FAIL); исправь output до возврата.

PG/CH `REFACTOR_AND_TEST` / `CERTIFY` gaps → соответствующие packets в
`ROUTE_PACKETS` (не смешивать в TEST_ONLY).

## Required output

Для `mode=plan` достаточно plan-shaped output:

```text
STATUS: ORIENTED | BLOCKED | GAP
VERDICT: not_applicable
MODE: READ_ONLY
SCENARIO_MODE: plan
CHANGE:
LIFECYCLE_STATUS: DERIVED | UNRESOLVED | LEGACY_ECHO | NOT_APPLICABLE
LIFECYCLE_COVERAGE: ...   # L* ↔ Spec Scenario mapping (or gaps)
SCENARIO_COVERAGE_PLAN: ...
NEXT_ACTION:
```

Для `mode=audit` / `mode=certify`:

```text
STATUS:
VERDICT:
MODE: READ_ONLY
SCENARIO_MODE: audit | certify
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

ROUTE_PACKETS:
  TEST_ONLY_PACKET: <fenced SCENARIO_TEST_ONLY_PACKET | none>
  REFACTOR_AND_TEST_PACKET: <fenced packet | none>
  CERTIFY_PACKET: <fenced packet | none>

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

При FAIL / BLOCKED после успешного arg gate `NEXT_ACTION` должен быть один
основной executable handoff по наиболее раннему blocking gap; остальные paths
перечисли как `ALSO_OK`. Arg-gate BLOCKED → единственный NEXT = исправить
аргументы (или wrong-command target).

На FAIL с TEST_ONLY gaps: `ROUTE_PACKETS.TEST_ONLY_PACKET` MUST быть полным
fenced packet (см. «FAIL → pasteable ROUTE_PACKETS»), не `none` и не «см. GAPS».

## Safety

- Never edit production, tests, OpenSpec artifacts, commands or policies.
- Never create/update durable report in v1; report is chat output.
- Never invent or author Derived Lifecycle / `OWNER_LIFECYCLE_ECHO` here —
  planning writers only (`/opsx-continue` / `/opsx-ff` / `/opsx-update`).
- Never treat scenario `VERDICT=PASS` as clearing Product Acceptance without
  durable Derived Lifecycle (or legacy confirmed echo); verify owns PA DONE.
- Never stage, commit, push, create PR, archive, deploy or run migrations.
- Never access production credentials, production DB, WB seller account or
  Kubernetes.
- Never run live/destructive tests without their own exact authorization.
- Never infer PASS from test existence, test name, collection or authored-only
  evidence.
- Never call another primary OPSX command from this audit.
- Never proceed past Arg gate with missing/unknown/wrong `mode=` or foreign tokens.
- Never emit `mode=plan` coverage PASS or `mode=certify` PASS without fresh
  provider receipts when PG/CH evidence is required.
- Never emit `BLOCKED_NEEDS_OWNER_LIFECYCLE` for Changes with reviewed
  Owner Contract when Derived Lifecycle is present or unambiguously
  derivable; never require `CONFIRM_LIFECYCLE` on that primary path.
- Never emit ready/provisional `mode=plan` under PA when Derived Lifecycle
  (primary) or legacy echo (legacy-only) is missing/UNRESOLVED and temporal
  behavior applies — use the correct failure class
  (`PLANNING_LIFECYCLE_GAP` / `UNRESOLVED_PRODUCT_SEMANTICS` /
  `BLOCKED_NEEDS_OWNER_LIFECYCLE` legacy).

## Self-review

- `mode=` and `change=` parsed; Arg gate ran before scenario work.
- `SCENARIO_MODE` in output matches requested `mode=`.
- `mode=plan` produced `SCENARIO_COVERAGE_PLAN` / `LIFECYCLE_COVERAGE`, not certified PASS.
- Under PA primary path, `mode=plan` uses Derived Lifecycle; does not demand
  `OWNER_LIFECYCLE_ECHO` / `CONFIRM_LIFECYCLE` when reviewed Owner Contract exists.
- Under PA, audit/certify rows mapped to Derived Lifecycle steps (or FAIL/BLOCKED).
- `mode=certify` checked receipt freshness before PASS.
- Every exact Spec Scenario has one matrix row (`audit`/`certify`).
- Every Scenario has an adequate scenario-seam or an explicit FAIL.
- Every thin-end stub has a boundary integration and executable parity proof.
- Write/read store boundaries have separately attributable integration tests.
- Unit, scenario-seam, boundary integration and destructive execution classes
  are not conflated.
- Required tests are distinguished as found vs executed.
- Focus PASS is not reported as full change PASS.
- No legacy compatibility rule weakened this command's strict verdict.
- Output includes one clear next action without performing fixes.
- FAIL with TEST_ONLY gaps includes pasteable `ROUTE_PACKETS.TEST_ONLY_PACKET`
  covering every blocking stub thin end (not prose-only GAPS).
- When reconcile-on-observe applies: steady-state / already-true Scenario is
  present, or explicit `MISSING_STEADY_STATE_RECONCILE_SCENARIO` FAIL / plan
  `OPEN_QUESTIONS` (not silent PASS on transition-only Scenario sets).

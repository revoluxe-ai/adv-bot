# Scenario Test Coverage Lifecycle

Producer/consumer contract для полного test-evidence lifecycle OpenSpec
Scenarios.

```text
CONTRACT_ID=OPSX_SCENARIO_TEST_COVERAGE_V1
TAXONOMY=.cursor/pipeline/contracts/TEST_EVIDENCE_TAXONOMY.md
```

## Goal

Связать без скрытой истории:

```text
Spec Scenario
→ coverage plan
→ test/refactor packets
→ authored evidence
→ authorized provider execution receipt
→ independent scenario coverage report
→ archive verify
```

Этот contract не даёт writer-команде право выдавать независимый coverage или
archive verdict.

## Authority

```text
/opsx-spec-scenario-coverage
  owns: plan, matrix, gap disposition, independent coverage verdict
  CLI: mode=plan | mode=audit | mode=certify  (required; no silent default)

/opsx-test
  owns: ContractCase, test fixtures/goldens, fake/stub, scenario tests
  boundary: tests/** only

/opsx-close-external-gap
  owns: PG/CH production seam, real provider integration, live authorization,
        PROVIDER_EXECUTION_RECEIPT
  does_not_own: final Scenario coverage PASS

/opsx-verify
  owns: archive GO/NO_GO

Owner
  owns: material behavior ambiguity, intentional golden/ContractCase semantic
        change, one-shot live authorization
```

## CLI modes (binding)

Command surface for `/opsx-spec-scenario-coverage` MUST require:

```text
mode=plan | mode=audit | mode=certify
change=<change-id>
```

| mode | Produces | Must not |
|---|---|---|
| `plan` | `SCENARIO_COVERAGE_PLAN` | claim tests exist; emit coverage PASS; execute tests |
| `audit` | `SCENARIO_TEST_COVERAGE_REPORT` + gaps/packets (+ optional `INDEPENDENT_REAUDIT`) | silent-default when `mode=` missing; full PASS via `scenario=` focus |
| `certify` | full-change report; PASS only with fresh `PROVIDER_EXECUTION_RECEIPT` when PG/CH required | PASS without receipts; accept `scenario=` focus as full certify |

Fail-closed arg rules (missing `mode=`, unknown `mode=`, foreign tokens such as
`base=` / `AUTHORIZE_ONE_LIVE_RUN` / writer `GO`, invalid combos) are owned by
the command file Arg gate. Contract consumers and handoffs MUST pass explicit
`mode=`; do not imply default `audit`.

Recommended handoffs:

```text
/opsx-spec-scenario-coverage mode=plan change=<id>
/opsx-spec-scenario-coverage mode=audit change=<id>
/opsx-spec-scenario-coverage mode=certify change=<id>
```

## Lifecycle states

```text
coverage_unplanned
coverage_plan_ready
coverage_gaps
coverage_tests_authored
coverage_provider_ready
coverage_live_blocked
coverage_receipt_ready
coverage_certified
```

Recommended transition:

```text
planning artifacts ready
→ scenario coverage plan
→ apply
→ scenario coverage audit
→ test-only and/or refactor writers
→ independent re-audit
→ authorized live provider execution when required
→ scenario coverage certification
→ verify
```

## Stable identity

```text
SCENARIO_ID=<repo-relative-delta-spec-path>::<exact Scenario heading>
GAP_ID=<change-id>::<scenario-id-hash>::<ordinal>
GAP_FILE_ID=<first-16-hex of sha256(GAP_ID)>
CONTRACT_ID=<stable boundary + case-set identity>
```

Не переименовывай Scenario только ради test mapping. Изменение exact Scenario
heading инвалидирует прежнюю привязку и требует нового plan/audit.
`GAP_ID` хранится только как data; для Windows-safe filenames используй только
`GAP_FILE_ID` (`[0-9a-f]{16}`), без `:`, `/`, `\` или Scenario title.

## Steady-state / already-true reconcile (mandatory)

When Spec, design, or an accepted decision implies an invariant that must hold
on **observe / reconcile / deploy** (not only after a producer event), the
change MUST include at least one Spec Scenario shaped as:

```text
GIVEN already-true precondition state (no fresh producer event required)
WHEN periodic / ensure / reconcile entrypoint runs
THEN the same allowed effect as the post-event transition path
     (+ paired forbidden sibling if the Scenario is a gate)
```

Encoding **only** post-event transition producers for that invariant is
**FAIL_CLOSED**:

| Where | Required outcome |
|---|---|
| `mode=plan` | `OPEN_QUESTIONS` (or `PLAN_STATUS=provisional\|blocked`) naming the missing steady-state Scenario |
| `mode=audit` / `mode=certify` | gap class `MISSING_STEADY_STATE_RECONCILE_SCENARIO` → row/report FAIL |

Disposition:

```text
Spec omits the steady-state Scenario
→ PLANNING_UPDATE → /opsx-update

Spec has the Scenario but evidence is missing/weak
→ TEST_ONLY → /opsx-test
```

Non-normative class note (do not treat as product requirement text here):
ROOT-001 / empty-keywords — empty active keywords + Search STARTED + bot on
must arm Search EMPTY_KEYWORDS pause without a prior V3 intent (activity-control
reconcile), not only after a FORCE_OFF → intent producer hop.

## Common freshness envelope

Каждый packet/report/receipt MUST содержать применимые поля:

```text
SCHEMA_VERSION: 1
CHANGE_ID:
GAP_ID:
GAP_FILE_ID:
SOURCE_SPEC_SHA:
WORKTREE_FINGERPRINT:
CONTRACT_ID:
CONTRACT_SHA:
TEST_CONTENT_SHA:
PRODUCTION_BOUNDARY_SHA:
FAKE_SHA:
SCHEMA_SHA:
CREATED_AT:
PRODUCER_COMMAND:
```

Неприменимое поле записывай `not_applicable`, а неизвестное —
`unknown` с причиной. Не подставляй пустую строку.

Изменение обязательного hash делает downstream evidence `STALE`.

## SCENARIO_COVERAGE_PLAN

Plan описывает required evidence, но не утверждает, что оно существует.

```text
SCENARIO_COVERAGE_PLAN:
  SCHEMA_VERSION: 1
  CHANGE_ID:
  SOURCE_SPEC_SHA:
  PLAN_STATUS: ready | provisional | blocked
  SCENARIOS:
    - SCENARIO_ID:
      GIVEN_WHEN_THEN:
      PRODUCTION_ENTRYPOINT:
      CAUSAL_PATH:
      THIN_ENDS:
      REQUIRED_EVIDENCE:
        SCENARIO_SEAM:
        CONTRACT_CASES:
        STUB_CONTRACT:
        BOUNDARY_INTEGRATION_WRITE:
        BOUNDARY_INTEGRATION_READ:
        BOUNDARY_INTEGRATION_OTHER:
        LOAD_OR_PERFORMANCE:
      REALITY_CONSTRAINTS:
      MOCKING_CONSTRAINTS:
  OPEN_QUESTIONS:
```

Material behavior ambiguity → `/opsx-update`, не догадка planner-а.

## Gap dispositions

```text
TEST_ONLY
  tests/** достаточно; production seam уже пригоден

REFACTOR_AND_TEST
  требуется PG/CH production seam/session-client handoff + integration

CERTIFY
  code/tests authored; не хватает свежего authorized provider execution

PLANNING_UPDATE
  Spec/target/behavior неоднозначны
  (includes MISSING_STEADY_STATE_RECONCILE_SCENARIO when Spec omits
   already-true / reconcile Scenario for a reconcile-on-observe invariant)
```

## SCENARIO_TEST_ONLY_PACKET

Consumer: `/opsx-test`.

```text
SCENARIO_TEST_ONLY_PACKET:
  SCHEMA_VERSION: 1
  SOURCE: SCENARIO_TEST_COVERAGE_REPORT
  CHANGE_ID:
  SOURCE_SPEC_SHA:
  WORKTREE_FINGERPRINT:
  ITEMS:
    - GAP_ID:
      GAP_FILE_ID:
      SCENARIO_ID:
      DISPOSITION: TEST_ONLY
      REQUIRED_ARTIFACTS:
        CONTRACT_CASES:
        FAKE_OR_STUB:
        SCENARIO_SEAM_TEST:
        STUB_CONTRACT_TEST:
        BOUNDARY_ADAPTER_TEST:
      PRODUCTION_ENTRYPOINT:
      REAL_BOUNDARY_SYMBOLS:
      REALITY_CONSTRAINTS:
      MOCKING_CONSTRAINTS:
```

Writer MUST вернуть per-item test ids и hashes. Он не выдаёт independent
coverage PASS.

## SCENARIO_REFACTOR_AND_TEST_PACKET

Consumer: `/opsx-close-external-gap`; только PG/CH и доказанный
`UNTESTABLE_SEAM`.

```text
SCENARIO_REFACTOR_AND_TEST_PACKET:
  SCHEMA_VERSION: 1
  SOURCE: SCENARIO_TEST_COVERAGE_REPORT
  CHANGE_ID:
  SOURCE_SPEC_SHA:
  WORKTREE_FINGERPRINT:
  ITEMS:
    - GAP_ID:
      GAP_FILE_ID:
      SCENARIO_ID:
      DISPOSITION: REFACTOR_AND_TEST
      KIND: PG | CH
      PRODUCTION_BOUNDARY:
      REQUIRED_SEAM:
      CONTRACT_ID:
      CONTRACT_SHA:
      CONTRACT_CASES_PATH:
      REQUIRED_PROVIDER_TESTS:
        WRITE:
        READ:
        READ_AFTER_WRITE:
      SESSION_MODE_INTENT:
```

Close writer MUST NOT менять reviewed ContractCase semantic expectation.
Mismatch → `BLOCKED_CONTRACT_MISMATCH` или Owner semantic decision.

## SCENARIO_CERTIFY_PACKET

Consumer: `/opsx-close-external-gap`; v1 только PG/CH live/destructive
provider execution.

```text
SCENARIO_CERTIFY_PACKET:
  SCHEMA_VERSION: 1
  SOURCE: SCENARIO_TEST_COVERAGE_REPORT
  CHANGE_ID:
  WORKTREE_FINGERPRINT:
  ITEMS:
    - GAP_ID:
      GAP_FILE_ID:
      SCENARIO_ID:
      DISPOSITION: CERTIFY
      KIND: PG | CH
      CONTRACT_ID:
      CONTRACT_SHA:
      PROVIDER_TEST_IDS:
      TEST_CONTENT_SHA:
      PRODUCTION_BOUNDARY_SHA:
      SCHEMA_SHA:
      REQUIRED_EXECUTION_CLASS: destructive_local | authorized_live
```

`AUTHORIZE_ONE_LIVE_RUN` остаётся one-shot и принимается только по собственному
contract `/opsx-close-external-gap`.

## Independent provider re-audit

До live authorization независимый
`/opsx-spec-scenario-coverage mode=audit change=<CHANGE_ID>`
должен проверить authored provider tests и current audited state:

```text
INDEPENDENT_REAUDIT:
  SCHEMA_VERSION: 1
  SOURCE_COMMAND: /opsx-spec-scenario-coverage
  VERDICT: READY_FOR_ONE_AUTHORIZED_RUN
  CHANGE_ID:
  GAP_IDS:
  GAP_FILE_IDS:
  CONTRACT_IDS:
  CONTRACT_SHAS:
  PROVIDER_TEST_IDS:
  TEST_CONTENT_SHAS:
  PRODUCTION_BOUNDARY_SHAS:
  SCHEMA_SHAS:
  AUDITED_HEAD:
  AUDITED_STATUS_SHA256:
  AUDITED_TRACKED_DIFF_SHA256:
  AUDITED_UNTRACKED_MANIFEST_SHA256:
  ALLOWED_RUN_BLOCK_SHA256:
  CREATED_AT:
```

Любое изменение audited state после re-audit инвалидирует live readiness.
Writer `/opsx-close-external-gap` MUST NOT выпускать этот verdict сам.

## PROVIDER_EXECUTION_RECEIPT

Producer: `/opsx-close-external-gap` после фактического разрешённого запуска.

Recommended durable path:

```text
.tmp/opsx-scenario-coverage/<CHANGE_ID>/receipts/PROVIDER-<GAP_FILE_ID>.md
```

Schema:

```text
PROVIDER_EXECUTION_RECEIPT:
  SCHEMA_VERSION: 1
  CHANGE_ID:
  GAP_ID:
  GAP_FILE_ID:
  SCENARIO_ID:
  KIND: PG | CH
  CONTRACT_ID:
  CONTRACT_SHA:
  PROVIDER_TEST_IDS:
  TEST_CONTENT_SHA:
  PRODUCTION_BOUNDARY_SHA:
  SCHEMA_SHA:
  WORKTREE_FINGERPRINT:
  EXECUTED_AT:
  EXECUTION_CLASS:
  RESULT: PASS | FAIL | ERROR | BLOCKED
  TESTS_PASSED:
  TESTS_FAILED:
  AUTHORIZATION_STATUS: consumed | not_required
  LOG_PATH:
  LOG_SHA:
  SECRETS_REDACTED: YES
```

Receipt:

- не содержит DSN, credentials или raw production/customer data;
- не является Scenario coverage PASS;
- stale при несовпадении обязательного hash;
- не создаётся для неисполненного/collected-only теста.

## SCENARIO_TEST_COVERAGE_REPORT

Producer: независимый `/opsx-spec-scenario-coverage`.

```text
SCENARIO_TEST_COVERAGE_REPORT:
  SCHEMA_VERSION: 1
  CHANGE_ID:
  SOURCE_SPEC_SHA:
  WORKTREE_FINGERPRINT:
  ACTIVATION:
    SCENARIO_COVERAGE_REQUIRED: true | false
    ACTIVATION_VERSION:
  VERDICT: PASS | FAIL | BLOCKED
  SCENARIOS_TOTAL:
  SCENARIOS_PASS:
  SCENARIOS_FAIL:
  SCENARIOS_BLOCKED:
  ROWS:
    - SCENARIO_ID:
      GAP_IDS:
      GAP_FILE_IDS:
      REQUIRED_TEST_IDS:
      EXECUTED_TEST_IDS:
      STUB_CONTRACT_STATUS:
      PROVIDER_RECEIPTS:
      FRESHNESS:
      ROW_VERDICT:
      GAPS:
  ROUTE_PACKETS:
    TEST_ONLY_PACKET:   # full SCENARIO_TEST_ONLY_PACKET when any TEST_ONLY gap
    REFACTOR_AND_TEST_PACKET:
    CERTIFY_PACKET:
```

На `VERDICT=FAIL` с ≥1 gap disposition `TEST_ONLY`:
`ROUTE_PACKETS.TEST_ONLY_PACKET` MUST быть полным pasteable
`SCENARIO_TEST_ONLY_PACKET` (не пустой stub, не «см. GAPS»). Каждый blocking
stub thin end → отдельный `ITEMS[]` (или явные `REQUIRED_ARTIFACTS` на item)
с `CONTRACT_CASES` / `FAKE_OR_STUB` / `STUB_CONTRACT_TEST` /
`BOUNDARY_ADAPTER_TEST` где применимо. FAIL без такого packet = неполный
report (невалидный writer handoff).

Full PASS требует:

```text
all Spec Scenarios audited
all required scenario tests executed green
all used stubs have executable contract parity
all required provider receipts present, PASS and fresh
no weak/missing/blocked row
no MISSING_STEADY_STATE_RECONCILE_SCENARIO when reconcile-on-observe applies
```

## Verify activation

Legacy compatibility:

```text
SCENARIO_COVERAGE_REQUIRED absent|false
→ report absence is not automatic archive NO_GO
```

Versioned/opt-in:

```text
SCENARIO_COVERAGE_REQUIRED=true
→ fresh SCENARIO_TEST_COVERAGE_REPORT VERDICT=PASS required
→ missing/stale/FAIL/BLOCKED is archive blocker
```

Verify MUST NOT recompute the whole scenario matrix. It validates report
identity/freshness and spot-checks acceptance-relevant evidence.

## Anti-loop rules

- Auditor never writes tests/production.
- Writer never self-issues independent coverage PASS.
- Provider live output never auto-updates ContractCase/golden.
- Re-audit uses current hashes, not chat memory.
- FAIL packet routes to exactly one owning writer per item.
- Receipt is provider evidence, not final certification.
- FAIL with TEST_ONLY gaps without pasteable `SCENARIO_TEST_ONLY_PACKET` in
  `ROUTE_PACKETS` is an incomplete auditor handoff — do not send Owner to
  free-form `/opsx-test` with prose gaps alone.
- Writer closing a TEST_ONLY batch MUST inventory stub thin ends used by failing
  seams; partial closure (e.g. WB ContractCase only while notify stub remains)
  without explicit `REMAINING_GAPS` is forbidden.

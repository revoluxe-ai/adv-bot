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
CONTRACT_ID=<stable boundary + case-set identity>
```

Не переименовывай Scenario только ради test mapping. Изменение exact Scenario
heading инвалидирует прежнюю привязку и требует нового plan/audit.

## Common freshness envelope

Каждый packet/report/receipt MUST содержать применимые поля:

```text
SCHEMA_VERSION: 1
CHANGE_ID:
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

## PROVIDER_EXECUTION_RECEIPT

Producer: `/opsx-close-external-gap` после фактического разрешённого запуска.

Recommended durable path:

```text
.tmp/opsx-scenario-coverage/<CHANGE_ID>/receipts/PROVIDER-<GAP_ID>.md
```

Schema:

```text
PROVIDER_EXECUTION_RECEIPT:
  SCHEMA_VERSION: 1
  CHANGE_ID:
  GAP_ID:
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
      REQUIRED_TEST_IDS:
      EXECUTED_TEST_IDS:
      STUB_CONTRACT_STATUS:
      PROVIDER_RECEIPTS:
      FRESHNESS:
      ROW_VERDICT:
      GAPS:
  ROUTE_PACKETS:
    TEST_ONLY_PACKET:
    REFACTOR_AND_TEST_PACKET:
    CERTIFY_PACKET:
```

Full PASS требует:

```text
all Spec Scenarios audited
all required scenario tests executed green
all used stubs have executable contract parity
all required provider receipts present, PASS and fresh
no weak/missing/blocked row
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

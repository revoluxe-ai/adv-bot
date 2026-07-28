# Corrective V8 Report — Invariant-Centered Bug Family Fanout

```text
STATUS: OPSX_BUG_TEAM_CORRECTIVE_V8_IMPLEMENTED
COMMAND: /opsx-bug-team
CURRENT_ACTIVE_IMPLEMENTATION: ACTIVE_V1
V8_IMPLEMENTATION: SHADOW_CANDIDATE
BUG_FAMILY_FANOUT_ENABLED: false
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED (V8 modules)
REAL_BUG_EXECUTION_IN_BUILDER: FORBIDDEN
COMMIT_ALLOWED: NO
```

Evidence:

```text
.tmp/opsx-bug-team-harness/corrective-v8/<RUN_ID>/
```

## Control defect addressed

ACTIVE_V1 fixes root, runs bounded hunt, records siblings (e.g. PBH-007/008),
but siblings only block closure — user must manually re-invoke `/opsx-bug-team`.
V8 shadow adds automatic same-invariant fanout lifecycle without replacing ACTIVE_V1.

## Bug family model

Artifacts under `family/`:

```text
INVARIANT.md, FAMILY.json, BRANCHES.jsonl, DEPENDENCIES.json,
INTEGRATION.json, LEARNING_PACKET.json
```

Branch workspaces: `branches/<FINDING_ID>/{PATCH.diff,CHANGED_PATHS.json,GREEN_REPORT.md,BRANCH_SUMMARY.md}`

## Policy (command-native)

```text
.cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json
```

Defines hunt results, relation types, blocking rules, branch transitions,
family closure, learning, integration, write-set rules. Worker specs reference
this file instead of duplicating rules.

## Runtime modules (shadow)

| Module | Role |
|--------|------|
| `runtime/family_policy.py` | feature gate; CONTROLLED_TEST_FAMILY_FANOUT |
| `runtime/bug_family.py` | durable family/branch model + write-set conflicts |
| `runtime/family_fanout.py` | invariant, hunt, relation, patches, integrate, green, fan-in, learning, resume |

## Lifecycle (when enabled / controlled test)

```text
ROOT GREEN → INVARIANT CAPTURE → HUNT → MATERIALIZE+RELATION
→ SAME_INVARIANT branches (RED→FIX→GREEN in isolated workspaces)
→ INTEGRATION → FAMILY GREEN → FAMILY FAN-IN → LEARNING → CLOSURE
```

## PBH-006 resume path

```text
/opsx-bug-team case=BUGCASE-PBH-006 mode=resume-family-fanout
```

Implemented as `resume_family_fanout_from_root_green` (harness-tested).
Builder did **not** resume the real case or fix PBH-007/008.

## Shadow activation

```text
BUG_FAMILY_FANOUT_ENABLED: false
CONTROLLED_TEST_MODE: CONTROLLED_TEST_FAMILY_FANOUT
ACTIVE_DEFAULT_CHANGED: NO
```

## V8 tests

```text
command: python .cursor/pipeline/bug-team/harness/run_corrective_v8_tests.py
total: 28
passed: 28
failed: 0
```

Includes V8-FAMILY-01..16, INV-FAMILY-001..010, shadow + policy contracts.

## Regressions

| Suite | Result |
|-------|--------|
| V7 | 26/26 PASS |
| V6 | 31/31 PASS |
| V5 | 39/39 PASS |
| V4 | 29/29 PASS |
| V3 | 34/34 PASS |
| V2 | 18/18 PASS |

Note: CT-01 / V3-REG-NOT-ACTIVE adapted to accept ACTIVE_V1 (Owner already
activated CONTROLLED_LIVE_UNCOMMITTED). NOT_ACTIVE path still asserted when
inactive. V8 fanout remains shadow-disabled.

## Product isolation

```text
PRODUCT_FILES_CHANGED: NONE
REAL_BUG_CASES_CHANGED: NONE
RUNTIME_ACTIVATED_FOR_V8: NO
COMMIT_CREATED: NO
```

## ONE_NEXT_ACTION

```text
Independent Invariant-Fanout Controlled Test
```

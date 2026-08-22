# Corrective V9 Report — Invariant Proof, Family Fan-in, Learning, Parallelism

```text
STATUS: OPSX_BUG_TEAM_CORRECTIVE_V9_IMPLEMENTED
COMMAND: /opsx-bug-team
CURRENT_ACTIVE_IMPLEMENTATION: ACTIVE_V1
V8_V9_IMPLEMENTATION: SHADOW_CANDIDATE
BUG_FAMILY_FANOUT_ENABLED: false
CONTROLLING_VERDICT: INDEPENDENT_INVARIANT_FANOUT_TEST_FAIL
EVIDENCE_ROOT: .tmp/opsx-bug-team-harness/independent-invariant-fanout-test/20260728T210054Z/
```

Builder evidence:

```text
.tmp/opsx-bug-team-harness/corrective-v9/<RUN_ID>/
```

## Independent findings addressed

| ID | Finding | Fix |
|----|---------|-----|
| BF-V9-001 / I-04 | invariant contradicts root GREEN not rejected | `runtime/invariant_proof.py` + `ROOT-GREEN-PROOF.json` / `INVARIANT.json` |
| BF-V9-002 / FANIN_CONTENT | authoritative fan-in sparse | canonical `results/FAMILY-FANIN.json` → MD projection |
| BF-V9-003 / L-04 | learning packet incomplete | full `LEARNING_PACKET` + `validate_learning_packet` |
| BF-V9-004 | platform serialization treated as architecture FAIL | `PARALLEL_ELIGIBILITY` / `DISPATCH` / `EXECUTION_OBSERVED` |
| NF-V9-001 | shadow roles missing from REGISTRY | REGISTRY + worker specs |
| NF-V9-002 | placeholder CURSOR_AGENT_ID | `team/executions/<WEX>.identity.json` |
| NF-V9-003 | hardcoded blocks_closure | `blocks_closure_from_policy()` |

## Invariant root-proof validation

`capture_invariant` writes `INVARIANT.json` projection and, when
`ROOT-GREEN-PROOF.json` exists (or `require_root_proof=True`), validates:

- evidence hashes fresh
- scope overlap
- required/forbidden do not contradict root GREEN/FIX
- no unsupported / unrelated new behavioral rule

Rejection: `BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH` with diagnostics.

## Family fan-in canonical schema

`write_family_fanin` builds `results/FAMILY-FANIN.json` then projects
`FAMILY-FANIN.md` from that JSON only. Incomplete branch RED/GREEN/patch
hashes or omitted hunt candidates → `BLOCKED_INCOMPLETE_FAMILY_FANIN`.

## Learning packet canonical schema

Required fields listed in policy `LEARNING_PACKET_REQUIRED_FIELDS`.
Gates: fan-in READY, family GREEN PASS, no open blockers.
Stale source hashes → `BLOCKED_LEARNING_SOURCE_STALE`.

## Parallelism semantics

```text
PARALLEL_ELIGIBILITY + PARALLEL_DISPATCH + PARALLEL_EXECUTION_OBSERVED
NO_PLATFORM_SERIALIZED is NOT a blocking architecture failure
```

## Registry / identity / policy blocking

Shadow roles registered with `ACTIVATION_STATUS: SHADOW_V8`.
Agent IDs reconciled post-dispatch without rewriting immutable packets.
`BLOCKS_FAMILY_CLOSURE` derived from policy RELATION_RULES.

## PBH-006 controlled resume

Harness-only `V9-PBH006-RESUME-01` — real case not modified.

## V9 tests

```text
command: python .cursor/pipeline/bug-team/harness/run_corrective_v9_tests.py
total: 33
passed: 33
failed: 0
```

## Regressions

| Suite | Result |
|-------|--------|
| V8 | 28/28 PASS |
| V7 | 26/26 PASS |
| V6 | 31/31 PASS |
| V5 | 39/39 PASS |
| V4 | 29/29 PASS |
| V3 | 34/34 PASS |
| V2 | 18/18 PASS |

## Isolation

```text
PRODUCT_FILES_CHANGED: NONE
REAL_BUG_CASES_CHANGED: NONE
ACTIVE_DEFAULT_CHANGED: NO
BUG_FAMILY_FANOUT_ENABLED: false
RUNTIME_ACTIVATED_FOR_V8_V9: NO
COMMIT_CREATED: NO
```

## ONE_NEXT_ACTION

```text
Independent Invariant-Fanout Targeted Rerun
```

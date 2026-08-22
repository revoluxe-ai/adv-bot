# Corrective V10 Report — Authoritative Execution Identity Validation

```text
STATUS: OPSX_BUG_TEAM_CORRECTIVE_V10_IMPLEMENTED
COMMAND: /opsx-bug-team
CURRENT_ACTIVE_IMPLEMENTATION: ACTIVE_V1
V8_V10_IMPLEMENTATION: SHADOW_CANDIDATE
BUG_FAMILY_FANOUT_ENABLED: false
CONTROLLING_VERDICT: INDEPENDENT_INVARIANT_FANOUT_TARGETED_RERUN_FAIL
EVIDENCE_ROOT: .tmp/opsx-bug-team-harness/independent-invariant-fanout-targeted-rerun/20260728T215010Z/
BUILDER_EVIDENCE: .tmp/opsx-bug-team-harness/corrective-v10/20260728T220520Z/
```

## CONTROLLING_TARGETED_RERUN_FINDING

From `verdict/VERDICT.json` and `probes/PROBE_RESULTS.json`:

```text
FORMER_V9_BLOCKERS: CLEARED
BLOCKS_CLOSURE_POLICY_DERIVED: PASS
PBH_006_CONTROLLED_RESUME: PASS
SHADOW_BOUNDARY: PASS
CURSOR_AGENT_ID_RECONCILIATION: FAIL
NEW_BLOCKING_FINDING: EXECUTION_IDENTITY_VALIDATION_GAP
ONE_NEXT_ACTION: Corrective V10
```

Exact failed identity probe:

```text
PROBE: ID_MISSING_OUTPUT
PASS: false
DETAIL: "GAP: validate_identity accepts missing OUTPUT_PACKET_ID"
```

Blocking finding quote from VERDICT:

```text
"validate_identity accepts identity records with OUTPUT_PACKET_ID=None (missing output binding not rejected)"
```

## EXACT_IDENTITY_GAP

V9 `execution_identity.validate_identity` accepted records that looked
finalized (real agent id + MATCH + DISPATCH_RUNTIME) even when
`OUTPUT_PACKET_ID` was `None`. Identity JSON fields were trusted without
reconciling DISPATCH.jsonl, packet bytes/hashes, parent packet binding,
checkpoint attempt/generation, or supersession.

## AUTHORITATIVE_IDENTITY_MODEL

Canonical record at `team/executions/<WEX_SLUG>.identity.json` binds:

- one real Cursor Task agent (`CURSOR_AGENT_ID` from DISPATCH_RUNTIME)
- one exact `WORKER_EXECUTION_ID` / attempt
- one exact dispatch record id + hash
- one orchestration / case / finding / branch (branch may be explicit `null`)
- one input packet id/path/hash/generation
- one output packet id/path/hash/generation
- checkpoint path + generation
- `IDENTITY_STATUS` ∈ {PENDING_DISPATCH, DISPATCHED, OUTPUT_RECEIVED, VALIDATED, REJECTED}

`IDENTITY_RECORD_HASH` covers identity fields; `HOST_SIGNATURE` reuses
`retry_auth.ensure_host_secret` (HMAC). Identity cannot mint authority absent
from dispatch evidence.

API: `validate_execution_identity(...)` → `ExecutionIdentityValidationResult`
with STATUS/VALID/REASON_CODE and reconciliation fields.

Orchestration may advance worker terminal output only when identity validates
and is promoted to `IDENTITY_STATUS: VALIDATED`.

## CANONICAL_IDENTITY_PATH

```text
team/executions/<WORKER_EXECUTION_ID with '/' → '_'>.identity.json
```

Non-canonical paths → `IDENTITY_PATH_NON_CANONICAL`.
Copied identity under another WEX path → rejected.

## DISPATCH_RECONCILIATION

`finalize_live_hop` writes `DISPATCH_RECORD_ID` into DISPATCH.jsonl with real
`CURSOR_AGENT_ID`. Validator requires:

- dispatch record present for WEX
- DISPATCH_RECORD_ID / DISPATCH_RECORD_HASH match
- dispatch agent id finalized and equal to identity agent id

## PACKET_RECONCILIATION

- identity WEX == input WEX == output WEX == expected WEX
- INPUT/OUTPUT packet ids and hashes match current bytes
- `output.PARENT_PACKET_ID == input.PACKET_ID`
- orchestration/case/finding agree across packets and identity

## RETRY_AND_SUPERSESSION

- Attempt N identity cannot authorize attempt N+1
- Checkpoint `SUPERSEDED_WEX` / active WEX mismatch → `IDENTITY_SUPERSEDED` / `IDENTITY_STALE`
- Late formerly-valid identity remains rejected after supersession
- Complements (does not replace) stale-output and retry_auth gates

## ORCHESTRATOR_ENFORCEMENT

- `live_task_hop.finalize_live_hop`: placeholder/missing agent →
  `BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED`; after packet/WB/trace success,
  seal identity, validate, mark VALIDATED, only then advance checkpoint
- `OrchestratorRuntime.require_execution_identity`: dependent-wave gate
- `family_fanout.assert_family_worker_identity_gate` for family workers

## REAL_CURSOR_TASK_PROOF

```text
CURSOR_AGENT_ID: 99c887b7-6c4b-4c58-a39f-7ef60ffffdf7
MARKER: .tmp/opsx-bug-team-harness/corrective-v10/real-task-marker/PROOF.json
BINDING: fixtures/real-task-case + identity-records + DISPATCH + packets
VALIDATION: PASS → IDENTITY_STATUS VALIDATED
```

## V10_TESTS

```bash
python .cursor/pipeline/bug-team/harness/run_corrective_v10_tests.py
```

```text
total: 22
passed: 22
failed: 0
cases: V10-ID-01 .. V10-ID-20 + ID_MISSING_OUTPUT + PBH006-COMPAT
```

## V9_TO_V2_REGRESSIONS

```text
V9: 33/33 PASS
V8: 28/28 PASS
V7: 26/26 PASS
V6: 31/31 PASS
V5: 39/39 PASS
V4: 29/29 PASS
V3: 34/34 PASS
V2: 18/18 PASS
```

Former V9 targeted blockers remain PASS (invariant proof / family fan-in /
learning / parallelism / blocks_closure policy).

## SHADOW_BOUNDARY

```text
BUG_FAMILY_FANOUT_ENABLED: false
ACTIVE_DEFAULT_CHANGED: NO
RUNTIME_ACTIVATED: NO
REAL_PBH_006_RESUME: NOT_EXECUTED (compat gate only)
PRODUCT_FILES_CHANGED: NONE
REAL_BUG_CASES_CHANGED: NONE
COMMIT_CREATED: NO
```

## CANDIDATE_HASHES

See builder evidence:

```text
.tmp/opsx-bug-team-harness/corrective-v10/20260728T220520Z/candidate-hashes/
```

Primary modules changed:

- `runtime/execution_identity.py` (authoritative validator)
- `runtime/live_task_hop.py` (identity gate before checkpoint advance)
- `runtime/orchestrator.py` (`require_execution_identity`)
- `runtime/family_fanout.py` (family worker identity requirement)
- `harness/run_corrective_v10_tests.py`
- `.cursor/commands/opsx-bug-team.md` (V10 shadow note)

## ПРОСТОЕ ОБЪЯСНЕНИЕ

Раньше система могла принять «красивый» JSON с id агента даже без привязки
к реальному output-пакету и без сверки с DISPATCH. Теперь результат воркера
принимается только если доказано, что это один реальный Cursor Task, один
конкретный запуск (WEX), один dispatch, одни вход/выход пакеты и актуальная
попытка — иначе оркестрация не двигается.

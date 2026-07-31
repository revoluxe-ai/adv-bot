# OPSX Bug Team Candidate

```text
PACKAGE: .cursor/pipeline/bug-team/
COMMAND: /opsx-bug-team
COMMAND_PATH: .cursor/commands/opsx-bug-team.md
DEFAULT_FULL_BUG_ENTRY: /opsx-bug-team
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: ACTIVE
OWNER_ACTIVATION: ISSUED
ACTIVATION_MODE: CONTROLLED_LIVE_UNCOMMITTED
PIPELINE_GENERATION: ACTIVE_V1_WITH_INVARIANT_FANOUT_V10
BUG_FAMILY_FANOUT_ENABLED: true
BUG_FAMILY_FANOUT_STATUS: ACTIVE
SAME_INVARIANT_HUNT_FINDINGS: AUTOMATIC_FANOUT
MANUAL_SIBLING_RELAUNCH_REQUIRED: NO
FINAL_CONTROL: OWNER_REVIEWS_UNCOMMITTED_GIT_DIFF
MODEL_SELECTION_POLICY: auto
COMMIT_AUTHORITY: OWNER_ONLY
```

## Purpose

Registry-driven Cursor Task pipeline that orchestrates a full product/logic
bug lifecycle with separated worker roles, Owner gates, timeout/hang
protection, checkpoint resume, and free-form raw intake.

## Canonical layout

| Path | Role |
|------|------|
| `CANDIDATE_STATUS.md` | Hard status tokens |
| `REGISTRY.md` | Worker / Task registry |
| `ORCHESTRATION.md` | Waves, routing, Owner gates |
| `CHECKPOINT.md` | Checkpoint + resume schema |
| `TIMEOUT_POLICY.md` | Heartbeat / timeout / process-tree |
| `WRITE_BOUNDARY.md` | Fan-in and role write boundaries |
| `MODEL_POLICY.md` | Model = auto / inherit only |
| `packets/` | Input/output packet schemas |
| `roles/ROLES.md` | Contractual team roles |
| `controlled-tests/` | T1–T18 definitions |
| `harness/` | Controlled-test state machine (Candidate) |
| `CANDIDATE_REPORT.md` | Builder implementation report |

## Runtime model (discovery alignment)

Existing OPSX runtime is **registry-driven Cursor Task / slash-command
pipeline**, not `.cursor/agents/*`.

| Concern | Existing live SoT | Candidate extension |
|---------|-------------------|---------------------|
| Durable case map | `.tmp/opsx-bug-cases/**` | same |
| Route history | `ROUTE-TRACE.jsonl` v2 | worker role + heartbeat fields |
| Fan-in write | materialize `mode=fanin_assemble` → `FANIN.md` only | `FAN_IN_ASSEMBLER` role mirrors that boundary |
| Classification | `/opsx-classify-bug` | `CLASSIFIER` worker wraps same categories |
| RED/GREEN | `/opsx-test` | `RED_TEST_WORKER` / `GREEN_VERIFIER` |
| Orchestration policy | `ORCHESTRATION_MVP.md` | team waves + timeout/checkpoint |

## User front door

```text
Передайте описание бага в свободной форме.
Команда сама материализует сигнал, проверит дубликаты,
создаст case и выберет безопасный маршрут.
```

## Corrective V2 additions (machine enforcement)

```text
ACTIVATION.json + runtime/activation.py     BF-007
runtime/packets.py                          BF-002 UNKNOWN_FIELDS REJECT
runtime/fs_boundary.py                      BF-003 filesystem snapshot diff
runtime/owner_go.py                         BF-004 durable one-time GO
runtime/route_trace.py                      BF-005 append-only v2
runtime/timeout.py                          BF-006 honest cancellation limits
runtime/orchestrator.py                     reusable prep/validate/record
runtime/graph_fingerprint.py                BF-008 reproducible inventory
harness/run_corrective_tests.py             CT-01..CT-18
CORRECTIVE_LIVE_PROOF_REPORT.md             11/11 real Task proofs
```

Python harness does **not** replace Cursor Task dispatch. Host orchestrator
must invoke the Task tool; harness validates packets/FS/trace/gates.

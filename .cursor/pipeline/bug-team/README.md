# OPSX Bug Team Candidate

```text
PACKAGE: .cursor/pipeline/bug-team/
COMMAND: /opsx-bug-team
COMMAND_PATH: .cursor/commands/opsx-bug-team.md
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
MODEL_SELECTION_POLICY: auto
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

See `.cursor/commands/opsx-bug-team.md`.

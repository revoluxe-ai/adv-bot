# Worker I/O packet schema

```text
SCHEMA: opsx-bug-team/WORKER_IO
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
```

## Paths

```text
INPUT:  .opsx/runs/bug-cases/<CASE_ID>/team/packets/<WEX>.in.md
OUTPUT: .opsx/runs/bug-cases/<CASE_ID>/team/packets/<WEX>.out.md
```

## Write safety (mandatory — packets / JSONL)

When writing `OUTPUT_PACKET`, heartbeats, `ROUTE-TRACE.jsonl`, or other
durable JSON via agent Shell/Python, follow
`.cursor/commands/opsx-execution-preflight.md` →
**Shell payload I/O (anti-heredoc)** and
**Windows Shell JSON / JSONL write safety**
(defect class `HEREDOC-SHELL-PAYLOAD-001`):

```text
FORBIDDEN: bash heredoc (cat <<EOF / <<'EOF') for multi-line JSON/Python/packet writes
REQUIRED: Write tool (or write .py/.json to path) then run/read by path
encoding=utf-8; ensure_ascii=True for agent-authored recipes
on heredoc failure: do not retry heredoc — switch Write->path once
```

## Common input header

```text
WORKER_ID:
WORKER_EXECUTION_ID:
PARENT_ORCHESTRATION_ID:
CASE_ID:
FINDING_ID:
ATTEMPT:
MAX_ATTEMPTS:
TIMEOUT_SECONDS:
ALLOWED_INPUT_ARTIFACTS:   # explicit list; no ambient peek
WRITE_BOUNDARY_SUMMARY:
HEARTBEAT_PATH:
OUTPUT_PACKET_PATH:
```

Workers may read **only** paths listed in `ALLOWED_INPUT_ARTIFACTS`.
Seeing another worker's raw output without being listed is a boundary violation.

## Common output header

```text
WORKER_ID:
WORKER_EXECUTION_ID:
PARENT_ORCHESTRATION_ID:
STATUS: PASS|FAIL|BLOCKED|TIMEOUT|WAITING_OWNER|CANCELLED
TERMINAL_STATUS:
STARTED_AT:
COMPLETED_AT:
LAST_HEARTBEAT_AT:
ARTIFACTS_WRITTEN: []
ERROR:
```

Malformed / missing required fields → orchestrator rejects packet
(`MALFORMED_OUTPUT_PACKET`) and does not advance the wave.

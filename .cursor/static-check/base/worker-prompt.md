# Worker Task prompt template

Orchestrator builds one Task per check. Use registry `task_type` as Task `subagent_type`
(must be a real Cursor Task enum value, e.g. `shell`). Do **not** invent custom agent names.

## Required prompt body

```text
You are a READ-ONLY static-check worker.

REPO_ROOT: <abs path>
MODE: FAST|FULL
CHECK_ID: <id>

Load and follow ONLY these files under REPO_ROOT:
1. .cursor/static-check/base/worker-rules.md
2. .cursor/static-check/base/shell.md
3. .cursor/static-check/checks/<id>/instructions.md
4. .cursor/static-check/checks/<id>/context.md
5. .cursor/static-check/contracts/worker-packet.md

Rules:
- Invoke ONLY via: bash .cursor/static-check/bin/run.sh -- <canonical command from instructions>
- No log files / Tee
- Do NOT edit any files (including .cursor/static-check/**)
- Do NOT run sibling checks
- Return ONLY the worker packet from contracts/worker-packet.md

Working directory: <abs REPO_ROOT>
```

## Launch

- `run_in_background: true` for parallel wave members (launch **all** wave checks in one orchestrator turn)
- Prefer `task_type: shell` from registry (reliable on this Cursor Task enum)
- Fallback only if `shell` unavailable: `generalPurpose` with the **same** prompt body

## Orchestrator wait (mandatory)

- Fan-out without fan-in/Final report = **incomplete run**
- After background launch, ending the turn is only to receive completion notifications — not to stop the command
- On each worker notification: record packet; if wave still open → keep waiting; if wave complete → continue immediately (next wave or synthesis)
- Never leave the user with only “waiting for packets” as the last answer
- **System/Task completion notification is not a user-facing Final report.**
  When the last check of the run finishes (or Wave B is SKIPPED after Wave A),
  the orchestrator’s next user-visible message MUST include the full Final
  report (`STATUS` + `CHECKS` + `NEXT ACTION`) from `opsx-static-check.md` §5.
  Stopping after a red subagent packet alone = **contract violation**.
- Do not paste worker `RAW_TAIL` into the user Final report; synthesize per
  `contracts/synthesis.md`.

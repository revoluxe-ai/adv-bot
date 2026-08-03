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
- Run that canonical command **once**; do not re-read packs, re-plan, or re-invoke the suite
- No log files / Tee
- Do NOT edit any files (including .cursor/static-check/**)
- Do NOT run sibling checks
- Immediately after the command finishes, return ONLY the worker packet from contracts/worker-packet.md (no narration loops)

Working directory: <abs REPO_ROOT>
```

## Launch

- `run_in_background: true` for parallel wave members (launch **all** wave checks in one orchestrator turn)
- Use registry `task_type` as primary: `shell` for short checks (pyright /
  mypy / pytest-targeted); `generalPurpose` for long suite waves
  (`pytest-unit` / `pytest-integration` / `pytest-destructive`). Do **not**
  prefer shell for suite waves — shell Task often Agent-Loops / silent-stalls
  before pytest starts.
- Initial fallback if registry `task_type` unavailable in the live Task enum:
  `generalPurpose` with the **same** prompt body

## Launch-infra retry (exactly one Task retry)

Treat as **launch-infra failure** (not a pytest FAIL) when ANY of:

- first Task finishes with no parseable worker packet (missing `CHECK_ID` /
  `STATUS` / `COMMAND` shape);
- harness abort text such as Agent Looping / repeating pattern / aborted
  without `EXIT_CODE`;
- Task tool error with no packet body;
- **silent stall** (pre-completion): CHECK_ID in-flight, no parseable packet
  yet, owner reports hang/завис/стоп-воркера (or orchestrator probes after
  that signal), **and** evidence shows no matching `pytest`/`run.sh` for that
  check and/or Task transcript is only the initial prompt (no command output).
  Interrupt/abandon the open Task if still open before retrying.

Then retry **once** the same `CHECK_ID` with Task `subagent_type: generalPurpose`
and the **same** prompt body (still READ_ONLY; same `run.sh` command).

- If the retry yields a valid packet → use that packet (`PASS` / `FAIL` /
  `BLOCKED` as usual).
- Never more than one Task retry per `CHECK_ID` per run.
- Do not invent undeclared tool wrappers.
- Do not reclassify Agent Looping / empty packet / silent stall as a product
  test failure.
- **Not** launch-infra: matching `pytest`/`run.sh` is alive (e.g. PG lock
  hang) → env / concurrent-suite; owner `STOP_RUN` of entire static-check →
  no retry.

## Orchestrator-direct fallback (exactly one)

If the one Task launch-infra retry is exhausted **and** the check never
started (no parseable packet; no matching `pytest`/`run.sh` / command
output) → orchestrator runs **once** via its own Shell tool:
`bash .cursor/static-check/bin/run.sh -- <canonical command>`, synthesizes a
worker packet, continues cascade. Not a second Task retry. If that also fails
→ `STATUS=ERROR`; later pytest waves SKIPPED per cascade gates.

## Orchestrator wait (mandatory)

- Fan-out without fan-in/Final report = **incomplete run**
- After background launch, ending the turn is only to receive completion notifications — not to stop the command
- On each worker notification **or** silent-stall signal: record packet **or**
  apply Launch-infra Task retry once **or** (after Task budget) orchestrator-direct;
  if wave still open → keep waiting; if wave complete → continue immediately
  (next wave or synthesis)
- Never leave the user with only “waiting for packets” as the last answer
- **System/Task completion notification is not a user-facing Final report.**
  When the last check of the run finishes (or later waves are SKIPPED),
  the orchestrator’s next user-visible message MUST include the full Final
  report (`STATUS` + `CHECKS` + `NEXT ACTION`) from `opsx-static-check.md` §5.
  Stopping after a red subagent packet alone = **contract violation**.
- Do not paste worker `RAW_TAIL` into the user Final report; synthesize per
  `contracts/synthesis.md`.

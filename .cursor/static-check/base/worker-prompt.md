# Worker / orchestrator execution template for /opsx-static-check

## Default launch: `SERIAL_ORCHESTRATOR` (no nested Task)

Unless the Owner message contains the **exact** token `PARALLEL_TASKS`:

- Do **not** create Cursor Task workers for any check.
- The **parent orchestrator** runs every scheduled check via Shell:
  `bash .cursor/static-check/bin/run.sh -- <canonical command from instructions>`
- Synthesize each worker packet locally (schema in `contracts/worker-packet.md`).
- Registry `task_type` / wave `parallel` are ignored under this default.
- Complete the cascade, then emit the Final report (`STATUS` + `CHECKS` +
  `NEXT ACTION`). Progress-only lines are never terminal.
- **Long-suite heartbeat (pytest-unit / similarly long Shell):** before starting
  the unit xdist Shell, emit
  `WORKER RUNNING: pytest-unit (xdist; expect multi-minute)`. Prefer sliced
  waits (~60–120s) or background Shell + `AwaitShell` with periodic
  `WORKER RUNNING: pytest-unit (still in progress; ~Nm elapsed)` — **not** one
  opaque multi-tens-of-minutes silence. Align with `opsx-static-check.md` /
  `checks/pytest-unit/instructions.md`.
- Owner «зависло»/hang while SERIAL `pytest`/`run.sh` is **alive** is **not**
  launch-infra; keep heartbeat/poll or, if Owner aborts, treat as STOP_RUN.
- Owner `STOP_RUN` / Shell tool interrupted / abort mid-check → **no** retry;
  in-flight check `STATUS=ERROR` (`interrupted` / `STOP_RUN`); later pytest
  waves `SKIPPED`; fan-in known packets; **mandatory** Final **same turn**.
  Never leave mid-cascade silence or progress-only as terminal.

## Opt-in: `PARALLEL_TASKS` (legacy Task fan-out)

Only when Owner passes `PARALLEL_TASKS`: orchestrator builds one Task per
**Task-launched** check. Use registry `task_type` as Task `subagent_type` when
it is a real Cursor Task enum value (`shell` / `generalPurpose`). For
`task_type: orchestrator` (pytest-unit): **do not** create a Task — see
«pytest-unit orchestrator path» below. Do **not** invent custom agent names.

## Required prompt body (Task workers under `PARALLEL_TASKS` only)

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

## Launch (`PARALLEL_TASKS` only)

- `run_in_background: true` for parallel wave members (launch **all** wave checks in one orchestrator turn)
- Use registry `task_type` as primary:
  - `shell` — short checks (`pyright-strict` / `mypy` / `pytest-targeted`)
  - `orchestrator` — **pytest-unit only**: do **not** create a Task; the
    orchestrator runs hygiene + `run.sh` itself via Shell and synthesizes the
    worker packet (see pytest-unit instructions)
  - `generalPurpose` — other long suite waves (`pytest-integration` /
    `pytest-destructive`). Do **not** prefer shell for those — shell Task
    often Agent-Loops / silent-stalls before pytest starts
- Initial fallback if registry `task_type` unavailable in the live Task enum
  (and the check is **not** `orchestrator`): `generalPurpose` with the **same**
  prompt body

## pytest-unit orchestrator path (mandatory always)

1. Stale-pytest hygiene (≤ ~5s) per `checks/pytest-unit/instructions.md`.
2. Run once: `bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit -n 8 --dist=worksteal`.
3. Parse STATUS: PASS / FAIL (failed nodes) / ERROR `infra_suite` (xdist
   worker-death / INTERNALERROR / exit 2|3 with **no** failed node ids).
4. On `infra_suite`: exactly one INFRA recovery = hygiene again + one Shell
   re-run; emit `WORKER INFRA RETRY: pytest-unit → orchestrator-shell`.
5. Never fan-out Task for pytest-unit. Launch-infra Task retry does **not**
   apply to this check (already orchestrator-owned).

## Launch-infra retry (exactly one Task retry)

Applies only under `PARALLEL_TASKS` to checks launched via Task
(`shell` / `generalPurpose`). **Not** for `task_type: orchestrator`
(pytest-unit). **Not** under default `SERIAL_ORCHESTRATOR` (all checks already
parent Shell).

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
  hang) → env / concurrent-suite; Owner «зависло» while SERIAL pytest is alive
  → not launch-infra (heartbeat/poll or STOP_RUN if abort).
- **Not** launch-infra: owner `STOP_RUN` / Shell interrupt / abort of entire
  static-check → no retry; mandatory Final with ERROR+SKIPPED same turn
  (see SERIAL section above and `opsx-static-check.md`).
- **Not** launch-infra: pytest finished with `INTERNALERROR` / «no active
  workers» without failed nodes → that is **INFRA suite** recovery on
  pytest-unit (orchestrator path above), not a Task retry.

## Orchestrator-direct fallback (exactly one)

Applies under `PARALLEL_TASKS` only. If the one Task launch-infra retry is
exhausted **and** the check never started (no parseable packet; no matching
`pytest`/`run.sh` / command output) → orchestrator runs **once** via its own
Shell tool: `bash .cursor/static-check/bin/run.sh -- <canonical command>`,
synthesizes a worker packet, continues cascade. Not a second Task retry. If
that also fails → `STATUS=ERROR`; later pytest waves SKIPPED per cascade gates.

Does **not** apply to pytest-unit primary path (already orchestrator Shell);
pytest-unit uses INFRA recovery instead when the suite itself dies on xdist.
Under default `SERIAL_ORCHESTRATOR`, every check is already orchestrator Shell
— this fallback is unused.

## Orchestrator wait / completion (mandatory)

- Fan-out / progress without fan-in/Final report = **incomplete run**
  (`INCOMPLETE_RUN` for supervisor / owner envelopes — not PASS/FAIL).
- **Forbidden as sole/terminal user-visible content:**
  - “Wave A in flight”
  - “waiting for packets”
  - “cascade continues”
  - any equivalent progress-only wording without Final `STATUS:` + `CHECKS`
- Under SERIAL: long suites may emit `WORKER RUNNING` heartbeats / sliced
  waits **inside** the turn; still must Final when cascade completes **or**
  on STOP_RUN / Shell interrupt / Owner abort.
- After background launch (`PARALLEL_TASKS`), ending the turn is only to receive
  completion notifications — not to stop the command. Resume until Final
  **or** apply STOP_RUN Final.
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
- On known abort (STOP_RUN / Shell interrupt): synthesize from packets already
  collected + in-flight ERROR + later SKIPPED — never leave `INCOMPLETE_RUN`
  as the only outcome when abort is known.
- Do not paste worker `RAW_TAIL` into the user Final report; synthesize per
  `contracts/synthesis.md`.

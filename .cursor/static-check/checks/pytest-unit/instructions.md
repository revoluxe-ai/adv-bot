# pytest-unit — instructions

From repo root (full unit suite — pytest-xdist):

```bash
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit -n 8 --dist=worksteal
```

Packet COMMAND: `poetry run pytest -m unit -n 8 --dist=worksteal`

**Launch owner:** orchestrator Shell only (`task_type: orchestrator`). Do **not**
fan-out a nested Task for this check. See `registry.yaml` +
`opsx-static-check.md` Wave U.

**Orchestrator gate:** start only if `pytest-targeted` packet `STATUS=PASS`
(including PASS with `not_applicable_no_related_tests`).
If targeted is FAIL/BLOCKED/ERROR → do **not** run this check (`SKIPPED`).

## Stale-pytest hygiene (mandatory before first run and before INFRA retry)

Budget ≤ ~5s hard wall. Windows-first. Before invoking the canonical command:

1. Capture `RUN_START_TS` at the beginning of this check (before process probe).
2. Probe processes whose CommandLine matches this `REPO_ROOT` and
   `pytest` / `xdist` / `run.sh -- poetry run pytest`, collecting
   `pid`, `ppid`, `started_at` (if available), and commandline.
   Prefer a fast narrow probe (e.g. filtered `tasklist` / short PowerShell
   with timeout). Do **not** run unbounded full `Win32_Process` CIM scans
   that routinely exceed the budget.
3. Build current process tree roots for this run (orchestrator shell/python).
4. A process is **eligible orphan** only if ALL conditions are true:
   - matches repo-root + pytest/xdist signature;
   - `started_at < RUN_START_TS` (or parent already gone, with reliable probe);
   - is **not** in the current process tree of this run.
5. Terminate only eligible orphans. Never kill current-tree processes.
6. Concurrent second `pytest -n …` on the same tree is **unsupported**.
7. Do not use Docker / `poetry install` / network as part of hygiene.
8. If probe cannot reliably determine ancestry/start-time for candidates
   (ambiguous ownership), stop with `STATUS=BLOCKED` and
   `ERROR=blocked_hygiene_ambiguous` (do not blind-kill).
9. If the probe itself exceeds ~5s wall without a reliable answer: abort the
   probe, do **not** blind-kill, document
   `WORKER HYGIENE: pytest-unit → none (found=0 eligible=0 killed=0 skipped_current_tree=0)`
   with NOTES `hygiene_probe_timeout`, and proceed to the unit Shell
   (treat as no orphans found). Do **not** spend tens of seconds on hygiene.

Document progress with counters:
`WORKER HYGIENE: pytest-unit → cleared|none|blocked (found=<n> eligible=<n> killed=<n> skipped_current_tree=<n>)`.

## Long-suite heartbeat (SERIAL / orchestrator Shell)

Before starting the canonical xdist command, emit:
`WORKER RUNNING: pytest-unit (xdist; expect multi-minute)`.
Prefer sliced Shell waits (~60–120s) or background Shell + `AwaitShell` with
periodic `WORKER RUNNING: pytest-unit (still in progress; ~Nm elapsed)`.
Do **not** rely on one opaque multi-tens-of-minutes silent wait.
Owner «зависло» while this suite’s `pytest`/`run.sh` is alive is **not**
launch-infra retry. On Owner `STOP_RUN` / Shell interrupt / abort: packet
`STATUS=ERROR`, `ERROR=interrupted` or `STOP_RUN`, then orchestrator Final
(later waves SKIPPED) — see `opsx-static-check.md`.

## Rules

- Do **not** `--deselect` / exclude paths already run in `pytest-targeted`.
  Targeted is early-stop only; this wave is the full marker suite gate.
- Do not run pyright, mypy, integration, destructive, or bare `pytest`.
- Primary path keeps `-n` / `--dist` (full suite). Non-xdist is allowed only
  as final fallback classifier after INFRA retry exhaustion.
- xdist is **only** for this full unit pack — never for targeted /
  integration / destructive.
- If unavailable → STATUS=BLOCKED.

## Parsing / STATUS

Prefer failed node ids (`path::node`).
Collection problems → severity `collection-error`.

| Outcome | STATUS |
|---------|--------|
| Exit 0 | PASS |
| Non-zero **with** failed node ids / assertion failures | FAIL |
| `INTERNALERROR` / `Unexpectedly no active workers` / exit ∈ {2,3} **and** no failed node ids | ERROR (`infra_suite`) — **not** product FAIL |
| Fallback non-xdist also crashes with no failed nodes | ERROR (`infra_suite_hard`) |
| Owner STOP_RUN / Shell interrupt / abort mid-suite | ERROR (`interrupted` / `STOP_RUN`) — not product FAIL |

### INFRA recovery ladder (exactly once per stage per CHECK_ID per run)

When STATUS would be ERROR `infra_suite`:

1. Re-run stale-pytest hygiene.
2. Re-run the canonical xdist command once via orchestrator Shell.
3. Emit `WORKER INFRA RETRY: pytest-unit → orchestrator-shell`.
4. If retry result is PASS/FAIL, finish with `UNIT_RECOVERY_PATH=xdist_retry`.
5. If retry result is infra death again (no failed nodes), run one deterministic
   fallback classifier (no xdist):

   ```bash
   bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit -x
   ```

6. Fallback classification:
   - fallback Exit 0 → PASS (`UNIT_RECOVERY_PATH=fallback_non_xdist`)
   - fallback non-zero with failed node ids/assertions → FAIL
     (`UNIT_RECOVERY_PATH=fallback_non_xdist`)
   - fallback infra crash/no failed nodes → ERROR `infra_suite_hard`
     (`UNIT_RECOVERY_PATH=fallback_non_xdist`)
7. Never ask for manual "kill + full rerun" as first reaction after xdist retry
   exhaustion. The ladder must produce an in-run deterministic verdict unless
   fallback also infra-crashes.
8. Do **not** enter this ladder for `interrupted` / `STOP_RUN` packets.

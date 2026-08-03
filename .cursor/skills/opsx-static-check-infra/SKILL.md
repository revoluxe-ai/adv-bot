---
name: opsx-static-check-infra
description: >-
  How to extend /opsx-static-check: registry, SERIAL orchestrator default,
  optional Task workers, check packs, contracts.
  Use when adding a static-check worker or changing static-check architecture.
disable-model-invocation: true
---

# opsx-static-check infrastructure

Working team layout for this repo (keep it lean):

```text
.cursor/commands/opsx-static-check.md     # human orchestrator
.cursor/static-check/                     # SoT
  registry.yaml                           # default_launch + waves + packs
  base/                                   # worker + shell + prompt rules
  contracts/                              # packet + synthesis
  checks/<id>/instructions.md + context.md
.cursor/skills/opsx-static-check-infra/   # this skill
.cursor/rules/opsx-static-check-infra.mdc # short invariants
```

## Authority split

| Layer | Owns |
|-------|------|
| Command | MODE UX, launch/fan-in, human report |
| Registry | `default_launch`, waves, `task_type` (PARALLEL only), pack path |
| Pack | how to run/parse one check |
| Skill | how to extend the system |
| Rule | must-not-violate invariants |

## Add a check

1. Create `.cursor/static-check/checks/<id>/instructions.md` + `context.md`
2. Add row + wave membership in `registry.yaml` with appropriate `task_type`
   (`shell` short; `orchestrator` only if the orchestrator must own the run
   like pytest-unit; `generalPurpose` for other long suites) and `pack:`
   (`task_type` used only under Owner token `PARALLEL_TASKS`)
3. Do **not** create custom `.cursor/agents/opsx-sc-*` launch names (Task enum rejects them)
4. Do **not** put tool details into the command body
5. Smoke: under SERIAL, orchestrator Shell `run.sh` → valid worker packet; then
   `/opsx-static-check FAST`. Optional: `PARALLEL_TASKS` + Task(`shell`) smoke.

## Shell / env gate

Canonical human cmds: `pyright-strict`, `mypy .`, targeted
`poetry run pytest -m unit|integration <paths>` (**no xdist**), full
`poetry run pytest -m unit -n 8 --dist=worksteal` (**xdist only here**),
fallback classifier `poetry run pytest -m unit -x` (only after xdist infra
retry exhaustion),
`poetry run pytest -m integration`, and FULL-only
`poetry run pytest -m destructive_local` (+ ALLOW_*). Never bare
`poetry run pytest`.
Workers **must** invoke via `bash .cursor/static-check/bin/run.sh -- ...` (see `base/shell.md`).

Launch:
- **Default `SERIAL_ORCHESTRATOR`:** no nested Task; parent Shell cascade for
  every check (`registry.yaml` `default_launch`)
- Optional retry profile: `FROM_WAVE=U` (skip Wave A) is valid only with
  `A_REUSE_FINGERPRINT=<id>` plus accepted evidence that Wave A was PASS for
  the same fingerprint; otherwise run full cascade
- Opt-in exact token `PARALLEL_TASKS`:
  - `task_type: shell` → Task shell (short checks)
  - `task_type: orchestrator` → **pytest-unit**: no nested Task; orchestrator
    Shell + stale-pytest hygiene + one xdist INFRA retry; if infra repeats
    without failed nodes, one non-xdist fallback classifier in-run
    (`UNIT_RECOVERY_PATH=xdist_retry|fallback_non_xdist`; only fallback crash
    remains `ERROR infra_suite_hard`, not product FAIL / not sole
    `/opsx-test-triage`)
  - `task_type: generalPurpose` → other long suite waves

Launch-infra (`PARALLEL_TASKS` Task checks only): missing packet / Agent
Looping / **silent stall** → interrupt open Task if needed → exactly one Task
`generalPurpose` retry (same prompt). If Task budget exhausted and suite never
started → one **orchestrator-direct** `run.sh` + synthesize packet; then ERROR.
Not a product-test FAIL. Exclude live pytest (PG lock) and full `STOP_RUN`.

Optional `PREFLIGHT` token only; default off. Wave U stale-pytest hygiene is
mandatory whenever pytest-unit runs (not the same as file PREFLIGHT).
Check runs must not edit infra to self-heal.
Pytest cascade: targeted → unit → integration → (FULL) destructive; hard-stop
on FAIL|BLOCKED|ERROR; no deselect of dirty paths in suite waves.

Completion: Final report required (`STATUS` + `CHECKS`). Progress-only
(«Wave A in flight», «waiting for packets», «cascade continues») =
`INCOMPLETE_RUN`, never a successful terminal envelope.

## Do not

- Duplicate SoT in `opsx-static-check-workers/` or fat agent bodies
- Prefer custom project agent names that are not in the Cursor Task enum
- Prefer Task fan-out as the default (SERIAL is default; Task only with
  `PARALLEL_TASKS`)
- Prefer Task `shell` for long suite waves that use `generalPurpose`
- Fan-out a nested Task for `task_type: orchestrator` (pytest-unit) or under
  default SERIAL for any check
- Put xdist on targeted / integration / destructive
- Auto-delegate workers with vague “use proactively” for general coding
- Run suite pytest waves in parallel with each other or with targeted
- Schedule `pytest-destructive` in FAST / launch retired `pytest-full`
- Retry the same CHECK_ID more than once via Task after launch-infra failure
  (orchestrator-direct once is allowed after Task budget; pytest-unit INFRA
  recovery is a separate one-shot)
- Treat Agent Looping / empty packet / silent stall as pytest FAIL without a
  worker packet
- Treat xdist «no active workers» without failed nodes as product
  `/opsx-test-triage` (use INFRA recovery / owner kill leftover pytest)
- End the orchestrator chat after fan-out / partial READY / progress-only
  without Final report (completion contract in command + `base/worker-prompt.md`)

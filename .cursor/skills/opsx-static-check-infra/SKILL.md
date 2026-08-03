---
name: opsx-static-check-infra
description: >-
  How to extend /opsx-static-check: registry, Task shell workers, check packs, contracts.
  Use when adding a static-check worker or changing static-check architecture.
disable-model-invocation: true
---

# opsx-static-check infrastructure

Working team layout for this repo (keep it lean):

```text
.cursor/commands/opsx-static-check.md     # human orchestrator
.cursor/static-check/                     # SoT
  registry.yaml                           # waves + task_type + packs
  base/                                   # worker + shell + prompt rules
  contracts/                              # packet + synthesis
  checks/<id>/instructions.md + context.md
.cursor/skills/opsx-static-check-infra/   # this skill
.cursor/rules/opsx-static-check-infra.mdc # short invariants
```

## Authority split

| Layer | Owns |
|-------|------|
| Command | MODE UX, fan-out/fan-in, human report |
| Registry | waves + `task_type` (Task enum) + pack path |
| Pack | how to run/parse one check |
| Skill | how to extend the system |
| Rule | must-not-violate invariants |

## Add a check

1. Create `.cursor/static-check/checks/<id>/instructions.md` + `context.md`
2. Add row + wave membership in `registry.yaml` with `task_type: shell` and `pack:`
3. Do **not** create custom `.cursor/agents/opsx-sc-*` launch names (Task enum rejects them)
4. Do **not** put tool details into the command body
5. Smoke: Task(`shell`) with `base/worker-prompt.md` → valid worker packet; then `/opsx-static-check FAST`

## Shell / env gate

Canonical human cmds: `pyright-strict`, `mypy .`, targeted
`poetry run pytest -m unit|integration <paths>`, full
`poetry run pytest -m unit -n 8 --dist=worksteal`,
`poetry run pytest -m integration`, and FULL-only
`poetry run pytest -m destructive_local` (+ ALLOW_*). Never bare
`poetry run pytest`.
Workers **must** invoke via `bash .cursor/static-check/bin/run.sh -- ...` (see `base/shell.md`).
Launch workers via Task `subagent_type` = registry `task_type` (`shell` short
checks; `generalPurpose` long suite waves).
Launch-infra: missing packet / Agent Looping / **silent stall** → interrupt
open Task if needed → exactly one Task `generalPurpose` retry (same prompt).
If Task budget exhausted and suite never started → one **orchestrator-direct**
`run.sh` + synthesize packet; then ERROR. Not a product-test FAIL. Exclude
live pytest (PG lock) and full `STOP_RUN`.
Optional `PREFLIGHT` token only; default off. Check runs must not edit infra to self-heal.
Pytest cascade: targeted → unit → integration → (FULL) destructive; hard-stop
on FAIL|BLOCKED|ERROR; no deselect of dirty paths in suite waves.

## Do not

- Duplicate SoT in `opsx-static-check-workers/` or fat agent bodies
- Prefer custom project agent names that are not in the Cursor Task enum
- Prefer Task `shell` for long suite waves (use registry GP)
- Auto-delegate workers with vague “use proactively” for general coding
- Run suite pytest waves in parallel with each other or with targeted
- Schedule `pytest-destructive` in FAST / launch retired `pytest-full`
- Retry the same CHECK_ID more than once via Task after launch-infra failure
  (orchestrator-direct once is allowed after Task budget)
- Treat Agent Looping / empty packet / silent stall as pytest FAIL without a
  worker packet
- End the orchestrator chat after fan-out / partial READY without Final report (WAIT contract in command + `base/worker-prompt.md`)

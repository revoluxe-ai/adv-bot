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

Canonical human cmds: `pyright-strict`, `mypy .`, `poetry run pytest -m unit`, `poetry run pytest .`.
Workers **must** invoke via `bash .cursor/static-check/bin/run.sh -- ...` (see `base/shell.md`).
Launch workers via Task `subagent_type` = registry `task_type` (`shell` primary).
Optional `PREFLIGHT` token only; default off. Check runs must not edit infra to self-heal.
Wave B only if `pytest-unit` STATUS=PASS.

## Do not

- Duplicate SoT in `opsx-static-check-workers/` or fat agent bodies
- Prefer custom project agent names that are not in the Cursor Task enum
- Auto-delegate workers with vague “use proactively” for general coding
- Run `pytest-full` in parallel with `pytest-unit`
- End the orchestrator chat after fan-out / partial READY without Final report (WAIT contract in command + `base/worker-prompt.md`)

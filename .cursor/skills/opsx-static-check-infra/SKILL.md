---
name: opsx-static-check-infra
description: >-
  How to extend /opsx-static-check: registry, thin agents, check packs, contracts.
  Use when adding a static-check worker or changing static-check architecture.
disable-model-invocation: true
---

# opsx-static-check infrastructure

Working team layout for this repo (keep it lean):

```text
.cursor/commands/opsx-static-check.md     # human orchestrator
.cursor/agents/opsx-sc-*.md               # THIN Cursor subagents
.cursor/static-check/                     # SoT
  registry.yaml
  base/                                   # shared worker + shell rules
  contracts/                              # packet + synthesis
  checks/<id>/instructions.md + context.md
.cursor/skills/opsx-static-check-infra/   # this skill
.cursor/rules/opsx-static-check-infra.mdc # short invariants
```

## Authority split

| Layer | Owns |
|-------|------|
| Command | MODE UX, fan-out/fan-in, human report |
| Agent | isolation + LOAD list only |
| Pack | how to run/parse one check |
| Skill | how to extend the system |
| Rule | must-not-violate invariants |

## Add a check

1. Create `.cursor/static-check/checks/<id>/instructions.md` + `context.md`
2. Create thin `.cursor/agents/opsx-sc-<short>.md` (LOAD list only)
3. Add row + wave membership in `registry.yaml`
4. Do **not** put tool details into the agent or command body
5. Smoke: launch agent alone → valid worker packet; then `/opsx-static-check FAST`

## Shell

Default: PowerShell + `poetry run` (repo terminal rule).
Git-bash only when a pack needs a bash pipeline — see `base/shell.md`.

## Do not

- Duplicate SoT in `opsx-static-check-workers/` or fat agent bodies
- Auto-delegate workers with vague “use proactively” for general coding
- Run `pytest-full` in parallel with `pytest-unit`

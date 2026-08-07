# OPSX adapter: poetry-scripts

Target: `meta-repo/scripts` (WB Sky — Poetry / Python 3.11).

## Purpose

Capability map for `/opsx-projectize` and gated workers. Replaces game
`vue-npm` assumptions. Does **not** install dependencies.

## Detect

| Signal | Expected |
|---|---|
| `pyproject.toml` | present |
| `poetry.lock` | present |
| `app/` | main package |
| `tests/` | pytest |
| `package.json` | optional tooling only (e.g. smithery) — **not** Vue app |
| `src/` / `public/` | absent |

## Capabilities

```text
stack: poetry-python
package_manager: poetry
test: poetry run pytest
typecheck: poetry run pyright-strict
unit_marker: -m unit
integration_marker: -m integration
docs: AGENTS.md + .cursor/rules/documentation.mdc
k8s_ops: PowerShell + kubectl (see .cursor/rules/terminal.mdc)
openspec_root: openspec/
```

## Forbidden remap (from Vue templates)

- Do not treat `package.json` scripts as the primary quality gate.
- Do not require `.opsx/adapters/vue-npm/`.
- Do not wipe `openspec/**` or `app/**` during projectize.

## Refresh

`/opsx-adapt-project` after COMPLETE when Poetry scripts or gates change.

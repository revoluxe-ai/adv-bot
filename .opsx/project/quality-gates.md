# Quality gates — poetry-python (WB Sky)

Source of truth for TARGET OVERRIDE “mandatory declared executable checks”
after projectize dropped `vue-npm` for `poetry-python`.

## Adapter

- `adapter_id`: `poetry-python`
- Capability signals: `pyproject.toml`, `poetry.lock`, `app/`, `tests/`

## Declared checks (when in scope)

Run only when the corresponding capability is present. Missing capability →
`UNAVAILABLE` or `FAIL_CLOSED` — never PASS-by-absence.

| Check | Command / signal | Notes |
|---|---|---|
| unit/integration (targeted) | `poetry run pytest` (scoped path or `-m`) | Prefer targeted suite for process commits |
| typecheck | `poetry run pyright-strict` | Strict config from repo |
| whitespace / conflict markers | `git diff --check` | Always cheap; use on staged/process diff |

## Not applicable (UNAVAILABLE)

| Check | Reason |
|---|---|
| `npm run build` | `vue-npm` dropped; root `package.json` has no `build` script |
| frontend smoke / acceptance / lint / typecheck | Not a Vue/npm tree unless adapter says otherwise |

## Policy

- Do not invent missing adapters or treat absence of npm as a pass.
- Process commands cite this file; do not hard-code `npm run build` as mandatory.

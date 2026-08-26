# Adapter: poetry-python

Target stack adapter for this repository after `/opsx-projectize`.

## Identity

| Field | Value |
|---|---|
| adapter_id | `poetry-python` |
| product | WB Sky (`implement-free-bot-rebase` / adv-bot family) |
| runtime | Python 3.11 + Poetry |
| process plane | `opsx-lite` (required) |

## Capability signals

- `pyproject.toml` / `poetry.lock`
- `app/` runtime package
- `tests/` with pytest markers (`unit` / `integration`)
- Quality gates (typical): `poetry run pytest`, `poetry run pyright-strict`,
  `git diff --check`
- OpenSpec product tree under `openspec/` (keep; never wipe on projectize)

## Non-goals

- Not `vue-npm`. Do not seed or require Vue/`package.json` game scripts.
- Does not own product code edits under `app/**`.
- Dependency install remains Owner/CI concern — adapt-project must not
  `poetry install` as a side effect.

## Refresh

Use `/opsx-adapt-project` (read-only) or `:GO` to refresh adapter notes and
capability-bound activation rows after tooling changes.| product | WB Sky (`adv-bot` Poetry package) |

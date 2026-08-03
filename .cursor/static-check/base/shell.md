# Shell for static-check workers

## Canonical human commands

```text
pyright-strict
mypy .
poetry run pytest -m unit <paths…>          # pytest-targeted (unit bucket)
poetry run pytest -m integration <paths…>   # pytest-targeted (integration bucket)
poetry run pytest -m unit -n 8 --dist=worksteal
poetry run pytest -m integration
poetry run pytest -m destructive_local      # FULL only; requires ALLOW_*
```

## Mandatory agent invoke

```bash
bash .cursor/static-check/bin/run.sh -- pyright-strict
bash .cursor/static-check/bin/run.sh -- mypy .
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit <paths…>
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m integration <paths…>
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit -n 8 --dist=worksteal
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m integration
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m destructive_local
```

From repo root. Works in **Git Bash and WSL**.

Runner resolves **absolute** `.venv/Scripts/*.exe` (or `.venv/bin/*`) and does **not** source `~/.bashrc` (avoids npm pyright/node).

Packet `COMMAND`: human form (`pyright-strict`, `mypy .`, `poetry run pytest -m …`, …).

Do **not** invoke `poetry run pytest .` — path `.` overrides `testpaths` and may
collect `.tmp/**`.

Do **not** invoke bare `poetry run pytest` (no marker) — retired with
`pytest-full`. Use the cascade markers above.

## Forbidden

- `bash -lc 'source ~/.bashrc; source .venv/Scripts/activate; …'`
- bare `pyright` / global npm shims
- durable Tee/log files by default
- `poetry run pytest .`
- bare `poetry run pytest` (no `-m`)

## Hard rules

- Missing venv tool → `STATUS=BLOCKED` (exit 127 from runner).
- Pytest cascade: targeted PASS → unit → integration → (FULL only) destructive.
  Later pytest waves SKIPPED on FAIL|BLOCKED|ERROR. Never deselect dirty paths
  from suite waves. Never schedule destructive in FAST.

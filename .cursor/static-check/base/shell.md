# Shell for static-check workers

## Canonical human commands

```text
pyright-strict
mypy .
poetry run pytest -m unit
poetry run pytest .
```

## Mandatory agent invoke

```bash
bash .cursor/static-check/bin/run.sh -- pyright-strict
bash .cursor/static-check/bin/run.sh -- mypy .
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit
bash .cursor/static-check/bin/run.sh -- poetry run pytest .
```

From repo root. Works in **Git Bash and WSL**.

Runner resolves **absolute** `.venv/Scripts/*.exe` (or `.venv/bin/*`) and does **not** source `~/.bashrc` (avoids npm pyright/node).

Packet `COMMAND`: human form (`pyright-strict`, `mypy .`, …).

## Forbidden

- `bash -lc 'source ~/.bashrc; source .venv/Scripts/activate; …'`
- bare `pyright` / global npm shims
- durable Tee/log files by default

## Hard rules

- Missing venv tool → `STATUS=BLOCKED` (exit 127 from runner).
- Wave B only if pytest-unit PASS.

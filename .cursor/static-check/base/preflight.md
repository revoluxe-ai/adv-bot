# Optional environment preflight

Used **only** when `/opsx-static-check` is invoked with token `PREFLIGHT`.
Default check runs **skip** this file entirely.

**Budget: &lt; 1s.** File/PATH existence only.

If any probe fails → **STOP** (`STATUS=BLOCKED`). Do not launch workers. Do not edit files.

## Allowed probes

From repo root, filesystem only:

1. `pyproject.toml`
2. `pyrightconfig_strict.json`
3. `mypy.ini`
4. `.venv/Scripts/python.exe` (Win) / `.venv/bin/python`
5. `.venv/Scripts/pyright.exe` / `.venv/bin/pyright`
6. `.venv/Scripts/mypy.exe` / `.venv/bin/mypy`
7. `.venv/Scripts/pytest.exe` / `.venv/bin/pytest`
8. `.venv/Scripts/poetry.exe` or `poetry.exe` on PATH (file existence; do not run poetry)
9. `.cursor/static-check/bin/run.sh` exists

## Forbidden

- `poetry install` / version storms / bash activation
- any pyright/mypy/pytest execution
- editing repository files to “fix” probes

## STOP output

```text
STATUS: BLOCKED
PREFLIGHT: failed
Problem: ...
Cause: ...
Action: ...
NEXT ACTION: <human fix; this command must not patch infra>
```

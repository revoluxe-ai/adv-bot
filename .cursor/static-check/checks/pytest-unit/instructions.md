# pytest-unit — instructions

From repo root (full unit suite — pytest-xdist):

```bash
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit -n 8 --dist=worksteal
```

Packet COMMAND: `poetry run pytest -m unit -n 8 --dist=worksteal`

If unavailable → STATUS=BLOCKED.
Do not run pyright, mypy, or `pytest .`.
Do not drop `-n` / `--dist` for this check (full suite).

## Parsing

Prefer failed node ids (`path::node`).
Collection problems → severity `collection-error`.
Exit 0 → PASS. Non-zero with failures → FAIL.

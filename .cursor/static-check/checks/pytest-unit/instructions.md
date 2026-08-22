# pytest-unit — instructions

From repo root:

```bash
bash .cursor/static-check/bin/run.sh -- poetry run pytest -m unit
```

Packet COMMAND: `poetry run pytest -m unit`

If unavailable → STATUS=BLOCKED.
Do not run pyright, mypy, or `pytest .`.

## Parsing

Prefer failed node ids (`path::node`).
Collection problems → severity `collection-error`.
Exit 0 → PASS. Non-zero with failures → FAIL.

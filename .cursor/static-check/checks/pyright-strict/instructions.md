# pyright-strict — instructions

From repo root:

```bash
bash .cursor/static-check/bin/run.sh -- pyright-strict
```

Packet COMMAND: `pyright-strict`

If exit 127 / missing → `STATUS=BLOCKED` (no undeclared fallback).
Do not run mypy or pytest.

## Parsing

Extract path / symbol / code / message when present.
Exit 0 → PASS. Non-zero with typing diagnostics → FAIL.

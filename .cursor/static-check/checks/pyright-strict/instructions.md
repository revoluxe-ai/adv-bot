# pyright-strict — instructions

From repo root:

```bash
bash .cursor/static-check/bin/run.sh -- pyright-strict
```

Packet COMMAND: `pyright-strict`

If exit 127 / missing → `STATUS=BLOCKED` (no undeclared fallback).
Do not run mypy or pytest.

## Parsing

Typical: `path:line:col - error: message (code)`.
Extract filepath, **line** (required FINDINGS field), symbol / code / message
when present. Set `line: n/a` only if the diagnostic has no source line.
Exit 0 → PASS. Non-zero with typing diagnostics → FAIL.

# mypy — instructions

From repo root:

```bash
bash .cursor/static-check/bin/run.sh -- mypy .
```

Packet COMMAND: `mypy .`

If missing → `STATUS=BLOCKED`.
Do not run pyright or pytest.

## Parsing

Typical: `path:line: error: message  [code]`.
Extract filepath, **line** (required FINDINGS field), code / message when
present. Set `line: n/a` only if the diagnostic has no source line.
Exit 0 → PASS. Non-zero with typing diagnostics → FAIL.

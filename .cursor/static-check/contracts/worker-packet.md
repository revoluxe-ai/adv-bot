# Worker packet contract

Final answer of every static-check agent must be exactly:

```text
CHECK_ID: <id>
COMMAND: <exact command run>
EXIT_CODE: <int|n/a>
STATUS: PASS | FAIL | BLOCKED | ERROR
FINDINGS_TOTAL: <int>
FINDINGS_TRUNCATED: yes|no
FINDINGS:
- filepath: <path|n/a>
  line: <int|n/a>
  symbol_or_node: <name|node id|n/a>
  code: <code|n/a>
  message: <short>
  severity: typing | test-failure | collection-error | config | environment | other
RAW_TAIL:
<up to 40 lines>
ERROR: <n/a or short reason>
```

`line` is required on every finding: source line from the diagnostic when
present (mypy `path:line:`, pyright `file:line:col`); else `n/a` (e.g. env /
collection / pytest node without a file line).

STATUS rules:

- PASS — exit 0, no blocking diagnostics
- FAIL — tool ran; diagnostics/failures present
- BLOCKED — cannot run (missing poetry/config/script)
- ERROR — unexpected crash / invalid execution

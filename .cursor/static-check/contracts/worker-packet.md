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
  symbol_or_node: <name|node id|n/a>
  code: <code|n/a>
  message: <short>
  severity: typing | test-failure | collection-error | config | environment | other
RAW_TAIL:
<up to 40 lines>
ERROR: <n/a or short reason>
```

STATUS rules:

- PASS — exit 0, no blocking diagnostics
- FAIL — tool ran; diagnostics/failures present
- BLOCKED — cannot run (missing poetry/config/script)
- ERROR — unexpected crash / invalid execution

## Destructive cache extras (`CHECK_ID=pytest-full` or destructive in plan)

When the check planned any `@pytest.mark.destructive_local` node, append
after `ERROR:` (required — omit only if destructive not in plan):

```text
CACHE_MODE: off|dev|force
DESTRUCTIVE_TOTAL: <int>
DESTRUCTIVE_RAN: <int>
DESTRUCTIVE_CACHED: <int>
DESTRUCTIVE_FORCED: <int>
CACHE_DEGRADED: yes|no
```

INTERIM (planner missing): `CACHE_DEGRADED=yes`, `DESTRUCTIVE_CACHED=0`,
`DESTRUCTIVE_RAN=DESTRUCTIVE_TOTAL`. Never claim cached skips without planner.

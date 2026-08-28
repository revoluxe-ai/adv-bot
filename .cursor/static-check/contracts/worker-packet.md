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

- PASS — exit 0, no blocking diagnostics; also pytest-targeted bucket N/A
  (empty after prefilter / exit 5 no failed nodes) with NOTES such as
  `bucket_empty_skipped:<unit|integration>` or
  `bucket_empty_collection:<unit|integration>` / `not_applicable_no_related_tests`
- FAIL — tool ran; diagnostics/failures present (not empty-collection exit 5)
- BLOCKED — cannot run (missing poetry/config/script)
- ERROR — unexpected crash / invalid execution

Optional NOTES line (when used by a pack): short tokens only; do not replace
STATUS.
Recommended tokens:
- `UNIT_RECOVERY_PATH=none|xdist_retry|fallback_non_xdist` (pytest-unit)
- `bucket_empty_skipped:<unit|integration>` / `bucket_empty_collection:<unit|integration>`
- `not_applicable_no_related_tests`

For pytest-unit infra ladders:
- first xdist worker-death without failed nodes => `STATUS: ERROR` +
  `ERROR: infra_suite` (before retry/fallback handling),
- fallback non-xdist infra crash without failed nodes =>
  `STATUS: ERROR` + `ERROR: infra_suite_hard`.

Orchestrator Final vs this packet:

- Each check still returns the packet shape above (`CHECK_ID` / `STATUS` / …).
- The **command Final report** (user-visible completion) is separate and must
  start with `STATUS: PASS|FAIL|BLOCKED|ERROR` plus `CHECKS` (see
  `opsx-static-check.md` §5).
- Progress-only orchestrator text («Wave A in flight», «waiting for packets»,
  «cascade continues», or equivalent without that Final block) is an
  **incomplete run**. Supervisor / owner envelopes MUST set
  `REPORTED_STATUS=INCOMPLETE_RUN` (not success-shaped PASS/FAIL) when only
  progress was emitted.- PASS — exit 0, no blocking diagnostics
- FAIL — tool ran; diagnostics/failures present
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
INTERIM (planner missing): `CACHE_DEGRADED=yes`, `DESTRUCTIVE_CACHED=0`,
`DESTRUCTIVE_RAN=DESTRUCTIVE_TOTAL`. Never claim cached skips without planner.
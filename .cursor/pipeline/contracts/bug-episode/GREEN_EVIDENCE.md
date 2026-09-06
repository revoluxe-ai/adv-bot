# GREEN_EVIDENCE schema

Policy SoT: `.cursor/pipeline/ORCHESTRATION_MVP.md` §2.3–2.4.

## Durable path

```text
.opsx/runs/bug-cases/<CASE_ID>/results/GREEN-<FINDING_ID>.md
```

## Required fields

```text
TEST_ID                 # must equal RED TEST_ID
BUG_CASE_ID
FINDING_ID
COMMAND
PRODUCTION_HASH_AFTER   # ≠ PRODUCTION_HASH_BEFORE unless exception path
TEST_CONTENT_SHA256     # must match RED, or justified NON_WEAKEN_DELTA
STATUS: GREEN_CONFIRMED | GREEN_BLOCKED_PENDING_TEST_DELTA_REVIEW
TARGETED_REGRESSIONS: …
NON_WEAKEN_DELTA:       # optional; Owner-approved only
```

## Writer authority

```text
GREEN_WRITER: /opsx-test verify mode
```

- `/opsx-fix-bug` may re-run the same `TEST_ID` as an extra check only.
- `/opsx-fix-bug` MUST NOT edit tests.
- `/opsx-fix-bug` MUST NOT self-approve `NON_WEAKEN_DELTA` (Owner only).

## Anti-weaken

- GREEN must reuse the same `TEST_ID`.
- `TEST_CONTENT_SHA256` must match RED, **or** a recorded `NON_WEAKEN_DELTA`
  must explain every assertion/fixture change and must not remove or soften
  the failing expectation that proved the bug.
- Unexplained test content delta ⇒
  `GREEN_BLOCKED_PENDING_TEST_DELTA_REVIEW` (not `GREEN_CONFIRMED`).

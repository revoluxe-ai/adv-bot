# RED_EVIDENCE schema

Policy SoT: `.cursor/pipeline/ORCHESTRATION_MVP.md` §2.2.

## Durable path

```text
.tmp/opsx-bug-cases/<CASE_ID>/results/RED-<FINDING_ID>.md
```

## Required fields

```text
TEST_ID
BUG_CASE_ID
FINDING_ID
COMMAND
EXPECTED_FAILURE
ACTUAL_FAILURE
FAILURE_MATCH: YES | NO
PRODUCTION_HASH_BEFORE
TEST_CONTENT_SHA256
STATUS:
  RED_CONFIRMED
  | TEST_NOT_REPRODUCING
  | RED_WRONG_REASON
  | TEST_SETUP_DEFECT
  | BUG_NOT_TESTABLE
  | BLOCKED
  | TIMEOUT
```

## Rules

```text
TEST_ID = <repo-relative-path>::<pytest-nodeid>
```

- `STATUS=RED_CONFIRMED` requires `FAILURE_MATCH: YES` and a failing run on
  **unchanged** production (`PRODUCTION_HASH_BEFORE` recorded).
- Producer: `/opsx-test` bug-regression mode (`case=` + `finding=`).
- Production changes are forbidden while producing RED.

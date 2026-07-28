# /opsx-bug-team Candidate status

```text
COMMAND: /opsx-bug-team
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
RUNTIME_ENFORCEMENT: NOT_ACTIVE
READY_FOR_PRODUCTION: FORBIDDEN
GO_ACTIVATE: NOT_ISSUED
```

## Authority

This package is a **Candidate** only.

- Independent Reviewer has not passed.
- Independent Tester has not issued PASS.
- Owner has not issued activation.
- Live OPSX bug-episode policy remains
  `.cursor/pipeline/ORCHESTRATION_MVP.md` (LIVE_ACTIVATED).
- This candidate must **not** be treated as a replacement for live
  slash commands until Owner activation.

## Forbidden status tokens

Do not write any of the following into this package while Candidate:

```text
ACTIVE
READY_FOR_PRODUCTION
LIVE_ACTIVATED
RUNTIME_ENFORCEMENT: ACTIVE
GO_ACTIVATE: ISSUED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
```

Builder-local controlled-test runs are **not** Independent Tester PASS.

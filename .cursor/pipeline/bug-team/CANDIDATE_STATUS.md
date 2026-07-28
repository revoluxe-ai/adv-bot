# /opsx-bug-team status (Owner-activated)

```text
COMMAND: /opsx-bug-team
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: ACTIVE
OWNER_ACTIVATION: ISSUED
RUNTIME_ENFORCEMENT: ACTIVE
GO_ACTIVATE: ISSUED
ACTIVATION_MODE: CONTROLLED_LIVE_UNCOMMITTED
CONTROL_MODEL: USER_REVIEWS_UNCOMMITTED_WORKTREE
LOCAL_WORKTREE_WRITES: ALLOWED_AFTER_VALID_RED
INTERMEDIATE_OWNER_PRODUCTION_GATE: NOT_REQUIRED
INTERMEDIATE_OWNER_CLOSURE_GATE: NOT_REQUIRED
COMMIT_AUTHORITY: USER_ONLY
GIT_COMMIT: FORBIDDEN
GIT_PUSH: FORBIDDEN
DEPLOY: FORBIDDEN
EXTERNAL_PRODUCTION_MUTATIONS: FORBIDDEN
ACTIVATION_ARTIFACT: .cursor/pipeline/bug-team/ACTIVATION.json
BOUND_HEAD: d8bc67f67a896845d42a642e00aaee9405a5fc48
INDEPENDENT_TEST_VERDICT: INDEPENDENT_CONTROL_MODEL_TEST_PASS
VERDICT: .tmp/opsx-bug-team-harness/independent-control-model-v7/20260728T093944Z/verdict/VERDICT.json
UPDATED_AT_UTC: 2026-07-28T10:11:02Z
```

## Authority

Owner issued activation for `/opsx-bug-team` in
`CONTROLLED_LIVE_UNCOMMITTED` mode after Independent Control-Model Test V7 PASS.

- Local worktree writes allowed after valid RED (no intermediate Owner production GO).
- Auto closure when fan-in READY_FOR_CLOSURE (no intermediate Owner closure GO).
- Git commit / push / deploy / external production mutations remain forbidden.
- User reviews the final uncommitted diff and decides whether to commit.

## Activation binding

Bound to HEAD `d8bc67f67a896845d42a642e00aaee9405a5fc48`, candidate file hashes from independent evidence
`.tmp/opsx-bug-team-harness/independent-control-model-v7/20260728T093944Z/hashes/before.txt`, and
`TEST_VERDICT=INDEPENDENT_CONTROL_MODEL_TEST_PASS`.

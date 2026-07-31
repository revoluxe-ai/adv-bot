# /opsx-bug-team status (Owner-activated)

```text
COMMAND: /opsx-bug-team
DEFAULT_FULL_BUG_ENTRY: /opsx-bug-team
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: ACTIVE
OWNER_ACTIVATION: ISSUED
RUNTIME_ENFORCEMENT: ACTIVE
GO_ACTIVATE: ISSUED
ACTIVATION_MODE: CONTROLLED_LIVE_UNCOMMITTED
PIPELINE_GENERATION: ACTIVE_V1_WITH_INVARIANT_FANOUT_V10
CONTROL_MODEL: USER_REVIEWS_UNCOMMITTED_WORKTREE
LOCAL_WORKTREE_WRITES: ALLOWED_WITHIN_VALIDATED_WORKER_BOUNDARIES
INTERMEDIATE_OWNER_PRODUCTION_GATE: NOT_REQUIRED
INTERMEDIATE_OWNER_CLOSURE_GATE: NOT_REQUIRED
COMMIT_AUTHORITY: OWNER_ONLY
GIT_COMMIT: FORBIDDEN
GIT_PUSH: FORBIDDEN
DEPLOY: FORBIDDEN
EXTERNAL_PRODUCTION_MUTATIONS: FORBIDDEN
BUG_FAMILY_FANOUT_ENABLED: true
BUG_FAMILY_FANOUT_STATUS: ACTIVE
SAME_INVARIANT_HUNT_FINDINGS: AUTOMATIC_FANOUT
MANUAL_SIBLING_RELAUNCH_REQUIRED: NO
EXECUTION_IDENTITY_GATE: ACTIVE
FINAL_CONTROL: OWNER_REVIEWS_UNCOMMITTED_GIT_DIFF
FAMILY_FANOUT_POLICY: .cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json
ACTIVATION_ARTIFACT: .cursor/pipeline/bug-team/ACTIVATION.json
ACTIVATION_RECEIPT: .cursor/pipeline/bug-team/INVARIANT_FAMILY_FANOUT_ACTIVATION_RECEIPT.json
BOUND_HEAD: fb009fd6645ee3b20774f670504cad4eeb4bbc75
INDEPENDENT_TEST_VERDICT: INDEPENDENT_EXECUTION_IDENTITY_TARGETED_RERUN_PASS
VERDICT: .tmp/opsx-bug-team-harness/independent-execution-identity-targeted-rerun/20260728T221214Z/verdict/VERDICT.json
UPDATED_AT_UTC: 2026-07-28T22:27:18Z
COMMAND_NATIVE_SINGLE_SOURCE_OF_TRUTH: PLANNED_SEPARATELY
```

## Authority

Owner issued `ACTIVATE_INVARIANT_FAMILY_FANOUT` for `/opsx-bug-team` after
Independent Execution-Identity Targeted Rerun PASS.

- Root-bug ACTIVE_V1 behavior remains enabled (not replaced by command-native v2).
- After root GREEN: invariant capture → bounded hunt → relation classify →
  automatic same-invariant fanout → branch RED/FIX/GREEN → integration →
  family GREEN → family fan-in → learning → family closure → HUMAN_SUMMARY.
- Manual sibling relaunch (e.g. separate PBH-007 launch) is **not** required
  for same-invariant findings.
- Local worktree writes allowed within validated worker boundaries.
- Git commit / push / deploy / external production mutations remain forbidden.
- Owner reviews the final uncommitted diff and decides whether to commit.

## Activation binding

Bound to HEAD `fb009fd6645ee3b20774f670504cad4eeb4bbc75`, candidate hashes frozen
in `INVARIANT_FAMILY_FANOUT_ACTIVATION_RECEIPT.json`, controlling evidence
`.tmp/opsx-bug-team-harness/independent-execution-identity-targeted-rerun/20260728T221214Z`,
`TEST_VERDICT=INDEPENDENT_EXECUTION_IDENTITY_TARGETED_RERUN_PASS`.

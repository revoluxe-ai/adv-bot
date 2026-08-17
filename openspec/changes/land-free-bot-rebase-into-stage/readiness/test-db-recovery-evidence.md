# Test-DB recovery evidence

Change: `land-free-bot-rebase-into-stage`  
Candidate SHA: `1ac5a053aaeb444f30524536de6a8d4223113a95`

## Recovery route

The local test-DB contract uses a forward compensating action for an
interrupted transition. The retry is idempotent: rows already classified by
`bot_active` are not assigned an incompatible value, and the final
invariant reports zero incompatible residue.

Evidence:

- `tests/migrations/test_auto_update_minus_phrases_backfill.py::test_retry_after_interrupted_constraint_transition_is_idempotent`
- `tests/integration/migrations/test_auto_update_minus_phrases_backfill_live_pg.py::test_live_backfill_classifies_paid_state_and_retries_idempotently`
- `tests/unit/test_release_readiness.py::test_test_db_forward_recovery_evidence_is_fail_closed`
- `tests/unit/test_release_readiness.py::test_destructive_downgrade_cannot_be_recovery_evidence`

## Result

`PASS` for the disposable live test-DB classifier/retry path and the local
forward-recovery contract. No destructive production downgrade is used or
authorized by this change.

This is test-DB recovery evidence only. It does not provide a stage or
production migration receipt; those later release states remain separate
`NO_GO` gates until the approved write-path supplies receipts.

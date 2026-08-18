# Readiness package

Change: `land-free-bot-rebase-into-stage`  
Status: `GO` (merge readiness only; owner rollout deferred)
Base ref: `origin/stage`  
Base SHA: `d4b7fa385526a4f7831d6108c3cda82532dcfabd`  
Candidate commit SHA: `4cfd61209a065c6105c5f12e44f7b1771fba69c4`
Candidate state: scoped landing files are committed at the final candidate;
unrelated pre-existing worktree state remains excluded from this evidence
package.

## Scope

The implementation scope is limited to the migration schema step, the approved
Job backfill path, merge-readiness evaluator, runtime fallback regression and
their tests. Unrelated pre-existing worktree state is excluded. Image build,
Harbor upload, deployment restart, pod startup, stage/prod smoke and
post-deploy verification are owner-owned operational work after merge.

## Evidence

- Provenance: `readiness/provenance.md`
- Test-DB recovery: `readiness/test-db-recovery-evidence.md`
- Existing-client compatibility: `readiness/compatibility-baseline-evidence.md`
- Route: `rewrite-before-landing`
- Migration graph: `poetry run alembic heads` → one head `8c541a39b7e2`
- Focused migration/data tests: PASS
- Full unit suite: `3629 passed, 31 skipped`
- Strict Pyright: PASS (`0 errors`)
- OpenSpec strict validation: PASS
- Test-DB affected-record preview and classifier retry: PASS on disposable
  `TEST_DATABASE_URL` using a transaction-local `advsetting` table
- Test-DB recovery evidence: PASS for forward compensating retry contract
- Merge-readiness receipt: PASS for candidate SHA above
- Stage schema/backfill/UI/smoke receipt: DEFERRED to owner after merge
- Database application receipt: DEFERRED to owner operational flow
- Production migration/deployment receipt: DEFERRED to owner operational flow
- Production compatibility verification: OUT OF SCOPE for this change
- Final compatibility review: local/test-DB contract PASS; post-deploy review
  belongs to owner-owned operational flow

## Final verdict

`GO` for safe merge into the declared target branch derived from `stage`.
This package does not claim image build, Harbor upload, deployment restart, pod
startup, stage/prod smoke or post-deploy compatibility. Those actions remain
Owner-owned after merge and require their own operational evidence; no
production action is authorized by this local merge-readiness package.

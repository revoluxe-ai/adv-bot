# Existing-client compatibility baseline evidence

Change: `land-free-bot-rebase-into-stage`  
Candidate SHA: `a1291c7c00a846bd25f66be40954a7c2adf110c2`

## Evidence model

Readiness stores paid and free cohort baselines separately. Each cohort
captures effective automation flags, billing state, WB write activity and
campaign lifecycle. A baseline from another candidate SHA is invalid and
cannot satisfy the final compatibility gate.

The executable contract is covered by:

- `tests/unit/test_release_readiness.py::test_paid_and_free_compatibility_baselines_are_compared_separately`
- `tests/unit/test_release_readiness.py::test_compatibility_drift_requires_explicit_product_approval`
- `tests/unit/test_release_readiness.py::test_final_compatibility_requires_same_candidate_snapshot`

## Final local review

`PASS` for the fail-closed comparison contract: unexplained drift produces
`NO_GO`, and intentional drift requires an accepted product decision.

`NO_GO` for release completion: this local package does not contain a
stage/production representative-client receipt. The release operator must
attach paid and free before/after observations for the same candidate SHA
before advancing beyond readiness.

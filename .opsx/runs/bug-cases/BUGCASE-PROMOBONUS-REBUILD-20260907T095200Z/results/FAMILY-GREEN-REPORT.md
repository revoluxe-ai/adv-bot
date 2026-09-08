# FAMILY-GREEN-REPORT

```text
ROOT_GREEN: PASS
ALL_BLOCKING_BRANCH_GREENS: PASS
PATCH_INTEGRATION: PASS
FAMILY_INVARIANT_TEST: PASS
RELEVANT_REGRESSION_TESTS: PASS
FAMILY_GREEN_STATUS: PASS
```

## Family invariant pytest

```text
COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py -q --tb=line
OK: true
RETURNCODE: 0
RESULT: 6 passed, 1 warning in 0.31s
```

## FINDING-004 frozen node (root)

- TEST_ID: `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired`
- STATUS: PASSED (included in the 6-passed file run)
- GREEN: `results/GREEN-FINDING-004.md` GREEN_CONFIRMED
- Expectation remains remaining==150 (expired leftover 300 + live leftover 200 + spend 50)

## Sibling HC-FINDING-004-STALE-TEST

- TEST_ID: `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable`
- STATUS: PASSED (included in the 6-passed file run)
- GREEN: `results/GREEN-HC-FINDING-004-STALE-TEST.md` GREEN_CONFIRMED
- Assertion updated 200 -> 150 plus docstring; spend must hit live leftover, not expired leftover

## Integration

- BRANCH_STATUS: INTEGRATED
- INTEGRATION_STATUS: PASS
- IN_PLACE_MAIN_WORKTREE: true
- integrate_branch_patches: not called
- PRODUCTION_UNCHANGED: true (`app/shared/domains/wb/utils/promo_accounting.py` sha256 `4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b`)
- family/closed/ROOT-001 and family/closed/FINDING-002: not overwritten

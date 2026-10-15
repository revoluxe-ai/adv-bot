---
cursor:
  subagentId: "bc-32bdaafb-bc6f-532c-901a-2eb4845c2b03"
---

# SEPARATE_AUTO_SEARCH_CPO_LIFECYCLE_REPORT

Feature reconciled onto current `origin/stage` and pushed. Live ClickHouse seam passes on a cloud-owned disposable container. Merge into `stage` is not done: `poetry run pyright-strict` exits 1 with 19 errors, all in `ai_package_v1`, identical class to the stage baseline. Those files are outside this change.

```text
BASELINE_STAGE: 23c0671f372f0435b13a3573ec8990b4303b3e4a
CURRENT_STAGE: 1443649281543bc00411d9940a047037ed6d3ffd
FEATURE_CHECKPOINT: 784f468becfffcba5118592348adf914dc994d73
RECONCILED_FEATURE_HEAD: 9b97462b16120c6b900b9e57b93bda515b33787c

RECONCILIATION: PASS

SEMANTIC_CONFLICTS: none
MECHANICAL_CONFLICTS: pyrightconfig_strict.json union (stage includes kept + leg-CPO entries); manager.py auto-merge (shop-wide + 3 attach_leg_cpo)

TESTS: PASS — targeted unit 442 passed on first reconciled HEAD; seed + economics unit 10 passed after seam fix; destructive_lifecycle unit included
PYRIGHT: FAIL — exit 1, 19 errors, all ai_package_v1; FEATURE_OWNED_ERRORS none; same baseline as origin/stage
OPENSPEC: PASS — npx openspec validate separate-auto-search-cpo --strict exit 0
SCENARIO_COVERAGE: CH boundary LEG-CPO-001 executed 10/10 on owned CH; formal audit.receipt.json not written; certify not run

CLICKHOUSE_PROVIDER_ENV: owned containers leg-cpo-ch-proof-rerun :8124 and leg-cpo-pg-proof-rerun :5433; ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1; ALLOW_DESTRUCTIVE_TEST_DB=1; database test_adv_bot_clickhouse; containers removed after the run
CLICKHOUSE_PROVIDER_EXECUTION: PASS

OPSX_VERIFY: NOT_RUN
MERGE_REVIEW: NOT_RUN

MERGE: NOT_DONE

POST_MERGE_VERIFY: NOT_RUN
ARCHIVE: NOT_DONE
CLEANUP: NOT_DONE

STAGE_AFTER: 1443649281543bc00411d9940a047037ed6d3ffd

PRODUCTION_WRITES: NONE

FINAL_STATUS: VERIFY_FAILED
```

Remote feature branch: `origin/separate-auto-search-cpo` at `9b97462b16120c6b900b9e57b93bda515b33787c`. `origin/stage` is an ancestor of that HEAD. No force-push.

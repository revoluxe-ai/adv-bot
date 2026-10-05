# SHOP_WIDE_COMMON_SALES_LIFECYCLE_REPORT

```text
CHANGE: shop-wide-common-sales-collection
HOME_PC_ACCESS: ONLINE
FEATURE_PREMERGE_STATE: UNCHANGED
FEATURE_COMMIT: 3afdde673e667cc725131cab7f463db7e2b34b66
FEATURE_TIP_MERGED: 2ccff6321700499c22cbc1a1f5b5541cb8683fef
FINAL_MERGE_REVIEW: PASS
STAGE_PRE_MERGE_HEAD: 37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0
STAGE_DIRTY_OVERLAP: NO
MERGE_METHOD: local git merge --no-ff
STAGE_POST_MERGE_HEAD: 58441b3589200e02f642628e05920e680e553355
FEATURE_IS_ANCESTOR_OF_STAGE: YES
POST_MERGE_TESTS: 76 PASS (74 unit + 2 isolated ClickHouse integration)
POST_MERGE_PYRIGHT: committed merged stage 755 files / 0 errors / 0 warnings; actual dirty stage 4 baseline errors / 0 new diagnostics
POST_MERGE_OPENSPEC: PASS
POST_MERGE_VERIFY: PASS (CHANGE_SCOPED)
OPENSPEC_ARCHIVE_STATUS: DONE
ARCHIVE_COMMIT: 50b4314618591bd9f3b92b33251753baa11d4fca
WORKTREE_REMOVED: YES
FEATURE_BRANCH_REMOVED: YES
UNRELATED_STAGE_CHANGES_PRESERVED: YES (92/92 paths, statuses and hashes unchanged)
DEPLOY_PERFORMED: NO
PRODUCTION_WRITES_PERFORMED: NO
PUSH_PERFORMED: NO
FINAL_STATUS: MERGED_AND_CLEANED
NEXT_ACTION: No action required for this local lifecycle.
```

The runtime remained identical to the certified implementation: final guard verified all 15 source/test/config SHA256 values. Documentation consistency and formatting were fixed in separate commits. The historical scenario certificate (33/33), spec/plan/report bindings, raw execution logs and independent receipts remain preserved.

## Archive and canonical artifacts

- Archive: `openspec/changes/archive/2026-10-05-shop-wide-common-sales-collection/`
- Synced main spec: `openspec/specs/shop-wide-common-sales-collection/spec.md`
- Promoted accepted decision: `openspec/decisions/shop-wide-common-sales-ownership/decision.md`
- Independent archive GO: `VERIFY_ARCHIVE_RECEIPT.md` (0480/0481, Product Acceptance PASS).
- Archive command: `poetry run openspec archive shop-wide-common-sales-collection -y`, with normal validation/spec sync.

## Quality scope

All 76 targeted tests passed on the actual merged main checkout. Actual dirty stage retains four pyright errors in the unrelated `campaigns_info_v2/adapter.py`. The pre-merge snapshot with the same preserved dirty files has exactly the same diagnostics; no new diagnostic was introduced. A Git archive of committed merged stage, using the same ready environment, passed the canonical strict gate with 755 files and zero errors/warnings.

The full repository test suite and production readiness are not claimed. Financial currency remains unknown; Store DRR numerator remains blocked by campaign coverage; history beyond seven days remains deferred.

## Cleanup incident and repair

The initial cleanup report committed as `8938428d2c05d3fcfa86024ed88729f125026ebe` prematurely marked completion while an empty directory remained. Git traversed the feature `.venv` junction and removed the campaign environment. This was an unintended cleanup error.

The campaign environment was restored as a separate physical virtualenv from the ready main environment, without network downloads. All 228 main-environment package/version records are present; imports and pytest launch passed; 63 console scripts were regenerated, and the editable project path points to the campaign checkout. Exact identity with the deleted original environment is not claimed.

The orphan directory was held by a completed runner-owned PowerShell/Poetry/`check_openspec.py` process chain. Only those confirmed processes were stopped. Once Git registration had already been removed and the directory was verified empty, the directory was removed normally. No force branch deletion or manual deletion before Git cleanup was used.

Final guard at `2026-10-05T02:51:15.174794+00:00` verified both filesystem and Git absence, both feature commits as ancestors of stage, all required archive artifacts, unchanged certified bindings, an empty index, all 92 foreign dirty records, and working main/campaign Python executables. The task-owned test ClickHouse container was stopped; no shared service was stopped.

Repair evidence: `CLEANUP_REPAIR_RECEIPT.md`, `lifecycle-proof/cleanup-repair.json`, `lifecycle-proof/final-guard.json`.

This report replaces the premature completion wording while preserving its original Git history.

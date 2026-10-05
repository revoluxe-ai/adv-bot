# CLEANUP_REPAIR_RECEIPT

CHANGE_ID: shop-wide-common-sales-collection
FINAL_STATUS: MERGED_AND_CLEANED

The initial Git worktree cleanup traversed the feature virtualenv junction, removed the campaign virtualenv contents, and left an empty directory locked by an old SDK process chain. The original report's completion claim was premature.

## Environment repair

The existing ready main environment was used as an offline recovery source. A physical campaign virtualenv was recreated with the same local Python base, installed packages copied, editable project path corrected to the campaign checkout, and 63 console scripts regenerated. All 228 source package/version records are present; pip/setuptools seed records add two records. Imports and pytest launch passed. No dependency resolution or network download was used. The original environment's exact bytes/versions were not inventoried before deletion, so exact original identity is not claimed.

Actual recovery log: `lifecycle-proof/cleanup-repair.json`. That log records the first orphan-removal failure. The later final guard supersedes that orphan result.

## Orphan directory cleanup

A read-only process current-directory probe identified PowerShell PID 26076 as a runner-owned SDK command. Its Poetry child PID 12008 and Python child PID 14012 were executing `check_openspec.py` in the removed feature path. Executable, command markers and exact parent-child identities were checked. Only that completed command chain was stopped; the parent SDK bridge and user applications were not stopped.

Git worktree registration had already been removed by the non-force `git worktree remove` attempt. After confirming absence from Git and an empty filesystem directory, the remaining directory was removed normally. Feature branch deletion used `git branch -d`; force deletion was not used.

## Final verification

`lifecycle-proof/final-guard.json` records:
- 92 foreign paths/statuses/hashes preserved, no unexpected dirty paths.
- All 15 certified source/test/config SHA256 values unchanged.
- Both feature commits are ancestors of stage.
- Feature branch, Git worktree registration and filesystem directory absent.
- Required archive artifacts and historical spec/plan/report hash bindings preserved.
- Independent archive receipt ends with the required GO marker.
- Main and repaired campaign Python executables exist.
- Empty Git index and passing plain diff check.

The task-owned ClickHouse container `wb-sky-common-sales-lifecycle-20261005-0470` was ownership-label checked and stopped after testing. Its automatic removal was enabled. No shared service was stopped.

No deployment, push, live WB call, production ClickHouse write or production DDL was performed.

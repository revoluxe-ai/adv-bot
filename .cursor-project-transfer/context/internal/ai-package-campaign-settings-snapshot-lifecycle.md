---
cursor:
  subagentId: "bc-f8fe0236-d51b-5c44-8a89-06a71f0fcc73"
---

# AI_PACKAGE_CAMPAIGN_SETTINGS_SNAPSHOT_LIFECYCLE_REPORT

No archive commit, verify gate, worktree remove, or branch delete ran. The Owner checkout is not mounted on this Cloud Agent VM. Production writes were not attempted. Product implementation was not edited.

Sibling pattern: `/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/internal/campaign-settings-history-lifecycle.md`

## Host proof

| Check | Result |
|---|---|
| This process hostname | `cursor` (Linux) |
| Cloud `stage` HEAD | `4763b0a1602d00da285739f2be9af5a553ef3c0a` (`origin/stage`) |
| Hint stage `0b05f8dbd28d08d2c8a160e48ddc4a43c450cd18` | object absent in this clone |
| Hint feature `e5e3a7126fc496ec2ff55a3ac74205837b55a7c8` | object absent in this clone |
| `C:\Users\vkita\my_code\meta-repo\adv-bot` | not on this VM |
| Connected worker | `vkita-pc` `71b3661e-2ad7-4234-a792-7c39a22963a4`, `eligibleForSubagent: true`, idle |
| Task spawn | [Close snapshot archive locally](bc-734a3a5e-8ccf-534c-ba25-88e44f6232fd) received `workerId` and still ran on hostname `cursor` |

`workerId` is not in the Task tool schema. Passing it did not place the shell on HOME-PC. A cloud commit against `origin/stage` would not see the unpushed local archive delta and is forbidden.

## Report

```text
FEATURE_HEAD:
e5e3a7126fc496ec2ff55a3ac74205837b55a7c8
(hint from Owner live snapshot; NOT re-verified on disk)

STAGE_PRE_CLOSURE_HEAD:
0b05f8dbd28d08d2c8a160e48ddc4a43c450cd18
(hint; NOT re-verified. Cloud origin/stage is 4763b0a1602d00da285739f2be9af5a553ef3c0a and was not used)

FEATURE_ANCESTOR_OF_STAGE:
NOT_RUN

IMPLEMENTATION_MERGED:
NOT_RUN

ARCHIVE_MATERIALIZED:
NOT_RUN

ARCHIVE_PROVENANCE:
NOT_RUN

DECISIONS_INDEX_OWNERSHIP:
UNKNOWN

TESTS:
NOT_RUN

RUFF:
NOT_RUN

PYRIGHT:
NOT_RUN

OPENSPEC:
NOT_RUN

OPSX_ARCHIVE_VERIFY:
NOT_RUN

ARCHIVE_COMMIT:
NONE

STAGE_POST_CLOSURE_HEAD:
UNCHANGED

ACTIVE_CHANGE_REMOVED:
NOT_RUN

ARCHIVE_TRACKED:
NOT_RUN

WORKTREE_REMOVED:
NO

BRANCH_REMOVED:
NO

UNRELATED_DIRTY_STATE_PRESERVED:
YES

PRODUCTION_WRITES:
NONE

FINAL_STATUS:
CLEANUP_BLOCKED
```

`CLEANUP_BLOCKED` is the closest allowed status. The real stop is host placement: archive provenance, gates, and the scoped commit did not start. Do not treat hint SHAs as proof.

## Next local action

Run the continuation in local Cursor on HOME-PC with workspace `C:\Users\vkita\my_code\meta-repo\adv-bot`. Do not start it again from a Cloud Agent VM. Do not push.

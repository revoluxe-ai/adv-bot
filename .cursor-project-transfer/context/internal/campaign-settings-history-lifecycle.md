---
cursor:
  subagentId: "bc-b57d1959-8648-59bf-ac96-9f0648e3ed08"
---

# CAMPAIGN_SETTINGS_HISTORY_LIFECYCLE_REPORT

`LOCAL_AGENT_ROUTING_FAILED`. The change was not continued on the Cloud VM. No git writes. Production writes: none.

`FINAL_STATUS` below stays `BLOCKED` only as the prior template. The blocker is routing to `vkita-pc`, not the change itself.

Sibling report: `/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/internal/campaign-settings-history-reconciliation.md`

```text
CHANGE:
campaign-settings-history

FEATURE_HEAD:
UNKNOWN

STAGE_PRE_MERGE_HEAD:
UNKNOWN on the Owner disk.
Cloud snapshot stage (not used for merge): 4763b0a1602d00da285739f2be9af5a553ef3c0a

FIELD_REGISTRY:
UNKNOWN

EXCEL_EXPORT:
UNKNOWN

EXCEL_IMPORT:
UNKNOWN

EXCEL_PARITY:
UNKNOWN

HISTORY_BEFORE_AFTER:
UNKNOWN

REASON_INTENT:
UNKNOWN

PG_HISTORY:
UNKNOWN

CLICKHOUSE_HISTORY:
UNKNOWN

MIGRATION:
UNKNOWN

MIGRATION_COLLISION_RESOLUTION:
NOT_EVALUATED

SCENARIO_COVERAGE:
UNKNOWN

PYTEST:
NOT_RUN

RUFF:
NOT_RUN

PYRIGHT:
NOT_RUN

OPENSPEC:
NOT_RUN

OPSX_VERIFY:
NOT_RUN

FINAL_MERGE_REVIEW:
NOT_RUN

MERGE_COMMIT:
NONE

STAGE_POST_MERGE_HEAD:
UNCHANGED

POST_MERGE_VERIFY:
NOT_RUN

ARCHIVE_STATUS:
NOT_RUN

WORKTREE_REMOVED:
NO

BRANCH_REMOVED:
NO

UNRELATED_STAGE_CHANGES_PRESERVED:
YES — this hop made no git writes. Owner dirty stage was not touched because it was not mounted.

PRODUCTION_WRITES:
NONE

FINAL_STATUS:
BLOCKED

BLOCKERS:
Owner paths C:\Users\vkita\my_code\meta-repo\adv-bot and C:\Users\vkita\my_code\meta-repo\campaign-settings-history are not visible from this Cloud Agent VM. Origin has no campaign-settings-history branch (166 heads checked). Connected worker vkita-pc (71b3661e-2ad7-4234-a792-7c39a22963a4) did not receive Task tool calls; workerId and env.type=machine were ignored and child agents stayed on hostname cursor.

NEXT_ACTION:
Run the existing change continuation on vkita-pc (local Cursor or a Cloud Agent whose tool calls execute on that My Machines worker). First command is read-only inventory of the feature worktree against current committed local stage. Do not start a greenfield change on the cloud stage snapshot. Do not push.
```

---
cursor:
  subagentId: "bc-b57d1959-8648-59bf-ac96-9f0648e3ed08"
---

# CAMPAIGN_SETTINGS_HISTORY_RECONCILIATION_REPORT

Diagnosis corrected: this is `ROUTING_BLOCKED` / `LOCAL_AGENT_ROUTING_FAILED`, not evidence that change `campaign-settings-history` is absent.

`vkita-pc` (`71b3661e-2ad7-4234-a792-7c39a22963a4`) is connected and `eligibleForSubagent`. Task has no worker placement field. Extra `workerId`, `env.type=machine`, `placement`, and `targetWorkerId` were ignored. The probe agent `bc-d427b580-b765-566e-b0ca-a6bc99eeef2b` returned `ROUTING_LANDED_OFF_MACHINE cursor`. Cloud snapshot `4763b0a1602d00da285739f2be9af5a553ef3c0a` and origin are not authority. No feature conclusion follows from this VM.

## Where this hop ran

| Check | Result |
|---|---|
| Host | Linux hostname `cursor` (kernel 6.12.94+) |
| Cloud checkout | `/agent/repos/adv-bot`, branch `stage`, HEAD `4763b0a1602d00da285739f2be9af5a553ef3c0a`, clean status, single worktree |
| Owner main | `C:\Users\vkita\my_code\meta-repo\adv-bot` — absent (`/mnt/c/...` absent) |
| Owner feature worktree | `C:\Users\vkita\my_code\meta-repo\campaign-settings-history` — absent |
| Origin | `git ls-remote --heads origin` returned 166 heads. No `campaign-settings-history` and no `shop-wide-campaign-data-collection` head |
| Cloud OpenSpec | `openspec/changes/campaign-settings-history/**` not present |
| Self-hosted worker | `vkita-pc` connected, `workerId` `71b3661e-2ad7-4234-a792-7c39a22963a4`, `eligibleForSubagent` true, `sharedAssignmentAllowed` true, `isInUse` false |
| Placement attempt | Task calls with `workerId` and `env.type=machine` still executed on hostname `cursor` (subagents `bc-c9249a97-17b1-5ac3-a550-6546d12ec714`, `bc-9daa6365-ce06-55ea-b1f1-86200eb615e9`) |

The cloud `stage` SHA is a snapshot of GitHub `origin/stage`. It is not the Owner's current committed local `stage` and was not used as the feature baseline.

```text
WORKTREE:
PATHS_MISSING

BRANCH:
PATHS_MISSING

FEATURE_HEAD:
PATHS_MISSING

CURRENT_STAGE_HEAD:
PATHS_MISSING on the authoritative Owner disk.
Cloud snapshot only (not authority): 4763b0a1602d00da285739f2be9af5a553ef3c0a, clean stage, one worktree.

WORKTREE_STATUS:
Owner feature worktree not mounted. Cloud repo has no second worktree.

CURRENT_OPENSPEC_PHASE:
UNKNOWN — change tree not on this disk.

OWNER_CONTRACT_STATUS:
UNKNOWN — not read from the feature worktree.

IMPLEMENTATION_PRESENT:
UNKNOWN

FIELD_REGISTRY_STATUS:
UNKNOWN

EXCEL_EXPORT_STATUS:
UNKNOWN

EXCEL_IMPORT_STATUS:
UNKNOWN

EXCEL_PARITY_STATUS:
UNKNOWN

BEFORE_AFTER_HISTORY_STATUS:
UNKNOWN

REASON_INTENT_STATUS:
UNKNOWN

PG_HISTORY_STATUS:
UNKNOWN

CLICKHOUSE_HISTORY_STATUS:
UNKNOWN

CURRENT_MIGRATION_CANDIDATE:
UNKNOWN — migration sequence was not inventoried on current committed local stage.

MIGRATION_NUMBER_COLLISION:
UNKNOWN

SHOP_WIDE_CAMPAIGN_MIGRATION_OVERLAP:
UNKNOWN

SCENARIO_COVERAGE_STATUS:
UNKNOWN

VERIFY_STATUS:
NOT_RUN

KNOWN_BLOCKERS:
Authoritative worktree is on vkita-pc. This agent cannot route shell or file tools onto that worker. Continuing here would be a new implementation on a GitHub stage snapshot, which this assignment forbids.

MATERIAL_GAPS:
No owner contract, design, specs, tasks, registry, Excel surface, history collectors, or migration 006 inventory from the feature worktree.

RECOMMENDED_NEXT_BOUNDED_STEP:
Re-run this same read-only inventory on vkita-pc against the two Owner paths, then continue the existing lifecycle only after that report is filled from disk.

GO_TO_CONTINUATION:
NO
```

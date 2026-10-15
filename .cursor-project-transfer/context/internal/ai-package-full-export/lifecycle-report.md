---
cursor:
  subagentId: "bc-d5bd05fc-7f0b-501d-9040-ae55da7b551f"
---

# AI_PACKAGE_FULL_EXPORT_LIFECYCLE_REPORT

Sibling evidence: [reconciliation-report.md](/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/internal/ai-package-full-export/reconciliation-report.md).

No product files were created. No branch, commit, push, worktree, or OpenSpec change was created on the cloud clone. Cloud `stage` is the wrong tree: it does not contain `ExportService` or the dataset owners this assembler must reuse.

```text
CHANGE:
  ai-package-full-export
  NOT CREATED (Owner worktree not reachable)

FEATURE_HEAD:
  NONE

STAGE_BASE:
  Owner committed local stage — UNKNOWN
  Non-authority origin/stage fetched 2026-10-05:
  4763b0a1602d00da285739f2be9af5a553ef3c0a

DATASET_FAMILIES:
  NOT ASSEMBLED
  Target once local stage is readable and keyword merge is YES:
    campaign settings snapshot (existing owner)
    campaign advertising daily (existing owner, if stage contains a safe read contract)
    shop SKU daily / common sales (existing owner)
    keyword daily / positions / windows / current state / changes (existing owner)
    meta: MANIFEST, DATA_MAP, PACKAGE_SUMMARY
  Explicit non-owners: campaign_settings_history, store_drr
  (GAP unless a merged read contract already exists; no formula and no history reader in this change)

CAMPAIGN_SETTINGS_STATUS:
  GAP on origin/stage; Owner UNKNOWN

COMMON_SALES_STATUS:
  GAP on origin/stage; Owner UNKNOWN

CAMPAIGN_ADVERTISING_STATUS:
  GAP on origin/stage; Owner UNKNOWN

KEYWORD_PERFORMANCE_STATUS:
  MERGED_AND_CLEANED (USER_ASSERTED)
  feature c66f46e09, merge b8c810159, later stage seen as f86e943ed
  archive openspec/changes/archive/2026-10-05-ai-package-keyword-performance-history
  SHAs not on GitHub and not in cloud origin/stage 4763b0a16
  This hop did not reopen or modify that archive.

CAMPAIGN_SETTINGS_HISTORY_STATUS:
  GAP on origin/stage; Owner OPTIONAL_PENDING / UNKNOWN

MANIFEST:
  NOT BUILT

DATA_MAP:
  NOT BUILT

PACKAGE_SUMMARY:
  NOT BUILT

ONE_BUTTON_ENTRYPOINT:
  NOT FOUND on origin/stage; Owner UNKNOWN

DETERMINISTIC_PACKAGE:
  NOT BUILT

VALIDATOR:
  NOT BUILT

TESTS:
  NOT RUN

RUFF:
  NOT RUN

PYRIGHT:
  NOT RUN

OPENSPEC:
  NOT STARTED
  preflight / opsx-new / owner contract / design / specs / tasks / scenario plan / planning review
  were not executed because the authority checkout is on vkita-pc

SCENARIO_AUDIT:
  NOT RUN

OPSX_VERIFY:
  NOT RUN

FINAL_MERGE_REVIEW:
  NOT RUN

MERGE_COMMIT:
  NONE

POST_MERGE_VERIFY:
  NOT RUN

ARCHIVE:
  NOT RUN

WORKTREE_REMOVED:
  NO (none created by this hop)

BRANCH_REMOVED:
  NO (none created by this hop)

PRODUCTION_WRITES:
  NONE

FINAL_STATUS:
  BLOCKED

NEXT_ACTION:
  Keyword merge is USER_ASSERTED YES. No second product GO is required.
  This cloud checkout cannot see the commits, so implementation stays unstarted.
  Continue on vkita-pc: re-read committed stage (expect f86e943ed or a later
  descendant; reject 4763b0a16), confirm ExportService and dataset owners,
  then planning plus bounded implementation in
  C:\Users\vkita\my_code\meta-repo\ai-package-full-export.
  Do not edit the archived keyword-history change. No push.
```

## Why this hop stopped

`list-self-hosted-workers` shows `vkita-pc` connected and eligible. A `Task` launch with `workerId` still executed on the Linux cloud VM (`/agent/repos/adv-bot`). A second launch failed validation: `machine.type` allows only `same_machine` or `new_cloud_vm`. There is no API key in this environment to create a machine-routed agent (`env.type=machine`, `env.name=vkita-pc`).

Writing OpenSpec or assembler code against origin/stage `4763b0a16` would invent an exporter the local stage may already own, and it would race the keyword change’s `ExportService` files.

## Local prompt (vkita-pc)

```text
Chat: OPSX / ai-package-full-export
Workspace: C:\Users\vkita\my_code\meta-repo\adv-bot
Model: composer-2.5
Command: read-only inventory first, then OPSX planning. Implementation only if the checks below print YES.

You are on vkita-pc. Authority is the current committed local branch stage in C:\Users\vkita\my_code\meta-repo\adv-bot. Do not use origin/stage as the base. PowerShell only. No stash, reset, clean, git add -A, commit of unrelated files, push, deploy, WB API writes, or ClickHouse/PG writes.

KEYWORD_CHANGE_MERGED_INTO_STAGE is USER_ASSERTED YES (c66f46e09 via b8c810159; later stage f86e943ed; archive 2026-10-05-ai-package-keyword-performance-history). Do not reopen or edit that archive. Re-read stage anyway. If committed HEAD is not f86e943ed and is not a descendant of b8c810159, stop and report the actual HEAD. If it is, continue planning and bounded implementation with no new product GO.

1. git -C C:\Users\vkita\my_code\meta-repo\adv-bot branch --show-current
2. git -C C:\Users\vkita\my_code\meta-repo\adv-bot rev-parse HEAD
3. git -C C:\Users\vkita\my_code\meta-repo\adv-bot status --short
4. git -C C:\Users\vkita\my_code\meta-repo\adv-bot worktree list
5. For each change id, say whether it is contained in committed stage (commit SHA) or only in a worktree: ai-package-campaign-settings-snapshot, shop-wide-common-sales-collection, shop-wide-campaign-data-collection, ai-package-keyword-performance-history, campaign-settings-history, ai-package-v1-contract.
6. Locate ExportService, MANIFEST, DATA_MAP, PACKAGE_SUMMARY, package validator, deterministic ZIP/hash, and the human export entrypoint. Cite paths.
7. git diff --stat between stage and the keyword-performance worktree for any shared ExportService / AI package files.

Write AI_PACKAGE_FULL_EXPORT_RECONCILIATION_REPORT with the required fields. IMPLEMENTATION_GATE = WAIT_FOR_KEYWORD_MERGE when keyword is not in committed stage. IMPLEMENTATION_GATE = READY only when keyword is merged and shared paths are reconciled.

If READY: create worktree C:\Users\vkita\my_code\meta-repo\ai-package-full-export on branch ai-package-full-export from that stage HEAD if it does not exist, then run OPSX command-only through planning, bounded implementation, tests, pyright-strict, verify, dirty-overlap analysis, merge into local stage, post-merge verify, archive, cleanup. Assembler only. ExportService stays the only exporter. No second exporter. No new collectors. One shop. One ZIP. Explicit GAP for missing families. No push.
```

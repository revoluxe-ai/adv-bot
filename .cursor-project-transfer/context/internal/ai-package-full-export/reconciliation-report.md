---
cursor:
  subagentId: "bc-d5bd05fc-7f0b-501d-9040-ae55da7b551f"
---

# AI_PACKAGE_FULL_EXPORT_RECONCILIATION_REPORT

Checked 2026-10-05. Authority requested: committed local `stage` on `C:\Users\vkita\my_code\meta-repo\adv-bot`. That disk was not readable from this hop.

```text
WORKTREE:
  Owner path C:\Users\vkita\my_code\meta-repo\ai-package-full-export — NOT READ
  Cloud checkout used only as a negative control: /agent/repos/adv-bot (single worktree, branch stage)

BRANCH:
  Owner local stage — NOT READ
  Cloud / origin/stage (fetched 2026-10-05): stage

BASE_HEAD:
  Owner committed stage — UNKNOWN
  origin/stage (not the authority): 4763b0a1602d00da285739f2be9af5a553ef3c0a
  subject: Merge branch 'stage' of github.com:revoluxe-ai/adv-bot into stage
  committer date: 2026-10-03 03:13:44 +0300
  cloud status: clean

EXPORT_SERVICE_STATUS:
  ABSENT on origin/stage app/ (no class ExportService, no ai_package module)
  Owner local stage — UNKNOWN

CAMPAIGN_SETTINGS:
  GAP on origin/stage (openspec change ai-package-campaign-settings-snapshot absent; no matching commit subject)
  Owner local — UNKNOWN

COMMON_SALES:
  GAP on origin/stage (shop-wide-common-sales-collection absent)
  Owner local — UNKNOWN

CAMPAIGN_ADVERTISING:
  GAP on origin/stage (shop-wide-campaign-data-collection absent; no remote branch head)
  Owner local — UNKNOWN
  Stale store snapshot 2026-09-30 lists worktree
  C:/Users/vkita/my_code/meta-repo/shop-wide-campaign-data-collection @ b79534379 dirty
  (docs/adv-bot-local-worktrees.md). That SHA is older than origin/stage 4763b0a16 and is not current evidence.

KEYWORD_PERFORMANCE:
  GAP on origin/stage
  Owner local — NOT CONFIRMED MERGED
  Project notes.md (2026-10-05): implementation is still in a worktree; agent
  bc-e8cac6b2-2fa4-5a4f-a372-99c58e8e5e42 is closing lifecycle toward a local stage merge, no push

CAMPAIGN_SETTINGS_HISTORY:
  GAP on origin/stage
  Owner local — UNKNOWN (treat as OPTIONAL_PENDING until a local read proves a stable read contract)

EXISTING_MANIFEST:
  ABSENT on origin/stage as an AI Package contract
  Unrelated COMPOSE_MANIFEST / PACKAGE_MANIFEST exist under tools/scripts and scripts/a1_* only
  Owner local — UNKNOWN (stale 2026-09-30 worktree ai-package-v1-contract @ 30d7473e6 dirty)

EXISTING_DATA_MAP:
  ABSENT on origin/stage
  Owner local — UNKNOWN

EXISTING_PACKAGE_VALIDATOR:
  ABSENT on origin/stage
  Owner local — UNKNOWN

EXISTING_ZIP_DETERMINISM:
  ABSENT on origin/stage for an AI Package ZIP
  Owner local — UNKNOWN

CURRENT_EXPORT_ENTRYPOINT:
  ABSENT on origin/stage
  Owner local — UNKNOWN

FILE_OWNERSHIP_OVERLAPS:
  NOT COMPUTED — Owner worktrees were not reachable
  Expected collision surface once local disk is readable:
    ExportService and AI Package modules shared with
    ai-package-keyword-performance-history
    and any campaign-data export files still unmerged
  Do not edit those paths until keyword merge is proven and a diff --stat overlap check is clean

KEYWORD_CHANGE_MERGED_INTO_STAGE:
  YES (USER_ASSERTED 2026-10-05, not re-read from disk on this hop)
  Feature commit c66f46e09 merged by b8c810159.
  Later stage observed by the keyword lifecycle report: f86e943ed.
  Archive path (do not reopen or edit):
  openspec/changes/archive/2026-10-05-ai-package-keyword-performance-history
  Worktree and local feature branch removed.
  These SHAs are absent from GitHub and from origin/stage 4763b0a16 (HTTP 422).

CAMPAIGN_DATA_MERGED_INTO_STAGE:
  NO
  Meaning: not proven. origin/stage does not contain shop-wide-campaign-data-collection.
  A 2026-09-30 worktree row is not a current merge proof.

PROPOSED_PACKAGE_STRUCTURE:
  Not created. Logical contract to apply only after local inventory, reusing whatever
  ExportService already emits:
    AI_PACKAGE/
      MANIFEST.json
      DATA_MAP.json
      PACKAGE_SUMMARY.json
      datasets/
        <existing dataset ids, JSON/JSONL primary>
  Excel is not the canonical format.
  Campaign settings history and store DRR stay explicit GAP unless their owners
  already expose a stable read contract. This change does not own those formulas
  and does not add collectors.

PROPOSED_PACKAGE_SUMMARY:
  Deterministic index only (not an LLM-written narrative):
    shop_id, package_cutoff, timezone
    available / partial / unavailable dataset families
    date_ranges, campaign_count, sku_count, keyword/query count
    coverage summary, important gaps, recommended logical entrypoints
  Family states: COMPLETE | PARTIAL | GAP | UNSUPPORTED | FAILED
  Absence is not empty and empty is not zero.
  Unproven currency stays financial_semantics = GAP / UNKNOWN.

KNOWN_GAPS:
  - Owner Windows paths are unreachable from this cloud agent
  - Task.machine accepts only same_machine | new_cloud_vm; workerId was ignored
  - vkita-pc worker is connected (workerId 71b3661e-2ad7-4234-a792-7c39a22963a4,
    displayName vkita-pc, repo revoluxe-ai/adv-bot, idle, sharedAssignmentAllowed)
    but this hop cannot place a shell there
  - origin/stage has no ExportService and none of the dependency changes
  - Planning artifacts were not written on the cloud clone: they would not be
    based on committed local stage

OWNER_DECISIONS_REQUIRED:
  None for product semantics. Execution must move to vkita-pc.
  No new product GO is required after keyword merge is proven on that disk.

IMPLEMENTATION_GATE:
  BLOCKED
  Keyword dependency is no longer the blocker.
  Blocker: current committed local stage was not re-read. Cloud HEAD is still
  4763b0a1602d00da285739f2be9af5a553ef3c0a and does not contain c66f46e09,
  b8c810159, or f86e943ed. Implementing here would ignore the required stage
  re-read and would not see ExportService after the keyword merge.
  vkita-pc worker 71b3661e-2ad7-4234-a792-7c39a22963a4 is connected and idle.
  Task.machine still accepts only same_machine | new_cloud_vm.
```

Dependency changes searched on origin/stage (all absent as `openspec/changes/<id>` and as commit subjects): `ai-package-campaign-settings-snapshot`, `shop-wide-common-sales-collection`, `shop-wide-campaign-data-collection`, `ai-package-keyword-performance-history`, `campaign-settings-history`, `ai-package-full-export`, `ai-package-v1-contract`.

OpenSpec command files present on the cloud stage tree: `.cursor/commands/opsx-new.md`, `opsx-ff.md`, `opsx-apply.md`, `opsx-verify.md`. That does not authorize apply here.

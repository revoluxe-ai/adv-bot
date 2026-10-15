---
cursor:
  subagentId: "bc-6eb42fe6-562d-5111-9d07-0ad300478b4b"
---

# ADV_BOT_CURSOR_PROJECT_BOOTSTRAP_RECONCILIATION

Read-only. No commit, merge, push, stash, reset, or product edit.

Authority required by the task: committed local `stage` at `C:\Users\vkita\my_code\meta-repo\adv-bot` plus proven local feature branches/worktrees. This hop did not read that disk.

## Placement

| Attempt | Target | Result |
|---|---|---|
| Task `workerId=71b3661e-2ad7-4234-a792-7c39a22963a4` | vkita-pc | [Inventory local adv-bot](bc-014f161b-8478-5f30-9ea4-d892a0841092) ran on Linux `cursor`. `usePrivateWorker=false`, `privateWorkerId=null`. HOST_PROOF_FAIL |
| Task `env.type=machine` `env.name=vkita-pc` plus the same worker id | vkita-pc | [Prove vkita-pc shell](bc-b1659b2d-ddc5-520b-bdd3-cd5c50084605) returned `PLACEMENT_FAIL` |

Worker was connected at inventory start: `vkita-pc`, Windows, `workerId` `71b3661e-2ad7-4234-a792-7c39a22963a4`, repo `revoluxe-ai/adv-bot`, `eligibleForSubagent=true`, `sharedAssignmentAllowed=true`, `isInUse=false`. Connected does not place this agent's shell there.

```text
LOCAL_STAGE_HEAD:
UNREAD — canonical path not mounted on this VM

ORIGIN_STAGE_HEAD:
4763b0a1602d00da285739f2be9af5a553ef3c0a
(source: cloud checkout /agent/repos/adv-bot after git fetch origin stage; this is GitHub origin/stage, not local authority)

LOCAL_STAGE_AHEAD:
UNKNOWN

LOCAL_STAGE_BEHIND:
UNKNOWN

MAIN_DIRTY:
UNKNOWN

DIRTY_PATH_COUNT:
UNKNOWN

WORKTREES:
UNKNOWN — local worktree list not read this hop

ACTIVE_EXECUTORS:
UNKNOWN — live Cursor/OPSX/runner processes on HOME-PC were not inspected.
Worker isInUse was false at list time. That does not prove chats are idle.

CHANGES:
  ai-package-keyword-performance-history:
    HEAD: UNKNOWN
    LIFECYCLE: UNKNOWN
    ACTIVE: UNKNOWN
    SAFE_TO_TOUCH: NO
  campaign-settings-history:
    HEAD: UNKNOWN
    LIFECYCLE: UNKNOWN
    ACTIVE: UNKNOWN
    SAFE_TO_TOUCH: NO
  ai-package-full-export:
    HEAD: UNKNOWN
    LIFECYCLE: UNKNOWN
    ACTIVE: UNKNOWN
    SAFE_TO_TOUCH: NO
  shop-wide-campaign-data-collection:
    HEAD: UNKNOWN
    LIFECYCLE: UNKNOWN
    ACTIVE: UNKNOWN
    SAFE_TO_TOUCH: NO

MERGE_READY_CHANGES:
none proven

IN_PROGRESS_CHANGES:
UNKNOWN

PARKED_CHANGES:
UNKNOWN

UNKNOWN_CHANGES:
all local changes — disk unread

DIRTY_PATH_OWNERSHIP:
UNKNOWN

REMOTE_BRANCH_GAPS:
UNKNOWN versus local refs.
Cloud snapshot HEAD equals origin/stage 4763b0a1602d00da285739f2be9af5a553ef3c0a, clean, one worktree.

PROJECT_CONFIG_CURRENT_STATE:
On origin/stage snapshot only (not local dirty):
AGENTS.md present (repository guidelines, not the short WB Sky authority contract).
.cursor/rules: 14 files
.cursor/skills: 23 (openspec-* and speckit-*)
.cursor/commands: 71
.cursor/environment.json: absent
.cursor/hooks.json: absent
No routing rule for Cloud vs Local. No authority-detection rule.

CLOUD_ENVIRONMENT_CURRENT_STATE:
This VM booted from a prebuilt environment and has the origin/stage checkout.
.cursor/environment.json is not in the repo snapshot, so Cloud Agent reproducibility is not declared in git.

BLOCKERS:
LOCAL_AUTHORITY_UNREACHABLE
Task placement onto vkita-pc is ignored (subagents stay on the Cursor-hosted VM).
Safe consolidation, verification, and push of local stage cannot start without a shell on C:\Users\vkita\my_code\meta-repo\adv-bot.

SAFE_CONSOLIDATION_PLAN:
Do not commit, merge, or push from the cloud snapshot.
Re-run the read-only inventory on vkita-pc.
Only after that report: classify changes, touch SAFE_TO_TOUCH=YES paths, push fast-forward only.

GO_TO_BOOTSTRAP:
NO
```

## Stale store notes (not disk proof)

`notes.md` (2026-10-05, prior hops) claims keyword-performance-history was merged into local stage at `f86e943ed` and campaign-settings-history at `4fe28087a`, with origin still behind. Those SHAs are not on this cloud `stage`. Treat them as unverified until the local inventory reprints `git rev-parse`.

## Next action

Run the inventory on vkita-pc. The copy-paste prompt is in the coordinator reply.

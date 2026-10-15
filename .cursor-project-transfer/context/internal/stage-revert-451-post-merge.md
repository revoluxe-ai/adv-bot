---
cursor:
  subagentId: "bc-f64a91ed-6e30-5fb7-b6a0-085dd926f00f"
---

# STAGE_REVERT_451_POST_MERGE

Owner-authorized lifecycle only: mark #451 ready, merge commit, verify, stop. No force-push, rebase, reset, or direct push to `stage`. PR #450, PR #449, and `separate-auto-search-cpo` were not modified.

## Pre-merge proof

Immediately before the ready/merge writes:

| Check | Result |
|---|---|
| `origin/stage` | `1443649281543bc00411d9940a047037ed6d3ffd` |
| PR #451 head | `61c4de8648bb7e2aa73371f0ebe9d157210f74ac` |
| mergeable | `MERGEABLE` / `CLEAN` |
| issue comments / review comments / reviews | 0 / 0 / 0 |
| status checks | empty rollup |
| PR `updatedAt` before ready | `2026-10-05T17:48:00Z` |

`PREMERGE_STATE_CHANGED` did not apply. After marking ready, the same SHAs were re-read (`isDraft=false`) before merge.

## Merge

- Draft cleared via PR update (ready for review).
- Merged with `gh pr merge 451 --merge --match-head-commit 61c4de8648bb7e2aa73371f0ebe9d157210f74ac`.
- Branch `cursor/revert-unauthorized-package-archive-a089` still exists at `61c4de864`.

## Post-merge

```text
PR_451:
MERGED

MERGED_AT:
2026-10-05T21:06:23Z

MERGE_COMMIT:
d2166b2d805b27a6656f46c6ccb8e56066b4e888

PARENTS:
1443649281543bc00411d9940a047037ed6d3ffd
61c4de8648bb7e2aa73371f0ebe9d157210f74ac

ORIGIN_STAGE:
d2166b2d805b27a6656f46c6ccb8e56066b4e888

STAGE_TREE:
b2ac12313617f04a9393c7869cce8d329cd7adc9

EXPECTED_TREE:
b2ac12313617f04a9393c7869cce8d329cd7adc9

TREE_MATCH:
YES

DIFF_23c0671f_TO_STAGE:
EMPTY

DIFF_CHECK:
PASS (exit 0 vs 23c0671f)

TESTS:
NOT_REQUIRED (same tree already passed 136 unit tests in the pre-merge review)

MIGRATIONS:
NONE

MANUAL_DEPLOY:
NONE

IMAGE_CLEANUP:
NONE
```

`git diff 23c0671f372f0435b13a3573ec8990b4303b3e4a..origin/stage` has zero files. The merge commit’s tree is the certified revert tree.

Untouched after this hop:

- PR #450 still `OPEN`/`DRAFT`, head `1b636542a41e1dbfd66585c64d5c93dfff0bed18`
- PR #449 still `OPEN`/`DRAFT`, head `2b9b4f1d2d7b7a8ccf931aa1cc1bf83713e6ce36` (not edited here)
- `separate-auto-search-cpo` still `9b97462b16120c6b900b9e57b93bda515b33787c`

## Stage image caveat

Actions run [37350705614](https://github.com/revoluxe-ai/adv-bot/actions/runs/37350705614) published the unauthorized stage image from `144364928`. That SHA image may remain in GHCR and Harbor. This hop did not delete or retag it.

The merge push auto-queued [37373827350](https://github.com/revoluxe-ai/adv-bot/actions/runs/37373827350) (`GitHub Container Registry Deploy`, head `d2166b2d`, status queued at verification). That is the existing `stage` push workflow, not a manual deploy. It was left running. No image cleanup was performed.

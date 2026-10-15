---
cursor:
  subagentId: "bc-f64a91ed-6e30-5fb7-b6a0-085dd926f00f"
---

# STAGE_REVERT_451_FINAL_REVIEW

Review only. No merge, no rebase, no force-push, no product edits, no PR #450 edits, no image cleanup.

```text
ORIGIN_STAGE:
1443649281543bc00411d9940a047037ed6d3ffd

PR:
#451

PR_STATE:
OPEN / DRAFT

PR_HEAD:
61c4de8648bb7e2aa73371f0ebe9d157210f74ac

EXPECTED_BASE_MATCH:
YES

REVERT_COMMITS:
e832b6a64
f17399f66
61c4de864

UNAUTHORIZED_COMMITS_FULLY_REVERTED:
YES

AFFECTED_TREE_MATCHES_23c0671f:
YES

UNRELATED_PATHS_TOUCHED:
NONE

CONTROL_PLANE_TOUCHED:
NO

CAMPAIGN_SETTINGS_HISTORY_TOUCHED:
NO

SEPARATE_AUTO_SEARCH_CPO_TOUCHED:
NO

DIFF_CHECK:
BASELINE_CLEAN (exit 0 vs 23c0671f); STAGE_DIFF reports restored baseline EOF blank line only (openspec/specs/ai-package-v1-exporter/spec.md:323, exit 2)

TESTS:
PASS

OPENSPEC:
NOT_APPLICABLE

PUBLISHED_STAGE_IMAGE_CAVEAT:
CONFIRMED

PRODUCTION_WRITES:
NONE

MERGE_PERFORMED:
NO

MERGE_READINESS:
READY

BLOCKER:
NONE
```

## Authority

- `git fetch origin` then `origin/stage` = `1443649281543bc00411d9940a047037ed6d3ffd` (matches expected base; not `BASE_CHANGED`).
- PR #451: https://github.com/revoluxe-ai/adv-bot/pull/451
- state `OPEN`, `isDraft=true`
- base `stage` @ `1443649281543bc00411d9940a047037ed6d3ffd`
- head `cursor/revert-unauthorized-package-archive-a089` @ `61c4de8648bb7e2aa73371f0ebe9d157210f74ac`
- merge-base(stage, PR) = `1443649281543bc00411d9940a047037ed6d3ffd`

Unauthorized chain on `stage` (only these three commits after the baseline):

| SHA | Parent | Subject |
|---|---|---|
| `cfa8f4f74625f3c51959454c47d4ffc156b3df9b` | `23c0671f372f0435b13a3573ec8990b4303b3e4a` | feat(ai-package): add PACKAGE_SUMMARY and canonical family status |
| `8026a18eb46b03f9e9fb10b55ab07f8efd01dc3d` | `cfa8f4f74` | docs(openspec): fix archive validation for contract repair change |
| `1443649281543bc00411d9940a047037ed6d3ffd` | `8026a18eb` | chore(openspec): archive ai-package-full-export-contract-repair |

## Revert chain

Reverse order, each message cites the full original SHA, each patch is the exact inverse (`git diff orig^ orig` == `git diff revert revert^`):

| Revert | Parent | Reverts |
|---|---|---|
| `e832b6a64c5be158a24a8c3139b83540e598b5de` | `144364928` | `144364928` |
| `f17399f66d4e83a3355f30da2175112f328ed7c4` | `e832b6a64` | `8026a18eb` |
| `61c4de8648bb7e2aa73371f0ebe9d157210f74ac` | `f17399f66` | `cfa8f4f74` |

No hidden semantic delta: tree(`61c4de864`) = tree(`23c0671f`) = `b2ac12313617f04a9393c7869cce8d329cd7adc9`. `git diff 23c0671f 61c4de864` is empty.

## Scope

PR vs `stage` touches only paths introduced or modified by those three commits (ai_package_v1 export/validator/tests, the contract-repair OpenSpec change then its archive, `openspec/specs/ai-package-v1-exporter/spec.md`, and the `package-lock.json` name field `adv_bot` → `adv-bot` from `cfa8f4f74`). Final content of every path matches `23c0671f`.

Not in the diff: campaign-settings history, shop-wide campaign/common sales, control plane, migrations, `k8s/`, deploy workflows. `separate-auto-search-cpo` remains `9b97462b16120c6b900b9e57b93bda515b33787c`. PR #450 left untouched (`OPEN`/`DRAFT`, head `1b636542a41e1dbfd66585c64d5c93dfff0bed18`).

## Checks

- `git diff --check 23c0671f 61c4de864`: exit 0.
- `git diff --check origin/stage...61c4de864`: exit 2, `openspec/specs/ai-package-v1-exporter/spec.md:323: new blank line at EOF`. The restored file ends in `\n\n`, identical to `23c0671f`. Stage’s unauthorized archive tip ends without that extra blank line. Clearing it would diverge from the authorized baseline, so it is not a merge blocker.
- Tests on the PR tree (`poetry run pytest -m unit tests/unit/ai_package_v1 -q`): **136 passed**. No migrations or production-write scripts were run.
- OpenSpec: the unauthorized change dir and `openspec/changes/archive/2026-10-05-ai-package-full-export-contract-repair/` are absent on the revert tree, so change/archive validation is not applicable. Local config contract check passed and does not cover those removed paths.

## Image caveat

GitHub Actions run [37350705614](https://github.com/revoluxe-ai/adv-bot/actions/runs/37350705614) completed **success** on push to `stage` at `144364928`. Job steps include successful GHCR push and successful Harbor push. `.github/workflows/deploy_stage.yml` pushes `${sha}` and floating tag `stage`. It has no delete/untag step. Merging the revert does not delete the already published SHA image. A later push to `stage` would build a new image and move the floating `stage` tag; that is a separate operational concern and does not block restoring git history.

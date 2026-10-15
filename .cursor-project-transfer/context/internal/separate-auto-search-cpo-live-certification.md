---
cursor:
  subagentId: "bc-1d9d0829-ea97-5f99-ac15-78ecc4eaa622"
---

# separate-auto-search-cpo — merge-ready

HOME-PC live cert of `f6c18bb76` remains valid. Stage was integrated without touching the leg-CPO read path. Draft PR is open. Not merged.

```text
PR: https://github.com/revoluxe-ai/adv-bot/pull/478
BRANCH: cursor/separate-auto-search-cpo-clean-a089
VERIFIED_HEAD: 890799160107d5d6b03dce79c23acf14280e2d3c
CERTIFIED_READ_PATH: f6c18bb76843a73a0ec929d087592d50d6dcedad
INTEGRATED_STAGE: 8d2383d6d821146602fc931a60af6184bc930538
ORIGIN_STAGE_NOW: 1e1558d9bc7fe3a8a5ea7bc2dfca3d842edf2d66
MERGE_TREE_VS_CURRENT_STAGE: CLEAN (f1c110633aaefce35acb08a176cf1de77fdabc3a)
GITHUB_MERGEABLE: MERGEABLE / CLEAN
LIVE_CERT_STILL_VALID: YES
FINAL_STATUS: READY_FOR_MERGE
```

Parents of `890799160`: `f6c18bb76` + `8d2383d6d`. `git diff f6c18bb76 HEAD` is empty for `leg_cpo.py` and `full_wb_adv_stat.py` (`get_stats_by_adv_ids_last_days`, `load_leg_cpo_snapshot`).

Stage tip moved to `1e1558d9b` (PR #476 shop-order GMV) after the integration commit. No overlapping paths with the feature delta. No second merge.

## Gates

| Gate | Result |
|---|---|
| Tests | PASS — 18 unit + 2 keyword UI |
| Ruff | PASS on certified test files. LOW UP037 at `leg_cpo.py:109` left unrepaired |
| Pyright strict (5 feature paths) | PASS — 0 errors |
| OpenSpec 1.6.0 strict | PASS |
| opsx_verify (`openspec_guard --scenario opsx_verify --strict`) | PASS — exit 0, known baseline WARN |
| git diff --check | PASS |
| GitHub CI | No applicable pull_request checks. `migration-gates.yml` is path-filtered and this delta does not match. Deploy workflows are push-to-stage only |

## Review

[Independent review](bc-5674be8e-1cb7-57c0-bc1c-398c5833e03d) (`composer-2.5`): CRITICAL/HIGH/MEDIUM none. LOW UP037. VERDICT APPROVE. LIVE_CERT_STILL_VALID YES.

Live evidence: [separate-auto-search-cpo-home-pc-live-cert-result.md](./separate-auto-search-cpo-home-pc-live-cert-result.md).

## T5 re-verification (2026-10-10)
- PR #478 state: MERGED 2026-10-10T14:18:38Z by app/cursor (not by me), merge commit a3763942cf3f0992a2e391cbe692ad28555f3cd1; PR head 890799160107d5d6b03dce79c23acf14280e2d3c.
- Gates on 890799160: unit 18 pass, UI 2 pass, ruff only LOW UP037 leg_cpo.py:109, pyright-strict 14 errors all outside feature files (other features on stage), openspec@1.6.0 strict valid, opsx_verify exit 0 (known baseline WARN), git diff --check OK, stage deploy CI success on a3763942c.
- Review (grok-4.7-medium, bc-4feed5c9-fa02-5492-84bb-c281e06b57c0): APPROVE, no CRITICAL/HIGH/MEDIUM. Detail: internal/reviews/separate-auto-search-cpo-890799160.md
- Live cert (f6c18bb76) still valid: read path byte-identical.

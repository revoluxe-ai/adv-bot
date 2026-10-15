---
cursor:
  subagentId: "bc-32bdaafb-bc6f-532c-901a-2eb4845c2b03"
---

# separate-auto-search-cpo — reconciliation inventory (read-only)

**Repo:** `/agent/repos/adv-bot`  
**Fetched:** 2026-10-05  
**Merge-base:** `b79534379971e94e0200b50ebc6787ea96455452`

## Checkpoint vs feature tip

- Checkpoint `784f468becfffcba5118592348adf914dc994d73` **is an ancestor** of `origin/separate-auto-search-cpo`.
- Checkpoint **equals** feature tip (single FEATURE_ONLY commit on branch).

## Feature semantics (from `openspec/changes/separate-auto-search-cpo/**`)

- Introduce **leg-scoped factual CPO**: Auto CPO from Auto `adv_id` stats, Search CPO from linked `search_adv_id`; shared read provider + `LegCpoSnapshot`; same observation window for both legs; formula `spend / max(orders, 1)`; missing Search → `None` without cross-leg fallback.
- **Preserve aggregate** `fact_pay_for_order` / plan-fact for campaign-level reporting; leg consumers must not use aggregate as substitute.
- **Search consumers** (V3 keyword, common-bid updater, bidder/cluster safety caps, A/B Hold overspend) use Search CPO only; **Auto consumers** (shelf bid control, activity/cost confirmation) use Auto CPO only.
- **Paid UI** shows labeled `CPO Auto` and `CPO Search` from the same snapshot as runtime; unavailable legs shown explicitly.
- Tasks marked complete on feature branch (WIP checkpoint commit message); proposed decision `leg-cpo-economics-ownership` documents ownership and forbidden fallbacks.

## Branch divergence

| Ref | SHA |
|-----|-----|
| `origin/stage` | `23c0671f372f0435b13a3573ec8990b4303b3e4a` |
| `origin/separate-auto-search-cpo` | `784f468becfffcba5118592348adf914dc994d73` |
| merge-base | `b79534379971e94e0200b50ebc6787ea96455452` |
| `stage...feature` count | `46` stage-only / `1` feature-only |

Feature tip is **not** contained in `origin/stage`.

## Path overlap (both branches changed vs merge-base)

Intersection of `git diff --name-only $MB origin/stage` and `git diff --name-only $MB origin/separate-auto-search-cpo`:

1. `app/modules/shop_runner/service_manager/manager.py`
2. `pyrightconfig_strict.json`

No `openspec/changes/separate-auto-search-cpo/**` files on stage (feature-only OpenSpec tree).  
No shared test or `conftest.py` overlap (feature-only: `conftest.py`, `tests/support/destructive_lifecycle.py`, many leg-CPO tests).

### `pyrightconfig_strict.json` (PYRIGHT_CONFIG_OVERLAP)

| Side | Change vs merge-base |
|------|----------------------|
| **Feature** | Adds five file paths under `strict` includes: `adv_keyword_messages.py`, `data_manager.py`, `full_wb_adv_stat.py`, `wb_adv_dto.py`, `leg_cpo.py`. |
| **Stage** | Adds three `include` directory entries (shop-wide common sales modules) and fourteen paths (campaign settings, CH migration control plane, `ai_package_v1` tests/modules). |

**Assessment:** Feature adds **only** leg-CPO-related strict entries for this change. Stage has **newer unrelated** strict entries the feature must **not** drop on merge — union both disjoint sets. `git merge-tree` reports **content conflict** with `<<<<<<< .our` / `>>>>>>> .their` in the trailing `include` list (mechanical union).

### `manager.py` (PRODUCT overlap)

| Side | Evidence |
|------|----------|
| **Stage** | Replaces inline `update_common_sale_stat` loop with `run_shop_wide_common_sale_stat_tick`; adds `collect_shop_wide_campaign_advertising` coroutine (shop-wide dual-path collection). |
| **Feature** | Inserts `await self._wb_shop_data_manager.attach_leg_cpo(...)` before A/B Hold pipeline, auto-budget refresh, and auto control candidates. |

**Assessment:** **MECHANICAL** — non-overlapping hunks; `merge-tree` auto-combines both sides without conflict markers.

## `git merge-tree` summary

- **Conflicted paths:** `pyrightconfig_strict.json` only (disjoint strict-include tail).
- **Changed in both (auto-merged):** `app/modules/shop_runner/service_manager/manager.py`.
- Remaining feature deltas merge as additive file changes (new `leg_cpo.py`, consumer wiring, tests, OpenSpec change dir).

## Feature-only product surface (no stage overlap)

47 paths on feature vs merge-base including new `app/modules/shop_runner/wb_stat_manager/leg_cpo.py`, `ComplexAdv`/`WBAdvDTO` extensions, Search/Auto consumer migrations, UI loaders/messages, CH stat read path, and full test/support corpus for leg CPO.

---

```text
CURRENT_STAGE: 23c0671f372f0435b13a3573ec8990b4303b3e4a
FEATURE_CHECKPOINT: 784f468becfffcba5118592348adf914dc994d73
FEATURE_TIP: 784f468becfffcba5118592348adf914dc994d73
MERGE_BASE: b79534379971e94e0200b50ebc6787ea96455452

STAGE_ONLY_COMMITS:
Merge pull request #448 from revoluxe-ai/cursor/cloud-project-bootstrap-8b4b
chore(cursor): add cloud-first Project routing and environment
test: scope destructive_local markers per integration test
fix(openspec): normalize campaign-settings spec and CH scenario map
test(clickhouse): align read-only corpus tests with 006/007 fingerprint
spec(openspec): archive campaign-settings-history lifecycle
chore(openspec): archive shop-wide-campaign-data-collection lifecycle
spec(openspec): archive ai-package-campaign-settings-snapshot
docs(openspec): archive ai-package-full-export lifecycle
feat(ai-package): full ZIP assembler with family gaps catalog
docs(openspec): keyword history lifecycle MERGED_AND_CLEANED receipt
chore(openspec): archive ai-package-keyword-performance-history
merge: ai-package-keyword-performance-history into stage
test(ai-package): S15/S18 campaign-settings snapshot scenario seams
fix(ch-migrations): extend corpus to 007 for stage reconcile
merge(stage): reconcile with local stage authority 47a94d4
feat(campaign-settings): registry, Excel parity, CH 006 history, PG collector
docs(ai-package): lifecycle receipts — merge blocked by stage dirty overlap
Merge branch 'stage' into shop-wide-campaign-data-collection
chore(ai-package): preserve raw evidence and fix formatting
feat(ai-package): export full keyword performance history
docs: record verified common sales cleanup repair
docs: add shop-wide common sales lifecycle closure report
docs: archive shop-wide common sales lifecycle
docs: close archive verify receipt for common sales (0481)
feat(shop-runner): collect shop-wide campaign advertising
docs: verify common sales merged lifecycle
Merge branch 'shop-wide-common-sales-collection' into stage
docs: independent final merge review PASS for shop-wide common sales
docs: normalize common sales lifecycle evidence
feat: collect shop-wide common sales
Merge branch 'ai-package-campaign-settings-snapshot' into stage
feat(ai-package): add campaign settings snapshot export
Merge WORKLOG
Update TODO
docs(doto): log clickhouse migration control plane work (записать работу в WORKLOG)
chore(ci): extend strict pyright to migration package (расширить strict pyright на пакет миграций)
test(clickhouse-migration-control-plane): add unit acceptance suite (добавить unit-набор acceptance)
feat(clickhouse-migration-control-plane): add migration runner package (добавить пакет control plane миграций CH)
spec(openspec): add archive test regression contract (контракт регрессии архива)
spec(openspec): promote ClickHouse migration lifecycle (промотировать lifecycle миграций CH)
Merge branch 'stage' of github.com:revoluxe-ai/adv-bot into stage
Merge branch 'clickhouse-migrations-control-plane' into stage
fix(bot): stale create-both confirm message (PAT-ADV-003)
fix(bot): reply on stale ce_create_both confirm (PAT-ADV-003)
fix: do not abort create_complex_advs on Telegram progress notify failure

FEATURE_ONLY_COMMITS:
feat(leg-cpo): checkpoint separate-auto-search-cpo WIP

PRODUCT_OVERLAPS:
app/modules/shop_runner/service_manager/manager.py

TEST_OVERLAPS:
(none)

TEST_INFRA_OVERLAPS:
(none)

PYRIGHT_CONFIG_OVERLAP:
pyrightconfig_strict.json

OPENSPEC_OVERLAPS:
(none)

SEMANTIC_CONFLICTS:
(none)

MECHANICAL_CONFLICTS:
pyrightconfig_strict.json — disjoint strict include tails; merge-tree conflict markers; union stage CH/ai_package/campaign-settings entries with feature leg_cpo file entries
app/modules/shop_runner/service_manager/manager.py — stage shop-wide coroutine refactor + feature attach_leg_cpo hooks; merge-tree auto-merge

RECONCILIATION_READY:
YES
```

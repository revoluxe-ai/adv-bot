---
cursor:
  subagentId: "bc-69bac1ed-b800-5b4d-9da9-05ab10ed89e7"
---

# Independent review — attribution-facts-contract Slice A

PR [#456](https://github.com/revoluxe-ai/adv-bot/pull/456) · branch `cursor/attribution-facts-contract-slice-a` · reviewed at `96ebe45596ba1c88f223eaf588c89687cfa84429`

## Preflight

| Check | Result |
|---|---|
| PR #456 head | `96ebe455…` (matches expected) |
| `origin/stage` | `c956e167…` (matches reported implementation base) |
| merge-base | `c956e167…` |
| HEAD match | yes |
| worktree clean | yes |
| diff vs base | 23 paths only — `app/modules/attribution_facts/**`, `tests/unit/attribution_facts/**`, `openspec/changes/attribution-facts-contract/**` |
| unrelated product diff | none |
| migrations / CH / collector / AI / MCP | absent from diff |

## Contract review

- **Canonical grain:** `AttributionFactKey` = `shop_id`, `physical_adv_id`, `event_date`, `app_type`, `ordered_nm_id` (+ `source_family` default, design-aligned).
- **advertised_nm_id:** excluded from key; docstring + `test_fact_key_excludes_advertised_nm`.
- **DIRECT / LINKED / UNKNOWN:** `classify_ordered_nm` — promoted membership; no DIRECT fallback; empty/non-authoritative/missing → UNKNOWN.
- **Reconciliation:** pure `reconcile_campaign_day`; same-source campaign-day totals only; no supplier/wb_common_stat.
- **Spend:** `CampaignDaySpendReference` external; metrics on facts exclude spend authority.

## Domain boundary

Slice A only: domain, port, in-memory fake, unit tests, OpenSpec planning artifacts (incl. proposed ADR for B). No B/C/D implementation leakage.

## Gates (this VM)

| Gate | Result | Notes |
|---|---|---|
| `pytest -m unit tests/unit/attribution_facts/` | **PASS** 20/20 | `--confcutdir` (no Poetry 3.11 venv on VM) |
| `openspec validate … --strict` | **PASS** | npx `@fission-ai/openspec` |
| `git diff --check` | **PASS** | |
| merge dry-run into `origin/stage` | **PASS** | no conflicts |
| `ruff check` (attribution paths) | **FAIL** | 27× FURB157/I001 (style) |
| `pyright` (`pyrightconfig.json`, `app/modules/attribution_facts`) | **FAIL** | 6 errors (`in_memory_reader` missing param types; unused imports) |
| `poetry run pyright-strict` | **N/A** | module not in `pyrightconfig_strict.json` include → canonical strict gate does not cover new package yet |
| `openspec_guard.py` (repo-wide) | **FAIL** | pre-existing skill/rule budget failures; not introduced by Slice A |
| `/opsx-verify mode=archive` | **NO_GO** | B/C/D open; no `scenario-coverage/plan.receipt.json` or audit receipt |
| `/opsx-verify mode=impl` (Slice A) | **IMPL_OK** | tasks A.* checked; behavior matches slice scope |

## Scenario audit (L1 / Slice A only)

No durable `plan.receipt.json` or certify receipt for this change. Bounded L1 mapping from tests:

| Scenario | Confirmed | Evidence |
|---|---|---|
| S01 DIRECT | yes | `test_direct_classification` |
| S02 LINKED | yes | `test_linked_classification` |
| S03 UNKNOWN empty promoted | yes | `test_empty_promoted_unknown_not_linked` |
| S04 reconciliation / gap | partial | pass + gap tests; `UNATTRIBUTED` class not asserted (uses `unattributed_orders`) |
| S07 missing membership economics | partial | UNKNOWN classification + `BLOCKED_BY_ATTRIBUTION_FACTS` on non-COMPLETE; no end-to-end “no snapshot → economics blocked” |
| S10 revision replace | yes | `test_revision_replaces_not_sums` |
| S13 reader coverage axes | partial | `evaluate_window_coverage` PARTIAL reason codes; reader only asserts COMPLETE |
| S14 cutoff ≠ COMPLETE | partial | `package_cutoff_does_not_imply_complete` only; no `evaluate_window_coverage` cutoff→PARTIAL test |

**SLICE_A_SCENARIOS_CONFIRMED:** S01–S03, S10 strong; S04/S07/S13/S14 partial gaps as above.  
**FULL_CHANGE_CERT_DEFERRED:** yes (S05–S16, certify, archive).

## Findings

| Severity | Item |
|---|---|
| **HIGH** | Default `pyrightconfig.json` reports 6 errors in new `in_memory_reader.py` / `versioning.py` — likely CI risk if full `app` pyright runs on merge. |
| **MEDIUM** | S14/S13 test depth below scenario plan intent. |
| **MEDIUM** | `attribution_facts` not enrolled in `pyrightconfig_strict.json` (strict gate blind spot). |
| **LOW** | Ruff FURB157/I001 on Decimal/import style. |
| **LOW** | `tasks.md` P.5 `openspec_guard` on touched paths still unchecked. |

## Merge safety

- Incremental merge of Slice A into `origin/stage` is **technically clean** (merge-tree / dry-merge OK).
- OpenSpec change may remain **ACTIVE** with B/C/D unchecked; **no archive** and **no full-change certification** should be claimed.
- Project lifecycle does **not** block landing domain-only slice ahead of B/C/D.

## Verdict

**MERGE_READINESS:** conditional — contract and slice scope are sound; repair type annotations / unused imports before merge if repo runs default app pyright.

**FINAL_STATUS:** `REPAIR_REQUIRED` (pyright on `app/modules/attribution_facts`, optional ruff/style).

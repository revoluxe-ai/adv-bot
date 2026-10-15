---
cursor:
  subagentId: "bc-af960b65-913c-51f1-9b3f-30ad53d13c36"
---

# Slice D independent security/correctness review

**Branch:** `cursor/attribution-facts-contract-slice-d-89e7`  
**Cert subject:** `5baf182f329665d995eccc729548f480eece021f`  
**Review tip (local):** `8022f2188` (+17 unpushed commits vs `origin/…slice-d-89e7`)

## Verdict summary

| Severity | Count |
|----------|------:|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |
| LOW | 2 |

**Overall:** **PASS with MEDIUM process hygiene** on cert subject; economics/spend-gate logic is fail-closed and well-covered by matrix tests. No authz/injection or cross-tenant issues in reviewed paths.

## Prior MEDIUM dispositions

| # | Finding | Disposition | Evidence |
|---|---------|-------------|----------|
| 1 | Stray `tests/.\tests` path artifact | **Not fixed** (still open at cert subject and branch tip) | `git ls-tree -r 5baf182f` tracks `tests/.\tests\clickhouse-config/default-user.xml`; on-disk dir `tests/.\tests\clickhouse-config` (root-owned). Commit `677a0606f` removed it on another line; Slice D never dropped the blob. |
| 2 | Invalid slice-d receipt `certified_head` (`39aaaff7c`) | **Fixed on branch tip; not fixed at cert subject commit** | At `5baf182f`, `slice-d-l1-audit.receipt.json` had `certified_head: 39aaaff7c` — `git merge-base --is-ancestor` shows **not** on ancestry of `5baf182f`. HEAD receipt uses `executed_cert_subject_head: 5baf182f3` + guard matrix. |
| 3 | CH per-query client churn in `collect_attribution_evidence` | **Fixed** | `collect_attribution_evidence` dispatches to `ChAnalysisAttributionReader.collect_all_evidence` (single `get_clickhouse_client` per batch); `test_ch_attribution_reader_lifecycle.py` asserts `acquire_count == 1`. Export path uses `collect_attribution_evidence` (`export_service.py`). |
| 4 | Pyright/typing on new tests | **Fixed** | `npx pyright -p pyrightconfig_strict.json` on `test_attribution_economics_matrix.py` + `test_ch_attribution_reader_lifecycle.py` → 0 errors (uses `cast` helpers). |

## New findings (this review)

### MEDIUM (open at cert subject)

1. **Certification receipt ↔ code SHA mismatch at `5baf182f`** — same root as prior #2; mis-attests which commit was gated until receipt rewrite on tip.
2. **Malformed git path under `tests/`** — same as prior #1; hygiene/CI portability risk, not production runtime in reviewed export path.

### LOW

1. **`ChAnalysisAttributionReader.query_leg_window`** still acquires one CH client per call; safe if callers use `collect_attribution_evidence`, but the public method remains a churn footgun.
2. **Duplicated summation** — `_sum_class` (`attribution_evidence.py`) mirrors `_sum_metric` (`derived_metrics.py`); behavior aligned today, drift risk only.

## Correctness notes (focus files)

- **Spend gate:** `assess_campaign_spend_for_economics` requires campaign coverage `"COMPLETE"` and non-null `spend_rub` for every calendar day in `[window_start, window_end]`; blocks only `_ECON_METRIC_IDS` via `CAMPAIGN_SPEND_INCOMPLETE`, leaves count metrics emitted when attribution COMPLETE.
- **CPO/DRR decoupling:** `_emit_cpo_drr_pair` gates each metric on `orders_val` / `gmv_val` independently; matrix cases D–H match domain `compute_*` (missing ≠ zero; zero denominator → `DENOMINATOR_ZERO`).
- **Fail-closed:** partial attribution blocks economics via `can_emit_direct_linked_economics`; no numeric fallback when spend or denominators incomplete.

## Tests

Could not run pytest (no `poetry` / missing `clickhouse_connect` in VM); relied on receipt claims + static review + strict pyright on new test modules.

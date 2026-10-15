---
cursor:
  subagentId: "bc-6b6f51ae-c7a4-5d01-b222-ced388d09b94"
---

# Slice D independent review

**Repo:** `adv-bot`  
**Branch:** `cursor/attribution-facts-contract-slice-d-89e7`  
**HEAD:** `05f8a140a` (`feat(attribution-facts): Slice D AI Package attribution consumer`)  
**Diff base:** parent `e76988d15` (Slice C)

## Verdict counts

| Severity | Count |
|----------|------:|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 4 |

## Checklist (assigned)

| Check | Result |
|-------|--------|
| No direct SQL to `attribution_fact_observations` from `ai_package` | **PASS** — no matches under `app/modules/ai_package_v1`; observation SQL only in `attribution_facts/readers/ch_attribution_facts_reader.py`. AI path: `ChAnalysisAttributionReader` → `PortAnalysisAttributionReader` → `ChAttributionFactsReader`. |
| `AttributionFactsReader` boundary | **PASS** — consumption via port + domain types; CH adapter lives in `analysis/attribution_reader.py` (same composition pattern as `ChAnalysisCampaignReader`). No `persistence` / collector imports. |
| Fail-closed coverage | **PASS** — non-`COMPLETE` blocks all eight attribution metrics; missing pre-fetch → `BLOCKED_BY_ATTRIBUTION_FACTS`; linked metrics blocked with `ATTRIBUTION_RELATION_UNKNOWN` when linked absent; CPO/DRR use `can_emit_direct_linked_economics` + domain `compute_*`. |
| S16 package rollup | **PASS** — `_sum_member_metrics` excludes attribution IDs; `package_attribution_uncomputable` adds `ATTRIBUTION_SCOPE_MISMATCH` for multi-leg package rows; unit test `test_s16_package_scope_attribution_scope_mismatch`. |
| Spend authority | **PASS** — `spend_refs_for_leg_window` builds `CampaignDaySpendReference` from `CampaignDailyFact` (`full_adv_wb_stat` analysis reader); CPO/DRR numerators from `derived_metrics._sum_spend(spend_refs)`, not observation rows. |
| No Slice B/C leakage | **PASS** — no `clickhouse_observation_repository`, ingest, or collector wiring in Slice D diff. |

## Evidence

- `poetry run pytest -m unit tests/unit/ai_package_v1/analysis/test_attribution_consumption.py` — **5 passed**
- `git diff e76988d15..05f8a140a` — 12 files, core under `app/modules/ai_package_v1/analysis/*`, `export_service.py`, unit tests

## MEDIUM findings

1. **Stray duplicate tree entry** — `git ls-tree` shows both `tests/clickhouse-config/default-user.xml` and `"tests/.\\tests\\clickhouse-config/default-user.xml"` (same blob). Accidental path; user noted possible follow-up removal.
2. **L1 receipt head drift** — `openspec/changes/attribution-facts-contract/scenario-coverage/slice-d-l1-audit.receipt.json` has `certified_head: "0d6fc9f0d"` while reviewed commit is `05f8a140a`.
3. **CH session churn** — `ChAnalysisAttributionReader.query_leg_window` opens `get_clickhouse_client()` per leg×window in `collect_attribution_evidence` (export scales with legs × windows).
4. **Strict pyright on touched export path** — `export_service.py`: unused `EmptyAnalysisAttributionReader` import; `collect_attribution_evidence(..., windows=windows)` `list[WindowSpec]` vs `list[object]` (reportArgumentType).

## Notes (non-counted)

- Zip contract tests use `EmptyAnalysisAttributionReader` via `package_zip_test_support.py` (intentional fail-closed export tests without CH).
- Unit `_complete_query()` uses empty `reconciliations=()`; production completeness is enforced by Slice C reader + `evaluate_window_coverage`.

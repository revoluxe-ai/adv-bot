---
cursor:
  subagentId: "bc-a52999cd-c682-5a79-b219-755cf97e34f8"
---

# AI_PACKAGE_MULTI_WINDOW_ANALYSIS_PLANNING_REPORT

```text
REPO: revoluxe-ai/adv-bot
BRANCH: cursor/ai-package-multi-window-analysis-34f8
HEAD: 88133bae8ecef3916385bec20748737f47796406
ORIGIN_STAGE: d2166b2d805b27a6656f46c6ccb8e56066b4e888

PR450_HEAD: 19ec4bf5ac0a6e16a1c43699a01232dc2d55cbd9
PR450_TOUCHED: NO

CHANGE_NAME: ai-package-multi-window-analysis

EXISTING_REUSE_FOUND:
- keyword window catalog 1d/3d/7d/14d/30d/90d/180d/365d plus calendar presets
  (app/modules/ai_package_v1/keyword_performance/windows/engine.py)
- PackageCutoff.last_closed_calendar_day = UTC generated_at date minus 1 day
- ExportPeriod separate from keyword history bounds
- keyword_windows.jsonl already aggregated; not copied
- PACKAGE_SUMMARY / PACKAGE_FAMILY_GAPS / DATA_MAP on PR #450
- family store_drr and shop sales already GAP
- full_adv_wb_stat daily grain has spend, orders, sum_price_orders
- safe_ratio / safe_cpo null-on-zero-denominator

PROPOSED_DOMAIN_SERVICE: AnalysisAggregationService under app/modules/ai_package_v1/

PROPOSED_CONTRACT_FILES:
- analysis/ANALYSIS_CONTRACT.json
- analysis/AI_ANALYSIS_GUIDE.md
- analysis/windows/shop.jsonl
- analysis/windows/campaigns.jsonl
- analysis/windows/products.jsonl
- analysis/comparisons.jsonl
- pointer to existing keyword_performance/keyword_windows.jsonl
- no analysis/windows/keywords.jsonl

STANDARD_WINDOWS: 1d 3d 7d 14d 30d 90d 180d 365d ending on latest complete UTC day
CALENDAR_YEAR_SUPPORT: year_to_date, previous_year, year_before_previous, plus calendar_year_YYYY for older years on shop and leg grain only
CUSTOM_PERIOD_SUPPORT: window_id requested_custom, not a preset id

LATEST_COMPLETE_DAY_RULE: last_closed_calendar_day = UTC date of package generated_at minus one calendar day. Not rolling 24h. Source day closure in WB timezone remains UNKNOWN, inherited from keyword history.

ANALYSIS_WINDOW_VS_HISTORY_CONTEXT: PASS
MISSING_ZERO_NULL: PASS
COVERAGE_PROPAGATION: PASS
AUTO_SEARCH_IDENTITY: PASS
DIRECT_LINKED_SEMANTICS: DEPENDENCY_GATED
SHOP_DRR_SEMANTICS: DEPENDENCY_GATED
DYNAMIC_CPO_SEMANTICS: DEPENDENCY_GATED

RAW_DATA_DUPLICATION: NONE

PERFORMANCE_STRATEGY: One domain service (option B). Export calls it. No new table. Campaign grain is one pass over daily legs. Keyword windows are reused, not scanned again. Default AI context is summary, contract, shop and campaign windows, comparisons. Keyword JSONL stays drill-down because uncompressed history is large.

ZIP_API_MCP_SEMANTIC_PARITY: PASS
VERSIONING_STRATEGY: package 1.1.0 when analysis present; analysis contract 1.0.0; guide version independent. Formula or window-boundary change bumps analysis contract major and package major. New metric id is contract minor.

DEPENDENCY_MATRIX:
READY_NOW: standard windows, campaign views/clicks/spend, CTR/CPC, campaign orders and order sum as CAMPAIGN_WB_STAT only, existing keyword windows, window vs history split
BLOCKED_BY_ATTRIBUTION_FACTS: CPO_FACT_DIRECT, DRR_FACT_DIRECT, CPO_FACT_LINKED, DRR_FACT_LINKED
BLOCKED_BY_COMMON_SALES: shop factual GMV denominator
BLOCKED_BY_SETTINGS_HISTORY: settings timeline as explanation
BLOCKED_BY_CHANGE_EVENTS: change-event timeline
BLOCKED_BY_SHOP_DRR_SOURCE: numeric store_drr

TEST_PLAN: S01–S23 in scenario-coverage/plan.md (PLAN_EVIDENCE_ID SCPV1-8c0bb2ab6613a007). Covers boundaries, partial today, horizons, calendar year, no raw duplication, missing/zero/null, partial/gap, Auto/Search, direct/linked isolation, no fallback, denominator zero, insufficient comparability, versions, stable order, transport seam, short and long local acceptance. WB writes forbidden.

OPEN_QUESTIONS: NONE

IMPLEMENTATION_GO: NO
PRODUCT_CODE_CHANGED: NO
PRODUCTION_WRITES: NONE

PLANNING_READINESS: READY_FOR_OWNER_REVIEW
FINAL_STATUS: PLANNING_COMPLETE
```

Change path: `openspec/changes/ai-package-multi-window-analysis/` on branch `cursor/ai-package-multi-window-analysis-34f8`.

PR was not opened. PR #450 was not modified.

Apply is not authorized. Next owner step is review of `owner-contract.md`, not implementation.

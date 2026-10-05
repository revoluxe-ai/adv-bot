# Tasks — ai-package-keyword-performance-history

Planning artifact. Implementation via `/opsx-apply` after independent planning review.
No product code in this planning hop.

```text
TASKS_STATUS: IMPLEMENTATION_COMMITTED (finalize hop WB-SKY-KEYWORD-HISTORY-FINALIZE-20261005-10)
PLANNING_READY: yes (repair3 20261005-0137; certified 20261005-0140)
APPLY_READY: yes (repair WB-SKY-KEYWORD-HISTORY-REMEDIATE-20261005-0201)
OWNER_CONTRACT_STATUS: REVIEWED PASS (WB-SKY-KEYWORD-HISTORY-OWNER-REREVIEW-20261005-0107)
INDEPENDENT_PLANNING_REVIEW: PASS (WB-SKY-KEYWORD-HISTORY-PLAN-CERTIFY-20261005-0140)
SCENARIO_AUDIT: SCAR-09 PASS 51/51 (WB-SKY-KEYWORD-HISTORY-INDEPENDENT-REAUDIT-20261005-09)
VERIFY_IMPL: VERIFY_PASS (WB-SKY-KEYWORD-HISTORY-INDEPENDENT-REAUDIT-20261005-09)
MERGE_REVIEW: NOT_YET (pending vs stage 9a80c813ed4edaf3c6f2da6ae65af4221f7ec36e)
SCENARIO_PLAN_EVIDENCE_ID: SCPV1-dad56a1027545bc3 (supersedes SCPV1-3bf22597d777c0f1; see plan.receipt.json)
WORKTREE_FINGERPRINT: 3929cd8e9e5e22a56c2cc4ef13b64757ca413c5698a188fcc7e6fe268fb75358 (65 paths; pre-commit authoritative)
SOURCE_SPEC_SHA: 2ef8006acefcbb8506ce35eefca25cc0120a122f3a0efa2f6bf1caf5465682b4 (unchanged)
AUDITED_HEAD_SHA: 37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0 (historical audit metadata only)
```

## Owner acceptance traceability (AT-01..AT-26)

| AT | Owner acceptance | Primary scenarios | Task slice |
|---|---|---|---|
| AT-01 | Daily query history on strict grain | S01, S02 | §2 daily reader |
| AT-02 | Full history not 7/30 clipped | S03, S04, S39, S45 | §2, §5 |
| AT-03 | Auto/Search not mixed | S05 | §2 scope/leg |
| AT-04 | Physical adv_id preserved | S02 | §2 daily |
| AT-05 | Rebound history not lost | S06, S07, S40, S46 | §1 scope |
| AT-06 | No duplicate logical counting | S08 | §2, §3 |
| AT-07 | Missing ≠ zero | S09 | §2 daily |
| AT-08 | Position missing not synthetic max | S10, S42 | §2 positions |
| AT-09 | Telegram/graph not used | S11, S12 | §1 forbidden guard |
| AT-10 | Position direction documented | S13 | §4 DATA_MAP |
| AT-11 | Standard windows correct | S14, S17 | §3 windows |
| AT-12 | Calendar year ≠ rolling 365d | S14 | §3 windows |
| AT-13 | Comparable prev windows | S15 | §3 windows |
| AT-14 | Insufficient history partial | S16 | §3 coverage |
| AT-15 | Current state deterministic | S20, S47 | §3 current |
| AT-16 | Derived metrics reproducible | S17 | §3 windows |
| AT-17 | Spend not fabricated | S18, S19, S41 | §2 spend |
| AT-18 | UNKNOWN/UNSUPPORTED explicit | S24, S25, S48 | §4 coverage |
| AT-19 | Deterministic serialization | S35 | §5 encode |
| AT-20 | Deterministic ZIP/hash | S35 | §5 encode |
| AT-21 | Tampered package detected | S36 | §5 validator |
| AT-22 | Cross-shop leakage forbidden | S26, S46 | §2 scope |
| AT-23 | DATA_MAP grain/joins | S24, S32, S44 | §4 DATA_MAP |
| AT-24 | ExportService single authority | S29, S30, S49 | §5 integration |
| AT-25 | No WB write | S37 | §5 contract |
| AT-26 | No PG/Redis/control-plane write | S28, S38 | §5 contract |

## LEGACY_BASELINE

- v1 ExportService exports campaign_full_stat, funnel, settings, shop orders unassigned.
- Keyword history exists in CH/scripts/UI only; no DATA_MAP/keyword datasets.
- `ExportScopeAdv` lacks adv_setting_id and rebound expansion.

## TARGET_REGRESSION

- Default `ExportService()` includes keyword datasets (real read-only assembler).
- Full history bounds independent of ExportPeriod for keyword family; cutoff at
  `package_cutoff_date` + `package_cutoff_instant` where source semantics allow.
- Unit tests inject fake keyword assembler/readers explicitly; no silent DISABLED path.
- Row-coherent daily snapshots; raw_query not fabricated; ownership validation on scope.

## FINAL_ACCEPTANCE

- `poetry run pytest -m unit tests/unit/ai_package_v1/keyword_performance/ -v`
- `openspec validate ai-package-keyword-performance-history --type change --strict`
- Independent `/opsx-planning-review` PASS after repair; then `/opsx-apply`.

---

## 0. Planning gates

- [x] 0.1 Scaffold proposal, owner-contract, design, specs, ADR, tasks, scenario plan
- [x] 0.2 Owner contract review PASS (OCR 20261005-0107)
- [x] 0.3 Independent `/opsx-planning-review` PASS (20261005-0110)
- [x] 0.4 Coordinator planning repair (20261005-0113)
- [x] 0.4b Repair2 planning package (20261005-0130 — P001-P007)
- [x] 0.4c Repair3 planning package (20261005-0137 — P008-P009)
- [x] 0.5 Independent `/opsx-planning-review` re-run after repair3 (WB-SKY-KEYWORD-HISTORY-PLAN-CERTIFY-20261005-0140 PASS)
- [x] 0.6 `/opsx-apply` bounded implementation hops (WB-SKY-KEYWORD-HISTORY-IMPLEMENT-20261005-0142)

---

## 1. Scope + source plumbing (semantic extraction slice)

- [x] 1.1 Add `keyword_performance/scope/keyword_export_scope_reader.py` — PG
      `AdvSetting.id` + `get_rebound_wb_adv_ids` read; internal `KeywordScopeRow` DTO
- [x] 1.2 Add `keyword_performance/scope/adv_id_collector.py` — dedupe expanded adv_ids;
      leg_role assignment; requested-shop PG ownership + global adv_id overlap probe;
      AMBIGUOUS_LEG / AMBIGUOUS_OWNERSHIP / FOREIGN_SHOP_ADV_ID flags
- [x] 1.3 Add SQL `keyword_performance/sql/keyword_daily_from_clusters.sql` —
      two-stage CTE row-coherent snapshot + nullable tuple uniqExact probe;
      `date <= package_cutoff_date` AND `timestamp <= package_cutoff_instant`; qualified `default_db`
- [x] 1.4 Add SQL `keyword_history_bounds.sql` — per-source MIN/MAX (clusters + positions)
      with source-appropriate cutoff filters (positions: `version <= cutoff_instant_ms`)
- [x] 1.5 Implement `ChKeywordDailyReader` with bounded batch/stream fetch (no N+1 per key)
- [x] 1.6 Implement spend mapper — `QUERY_SPEND_STATUS`; forbid CPM×views/1000 factual path
- [x] 1.7 Implement forbidden-source guard test — no import of graphic_positions_creator /
      KeywordDailyHistoryManager SQL on export path
- [x] 1.8 Unit tests: rebound expansion (S06,S40), ownership ambiguous (S46), leg separation (S05), missing≠zero (S09)

---

## 2. Daily + position facts (canonical evidence slice)

- [x] 2.1 Domain models: `KeywordDailyRowV1`, position observation row, coverage row types
- [x] 2.2 Implement daily assembler enrichment — shop_id, adv_setting_id, leg_role, raw_query_status,
      derived CTR/conversions (ratio 0..1, finite JSON)
- [x] 2.3 Implement `ChKeywordPositionReader` — `keyword_position_from_api` safe SQL
      with independent position bounds; proven ms-epoch `version <= cutoff_instant_ms`
      cutoff (`click_house_manager.update_positions:88`); separate position_type streams
      (CLUSTER_AVG_POS, WB_KEYWORD_POSITION_API); unproven legacy rows only →
      `UNKNOWN_VERSION_TIME_SEMANTICS` date-only fallback
- [x] 2.4 Optional split encoder `keyword_positions.jsonl` when cleaner than embed
- [x] 2.5 Row-coherent snapshot conflict detection + identical-duplicate collapse (S25, S43)
- [x] 2.6 Unit tests: physical adv_id (S02), NULL spend (S41), NULL position (S42), raw_query unavailable (S44),
      cross-shop (S26), cutoff (S45)

---

## 3. Window engine + current/changes (pure window slice)

- [x] 3.1 Implement `windows/engine.py` — UTC package cutoff, closed-day anchor, OPEN MTD/QTD/YTD
      with elapsed-day comparable formulas (leap-year safe)
- [x] 3.2 Implement window metric families — sum-ratio rates; ranking aggregates; observed/missing days
- [x] 3.3 Implement `keyword_current_state` selector — strict `(adv_id,nmid,norm_query)` from daily reader;
      `campaign_slot_role` ACTIVE vs REBOUND_HISTORICAL; separate optional product MV stream (S47)
- [x] 3.4 Implement `keyword_changes` — comparable prev windows; facts-only deltas; null prev=0 handling
- [x] 3.5 Economics fail-closed when spend not FACTUAL across window
- [x] 3.6 Unit tests: 365d vs prev_year (S14), partial 7d (S16), CTR ratio (S17), no AI labels (S21)

---

## 4. DATA_MAP + coverage (documentation slice)

- [x] 4.1 Implement `DataMapBuilder` — grain, joins, source_calendar_timezone UNKNOWN, package TZ UTC,
      cutoff, comparable window formulas, delta convention, source matrix
- [x] 4.2 Implement `CoverageAssembler` — requested/returned/observed/missing/unsupported/failed dimensions;
      bid_decision_log availability probe (S48)
- [x] 4.3 Document ExportPeriod vs keyword_history_bounds dual bounds + package_cutoff_date (S32, S51)
- [x] 4.4 Unit test: DATA_MAP contains keyword_daily PK + position direction + raw_query semantics (S13, S24, S44)

---

## 5. ExportService + hash integration slice

- [x] 5.1 Extend `ExportService.__init__` — default-build `KeywordPerformanceAssembler` (settings pattern);
      optional inject for tests
- [x] 5.2 Wire `_export_with_scope` — append keyword payloads; dataset cards; preserve existing cards
- [x] 5.3 Extend validator for DATA_MAP/coverage files; tamper detection (S36)
- [x] 5.4 Contract tests: deterministic hash (S35), no WB (S37), no PG/Redis writes (S38), cutoff (S51)
- [x] 5.5 Update existing `test_export_settings_integration` to inject fake keyword assembler (S34);
      MUST NOT rely on None→DISABLED
- [x] 5.6 Scenario seam tests: default keyword cards (S49,S50), full export with fake reader (S29,S33)
- [ ] 5.7 Integration test optional: CH destructive fixture subset for boundary read (marked integration)

---

## 6. Verification gates (apply)

- [x] 6.1 `poetry run pytest -m unit tests/unit/ai_package_v1/keyword_performance/ -n 8` (58/58 keyword; 87/87 ai_package_v1 unit pass)
- [x] 6.2 `poetry run pyright-strict` on keyword_performance + ai_package_v1 include (0 errors, 0 warnings on keyword_performance)
- [x] 6.3 `openspec validate ai-package-keyword-performance-history --type change --strict`
- [x] 6.4 `/opsx-spec-scenario-coverage mode=audit change=ai-package-keyword-performance-history` — SCAR-09 independent reaudit WB-SKY-KEYWORD-HISTORY-INDEPENDENT-REAUDIT-20261005-09: 51/51 PASS, 6/6 stub contracts; receipt `scenario-coverage/audit.receipt.json`; pytest log SHA256 `4baff5018cad462a66f2be8a22401f85467dbdf5fca30cb63b175972aed1ff42`; worktree fingerprint `3929cd8e9e5e22a56c2cc4ef13b64757ca413c5698a188fcc7e6fe268fb75358` (65 paths)
- [x] 6.5 `/opsx-verify mode=impl change=ai-package-keyword-performance-history` — VERIFY_PASS WB-SKY-KEYWORD-HISTORY-INDEPENDENT-REAUDIT-20261005-09; receipt `evidence/verify-impl-receipt-WB-SKY-KEYWORD-HISTORY-INDEPENDENT-REAUDIT-20261005-09.json`; 132/132 unit pass; pyright 0/0; openspec validate strict PASS

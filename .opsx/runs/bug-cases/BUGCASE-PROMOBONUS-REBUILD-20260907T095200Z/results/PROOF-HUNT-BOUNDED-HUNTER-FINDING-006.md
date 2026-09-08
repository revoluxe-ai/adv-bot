# Bounded hunt proof — journal bot-only; no manual-deposit persist sibling

```text
WORKER_ID: BOUNDED_HUNTER
WORKER_EXECUTION_ID: WEX/BOUNDED_HUNTER/14c710e724
ORCHESTRATION_ID: ORCH/sup-promo-t11-d11
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-006
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-006/JOURNAL-BOT-ONLY
HUNT_RESULT: CLEAR
CANDIDATE_COUNT: 0
MAPS_TO: /opsx-bug-hunt bounds
COMPLETED_AT: 2026-09-07T20:50:00Z
MISSION_COMPLETE: no
```

TOPIC_INTENT: PRODUCT_BRIEF
SOURCE_RESOLUTION:
- mode: exact_path
- primary_path: findings/FINDING-006.md
- fallback_used: false
- search_operations: 3 scoped rg (WBAutoBudgetTopUp( constructor; seller/portal/manual/deposit keywords; leftover/pool empty-as-journal-defect)
- search_scope: packet HUNT_SCOPE + ALLOWED_INPUT_ARTIFACTS only
- unresolved_gap: none
EXECUTION_PREFLIGHT:
- git_branch: deferred_not_required
- git_status: skipped
- other_ops: Pass 1 rg bounded to persist/load of manual seller-portal promo deposits into WBAutoBudgetTopUp, or missing-manual-deposits treated as a journal defect that empties leftover/pool
- blocked_on_preflight: false
JSON/packet writes via Write tool to path (anti-heredoc; no bash cat <<EOF). Windows Shell JSON write safety: Write->path, encoding=utf-8, ensure_ascii=True.

Verdict:
- plan_only (hunt only; no fix, no RED, no classify, no close)

Base/head:
- base: not required (packet-scoped hunt; git identity SKIP_IF)
- head: not required
- current branch: deferred_not_required
- inspected snapshot: current worktree after FINDING-006 CLASSIFIER FALSE_POSITIVE / ROUTE_C
- dirty files: not inspected (not REQUIRED_FOR hunt decision)

Invariant:
- WBAutoBudgetTopUp is the bot auto-budget journal only. Campaign remaining uses verified bot allocations minus UPD spend. Unused wallet promo stays on live WB cashbacks. Manual seller-portal deposits are outside this journal SoT.

Root finding packet:
- root finding id: FINDING-006
- title: journal only bot WBAutoBudgetTopUp; manual WB promo deposits invisible
- confirmed verdict: FALSE_POSITIVE / ROUTE_C (classifier PKT/WEX/CLASSIFIER/30d9a4e237/OUT; not reclassified here)
- classification: FALSE_POSITIVE
- causal boundary: journal records only bot WBAutoBudgetTopUp; classifier: that is the table contract, not a complete WB finance ledger
- write boundary: AutoBudgetManager.service _create_topup_entry -> wb_modifier.top_up_budget (bot auto-budget only)
- pre-fix ref: not applicable (FALSE_POSITIVE; no implementation)

## Hunt bound

FINDING-006 is FALSE_POSITIVE: WBAutoBudgetTopUp is the bot auto-budget journal by design; unused wallet promo stays on live WB cashbacks. Hunt ONLY sibling sites that actually persist or load manual seller-portal promo deposits into WBAutoBudgetTopUp, or that treat missing manual deposits as a journal defect that empties leftover/pool. Do not hunt leftover fraction (FINDING-005), FEFO expired-spend (FINDING-004), 90d cutoff (FINDING-003), pool-failure (FINDING-002), or overlay (ROOT-001) as same-invariant unless they literally write/read manual deposits in WBAutoBudgetTopUp. Do not reopen closed findings. Do not fix, write RED, classify, or close candidates. If no such sibling exists, HUNT_RESULT=CLEAR.

FINDING-006 journal-only-bot contract is already classified FALSE_POSITIVE / ROUTE_C. Not reclassified. Not fixed this hop. No RED. Not closed. No Route A/B/C/D chosen. Closed ROOT-001 / FINDING-002 / HC-001 / FINDING-003 / FINDING-004 / HC-FINDING-004-STALE-TEST / FINDING-005 not reopened. FINDING-007 not created.

## Result

HUNT_RESULT: CLEAR. No sibling in declared scope persists or loads manual seller-portal promo deposits into WBAutoBudgetTopUp. No site treats missing manual deposits as a journal defect that empties leftover or pool. CANDIDATES=[]. No new finding files.

## KNOWN_ROOT_RESULT

```text
ROOT_FINDING_ID: FINDING-006
STATUS: not_reproduced_on_inspected_snapshot
SNAPSHOT: current worktree after CLASSIFIER FALSE_POSITIVE / ROUTE_C
LOC_LINK: app/modules/common_slaves/wildberries/models/wb_auto_budget_topup.py:36
MATCHED_EFFECT: journal is bot auto-budget only; unused wallet promo stays on live WB cashbacks; manual seller-portal deposits are outside this SoT
MATCHED_CAUSAL_PATH: _create_topup_entry then wb_modifier.top_up_budget; load_success_tranches reads success promo_amount>0 bot rows only
MATCHED_WRITE_BOUNDARY: WBAutoBudgetTopUp persist via AutoBudgetManager.service _create_topup_entry
EVIDENCE: model docstring journal of bot campaign top-ups (LOC_LINK: app/modules/common_slaves/wildberries/models/wb_auto_budget_topup.py:36); sole constructor in allowed scope (LOC_LINK: app/modules/auto_budget_manager/service.py:653); callers ensure_budget (LOC_LINK: app/modules/auto_budget_manager/service.py:392) and ensure_common_budget (LOC_LINK: app/modules/auto_budget_manager/service.py:1109) then top_up_budget (LOC_LINK: app/modules/auto_budget_manager/service.py:423); load_success_tranches verified bot rows only (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:58); campaign remaining = verified WBAutoBudgetTopUp minus UPD spend (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:4); Redis derived, live WB + PG journals remain SoT (LOC_LINK: app/modules/auto_budget_manager/redis_promo_state_manager.py:1)
ACTION: do not emit FINDING-006 as a hunt candidate; do not reopen closed findings; do not create FINDING-007
```

DUPLICATE_ROOT_OBSERVATIONS:
- DUP-001: WBAutoBudgetTopUp model docstring states bot auto-budget journal (LOC_LINK: app/modules/common_slaves/wildberries/models/wb_auto_budget_topup.py:36). Same contract as FINDING-006 FALSE_POSITIVE. Not a child.
- DUP-002: _create_topup_entry is the only WBAutoBudgetTopUp( persist in allowed scope (LOC_LINK: app/modules/auto_budget_manager/service.py:653). Bot auto-budget write, not seller-portal ingest. Same write boundary as the known finding. Not a child.
- DUP-003: load_success_tranches selects status=success and promo_amount>0 (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:58). Loads verified bot allocations, not manual deposits. Same journal SoT. Not a child.

NEW_FINDINGS:
- none

Confirmed new production bugs:
- none

Findings requiring adjudication:
- none

Different-invariant candidates:
- none started. leftover mix remaining/tranche.amount (FINDING-005), FEFO expired-spend (FINDING-004), 90d leftover cutoff (FINDING-003), pool-failure redis false-empty (FINDING-002/HC-001), overlay (ROOT-001) classified out. CREATE_SEPARATE_ROOT_CANDIDATE not opened (bound forbids those invariants unless they literally write/read manual deposits in WBAutoBudgetTopUp).

Adjacent / dead legacy / tests-only / false positives:
- ADJ-001: resolve_promo_availability AND-stop only when both pool and campaign are empty (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:126). Empty campaign ledger does not zero live WB cashbacks / pool_usable. Not a journal-defect emptying leftover/pool.
- ADJ-002: pool_usable_from_pick uses live cashbacks[] pick (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:267). Unused wallet path, not WBAutoBudgetTopUp persist/load of seller-portal deposits.
- RedisPromoStateManager.set/get stores derived overlay only (LOC_LINK: app/modules/auto_budget_manager/redis_promo_state_manager.py:89). Does not persist or load manual deposits into WBAutoBudgetTopUp.

## Pass 1 — persist/load of manual seller-portal deposits

| Site | persist/load manual seller-portal deposits into WBAutoBudgetTopUp? | empties leftover/pool because journal lacks manual deposits? | Classification |
|------|-------------------------------------------------------------------|-------------------------------------------------------------|----------------|
| WBAutoBudgetTopUp model | No. Docstring: bot auto-budget journal (LOC_LINK: app/modules/common_slaves/wildberries/models/wb_auto_budget_topup.py:36) | No | FINDING-006 by design; DUP-001 |
| _create_topup_entry | No. Constructs bot journal row (LOC_LINK: app/modules/auto_budget_manager/service.py:653) | No | same write path; DUP-002 |
| ensure_budget caller | No. Then wb_modifier.top_up_budget (LOC_LINK: app/modules/auto_budget_manager/service.py:392) | No | bot auto-budget only |
| ensure_common_budget caller | No. Same bot persist (LOC_LINK: app/modules/auto_budget_manager/service.py:1109) | No | bot auto-budget only |
| load_success_tranches | No. success + promo_amount>0 bot rows (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:58) | No. Empty set => no campaign leftover; pool stays live WB | DUP-003 |
| load_campaign_ledgers | No. Calls load_success_tranches (LOC_LINK: app/modules/auto_budget_manager/promo_ledger.py:159) | No | same loader |
| campaign_ledger_from_rows / apply_spend_fefo | No. FEFO on verified bot tranches (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:218) | No | FINDING-004/005 out of bound |
| resolve_promo_availability | No persist/load of deposits (LOC_LINK: app/shared/domains/wb/utils/promo_accounting.py:285) | No. OR pool/campaign; AND-stop only if both empty | ADJ-001 |
| RedisPromoStateManager | No. Derived cache (LOC_LINK: app/modules/auto_budget_manager/redis_promo_state_manager.py:1) | No. Does not rewrite leftover/pool from missing journal rows | ADJ-002 / derived |

Pass 2: inspected the strongest sites above. No distinct persist/load of seller-portal deposits. No site treats missing manual deposits as a journal defect that empties leftover/pool. Pass 3 / `deep` absent; PASS_3=MANDATORY_STOP; no new working branches.

## Classified out of hunt bound (not candidates)

- ROOT-001 Telegram rec-bid overlay: closed_fixed; no WBAutoBudgetTopUp manual-deposit write/read.
- FINDING-002 / HC-001 pool-failure Redis false-empty: closed_fixed; different invariant; not hunted.
- FINDING-003 leftover 90d cutoff: closed_false_positive; not journal persist of manual deposits.
- FINDING-004 / HC-FINDING-004-STALE-TEST FEFO expired-spend: closed_fixed; not journal persist of manual deposits.
- FINDING-005 leftover fraction remaining/tranche.amount: closed_fixed; not journal persist of manual deposits.

## Why CLEAR

Classifier already decided journal-only-bot is by design (FALSE_POSITIVE / ROUTE_C). Allowed-scope persist is only `_create_topup_entry` after bot `top_up_budget`. Allowed-scope load is only `load_success_tranches` of verified bot success rows. Unused wallet promo remains live WB cashbacks[] / pool_usable. Missing seller-portal deposits are outside this journal SoT and do not force leftover/pool empty. FINDING-006 is not re-emitted. No `findings/` candidate files written.

## HUNT_EFFECTIVENESS

HIGH_WITHIN_DECLARED_SCOPE: enumerated WBAutoBudgetTopUp constructor, both _create_topup_entry callers, load_success_tranches / load_campaign_ledgers, campaign remaining SoT, resolve_promo_availability pool vs leftover, and Redis derived cache. Zero persist/load of seller-portal deposits. Zero leftover/pool empty-as-journal-defect. FINDING-006 not re-emitted; closed findings not opened.

## HUNT_FALSE_NEGATIVE_RISK

BOUNDED_TO_MANUAL_DEPOSIT_JOURNAL: hunt matches sites that persist or load manual seller-portal promo deposits into WBAutoBudgetTopUp, or that treat missing manual deposits as a journal defect that empties leftover/pool. Leftover fraction, FEFO spend skip, 90d leftover cutoff, pool-failure, and overlay classified out. `deep` flag absent; Pass 3 not expanded. Allowed-input read set did not include other app writers outside packet HUNT_SCOPE.

## FANOUT_INPUT

```text
ROOT_FINDING_ID: FINDING-006
INVARIANT: WBAutoBudgetTopUp is the bot auto-budget journal only. Manual seller-portal deposits are outside this journal SoT. Unused wallet promo stays on live WB cashbacks.
NEW_FINDING_IDS: (none)
CHILD_CHAT_CANDIDATES: (none)
ITEMS_NOT_REQUIRING_CHAT: FINDING-006 (known FALSE_POSITIVE, not re-emitted), ROOT-001, FINDING-002, HC-001, FINDING-003, FINDING-004, HC-FINDING-004-STALE-TEST, FINDING-005
PREREQ: do not emit GO; do not emit bare /opsx-fix-bug; do not create FINDING-007; do not reopen closed findings; do not classify or close
```

LEARNING_INPUT_STATUS:
- ready
- blockers: none
- evidence available: this proof; CLASSIFIER FALSE_POSITIVE / ROUTE_C; no HC candidate packets

Risks:
- A later writer outside this packet scope that inserts seller-portal deposits into WBAutoBudgetTopUp would be a new same-invariant sibling, not a current candidate.

Need from user:
- none

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/Python/packet writes
- Artifacts written via Cursor Write tool (utf-8 path writes)
- FINDING-006.md / ROOT-001.md / FINDING-002.md / HC-001.md / FINDING-003.md / FINDING-004.md / HC-FINDING-004-STALE-TEST.md / FINDING-005.md / CASE.md / LEDGER.md / INDEX.md / ROUTE-TRACE.jsonl / app/** / tests/** / team/CHECKPOINT.json not edited
- No findings/HC-* candidate (HUNT_RESULT=CLEAR)
- MISSION_COMPLETE: no

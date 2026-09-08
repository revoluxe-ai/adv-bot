FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: ROOT-001
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: H1 90d lookback false-stop — overlay OFF while campaign leftover remains
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: root
STATUS: closed_fixed
CHAT_REQUIRED: true
CLAIM_PRIORITY: 1
PACKET_PATH: findings/ROOT-001.md
OWNER_CHAT: SUP-PROMOBONUS-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z/ROOT-001/2026-09-07T11:54:28Z
CLAIMED_AT: 2026-09-07T11:54:28Z
COMPLETED_AT: 2026-09-07T13:35:05Z
PACKET_PURPOSE: closure
INVARIANT: Overlay не должен AND-stop (usable=false / M=1), пока на кампании есть usable leftover, даже при pool=0. Окно 90d не имеет права выкинуть живой leftover из ledger.
ORIGINAL_FINDING: H1 90d lookback false-stop: 90-day ledger window can turn overlay OFF while promo leftover still sits on the campaign (false AND-stop when pool=0).
EVIDENCE: Pre-fix load_campaign_ledgers ставил cutoff=now-PROMO_LOOKBACK_DAYS (90). GO hop 2026-09-07T12:30:20Z: load_campaign_ledgers читает allocation и spend без cutoff (окна выровнены). UPD ingest lookback не расширен. GREEN_CONFIRMED leftover-older-than-lookback. Closure 2026-09-07T13:35:05Z closed_fixed CLOSED_GREEN.
RUNTIME_PATH: app/modules/auto_budget_manager/promo_ledger.py
CAUSAL_BOUNDARY: PromoStateService.refresh → load_campaign_ledgers (no 90d cutoff on leftover-usable load) → resolve_promo_availability → RedisPromoStateManager.set.campaigns[].usable
WRITE_BOUNDARY: Redis derived promo overlay (usable/fraction); downstream shop-runner CPO/limits/budget reads treat leftover as exhausted.
SOURCE_SNAPSHOT: intakes/INTAKE-001.md H1; results/ADJUDICATION-INTAKE-001.md; results/FORENSICS-ROOT-001.md
DISPOSITION: closed_fixed
CREATED_AT: 2026-09-07T11:50:00Z
LAST_ACTIVITY_AT: 2026-09-07T13:35:05Z
BLOCKER:
RESULT_PATH: results/OWNER-CLOSURE-ROOT-001.md
EPISODE_TERMINAL: FIXED
RED_EVIDENCE_PATH: results/RED-ROOT-001.md
GREEN_EVIDENCE_PATH: results/GREEN-ROOT-001.md
OWNER_GO_RECEIPT_PATH: results/OWNER-GO-ROOT-001.md
FIX_EVIDENCE_PATH: results/FIX-ROOT-001.md
OWNER_CLOSURE_PATH: results/OWNER-CLOSURE-ROOT-001.md
HUMAN_SUMMARY_PATH: results/HUMAN_SUMMARY.md
TEST_ID: tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero
TEST_CONTENT_SHA256: ec18863bc09e7075787173b86c854ec6019eac58394d746904b7494c59eeb72a
FANIN_PATH: results/FANIN.md
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z chat_label="SUP-PROMOBONUS-FIX-20260907"

VERDICT: fix_now
RUNTIME_REACHABLE: yes
DEAD_OR_LEGACY: no
WRITE_BOUNDARY_REACHABLE: yes
CURRENT_CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
ROUTE_RECONCILIATION: MATCH
FINDING_TERMINAL: yes
FINDING_TERMINAL_KIND: CLOSED_GREEN
CASE_CLOSED: no
MISSION_COMPLETE: no
WORKTREE_STATUS: UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
COMMIT_CREATED: NO

ENTRYPOINT_CHAIN:
- shop-runner wb_shop.py TaskGroup → auto_budget_watchdog (manager.py) → AutoBudgetService.refresh_promo_state → PromoStateService.refresh → load_campaign_ledgers → Redis set
- WBShopDataManager.get_complex_advs / get_pre_complex_advs / _build_pre_complex_adv читает Redis overlay; fraction_from_cached_state пропускает not campaign.usable → M=1

MINIMAL_FIX_PLAN:
- files allowed: app/modules/auto_budget_manager/promo_ledger.py (и узкий caller PromoStateService.refresh, если cutoff надо снять только для leftover-usable)
- files forbidden: tests (RED пишет /opsx-test); app product за пределами ledger/refresh; alembic; enable RaisePlanOnPromobonuses; FINDING-H2..H6
- exact behavior change: leftover success-tranche с remaining>0 и не expired остаётся campaign_usable=true вне 90d окна; spend/allocation window alignment не должен false-stop живой leftover
- no-op: не расширять UPD ingest окно без отдельного finding
- this hop: ROOT-001 closed_fixed CLOSED_GREEN; production_patched uncommitted; case remains open (H2-H6 backlog)

RESIDUAL_ON_INTAKE:
- FINDING-H2..FINDING-H6 backlog (different invariant); MAX_ACTIVE_FINDINGS=1; не claimable until claim-next
- FOLLOW_UP_SCOPE: FINDING-H2 next via /opsx-claim-next-bug
- AUTO_MATERIALIZE: false

NEXT_COMMAND (STATUS=closed_fixed; ROOT CLOSED_GREEN; CASE open; backlog H2-H6):
/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z chat_label="SUP-PROMOBONUS-FIX-20260907"

MODE: closed_fixed; GREEN_CONFIRMED; production_patched uncommitted; CASE not closed

FORBIDDEN:
- do not git commit / push / PR from this hop
- do not close FINDING-H2..H6
- do not claim FINDING-H2 from CLOSURE_OPERATOR
- do not invent a second case
- do not enable RaisePlanOnPromobonuses
- do not rewrite FANIN.md
- do not create LEARNING_DECISION
- do not start FINDING-H2..H6 implementation here
- do not claim ROOT-001 of BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

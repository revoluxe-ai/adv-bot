# Owner manual test checklist — card A/B Hold epoch flow (§25.1)

**Status:** pre-rollout (OD-05 open — no broad enable without owner sign-off)  
**Scope:** epoch-managed flow behind feature flag; legacy NULL-phase MVP-1 unchanged  
**Decisions:** `ab-hold-epoch-lifecycle-and-generation-ownership`, `card-ab-hold-write-path-ownership`

## Preconditions

- [ ] Feature flag for epoch-managed ENTER enabled only for test shop/campaign (not broad prod enable)
- [ ] Campaign: V3 auto-updater, bot active, positive `max_price_for_order`
- [ ] Stats fresh enough for Enable (§2a gate)
- [ ] CONTROL / task ID documented for this test run

## S1 — ENTER → epoch phases (not legacy auto-ACTIVE)

| Step | Action | Pass | Fail |
|------|--------|------|------|
| 1.1 | Telegram Enable A/B Hold | Mode `PENDING_SETUP`, phase `awaiting_keyword_confirm` (epoch flag ON) | Mode `ACTIVE` immediately or phase NULL with auto-ACTIVE on first tick |
| 1.2 | Wait one shop-runner tick | `process_ab_setup` does **not** write TP or set ACTIVE | TP written on ENTER or ACTIVE without confirms |
| 1.3 | Legacy campaign (phase NULL, flag OFF) | Still reaches ACTIVE via legacy setup when allowed-set OK | Legacy path broken / epoch gate applied |

## S2 — WARM_UP timer

| Step | Action | Pass | Fail |
|------|--------|------|------|
| 2.1 | Confirm keyword set, start WARM_UP (≥24h) | Phase `warm_up`, timer fields persisted | TP fixed before confirm |
| 2.2 | Before 24h elapsed | Phase stays `warm_up`; no TP confirm screen forced | Early transition to TP confirm |
| 2.3 | After 24h + shop-runner tick | Phase auto → `awaiting_tp_confirm` (no TP write) | Stuck in `warm_up` forever or TP auto-written |

## S3 — Confirms → PENDING intent

| Step | Action | Pass | Fail |
|------|--------|------|------|
| 3.1 | Confirm target places | Durable `confirmed_target_places_json`; phase advances | TP recalculated from live position without confirm |
| 3.2 | Confirm Auto participation + bid | `pending_intent_json`, generation bump, sync `pending` | ACTIVE before intent or WB sync |
| 3.3 | Repeat confirm (same generation) | Idempotent no-op (duplicate idempotency key) | Generation bumped again |

## S4 — WB sync → ACTIVE

| Step | Action | Pass | Fail |
|------|--------|------|------|
| 4.1 | Successful WB sync tick | `sync_status=complete`, mode `ACTIVE`, phase `ready_active` | ACTIVE with partial sync |
| 4.2 | Simulated WB failure | `sync_status=partial`, phase `wb_sync`, same generation/intent | ACTIVE or generation bump |
| 4.3 | Retry after fix | Same generation succeeds → ACTIVE without re-confirms | User must re-confirm TP/Auto |

## S5 — Stale stats freeze (§23)

| Step | Action | Pass | Fail |
|------|--------|------|------|
| 5.1 | ACTIVE + stale stats | Hold enforcement / common bid / AutoReset skip mutations | Keywords minused or bids changed on stale |
| 5.2 | Same campaign | Campaign **not** stopped solely due to stale freeze | Campaign paused/stopped only because of freeze banner |
| 5.3 | Stats fresh again | Hold enforcement and bidder resume normal behavior | Permanent freeze after one stale tick |

## S6 — EXIT

| Step | Action | Pass | Fail |
|------|--------|------|------|
| 6.1 | Telegram EXIT | Mode `OFF`, epoch fields cleared (generation 0, phase NULL) | Stale snapshot or phase left set |
| 6.2 | Re-ENTER | New epoch from keyword confirm (not silent upgrade) | Old intent/generation reused |

## Sign-off

| Field | Value |
|-------|-------|
| Tester | |
| Date | |
| Shop / adv_id | |
| Result | PASS / FAIL |
| Notes | |

**Broad enablement:** blocked until OD-05 closed and this checklist PASS on staging/test cohort.  
See also: `rollout/od05-readiness.md` (readiness API + sign-off; OD-05 remains OPEN until owner accepts).

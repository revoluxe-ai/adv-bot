---
cursor:
  subagentId: "bc-aca7c624-5ad0-5cb7-accb-0a379a3f5813"
---

# Task 4.3 — allocator parameter lock (Owner decision)

**Status:** `ALLOCATOR_PARAMETERS_READY_FOR_OWNER_GO`  
**Implementation:** NO. **OpenSpec change:** NO. **PR:** NO.  
`HEADROOM_ALLOCATOR_NOT_ACCEPTED` stays until Owner GO. This packet does not flip it.

**Direction already accepted:** score-ranked steps (Candidate B). Tier rules are hard eligibility gates only (Candidate C). Proportional headroom splitting stays rejected. `shop_headroom_rub` is not a pool. The allocator does not recompute shop GMV, shop DRR, campaign attribution, campaign DRR, expected attributed order value, or target CPO.

Design packet: `internal/hierarchical-ad-control-settings/task-43-allocator-design.md`  
ADR: `openspec/decisions/drr-cpo-price-semantics/decision.md` §4–§10.

## Lanes

| Lane | Agent | Artifact |
|------|--------|----------|
| A sensitivity | [Lane A parameter sensitivity](bc-a625cf58-b58c-5da1-9598-c6b57cee619b) | `/tmp/allocator-param-lock/lane-a-sensitivity.md` |
| B stability | [Lane B oscillation stability](bc-c7f0a72b-e90b-5e52-84a0-1ce9db392d81) | `/tmp/allocator-param-lock/lane-b-stability.md` |
| C low-data / lag | [Lane C low-data lag](bc-4b80ab6c-bb84-5450-b874-8e2191d96e46) | `/tmp/allocator-param-lock/lane-c-low-data.md` |
| D portfolio | [Lane D portfolio cases](bc-90b81b15-a61f-552e-a119-f6917f19e2bd) | `/tmp/allocator-param-lock/lane-d-portfolio.md` |

Lane B’s executive starvation table does not match its raw dump. S3 was re-run from `/tmp/allocator-param-lock/lane_b_sim.py` and matches the raw dump. S4 in the writeup (`302_first_tick=None`) does not match the current simulator: with zero-step campaigns skipped before filling K, campaign 302 increases on tick 2 after 301 hits `absolute_max=160`. The lock uses that re-run.

Lane B’s `floor_headroom_rub` is an absolute headroom gate, not the direct-order floor. Order-floor evidence is lanes A, C, and D.

## Locked recommendations

```
K:
RECOMMENDED_DEFAULT: 1
SAFE_RANGE: 1–2
RATIONALE: K is the maximum number of campaigns that may receive an INCREASE on one tick. K=1 makes a shop-wide equal raise impossible. Lane A (330 cells, FALSE_WINNER=0 at floor>=5): at +20000 headroom, K=1 increases only the strongest scored campaign (101); K=2 and K=3 increase 101 and 102 on every floor×band combo. Lane D P3: K movers are exactly the top K gaps (601, then 602, then 603), never all 12. K=2 is the Owner override when two tied campaigns should both step (P2) or rank-2 must move on the same tick. K equal to the eligible set is rejected. K_decrease uses the same default 1 (safe range 1–2) so overspend also cuts one campaign per tick (P10).

DEAD_BAND:
RECOMMENDED_DEFAULT: 0.05
SAFE_RANGE: 0.05–0.10
RATIONALE: Shop neutral zone, not the campaign CPO band. Economically equivalent to zero when allowed_shop_ad_spend_rub > 0 and abs(shop_headroom_rub) / allowed_shop_ad_spend_rub <= 0.05, and when headroom == 0. The boundary is inside the band (Lane D: +4000/80000 = 0.05 does not act; +8000/80000 = 0.10 does). On an 8% target this is 0.4 percentage points of shop DRR. Lane A: 0.02 starts an increase at +4000 and a decrease at −4000; 0.10 also holds ±4000. Lane D P6: +500, +1600, and +4000 do not increase at 0.05; +500 does not increase at 0.02, 0.05, or 0.10. 0.10 is the wide edge: it also suppresses a real 10% underspend (+8000). Existing minimum_headroom_rub stays an extra increase-only absolute gate and does not replace this ratio.

MIN_DIRECT_ORDER_FLOOR:
RECOMMENDED_DEFAULT: 10
SAFE_RANGE: 5–20
RATIONALE: Hard increase gate on DIRECT orders from Task 4.1. Decrease does not use this floor. Lane C: floor 1 increases a solo 1-order campaign; floor 3 increases a solo 3-order campaign; floor >= 5 blocks both solos. In a mix, the 3-order campaign never outranks a 25-order campaign at any tested floor. Lane A: floor 10 and floor 20 both keep the 50-order winner eligible; floor 0 and 1 are rejected. Lane D P1: at floor 10 the 2-order and 4-order campaigns never increase; K=1 moves only the 60-order campaign. Floor 10 is stricter than the minimum that blocks one-order and three-order false winners, and it still leaves the reliability damper in force below 20 orders. Floor 5 is the bottom of the range. Floor 20 is the top: it also removes Lane C’s 10-order campaign that is 50% under target (score 0.25 vs a 50-order campaign at 0.125). That outrank is gap weighting, not a one-order fluke; tighten to 20 only if Owner wants every sub-20 sample ineligible.

ZERO_HEADROOM_BEHAVIOR:
RECOMMENDED_DEFAULT: Z0
RATIONALE: headroom == 0, or inside DEAD_BAND, or headroom is null, or allowed spend is missing or <= 0: every campaign HOLD. No increase and no decrease. Positive headroom outside the band starts the increase machine only. Negative headroom outside the band starts the decrease machine only. Z1 (decrease still allowed on the boundary) is rejected. Lane D P8: at exact zero, Z0 holds every campaign and Z1 decreases the over-target campaign. Lane B’s closed S2 run at band 0.05 has 0 actions under both Z0 and Z1, because those residuals sit inside the band and never open a direction. Zero headroom does not trigger increase.

ATTRIBUTION_LAG_GATE:
RECOMMENDED_DEFAULT: Read Task 4.1 trust fields only. No lag-day formula. No second attribution model. Optional L1 max_lag_days stays off.
RATIONALE: Lane C C3 (orders still 0, ORDER_VALUE_UNAVAILABLE or DIRECT_ATTRIBUTION_MISSING) HOLD. C4 incomplete window, C5 stale, C6 reconciliation fail: increase and decrease both blocked. C7 shop insufficiency: no proposals. C8 stale sibling does not freeze a fresh sibling. C9 sufficiency=SUFFICIENT but coverage INCOMPLETE: fail closed. No fixture supported a weaker decrease trust gate.

INCREASE_GATES:
- shop_sufficiency == SUFFICIENT
- shop_headroom_rub > 0 and strictly outside DEAD_BAND (ratio > 0.05)
- shop_headroom_rub >= configured minimum_headroom_rub
- campaign enrolled, not legacy passthrough, increase feature enabled
- campaign_sufficiency == SUFFICIENT
- window_coverage == COMPLETE
- freshness == FRESH
- reconciliation == OK
- blocker set contains none of: DIRECT_ATTRIBUTION_MISSING, DIRECT_ATTRIBUTION_INSUFFICIENT, ATTRIBUTION_WINDOW_INCOMPLETE, ATTRIBUTION_FACT_STALE, ORDER_VALUE_UNAVAILABLE, SHOP_ORDER_GMV_INCOMPLETE, SHOP_SPEND_INCOMPLETE, CPO_INPUTS_INCOMPLETE
- direct_orders >= 10
- target_cpo_rub is not null and observed_cpo_rub is not null
- observed_cpo_rub < target_cpo_rub * (1 - 0.05)
- increase cooldown elapsed and increase tick-memory complete; incomplete memory => no increase
- clamped increase step > 0 (does not consume K otherwise)
- campaign is among the top K=1 by increase score

DECREASE_GATES:
- shop_sufficiency == SUFFICIENT
- shop_headroom_rub < 0 and strictly outside DEAD_BAND
- campaign enrolled, not legacy passthrough, decrease feature enabled
- campaign_sufficiency == SUFFICIENT
- window_coverage == COMPLETE
- freshness == FRESH
- reconciliation == OK
- same ADR blocker set empty
- direct_orders >= 1
- target_cpo_rub is not null and observed_cpo_rub is not null
- observed_cpo_rub > target_cpo_rub * (1 + 0.05)
- decrease cooldown elapsed and decrease tick-memory complete; incomplete memory => no decrease
- clamped decrease step > 0 (does not consume K otherwise)
- campaign is among the top K_decrease=1 by decrease score
- not started when headroom == 0 or inside DEAD_BAND

RANKING_SCORE_INPUTS:
- From Task 4.1 only: target_cpo_rub, observed_cpo_rub, direct_orders
- reliability = min(1, direct_orders / 20); 20 is the full-weight normalizer, not the hard floor
- increase gap = (target_cpo_rub - observed_cpo_rub) / target_cpo_rub
- decrease gap = (observed_cpo_rub - target_cpo_rub) / target_cpo_rub
- score = gap * reliability; require score > 0
- not inputs: spend share, shop_headroom_rub magnitude, catalog price, LINKED facts, recomputed DRR

TIE_BREAK_RULE:
- Sort score descending, advert_id ascending
- Equal max-CPO deltas only when scores are exactly equal and K covers that tied prefix
- That case is a tie, not a headroom split

REPEATED_TICK_BEHAVIOR:
- One shop sign per tick: increase machine or decrease machine, never both
- Ceiling steps do not spend headroom and do not rewrite 4.1 facts
- Re-run of Lane B S3, frozen facts, K=1: cooldown 1 => campaign 301 moves every tick, 302/303/304 never move in 24 ticks; cooldown 2 => 301 and 302 alternate, 303 and 304 never move in 24 ticks; cooldown 4 => 302, 303, and 304 receive a step on ticks 1, 2, and 3 while 301 cools
- Re-run of S4: after 301 reaches absolute max, the zero step is skipped and 302 increases on the next tick
- Lane B S1 and S2: same-campaign increase-then-decrease pairs within 2 and within 4 ticks = 0 at the recommended cell
- Lane B S6 raw: a sign flip decreases the over-target campaign; the under-target campaign that just increased is not cut

HYSTERESIS_RULE:
- Shop layer is DEAD_BAND 0.05 (both directions off inside it)
- Campaign layer is hysteresis_ratio 0.05 around that campaign’s target CPO (increase below target*(1-0.05); decrease above target*(1+0.05))
- No cross-direction block. Lane B’s narrative asked for a 2-tick cross block; the raw S6 timelines have ping-pong count 0 without it, because an under-target campaign is not decrease-eligible

COOLDOWN_RULE:
- Separate increase and decrease clocks, using the existing feature fields cooldown_ticks
- Operating point: cooldown_ticks = 2 on each machine. Safe range 2–4. cooldown_ticks = 1 is outside the range: with K=1 the top score takes every tick until its step is zero
- Incomplete tick memory fails closed for that direction. Do not treat missing memory as “never acted”

RATE_LIMIT_RULE:
- At most K=1 increase and, on a decrease tick, at most K_decrease=1 decrease
- One configured step per selected campaign: min(iteration cap, safety step, room to absolute min/max), quantized 0.01 HALF_UP
- Headroom magnitude does not scale the step. Lane D P7: headroom +40000, sum of deltas = 30, not 40000
- A campaign with clamped step <= 0 is skipped before K is filled

SIMULATION_RESULTS:
- Lane A: 330 cells. FALSE_WINNER 0 in the 3×3×3 grid at floors 5/10/20. ZERO_INCREASE_VIOLATION 0. RANK_INVERSION 0. Cold-start campaign 105 never increased. Step never scaled by headroom. At K=1, band 0.05, floor 10, headroom +20000: increase 101 only. Headroom 0 and in-band residuals: HOLD under Z0
- Lane B re-run: S3 starvation as in REPEATED_TICK_BEHAVIOR. S4 handoff at tick 2 once the leader is capped, if zero-step does not consume K. S5 cooldown 2: 12 increases in 24 ticks, 0 cooldown violations. S2 jitter ±4%: direction flips 0, in-band actions 0 at bands 0.02/0.05/0.10. Stale ticks: 0 increases. Closed Lane B S2 at band 0.05: Z0 and Z1 both 0 actions. Lane D P8 is the case that separates them: Z1 decreases at exact zero, Z0 does not.
- Lane C: floor >= 5 blocks solo 1-order and solo 3-order increases. Delayed attribution HOLD via 4.1 blockers. Incomplete, stale, and reconciliation-fail block both directions. Shop insufficiency emits nothing. One stale campaign does not block its fresh sibling
- Lane D recommended cell K=1, band 0.05, floor 10, Z0: invariant violations 0. P2 tie moves only the lower advert_id at K=1. P4 all blocked: 0 increases, and positive headroom does not decrease. P5 spend is not in the score. P8 exact zero is HOLD under Z0. P9 increases on overspend: 0. P10 healthy campaign spared

OSCILLATION_RISK: LOW at K=1, dead band 0.05, cooldown 2, campaign hysteresis 0.05, Z0. Same-campaign ping-pong counts were 0. Band 0.02 starts actions at ±4000 on an 80_000 allowed spend. Z1 starts a decrease at exact zero when a campaign is above its own CPO band (Lane D P8).

STARVATION_RISK: MEDIUM, accepted for V1. With K=1 and cooldown 2, frozen facts, rank 3 and below did not move in 24 ticks. They move when a leader is on cooldown long enough (cooldown 4), becomes ineligible, or hits a zero step. K=2 is the override if that wait is too long. It is not the default.

EXPLORATION_RISK: LOW at floor 10 and K=1. Two-order and four-order apparent winners do not increase. K=3 at floor 10 also steps a 12-order mid-gap campaign (Lane D P1); K=1 prevents that. A 10-order campaign 50% under target can still outrank a 50-order campaign 12.5% under target because of the gap weight. That is the score, not a one-order false winner.

OVERSPEND_RISK: LOW. No increase at headroom <= 0 or inside the dead band. Large negative headroom cuts only the worst eligible over-target campaign. Campaigns at or below target*(1.05) are spared. The step is not a slice of headroom.

RECOMMENDED_OWNER_DECISION:
Accept K_increase=1 (K_decrease=1), shop DEAD_BAND ratio 0.05 inclusive, MIN_DIRECT_ORDER_FLOOR=10 for increase only, ZERO mode Z0, attribution gate = Task 4.1 coverage/freshness/reconciliation/sufficiency/ADR §9 blockers with no lag-day model, campaign hysteresis 0.05, reliability full-weight 20, cooldown_ticks=2, and skip zero-step campaigns before filling K. Keep HEADROOM_ALLOCATOR_NOT_ACCEPTED until that GO is explicit.

PARAMETERS_READY_TO_LOCK: YES

CRITICAL:
None. No simulation result overturned the conservative-increase posture.

HIGH:
- Select K only among campaigns whose clamped step is > 0. The design-packet pseudocode chooses K first and then HOLDs a zero step, which permanently consumes the slot after the leader hits absolute max. The re-run shows the skip hands the slot to the next rank.
- Do not set cooldown_ticks=1 with K=1. Re-run: the top campaign then takes all 24 increase ticks.
- Lane B’s executive table (rank-2 first move at tick 12) is not evidence. The raw dump and the re-run say rank-2 never moves at cooldown 1, and moves on tick 1 at cooldown 2.

MEDIUM:
- Rank 3+ starvation over a 24-tick frozen window at K=1 and cooldown 2.
- Floor 10 still allows a large CPO gap with 10 DIRECT orders to outrank a small gap with 50 orders (Lane C C10 scores 0.25 vs 0.125). Move the floor to 20 to close that.
- Dead band 0.10 also blocks a 10% shop underspend. Stay at 0.05 unless Owner wants that extra inert zone.
- Z0 does not trim a locally over-target campaign when the shop is exactly on target.

LOW:
- Exact score ties may take equal steps only when K covers the tie (Lane D P2, K=2). Default K=1 steps the lower advert_id only.
- Sufficiency labeled SUFFICIENT with incomplete coverage fails closed (Lane C C9).
- minimum_headroom_rub remains a configured absolute increase gate on top of the ratio band.

IMPLEMENTATION: NO
OPENSPEC_CHANGE: NO
PR: NO

FINAL_STATUS: ALLOCATOR_PARAMETERS_READY_FOR_OWNER_GO
```

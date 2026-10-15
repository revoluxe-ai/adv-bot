---
cursor:
  subagentId: "bc-0e81933b-16fd-5df8-97e5-1f8f1c8fa453"
---

# Task 4.3 — Owner parameter decision

Reconciled from this round's lanes plus the strong-lead review. No repo edits.

Sibling packet (not overwritten): `internal/hierarchical-ad-control-settings/task-43-allocator-parameter-lock.md` (other subagent). It reaches the same K=1, ratio band 0.05, and Z0, with floor 10. Its cited `/tmp/allocator-param-lock` dumps are not on this VM, so those cell counts are not repeated here as verified runs.

Lanes: [Allocator sensitivity lane](bc-4de4b842-afd8-5922-a03e-05737f22e8fa), [Allocator stability lane](bc-faea52ff-a08b-5a42-b334-8c9d0702f666), [Allocator low-data lane](bc-eca908e1-2672-58f8-a2c0-eb834f429dd5), [Allocator portfolio lane](bc-3c3cc3ef-d5b8-52dd-bd11-1f9e9eac2201), [Allocator parameter lead review](bc-84b97832-dd37-5b10-84f9-433b5b9950ec).

```
K:
RECOMMENDED_DEFAULT: 1
SAFE_RANGE: 1
RATIONALE: K is the maximum number of campaigns that may receive an INCREASE on one evidence key, not on one shop-runner loop. An evidence key is (shop, measurement window, window end date): one new closed attribution day. K=1 makes "shop below target => raise everything" impossible, including the case of exactly two eligible campaigns. Sensitivity lane and the lead both reject K>=2 as the default. Portfolio and stability preferred K=2 only to reduce starvation; that preference loses to the conservative-increase rule. K=2 is an Owner override that reopens this decision, not a value inside the safe range. K_decrease is a separate machine and is also 1 (safe range 1–2). Decreases are not uncapped: a shop-wide equal cut is the same failure mode in the other direction. Headroom magnitude never changes K.

DEAD_BAND:
RECOMMENDED_DEFAULT: 0.05
SAFE_RANGE: 0.05–0.10
RATIONALE: Shop neutral zone as a ratio, not rubles. When allowed_shop_ad_spend_rub > 0, the shop is inside the band iff abs(shop_headroom_rub) / allowed_shop_ad_spend_rub <= 0.05. The boundary is inside the band (equal to 0.05 does not act). Unit is that ratio, which is the relative distance of shop DRR to the configured target (headroom / allowed spend). 0.05 is the balanced sensitivity value and matches the design packet's hysteresis_ratio. 0.02 starts actions on small residuals (oscillation). 0.10 is the wide edge: it also holds a real 10% underspend, so it stays the top of the range and not the default. The lead's asymmetric +0.10 / −0.05 shop edges are not locked; increase is made stricter by the order floor, the lag gate, and K, which is what the lanes were asked to test. Campaign hysteresis is a second layer at the same 0.05 (see HYSTERESIS_RULE). minimum_headroom_rub stays an extra absolute increase-only gate from existing config. It is not redefined here and the test fixture value 100 RUB is not a production default.

MIN_DIRECT_ORDER_FLOOR:
RECOMMENDED_DEFAULT: 8
SAFE_RANGE: 5–10
RATIONALE: Hard increase gate on DIRECT attributed orders supplied by Task 4.1 for the same window as target_cpo_rub and observed_cpo_rub. Decrease does not use this floor (decrease needs direct_orders >= 1 and a computable observed CPO above the campaign band). Floor 1 is rejected: one order is a false winner. Floors 3 and 4 still admit the small-order excellent-DRR case. Floor 5 is the bottom of the range: it blocks the 0-order, 1-order, and 2–4 order cases the low-data lane tested, and the lead's worst-case "true target looks like a 2× winner" rate is still about 11% at 5. Floor 8 is the first point that lead put near 5% on that check, and it is the top of the low-data lane's range before small campaigns freeze. Floor 10 remains acceptable inside the range if the Owner wants the stricter sibling packet; floor 20 is the score full-weight normalizer, not a hard floor. Score weight stays min(1, direct_orders / 20) above the floor.

ZERO_HEADROOM_BEHAVIOR:
RECOMMENDED_DEFAULT: Z0
RATIONALE: If shop_headroom_rub is null, allowed spend is missing or <= 0, shop sufficiency is not SUFFICIENT, headroom_rub == 0, or the shop ratio is inside DEAD_BAND: every campaign HOLD. No increase and no decrease. Positive headroom strictly outside the band starts the increase machine only. Negative headroom strictly outside the band starts the decrease machine only. Z1 (decrease still allowed on the boundary) is rejected. Zero headroom does not trigger increase. Dust is the ratio band, not a second ruble epsilon.

ATTRIBUTION_LAG_GATE:
RECOMMENDED_DEFAULT: Increase and decrease both require this predicate, using Task 4.1 outputs only. No lag-day formula. attribution_lag_days is not read. Optional L1 max_lag_days stays off. Predicate: AttributionCoverage.status == COMPLETE AND every DayReconciliationResult.passed for the window AND source_complete_through >= window end (window closed) AND shop data_sufficiency == SUFFICIENT AND campaign data_sufficiency == SUFFICIENT AND the campaign measurement window matches the shop window AND none of the ADR §9 blockers are set (DIRECT_ATTRIBUTION_MISSING, DIRECT_ATTRIBUTION_INSUFFICIENT, ATTRIBUTION_WINDOW_INCOMPLETE, ATTRIBUTION_FACT_STALE, ORDER_VALUE_UNAVAILABLE, SHOP_ORDER_GMV_INCOMPLETE, SHOP_SPEND_INCOMPLETE, CPO_INPUTS_INCOMPLETE). If any required status is absent, the predicate is false.
RATIONALE: Unknown, stale, incomplete, or unreconciled facts produce no increase and no decrease. A stale or failed sibling does not, by itself, freeze a different campaign whose own 4.1 record passes. The allocator does not invent a second attribution model and does not interpret attribution_lag_days, which is present on ActualDrrObservation but not defined as an allocator input. There is no separate freshness enum to require; closed coverage plus SUFFICIENT is the freshness condition.

INCREASE_GATES:
- Allocator still not accepted for production write; this list is the decision, not an enablement
- shop_headroom_rub is not null; allowed spend > 0; shop data_sufficiency == SUFFICIENT
- shop ratio > 0.05 (strictly outside the band, positive)
- shop_headroom_rub >= configured minimum_headroom_rub
- this evidence key has not already emitted an increase
- increase feature enabled; campaign enrolled; not legacy passthrough
- ATTRIBUTION_LAG_GATE true for that campaign
- direct_orders >= 8
- target_cpo_rub and observed_cpo_rub present and target_cpo_rub > 0
- observed_cpo_rub < target_cpo_rub * (1 - 0.05)
- increase cooldown elapsed on prior evidence keys; increase tick-memory complete, else no increase
- clamped increase step > 0 (a zero step does not consume K)
- campaign is the top 1 by increase score after the tie-break

DECREASE_GATES:
- shop_headroom_rub is not null; allowed spend > 0; shop data_sufficiency == SUFFICIENT
- shop ratio < -0.05 (strictly outside the band, negative)
- this evidence key has not already emitted a decrease
- decrease feature enabled; campaign enrolled; not legacy passthrough
- ATTRIBUTION_LAG_GATE true for that campaign (same trust bar as increase)
- direct_orders >= 1 and observed CPO is computable (0 DIRECT orders: no decrease; ADR §9)
- observed_cpo_rub > target_cpo_rub * (1 + 0.05)
- campaigns at or below that band are spared
- decrease cooldown elapsed; decrease tick-memory complete, else no decrease
- a prior increase does not block a later decrease when the shop sign has flipped
- clamped decrease step > 0 (a zero step does not consume K_decrease)
- campaign is the top 1 by decrease score after the tie-break
- not started at headroom == 0 or inside the band

RANKING_SCORE_INPUTS:
- Task 4.1 only: target_cpo_rub, observed_cpo_rub, direct_orders
- reliability = min(1, direct_orders / 20)
- increase gap = (target_cpo_rub - observed_cpo_rub) / target_cpo_rub
- decrease gap = (observed_cpo_rub - target_cpo_rub) / target_cpo_rub
- score = gap * reliability; score <= 0 is ineligible
- not inputs: spend share, shop_headroom_rub magnitude, catalog price, LINKED facts, recomputed shop GMV, recomputed shop DRR, recomputed campaign DRR, recomputed expected order value, recomputed target CPO
- the lead's decrease score (spend - orders * target_cpo) is not locked; it would rank on spend, which these lanes kept out of the score

TIE_BREAK_RULE:
- Increase and decrease: score descending, then direct_orders descending, then advert_id ascending
- Deterministic. No randomness. No preference for a lower current max CPO
- Equal steps happen only when scores tie and K covers that tied prefix. Default K=1 steps one campaign

REPEATED_TICK_BEHAVIOR:
- The allocator is a pure function of 4.1 facts plus complete step memory
- One shop sign per evidence key: increase machine or decrease machine, never both
- At most one increase and, on a decrease key, at most one decrease for the whole shop
- A later runner loop on the same evidence key HOLDs, even if cooldown would otherwise skip to the next rank, and even if Apply has already changed the current max CPO
- A restated day is not a new key. A key that moves backwards yields no proposals
- Cooldown is counted in successive evidence keys (closed attribution days), not runner iterations
- Ceiling steps do not spend headroom and do not rewrite 4.1 facts
- With frozen facts, K=1 and no evidence-key rule, cooldown 2 alternates rank 1 and rank 2 and thereby raises more than one campaign on the same facts. That behavior is rejected
- Across new evidence keys, cooldown 2 lets rank 2 move on the days rank 1 is cooling. Rank 3+ waits until a leader is ineligible, cooling, or has a zero step

HYSTERESIS_RULE:
- Shop: DEAD_BAND 0.05 inclusive, both directions off inside it
- Campaign: hysteresis_ratio 0.05 around that campaign's target CPO. No increase at or above target * 0.95. No decrease at or below target * 1.05
- No shop-sign latch and no cross-direction dwell. An under-target campaign is not decrease-eligible, so the same campaign does not step up and down on one sign flip
- Every step must re-qualify. Nothing is latched from the previous key except cooldown memory

COOLDOWN_RULE:
- Separate increase and decrease clocks
- Operating point: cooldown_ticks = 2 evidence keys since the last step in that same direction. Safe range 2–4
- cooldown_ticks = 1 is outside the range: with K=1 the top score can step on every new evidence key
- Incomplete or missing tick memory fails closed for that direction. Do not treat missing memory as "never acted"
- A recent increase does not add extra delay to a decrease

RATE_LIMIT_RULE:
- Per evidence key: at most 1 increase, or on a decrease key at most 1 decrease
- One configured step per selected campaign: min(maximum_increase_per_iteration_rub or maximum_decrease_per_iteration_rub, safety bounds, room to absolute min/max)
- Headroom magnitude does not scale the step and is not divided across campaigns
- A campaign whose clamped step is <= 0 is skipped before K is filled
- No additional 10% up / 20% down cap in this lock; iteration caps already exist on the feature params

SIMULATION_RESULTS:
- Sensitivity: tested K in {1, 2, 5, unlimited}, shop bands about 2% / 5% / 10%, floors 1 / 3 / 5 / 8 / 10. Recommended K=1, shop band 5%, floor 5, symmetric campaign h=0.05. K>=3 and floor 1 rejected
- Stability: 12-tick traces. Aggressive (K=5, no band, no cooldown) sawtooths the same campaign. K=1 monopolizes every increase. K=3 jumps three ceilings in one tick. Recommended K=2 with h=0.05 and a cross-direction dwell. The dwell is not locked: an under-target campaign is already ineligible to decrease. The K=2 recommendation is not locked
- Low-data: 0 DIRECT orders => no increase and no decrease. 1 order and 2–4 orders with excellent apparent DRR => no increase. Incomplete window, stale sufficiency, and reconciliation failure => both directions blocked. Passing case (closed window, reconciliation ok, orders at the floor, positive headroom) => increase allowed. Recommended floor 5, safe 3–8. Default moved to 8 because 5 is only the bottom of the range
- Portfolio: positive headroom is room to spend; negative is overspend (ADR §5, headroom_eval.py). One strong campaign steps; weak campaigns hold. Two equals: K=1 steps one by tie-break. Eight eligible: only top K move. All blocked: hold, even if headroom is positive. A high-spend campaign with thin DIRECT evidence does not outrank a smaller campaign with more orders. Slight and large positive headroom both take one bounded step, not a step scaled by rubles. Zero and in-band: hold. Slight and large overspend: decrease only the over-target eligible campaigns, spare the rest. Portfolio wanted K=2; not locked
- Lead: K_increase=1 per evidence key, K_decrease=2, asymmetric band +0.10/−0.05, floor 8, evidence age <= 2 days, step caps 10% up and 20% down. Locked from the lead: evidence-key counting, floor 8, Z0, no use of attribution_lag_days. Not locked: K_decrease=2, the asymmetric band, the 2-day age formula, the percent-of-ceiling step caps, and the spend-based decrease score

OSCILLATION_RISK: LOW. The band holds the shop on small residuals, campaign hysteresis stops a step at the target, one evidence key cannot alternate increase and decrease, and cooldown 2 stops a daily sawtooth. Risk returns if K is counted per runner loop or if cooldown_ticks=1.

STARVATION_RISK: MEDIUM, accepted. K=1 gives the top score the only increase. Rank 2 moves on a later evidence key while rank 1 is inside cooldown 2, or sooner if rank 1 becomes ineligible or has a zero step. Rank 3+ waits. K=2 would cut this and is the override that fails the anti-blanket rule.

EXPLORATION_RISK: MEDIUM, accepted. Campaigns with fewer than 8 DIRECT orders cannot be increased, including a small campaign whose apparent DRR looks excellent. That is the floor doing its job. New campaigns have no special explore slot.

OVERSPEND_RISK: LOW for increases. No increase at zero, inside the band, or on failed attribution. A large overspend cuts one over-target campaign per evidence key, not a slice of headroom. Residual: a campaign with spend and 0 DIRECT orders cannot be decreased by this allocator (ADR §9). That gap is a finding, not a license to decrease on missing orders.

RECOMMENDED_OWNER_DECISION:
Accept Task 4.3 allocator parameters as: K_increase=1 and K_decrease=1 per evidence key (shop, measurement window, window end), not per runner loop; shop DEAD_BAND ratio 0.05 inclusive; campaign hysteresis_ratio 0.05; MIN_DIRECT_ORDER_FLOOR=8 for increase only and direct_orders>=1 for decrease; ZERO mode Z0; attribution gate = COMPLETE coverage, reconciliation PASS, closed window, shop and campaign SUFFICIENT, matching windows, no ADR §9 blockers, and no lag-day model; score = CPO gap times min(1, direct_orders/20); tie-break score, then direct orders, then advert_id; cooldown_ticks=2 evidence keys per direction; skip a zero step before filling K. Keep HEADROOM_ALLOCATOR_NOT_ACCEPTED until a separate implementation GO.

PARAMETERS_READY_TO_LOCK: YES

CRITICAL:
- Count K and cooldown on the evidence key. The design packet's per-runner-tick K plus "skip to the next rank" raises every eligible campaign on the same day's facts. Same-key retries must HOLD.

HIGH:
- ADR §9 forbids a proposal when a campaign has spend and zero DIRECT orders, so the worst spend-only overspender is not unwound here. Do not weaken the order floor to fix that.
- Incomplete step memory fails closed, so the allocator stays inert until some owner supplies complete per-campaign last-step memory. The parameter rule is locked; the memory owner is not chosen here.
- Select K only among campaigns whose clamped step is > 0. Choosing K first and then holding a zero step consumes the only slot after a leader hits its absolute max.

MEDIUM:
- Rank 3+ does not move while two stronger campaigns keep alternating across evidence keys at cooldown 2.
- A campaign can be over its own CPO target while the shop is inside the band. Z0 does not cut it.
- minimum_headroom_rub remains a configured absolute increase gate on top of the ratio. Its production value is not locked in this decision.
- Floor 5 is legal inside the safe range but keeps a higher false-winner rate. Floor 10 is legal and stricter. The default is 8.

LOW:
- attribution_lag_days exists on the observation type and is unused by this gate.
- Exact score ties are broken by higher direct_orders, then lower advert_id.
- A 10% / 20% of current max-CPO step cap was proposed by the lead and is not part of this lock.

IMPLEMENTATION: NO
OPENSPEC_CHANGE: NO
PR: NO

FINAL_STATUS: ALLOCATOR_PARAMETERS_READY_FOR_OWNER_GO
```

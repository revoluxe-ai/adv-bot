---
cursor:
  subagentId: "bc-4eb929d6-be21-5824-a99b-c7af0a6ac898"
---

# Task 4.3 — shop headroom allocator (Owner decision packet)

**Status:** `ALLOCATOR_DESIGN_READY_FOR_OWNER_DECISION`  
**Implementation:** NO. **PR:** NO. **OpenSpec edits:** none. **WB writes:** none. **Apply wiring:** none.

**Baseline:** `/agent/repos/adv-bot` @ `a2e8453e773411eab989b08fa1358f2195c2dee4`  
**Parent change:** `hierarchical-ad-control-settings` (tasks 4.1 and 4.2A stay on their lanes).

**Evidence lanes (Composer 2.5, read-only):**

| Lane | Agent | Artifact |
|------|--------|----------|
| A controller archaeology | [Controller archaeology](bc-7c9fb1c6-e657-50ab-9f42-77ebc68b32ea) | `/tmp/allocator-design/lane-a-controller-archaeology.md` |
| B historical evidence | [Historical failure evidence](bc-c15b8651-2c9d-51e2-8057-bece66572d85) | `/tmp/allocator-design/lane-b-historical-evidence.md` |
| C candidates | [Candidate allocator comparison](bc-2e43ce22-ba81-556a-bdaf-9b25d20ddcc9) | `/tmp/allocator-design/lane-c-candidates.md` |
| D simulation | [Simulation architecture](bc-396bfff2-863d-5cca-b049-bf569726b418) | `/tmp/allocator-design/lane-d-simulation.md` |

**Hindsight:** `HINDSIGHT_UNAVAILABLE`. No Hindsight corpus in the repo or project store. Evidence is repo + store + git-visible docs only.

## Architecture decisions cited

- `openspec/decisions/drr-cpo-price-semantics/decision.md` §4 (target CPO), §5 (shop headroom sign; **does not prescribe equal CPO increases**), §7 (`MAX_CPO_RUB` is a ceiling, not a bid), §9 (fail-closed blockers), §10 (`HEADROOM_ALLOCATOR_NOT_ACCEPTED`).
- `openspec/changes/hierarchical-ad-control-settings/owner-contract.md` — per-function independence; **no accepted production ranking formula**.
- `openspec/changes/hierarchical-ad-control-settings/decisions/hierarchical-ad-control-settings-ownership/decision.md` — configured policy separate from derived headroom; production ranking out of the foundation slice.
- Protocol only: `HeadroomAllocator.propose_bounded_adjustments` in `app/modules/ad_control_settings/domain/headroom.py`.

The ranking formula is deliberately absent. This packet proposes it for Owner GO. It does not create an OpenSpec decision file.

## What the allocator is

```text
shop_headroom_rub
+ CampaignEconomicControlState[]
+ CampaignCpoProposal[]
+ resolved feature modes (increase / decrease / safety)
+ read-only tick memory (cooldown)
→ BoundedCpoProposal[]
```

`shop_headroom_rub` is **ad-spend RUB** (ADR §5):

```text
allowed = whole_shop_order_gmv × configured_shop_target_drr
shop_headroom_rub = allowed − actual_shop_ad_spend
```

`CampaignCpoProposal.target_cpo_rub` is already:

```text
expected_attributed_order_value × effective_target_drr_fraction
```

The allocator **reads** those numbers. It does **not** recompute GMV, DIRECT vs LINKED, observed CPO, or target CPO.

`CampaignEconomicControlState` and `CampaignCpoProposal` are **not** on the stage tree at `a2e8453e`. Task 4.1 must emit them. Minimum fields this design consumes are listed under CONFIG_PARAMETERS. If 4.1 uses different names, the mapping is 4.1’s adapter. The formulas stay ADR §2–§5.

Output aligns with `BoundedCpoProposal`: `current_max_cpo_rub`, `proposed_max_cpo_rub`, `decision`, `reason_codes`. `proposed_max_cpo_rub` is a **safety ceiling**, not a WB bid and not a spend assignment.

## Unit trap (binds every candidate)

Headroom RUB and max-CPO RUB are different units. There is **no accepted spend-response model** (raising the ceiling does not spend `Δmax_cpo × orders`). Therefore:

- Do **not** set `Σ Δmax_cpo = shop_headroom_rub`.
- Do **not** split `shop_headroom_rub` into per-campaign CPO slices.
- Positive headroom is **permission and priority**, not a budget that must be filled this tick.
- V1 capacity is **ordinal**: at most `K` campaigns may take **one** configured step.

Lane C’s “capacity signal that scales a total CPO budget” is rejected for V1. Ordinal-only is the recommendation.

## Increase and decrease are separate machines

Configured today (`app/modules/ad_control_settings/domain/configured.py`):

| Direction | Feature | Existing knobs |
|-----------|---------|----------------|
| Increase | `CPO_INCREASE_ON_HEADROOM` | `minimum_headroom_rub`, `maximum_increase_per_iteration_rub`, `cooldown_ticks`, `min_data_sufficiency` |
| Decrease | `CPO_DECREASE_ON_OVERSPEND` | `maximum_decrease_per_iteration_rub`, `cooldown_ticks`, `min_data_sufficiency` |
| Clamp | `CPO_SAFETY_BOUNDS` | `absolute_min_cpo_rub`, `absolute_max_cpo_rub`, `max_step_up_rub`, `max_step_down_rub` |

Shop sign selects **at most one** direction per tick. A campaign may be eligible for one direction and disabled for the other. `DISABLED` on a feature means that direction emits `HOLD` for that campaign. The other direction is unchanged.

`DynamicDrrControlParamsV1.max_effective_delta_percent` is **not** an allocator step. Foundation dynamic DRR is still a placeholder (`headroom_eval.derive_shop_effective_control_drr` returns the configured target). Do not overload it as hysteresis.

---

## CANDIDATE_A: bounded proportional

**Mechanism.** After direction gating, give each eligible campaign a weight (spend share, or CPO-gap × spend), normalize, and split a tick budget of CPO rub in proportion to weights. Cap each slice by the per-iteration maximum.

| Heading | Policy |
|---------|--------|
| OBJECTIVE | Spread one tick of CPO movement across eligible campaigns in proportion to weights. |
| ELIGIBILITY | Same base gates as the recommendation (enrollment, sufficiency, feature on, ADR §9). Increase only if `headroom > 0` and `headroom ≥ minimum_headroom_rub` and campaign is under its target. Decrease only if `headroom < 0` and campaign is locally over target. |
| RANKING | No explicit order. Share is the rank. |
| HARD_BOUNDS | Existing safety bounds and per-iteration caps. |
| RATE_LIMITS | Per-campaign iteration cap. Total budget is an extra, undefined curve from headroom RUB into CPO RUB. |
| HYSTERESIS | Not native. Needs a new epsilon or it chatters at the target. |
| COOLDOWN | Existing `cooldown_ticks`, if tick memory is passed in. |
| POSITIVE_HEADROOM_POLICY | Weighted increases. Equal weights **are** the forbidden equal raise. |
| NEGATIVE_HEADROOM_POLICY | Weighted cuts. Spend-share weights under-cut small, very-high-DRR campaigns. |
| COLD_START_POLICY | Zero weight when DIRECT orders = 0. |
| INSUFFICIENT_DATA_POLICY | Fail closed per campaign; shop `headroom is None` → no proposals. |

**Why it loses.** It needs a headroom→CPO transfer function the ADR does not provide. Equal or near-equal weights implement the forbidden pattern. Spend weights recreate “large campaigns move most” without a marginal model (lane A: do not copy mass raise).

---

## CANDIDATE_B: score-ranked marginal allocation

**Mechanism.** Score eligible campaigns on the active direction only. Sort by score descending, tie-break `(advert_id)` ascending. Give a **full configured step** to the first `K` campaigns. Everyone else `HOLD`. The score is a **priority**, not a proven marginal ROI (no elasticity in the facts).

| Heading | Policy |
|---------|--------|
| OBJECTIVE | Move the campaigns furthest from their own target CPO, with more weight when DIRECT orders are numerous enough to trust the gap. |
| ELIGIBILITY | Direction-specific. `score > 0` required. Cooldown skips to the next rank. |
| RANKING | `score` desc, `advert_id` asc. |
| HARD_BOUNDS | Step = `min(iteration cap, safety step, distance to absolute min/max)`. Quantize 0.01 RUB HALF_UP. |
| RATE_LIMITS | `K` full steps per tick. Headroom magnitude does **not** scale the step. |
| HYSTERESIS | Dead band around target CPO: inside the band, score is 0. |
| COOLDOWN | Independent increase vs decrease cooldowns. |
| POSITIVE_HEADROOM_POLICY | Increase scores only. Top `K`. No decrease. |
| NEGATIVE_HEADROOM_POLICY | Decrease scores only. Campaigns at or below target score 0 (spared). Top `K` cut. |
| COLD_START_POLICY | Orders = 0 or missing order value → score 0, no proposal. |
| INSUFFICIENT_DATA_POLICY | That campaign score 0. Shop headroom `None` → shop-wide no-op. One bad campaign does not freeze the others. |

**Strength.** Cannot raise every campaign unless `K` is set to the whole eligible set **and** the Owner accepts that. Default `K = 1` makes the forbidden pattern impossible in one tick. Matches historical discipline: one GAP enable per tick; ranked UP; not “lift every keyword”.

**Weakness.** Low-order CPO is noisy, so the score must be damped by an order floor. Starvation of low-score campaigns is accepted in V1 (they wait until they rank). Calling the score “marginal profit” would overclaim.

---

## CANDIDATE_C: tiered eligibility allocation

**Mechanism.** Bucket campaigns with the resolved `DrrProfile` (`max_drr_percent ≥ target_drr_percent`):

- **T0** — facts missing, zero DIRECT orders, not enrolled, legacy passthrough, feature off, sufficiency fail. No action.
- **T_UNDER** — `campaign_actual_drr < target` (increase candidates when headroom > 0).
- **T_BAND** — `target ≤ campaign_actual_drr ≤ max`. Hold on both sides.
- **T_OVER** — `campaign_actual_drr > max` (decrease candidates when headroom < 0).

Within the active tier, either the same step for every member, or round-robin one campaign.

| Heading | Policy |
|---------|--------|
| OBJECTIVE | Act only on structurally under-target or over-max campaigns. |
| ELIGIBILITY | Tier membership plus base gates. Increase tier and decrease tier are disjoint. |
| RANKING | Tier first. Inside the tier: `advert_id` or round-robin. |
| HARD_BOUNDS | Same safety caps. Tier step equals the iteration cap. |
| RATE_LIMITS | Optional cap on how many members of a tier move. |
| HYSTERESIS | The target–max band is the hold zone. Extra epsilon still needed if target == max. |
| COOLDOWN | Existing per-direction cooldowns. |
| POSITIVE_HEADROOM_POLICY | Only T_UNDER increases. |
| NEGATIVE_HEADROOM_POLICY | Only T_OVER decreases. T_UNDER and T_BAND spared. |
| COLD_START_POLICY | T0. |
| INSUFFICIENT_DATA_POLICY | T0 for that campaign. Shop headroom `None` → all T0. |

**Why it loses as the allocator.** Inside T_UNDER, equal steps **are** “shop under target → raise every (eligible) campaign equally” whenever the tier is wide. Round-robin needs extra memory and still equalizes over a few ticks. Tier gates are good **eligibility**. They are a bad **allocation**.

---

## RECOMMENDED_CANDIDATE

**B, with C used only as eligibility gates. A is not used.**

Lane C preferred “C primary, B inside the tier”. This packet reverses that emphasis:

1. Within-tier equal steps are the forbidden invariant in disguise.
2. Proportional splitting (A) crosses the unit trap.
3. Historical shop-scope equal raise is **absent** (good). Historical **intra-campaign** mass raise of every operable keyword (`raise_state_to_target_cpo.py`) is exactly the pattern **not** to copy onto campaigns.
4. Proven anti-blanket pattern to echo: one enable per tick (`pay_for_order` GAP), ranked cost-first UP not wired as a shop allocator, 90% band as hysteresis **concept** only (do not import V3 ladder / `pay_for_order` math).

**Default Owner proposal:** `K_increase = 1`, `K_decrease = 1`, dead band `hysteresis_ratio = 0.05`, `min_direct_orders_for_full_weight = 20`. These four numbers are **not** accepted until the Owner checks them. Until GO, diagnostics stay `HEADROOM_ALLOCATOR_NOT_ACCEPTED`.

### Recommended policy headings

| Heading | Locked recommendation |
|---------|------------------------|
| OBJECTIVE | On a permissive shop sign, move at most `K` campaigns by one bounded max-CPO step toward the gap that 4.1 already measured. Do not fill headroom. Do not equalize. |
| ELIGIBILITY | See pseudocode. C-style gates: T0 never moves; increase only from under-target and below the dead band; decrease only from over-target and above the dead band. Feature flags independent. |
| RANKING | Increase: `gap_below × order_reliability`. Decrease: `gap_above × order_reliability`. Tie: smaller `advert_id` first. |
| HARD_BOUNDS | `CpoSafetyBoundsParamsV1` then iteration caps. Never above absolute max, never below absolute min. 0.01 HALF_UP. |
| RATE_LIMITS | One step per selected campaign per tick. At most `K` campaigns. Headroom RUB does not multiply the step. |
| HYSTERESIS | No increase if `observed_cpo >= target_cpo × (1 − h)`. No decrease if `observed_cpo <= target_cpo × (1 + h)`. `h` default 0.05. If `target_cpo` is null, campaign is T0. |
| COOLDOWN | Increase uses increase `cooldown_ticks` only. Decrease uses decrease `cooldown_ticks` only. Memory is an input `(advert_id, direction) → last_tick`. Missing memory → fail closed for that direction (`NO_PROPOSAL`), do not assume tick 0 means “never acted” unless 4.1 explicitly says the memory is complete and empty. |
| POSITIVE_HEADROOM_POLICY | If `headroom_rub ≥ minimum_headroom_rub` and increase feature resolves enabled: rank increase-eligible, step the top `K_increase`, hold the rest. Decreases do not run. |
| NEGATIVE_HEADROOM_POLICY | If `headroom_rub < 0` and decrease feature resolves enabled: rank decrease-eligible (above dead band), step down the top `K_decrease`, **spare** campaigns at or below target. Increases do not run. |
| COLD_START_POLICY | `DIRECT orders = 0` or `ORDER_VALUE_UNAVAILABLE` or `target_cpo_rub is None` → `HOLD`, reason from 4.1 blocker if present, else no new action. No catalog price. No LINKED fallback. |
| INSUFFICIENT_DATA_POLICY | Shop `headroom_rub is None` or shop sufficiency not sufficient → **zero** proposals (do not call ranking). Campaign insufficiency → that campaign `HOLD` only. |

### Zero headroom (Owner fork)

| Mode | Behavior |
|------|----------|
| **Z0** | `headroom == 0` → all `HOLD`. |
| **Z1** | No increases. Decrease path may still cut campaigns above the dead band, using decrease cooldown and `K_decrease`. |
| **Z2** | Diagnostics only (`control_pressure` already exists on `ShopHeadroomState`). |

**Recommend Z0 as the pre-GO default** (fail closed). **Recommend the Owner pick Z1** if campaign-local overspend should be trimmed when the shop is exactly on target. Pseudocode takes `zero_headroom_mode` and defaults to Z0.

### Asymmetric attribution lag (Owner fork)

4.1 already blocks **both** directions when sufficiency is `STALE` / `INSUFFICIENT` (`control_action_allowed`). That stays.

Optional **L1**, off unless Owner enables it: if `attribution_lag_days > max_lag_days_for_increase`, forbid **increases** even when sufficiency is still `SUFFICIENT`, and still allow decreases. Rationale from lane B: spend is in the numerator immediately; orders arrive late; raising ceilings on lagged windows overspends. Do not invent a second DRR formula.

---

## PSEUDOCODE

```text
function allocate(shop, campaigns, memory, policy) -> list[Proposal]:
    # policy defaults (Owner-lockable): K_inc=1, K_dec=1, h=0.05,
    # min_orders_full=20, zero_mode=Z0, lag_gate=OFF

    if shop.headroom_rub is None or shop.sufficiency != SUFFICIENT:
        return []   # ranking not invoked

    direction = NONE
    if shop.headroom_rub > 0:
        direction = INCREASE
    else if shop.headroom_rub < 0:
        direction = DECREASE
    else:  # == 0
        direction = DECREASE if policy.zero_mode == Z1 else NONE

    if direction == NONE:
        return hold_all(campaigns)

    ranked = []
    for c in campaigns:
        if not base_eligible(c):          # enrolled, not legacy, resolver ok
            continue
        if c.sufficiency_fails_feature(direction):
            continue
        if c.direct_orders == 0 or c.target_cpo_rub is None:
            continue                       # cold start
        if direction == INCREASE:
            if not c.increase_enabled:
                continue
            if shop.headroom_rub < c.increase.minimum_headroom_rub:
                continue
            if policy.lag_gate and c.attribution_lag_days > policy.max_lag_days_for_increase:
                continue
            if memory.missing(c, INCREASE):
                continue
            if memory.ticks_since(c, INCREASE) < c.increase.cooldown_ticks:
                continue
            if c.observed_cpo_rub is None:
                continue
            if c.observed_cpo_rub >= c.target_cpo_rub * (1 - policy.h):
                continue                   # dead band or already at/above target
            reliability = min(1, c.direct_orders / policy.min_orders_full)
            gap = (c.target_cpo_rub - c.observed_cpo_rub) / c.target_cpo_rub
            score = gap * reliability
        else:  # DECREASE
            if not c.decrease_enabled:
                continue
            if memory.missing(c, DECREASE):
                continue
            if memory.ticks_since(c, DECREASE) < c.decrease.cooldown_ticks:
                continue
            if c.observed_cpo_rub is None:
                continue
            if c.observed_cpo_rub <= c.target_cpo_rub * (1 + policy.h):
                continue                   # spare healthy and dead band
            reliability = min(1, c.direct_orders / policy.min_orders_full)
            gap = (c.observed_cpo_rub - c.target_cpo_rub) / c.target_cpo_rub
            score = gap * reliability
        if score > 0:
            ranked.append((score, c.advert_id, c))

    sort ranked by score desc, advert_id asc
    K = policy.K_inc if direction == INCREASE else policy.K_dec
    chosen = first K of ranked

    proposals = []
    for c in campaigns:
        if c not in chosen:
            proposals.append(HOLD(c))
            continue
        if direction == INCREASE:
            step = min(
                c.increase.maximum_increase_per_iteration_rub,
                c.safety.max_step_up_rub or +inf,
                (c.safety.absolute_max_cpo_rub or +inf) - c.current_max_cpo_rub,
            )
            if step <= 0:
                proposals.append(HOLD(c))
            else:
                proposals.append(INCREASE(c, quantize_0_01(c.current_max_cpo_rub + step)))
        else:
            step = min(
                c.decrease.maximum_decrease_per_iteration_rub,
                c.safety.max_step_down_rub or +inf,
                c.current_max_cpo_rub - (c.safety.absolute_min_cpo_rub or 0),
            )
            if step <= 0:
                proposals.append(HOLD(c))
            else:
                proposals.append(DECREASE(c, quantize_0_01(c.current_max_cpo_rub - step)))
    return proposals
```

`base_eligible` reuses `campaign_headroom_eligibility` outcomes supplied by 4.1. The allocator does not re-read supplier orders or attribution facts.

Forbidden inside this function:

- `delta = shop.headroom_rub / n`
- `delta = shop.headroom_rub * weight_i`
- any use of `ProductCpoResolver`, catalog price, LINKED GMV, or `wb_common_stat`
- any WB write, Apply call, or mutation of `target_cpo_rub`

---

## HARD_INVARIANTS

1. Shop DRR below target (`headroom_rub > 0`) never raises every campaign by the same delta.
2. Equal deltas across campaigns are allowed only when **all** of: scores tie exactly, `advert_id` tie-break is not applied because `K` covers the whole tied set, and the Owner set `K` to that width. Default `K = 1` ⇒ at most one mover, so equal-raise of the shop is impossible.
3. Increase machine and decrease machine never both fire for the same campaign on the same tick. Shop sign makes them mutually exclusive except Z1 at zero, which is decrease-only.
4. No proposal when shop headroom is null or shop data is not `SUFFICIENT`.
5. No increase and no target-based decrease when DIRECT orders = 0 or target CPO is absent (`ORDER_VALUE_UNAVAILABLE` family).
6. No LINKED and no catalog price in the score.
7. `Σ proposed Δmax_cpo` is not constrained to equal `shop_headroom_rub` and must not be tested as if it should.
8. `proposed_max_cpo_rub` stays inside absolute min/max and inside the configured step.
9. Stale / insufficient / unknown campaign facts ⇒ no new action for **that** campaign (`NO_CONTROL_ACTION_STALE_OR_UNKNOWN` and existing sufficiency codes).
10. `NOT_ENROLLED` and `LEGACY_PASSTHROUGH` stay ineligible.
11. Allocator does not redefine ADR §2–§5.
12. Until Owner GO, production diagnostics keep `HEADROOM_ALLOCATOR_NOT_ACCEPTED`. This packet does not flip that code.

---

## CONFIG_PARAMETERS

### Already on stage (consume resolved values; do not add schema)

- `CpoIncreaseOnHeadroomParamsV1.minimum_headroom_rub`
- `CpoIncreaseOnHeadroomParamsV1.maximum_increase_per_iteration_rub`
- `CpoIncreaseOnHeadroomParamsV1.cooldown_ticks`
- `CpoIncreaseOnHeadroomParamsV1.min_data_sufficiency`
- `CpoDecreaseOnOverspendParamsV1.maximum_decrease_per_iteration_rub`
- `CpoDecreaseOnOverspendParamsV1.cooldown_ticks`
- `CpoDecreaseOnOverspendParamsV1.min_data_sufficiency`
- `CpoSafetyBoundsParamsV1.absolute_min_cpo_rub`
- `CpoSafetyBoundsParamsV1.absolute_max_cpo_rub`
- `CpoSafetyBoundsParamsV1.max_step_up_rub`
- `CpoSafetyBoundsParamsV1.max_step_down_rub`
- Resolved `DrrProfile.target_drr_percent` / `max_drr_percent` only as **gates** if 4.1 also exposes `campaign_actual_drr`. The recommended score uses **target CPO vs observed CPO**, because that is the actuation pair. DRR tier is a cross-check, not a second formula.

### New, Owner must accept before any code (proposed defaults)

| Name | Proposed default | Role |
|------|------------------|------|
| `K_increase` | `1` | How many campaigns may step up per tick |
| `K_decrease` | `1` | How many campaigns may step down per tick |
| `hysteresis_ratio` | `0.05` | Dead band around `target_cpo_rub` |
| `min_direct_orders_for_full_weight` | `20` | Reliability damper; below this, score shrinks linearly; at 0, ineligible |
| `zero_headroom_mode` | `Z0` | Z0 / Z1 / Z2 |
| `lag_gate_enabled` | `false` | L1 off |
| `max_lag_days_for_increase` | unset | Used only if L1 on |

No `weight_mode`, no `headroom_to_cpo_slope`, no round-robin pointer in V1.

### Task 4.1 fields the allocator reads (names may differ; meanings may not)

Per shop: `headroom_rub`, shop data sufficiency, configured target DRR (already inside headroom state).

Per campaign:

- identity `(shop_id, advert_id)`
- `current_max_cpo_rub`
- `target_cpo_rub` from `CampaignCpoProposal` (precomputed)
- `observed_cpo_rub` (`campaign_ad_spend / DIRECT orders`)
- `direct_orders`, and a sufficiency / blocker set already evaluated
- `campaign_actual_drr` optional cross-check, not recomputed
- `attribution_lag_days` optional, for L1 only
- resolved enablement and params for increase, decrease, safety
- eligibility blockers (not enrolled, legacy, feature disabled)
- cooldown memory: last increase tick, last decrease tick, and a flag that memory is complete

Not read: raw GMV rows, LINKED facts, catalog price, bids, CPC, CPM.

---

## OWNER_DECISIONS_REQUIRED

1. Accept recommended candidate **B + C-gates**, reject **A** as the allocation rule.
2. Lock or replace defaults: `K_increase=1`, `K_decrease=1`, `hysteresis_ratio=0.05`, `min_direct_orders_for_full_weight=20`.
3. Zero headroom: keep **Z0** or switch to **Z1**.
4. Attribution lag: keep both directions on the existing sufficiency gate, or enable **L1** (block increases only past a lag threshold).
5. Cooldown memory owner: confirm Task 4.1 (or a later read model) supplies complete per-campaign last-tick memory. Incomplete memory must fail closed, not reset cooldowns.
6. Explicit GO phrase that production code may replace `HEADROOM_ALLOCATOR_NOT_ACCEPTED` for this formula. **This packet is not that GO.**

---

## SIMULATION_PLAN

Pure function. Frozen fixtures. Tick index is an input. No RNG. No clock. No WB. No live GMV. No Apply. Do not re-test ADR formulas (those belong to Task 4.1). The harness passes already-computed `shop_headroom_rub`, states, and proposals.

Future test module (do not create in this lane): `tests/unit/ad_control_settings/test_headroom_allocator_simulation.py`.

| ID | Shop headroom | Mix | Expected under recommended policy | Forbidden |
|----|---------------|-----|-----------------------------------|-----------|
| SIM-01 | `+10_000` | Three campaigns, different gaps and order counts | Exactly `K_increase` increases; highest score wins; others HOLD | Same positive delta on every campaign |
| SIM-02 | `+10_000` | Strong (50 DIRECT orders, large gap) vs weak (2 orders, larger raw gap) | Strong wins if reliability-weighted score says so; document the numeric winner in the fixture | Weak campaign increases while its score is lower |
| SIM-03 | `−10_000` (ADR example shape: GMV 1_000_000, target 8%, spend 90_000) | One above target CPO, one below | Decrease only the above-target campaign | Flat cut on the healthy campaign |
| SIM-04 | `0` | Any | All HOLD under Z0 | Any increase; any decrease unless fixture sets Z1 |
| SIM-05 | `+10_000` | Zero DIRECT orders | HOLD / empty proposal | Any increase |
| SIM-06 | `−10_000` | Spend high, orders lagged, sufficiency STALE | No movement | Treating lag as a reason to increase |
| SIM-07 | sign flips each tick | `cooldown_ticks = 2` | Direction may change in the proposal stream only after cooldown | A second same-direction step inside the cooldown window |
| SIM-08 | `+10_000` | All scores equal | With `K=1`, exactly one campaign (lowest `advert_id`) steps | Equal raise of every tied campaign |
| SIM-09 | `−10_000` | Increase feature off, decrease on | Decreases only | Any increase |
| SIM-10 | `null` | Shop facts insufficient | Allocator returns empty; ranking function not used | Any numeric proposal |
| SIM-11 | `+10_000` | One enrolled, one `NOT_ENROLLED`, one legacy | Only the enrolled campaign may move | Proposals for excluded campaigns |
| SIM-12 | `+5_000` | Four campaigns, step 30 RUB, `K=1` | One campaign `+30` max CPO | Asserting `sum(Δmax_cpo) == 5000` or scaling the step by headroom |
| SIM-13 | `+50` | `minimum_headroom_rub = 100` | All HOLD | Any increase |
| SIM-14 | `+10_000` | `current` near `absolute_max` | Step clamped; no proposal above absolute max | Exceeding absolute max |
| SIM-15 | `+10_000` | Campaign increase DISABLED, shop increase enabled | That campaign HOLD; another eligible may move | Disabled campaign increases via inheritance leak |
| SIM-16 | `−10_000` | Two over-target campaigns | Only `K_decrease` movers; worse score first | Equal cut of both when `K_decrease = 1` |

### Acceptance metrics (must be 0 violations)

| Metric | Rule |
|--------|------|
| M-EQ-RAISE | Count of ticks where two or more campaigns share the same positive delta while their scores differ, or while `K_increase = 1` |
| M-NO-PROP-STALE | Proposals with a numeric `proposed_max_cpo` when sufficiency blocks |
| M-STEP | `abs(delta)` ≤ min(iteration cap, safety step) |
| M-BOUNDS | `proposed` inside absolute min/max |
| M-COOLDOWN | Same direction repeats inside `cooldown_ticks` |
| M-DUAL-SIDE | Increase and decrease on one campaign in one tick |
| M-HEALTHY-CUT | Decrease when `observed_cpo <= target_cpo × (1+h)` |
| M-WEAK-MOVE | A lower score moves while a higher score was eligible and not on cooldown |
| M-UNIT-TRAP | Any assertion or implementation path that sets delta from `headroom_rub / n` or sums CPO deltas to headroom |
| M-COLD | Increase when `direct_orders = 0` |
| M-EXCLUDED | Proposal for not-enrolled or legacy |
| M-HOLD-ZERO | Non-HOLD at headroom 0 under Z0 |
| M-K | More than `K` numeric moves in one tick |

Lane D’s SIM-08 (“equal deltas allowed on a full tie”) is **withdrawn** for the recommended default `K = 1`. Equal deltas on a full tie are allowed only in a separate fixture that sets `K` equal to the tied set size, and that fixture must be labeled as the Owner override, not the default.

---

## FAILURE_MODES

| Mode | Evidence | How the recommendation treats it |
|------|----------|----------------------------------|
| Equal shop-wide CPO raise | **Absent** in production. ADR §5 forbids it as a meaning of headroom. | `K=1` plus score order. A rejected. |
| Mass raise of every operable keyword inside one campaign | **Proven** shape in `raise_state_to_target_cpo.py` (UP only, per keyword). | Do not copy to shop campaign set. |
| Competing UP and DOWN same tick | **Proven** in V3 validation notes (`docks/V3_UPDATER_VALIDATION.md` per lane B). | Shop sign is single; Z1 is decrease-only. |
| Overspend ceiling ignored | **Proven** V3 overspend / reset-over-max tests. | Negative headroom never increases. Decrease only above the dead band. |
| Oscillation around target | **Proven** risk: calibration ×2/÷2, 90% band exists because of it (`sales_states.py` OPTIMAL band). | Dead band `h` and independent cooldowns. Do not import ×2/÷2. |
| Cooldown shorter than the fact cycle | **Proven** above-target min-bid cooldown if TTL < cycle. | Cooldown is tick-based from configured params; memory must be complete or fail closed. |
| Attribution lag / spend before orders | **Proven** sufficiency gate; aggressive zero-order hierarchical raise is **absent** and must stay absent (ADR bad example). | Cold start HOLD. Optional L1. |
| LINKED or funnel GMV used as authority | **Proven** forbidden (ADR §2–§3, classification tests). | Score inputs are 4.1 DIRECT outputs only. |
| Shop DRR denominator = sum of campaign attributed GMV | **Proven** forbidden (ADR §3). | Allocator never builds shop DRR. |
| Low-order CPO rank churn | **Inferred** from noisy `observed_cpo` (lane B/C). | `min_direct_orders_for_full_weight` damper; orders = 0 excluded. |
| Rich-get-richer via spend weights | **Inferred** if A were chosen. | Score uses gap ratio, not spend share. |
| Starvation of low-score campaigns | **Accepted** V1 behavior. | They move only when they rank in the top `K`. Owner can raise `K` later. |
| False precision (headroom RUB → CPO RUB slope) | Design risk, not a prod incident. | Ordinal steps only. |
| Promo / Raise-MAX ceiling stacking | **Proven** in V3/promo notes; **out of this allocator**. | Do not read promo overlays here. Safety absolute max is the only clamp. |
| Hindsight corpus | **Unavailable**. | Not used. No invented incidents. Incident 138252141 is campaign-create/Telegram, not this economics. |

---

## What not to copy from current controllers

Reuse as **shape** only: separate up vs down, step caps, cooldowns, fail-closed sufficiency, spare the healthy campaign on the way down, one mover per tick.

Do not copy: V3 ladder, `pay_for_order`, `substitute_fact_cpo_for_max`, `ProductCpoResolver`, common-bid “same direction for every nmid”, CH point CPO, or any shop DRR loop (none exists). `HEADROOM_ALLOCATOR_NOT_ACCEPTED` stays until the six Owner decisions above are answered and a later lane is told to implement.

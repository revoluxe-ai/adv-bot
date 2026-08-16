# SCENARIO_COVERAGE_PLAN

```text
CHANGE_ID: fair-leg-pause-billing
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: sceplan-e9920b7d8f4bcbdb
SCENARIO_COUNT: 18
LIFECYCLE_STATUS: DERIVED
PRODUCT_ACCEPTANCE_REQUIRED: true
REMATERIALIZE_NOTE: supersedes sceplan-ecca8f12df6ed78c after SWT block in design.md (lifecycle L1–L6 unchanged)
```

## GENERATED_FROM

```text
DESIGN_REVISION:
  path: openspec/changes/fair-leg-pause-billing/design.md
  content_hash: a87786ee0b7a944b439b7fffa4603c2cdf4c1f0ee247ccccd3a5f43568b8870d
SPEC_REVISION:
  - path: openspec/changes/fair-leg-pause-billing/specs/billing-fair-leg-pause/spec.md
    content_hash: 4be3e9c2a57f21e48096f33ebaf5a921c0efe643a5b58decdebff1127671d383
LIFECYCLE_REVISION:
  source: design.md##Lifecycle (LIFECYCLE_STATUS: DERIVED L1–L6)
  content_hash: a87786ee0b7a944b439b7fffa4603c2cdf4c1f0ee247ccccd3a5f43568b8870d
OWNER_CONTRACT_REVISION:
  path: openspec/changes/fair-leg-pause-billing/owner-contract.md
  content_hash: 86ed264f21f375a0b9d38911ee94d486c5417d6a69ac920e7414a2140907a291
TASKS_ARTIFACT:
  path: openspec/changes/fair-leg-pause-billing/tasks.md
  content_hash: f0efa844f4c2ece06082584b0a5ad510c3181360a6b4a7720c6e4d2b65cd7118
  note: consumed for entrypoint hints only; not SoT
```

## LIFECYCLE_COVERAGE

| L* | Spec Scenarios |
|---|---|
| L1 Participation gate (`bot_active` on anchor) | Bot disconnected — no charge for the setup; Bot connected — setup enters billing |
| L2 Instant sample + anchor resolve | Paired setup uses search_adv_id anchor; Setup without Search link — anchor only; Per-leg weight scenarios (both/one/zero/no Search); Search paused by empty-keywords reduces Search slot only |
| L3 Latch accumulate (UTC-day) | Pause before charge does not erase started leg same UTC-day; Leg never started whole UTC-day — slot stays zero |
| L4 Bracket (`effective_count`) | Two half-units equal one tier unit; Per-leg weight scenarios (derive cabinet tier) |
| L5 Cabinet charge (grace/block unchanged) | Full-active setup matches legacy daily total; Legacy charge records remain readable; End-to-end half charge when one leg paused all day without prior started |
| L6 AdvPayment artifacts (split lines) | Two leg lines when both slots billable; One leg line when only one slot billable; End-to-end half charge… |

Orthogonality (billing read-only vs pause-runtime): Search paused by empty-keywords…

Steady-state / reconcile-on-observe: **NOT_APPLICABLE** — billing is UTC-day charge
with latch sampling on billing loop passes; no separate periodic reconcile entrypoint
for this change. Transition + latch anti-gaming scenarios cover material invariants.

## UNRESOLVED_GAPS / OPEN_QUESTIONS

```text
none
```

## SCENARIO_COVERAGE_PLAN

```text
SCHEMA_VERSION: 1
CHANGE_ID: fair-leg-pause-billing
SOURCE_SPEC_SHA: 4be3e9c2a57f21e48096f33ebaf5a921c0efe643a5b58decdebff1127671d383
PLAN_STATUS: ready
SHARED_ENTRYPOINTS:
  - app.modules.billing.leg_metering (anchor resolve, instant weight, effective_count)
  - app.modules.billing.leg_latch.LegLatchManager (Redis max per UTC-day)
  - app.modules.billing.pricer.Pricer (tariff context / preview)
  - app.modules.billing.billing._process_single_cabinet (sample, debit, AdvPayment)
SHARED_THIN_ENDS:
  - PG: AdvSetting.active_status read; AdvPayment insert (write + read for dedup/legacy)
  - Redis: billing:leg_latch:* keys (fakeredis OK); billing_process_for_day dedup
  - FORBIDDEN: shop-runner pause/start side effects from billing path
EXECUTION_NOTE: mode=plan — tests listed as REQUIRED; execution NOT_CLAIMED
```

Spec: `openspec/changes/fair-leg-pause-billing/specs/billing-fair-leg-pause/spec.md`

### S1 — Bot disconnected — no charge for the setup

```text
SCENARIO_ID: openspec/changes/fair-leg-pause-billing/specs/billing-fair-leg-pause/spec.md::Bot disconnected — no charge for the setup
LIFECYCLE: L1
PRODUCTION_ENTRYPOINT: leg_metering.effective_count / billing._process_single_cabinet (skip anchor)
CAUSAL_PATH: bot_active=False on anchor → excluded from Σ effective_count → no charge
THIN_ENDS: PG read AdvSetting.bot_active
REQUIRED_TESTS:
  SCENARIO_SEAM: billing.__process_single_cabinet with bot_active=False anchor → no AdvPayment
  UNIT_COMPONENT: leg_metering gate negative
  BOUNDARY_INTEGRATION_READ: PG AdvSetting.bot_active selection
HINT_TEST_IDS (not executed): tests/modules/billing/test_leg_metering.py::test_bot_inactive_not_in_effective_count
```

### S2 — Bot connected — setup enters billing

```text
SCENARIO_ID: .../spec.md::Bot connected — setup enters billing
LIFECYCLE: L1
PRODUCTION_ENTRYPOINT: leg_metering.effective_count
CAUSAL_PATH: bot_active=True on anchor + started leg → included in cabinet Σ
THIN_ENDS: PG read bot_active, active_status
REQUIRED_TESTS:
  SCENARIO_SEAM: billing path includes anchor in tariff calculation
  UNIT_COMPONENT: leg_metering positive gate (paired with S1)
HINT_TEST_IDS: tests/modules/billing/test_leg_metering.py::test_bot_active_included_when_started
```

### S3 — Paired setup uses search_adv_id anchor

```text
SCENARIO_ID: .../spec.md::Paired setup uses search_adv_id anchor
LIFECYCLE: L2
PRODUCTION_ENTRYPOINT: leg_metering.resolve_anchor / compute weights
CAUSAL_PATH: anchor = row with search_adv_id; Search row by adv_id match; MUST NOT WB marketing type
THIN_ENDS: PG AdvSetting search_adv_id + adv_id join
REQUIRED_TESTS:
  SCENARIO_SEAM: metering uses anchor.active_status for auto slot, search row for search slot
  UNIT_COMPONENT: anchor resolution; Search row never anchor
HINT_TEST_IDS: test_search_row_never_anchor; test_both_legs_started_full_unit
```

### S4 — Setup without Search link — anchor only

```text
SCENARIO_ID: .../spec.md::Setup without Search link — anchor only
LIFECYCLE: L2
PRODUCTION_ENTRYPOINT: leg_metering (no search row)
CAUSAL_PATH: unresolved search_adv_id → Search slot absent (not zero billable row)
REQUIRED_TESTS:
  SCENARIO_SEAM: single auto slot path through billing
  UNIT_COMPONENT: test_no_search_pair_only_auto_slot
HINT_TEST_IDS: test_no_search_pair_only_auto_slot; test_no_search_anchor_started_half
```

### S5 — Both legs started — full tariff for setup

```text
SCENARIO_ID: .../spec.md::Both legs started — full tariff for setup
LIFECYCLE: L2, L4, L5
PRODUCTION_ENTRYPOINT: leg_metering + latch + billing charge
CAUSAL_PATH: instant 0.5 + 0.5 → per_anchor_units=1.0 → full daily tariff
THIN_ENDS: PG active_status read; Redis latch; PG AdvPayment write
REQUIRED_TESTS:
  SCENARIO_SEAM: integration full-active charge = legacy total
  UNIT_COMPONENT: test_both_legs_started_full_unit
  BOUNDARY_INTEGRATION_WRITE: AdvPayment auto_leg + search_leg
  STUB_CONTRACT: fakeredis latch parity with LegLatchManager boundary
HINT_TEST_IDS: test_integration_full_active_matches_legacy_daily_total
```

### S6 — Only anchor leg started — half tariff

```text
SCENARIO_ID: .../spec.md::Only anchor leg started — half tariff
LIFECYCLE: L2, L4
CAUSAL_PATH: anchor started, Search paused → 0.5 units
REQUIRED_TESTS:
  SCENARIO_SEAM: integration one leg paused → half tariff
  UNIT_COMPONENT: test_only_anchor_started_half
HINT_TEST_IDS: test_integration_one_leg_paused_half_tariff
```

### S7 — Only Search leg started — half tariff

```text
SCENARIO_ID: .../spec.md::Only Search leg started — half tariff
LIFECYCLE: L2, L4
REQUIRED_TESTS:
  SCENARIO_SEAM: metering + charge at 0.5
  UNIT_COMPONENT: test_only_search_started_half
```

### S8 — Both legs not in work — zero for setup

```text
SCENARIO_ID: .../spec.md::Both legs not in work — zero for setup
LIFECYCLE: L2, L4
REQUIRED_TESTS:
  SCENARIO_SEAM: integration both paused → zero charge
  UNIT_COMPONENT: test_both_not_started_zero
HINT_TEST_IDS: test_integration_both_legs_paused_zero_charge
```

### S9 — No Search leg but anchor in work — half tariff

```text
SCENARIO_ID: .../spec.md::No Search leg but anchor in work — half tariff
LIFECYCLE: L2, L4
REQUIRED_TESTS:
  SCENARIO_SEAM: single-slot 0.5 through billing
  UNIT_COMPONENT: test_no_search_anchor_started_half
```

### S10 — Two half-units equal one tier unit

```text
SCENARIO_ID: .../spec.md::Two half-units equal one tier unit
LIFECYCLE: L4
PRODUCTION_ENTRYPOINT: Pricer bracket on effective_count
CAUSAL_PATH: two anchors each 0.5 → effective_count=1.0 for tier
REQUIRED_TESTS:
  SCENARIO_SEAM: pricer tariff context with summed slots
  UNIT_COMPONENT: test_two_half_units_effective_count_one
```

### S11 — Pause before charge does not erase started leg same UTC-day

```text
SCENARIO_ID: .../spec.md::Pause before charge does not erase started leg same UTC-day
LIFECYCLE: L3
PRODUCTION_ENTRYPOINT: LegLatchManager.record_sample → get_billable_weight at charge
CAUSAL_PATH: started earlier → latch max 0.5; pause before charge → still 0.5
THIN_ENDS: Redis billing:leg_latch:* (fakeredis OK)
REQUIRED_TESTS:
  SCENARIO_SEAM: integration gaming path (sample started, pause, charge)
  UNIT_COMPONENT: test_gaming_pause_before_charge_keeps_latch
  BOUNDARY_INTEGRATION_OTHER: Redis latch max semantics
  STUB_CONTRACT: scenario seam fakeredis ↔ LegLatchManager
HINT_TEST_IDS: test_integration_gaming_latch_keeps_search_slot_half
```

### S12 — Leg never started whole UTC-day — slot stays zero

```text
SCENARIO_ID: .../spec.md::Leg never started whole UTC-day — slot stays zero
LIFECYCLE: L3
REQUIRED_TESTS:
  SCENARIO_SEAM: charge with latch 0 for never-started leg
  UNIT_COMPONENT: test_never_started_stays_zero; test_latch_not_from_bot_active_alone
```

### S13 — Two leg lines when both slots billable

```text
SCENARIO_ID: .../spec.md::Two leg lines when both slots billable
LIFECYCLE: L6
PRODUCTION_ENTRYPOINT: billing.__process_single_cabinet AdvPayment insert
THIN_ENDS: PG AdvPayment write (auto_leg, search_leg)
REQUIRED_TESTS:
  SCENARIO_SEAM: test_adv_payment_split_two_slots_when_both_billable
  BOUNDARY_INTEGRATION_WRITE: PG AdvPayment rows with type constraint
  BOUNDARY_INTEGRATION_READ: dedup query by (date, adv_setting_id, type)
HINT_TEST_IDS: test_integration_adv_payment_split_two_rows
```

### S14 — One leg line when only one slot billable

```text
SCENARIO_ID: .../spec.md::One leg line when only one slot billable
LIFECYCLE: L6
REQUIRED_TESTS:
  SCENARIO_SEAM: single auto_leg row; MUST NOT zero duplicate for absent slot
  BOUNDARY_INTEGRATION_WRITE: single AdvPayment insert
HINT_TEST_IDS: test_adv_payment_single_auto_leg_when_search_paused
```

### S15 — Full-active setup matches legacy daily total

```text
SCENARIO_ID: .../spec.md::Full-active setup matches legacy daily total
LIFECYCLE: L5
REQUIRED_TESTS:
  SCENARIO_SEAM: LEGACY_BASELINE characterization + FINAL_ACCEPTANCE equals legacy
  UNIT_COMPONENT: test_legacy_baseline_full_active_daily_total_matches_legacy_tariff
HINT_TEST_IDS: test_integration_full_active_matches_legacy_daily_total
```

### S16 — Legacy charge records remain readable

```text
SCENARIO_ID: .../spec.md::Legacy charge records remain readable
LIFECYCLE: L5
PRODUCTION_ENTRYPOINT: billing._anchor_has_adv_payment_for_day / dedup
THIN_ENDS: PG AdvPayment read (type IS NULL)
REQUIRED_TESTS:
  SCENARIO_SEAM: legacy NULL type blocks duplicate split charge
  BOUNDARY_INTEGRATION_READ: PG legacy AdvPayment tolerant dedup
HINT_TEST_IDS: test_legacy_null_adv_payment_blocks_duplicate_split; test_legacy_null_adv_payment_skips_new_split_rows
```

### S17 — Search paused by empty-keywords reduces Search slot only

```text
SCENARIO_ID: .../spec.md::Search paused by empty-keywords reduces Search slot only
LIFECYCLE: L2 (orthogonality)
CAUSAL_PATH: billing reads Search active_status=paused; MUST NOT resume Search
THIN_ENDS: PG active_status read only; FORBIDDEN WB pause/start from billing
REQUIRED_TESTS:
  SCENARIO_SEAM: 0.5 charge with Search paused; assert no pause-manager calls
  UNIT_COMPONENT: test_search_paused_half_for_setup
```

### S18 — End-to-end half charge when one leg paused all day without prior started

```text
SCENARIO_ID: .../spec.md::End-to-end half charge when one leg paused all day without prior started
LIFECYCLE: L5, L6
CAUSAL_PATH: Search never started → latch 0 → debit 0.5 → single auto_leg row
REQUIRED_TESTS:
  SCENARIO_SEAM: integration e2e debit + AdvPayment
  BOUNDARY_INTEGRATION_WRITE: single auto_leg AdvPayment
  BOUNDARY_INTEGRATION_READ: cabinet balance debit (PG)
HINT_TEST_IDS: test_integration_e2e_half_charge_single_auto_leg_row
```

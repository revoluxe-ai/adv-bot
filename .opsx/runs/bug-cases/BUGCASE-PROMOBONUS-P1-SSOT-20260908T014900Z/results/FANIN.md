# FANIN assemble — BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z

CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
ROOT_FINDING_ID: ROOT-001
COMMAND: /opsx-materialize-bug-queue mode=fanin_assemble
ACTOR_AGENT_ID: WEX_FANIN_P1
ACTOR_CHAT_ID: SUP-PROMOBONUS-P1-SSOT-20260908
ASSEMBLED_AT: 2026-09-08T02:58:00Z
MISSION_ID: SUP-PROMOBONUS-P1-SSOT-20260908
TASK_ID: T-FANIN-P1-CASE
DISPATCH_ID: D-015

## STATUS

STATUS: FANIN_READY
CLOSURE_READINESS: READY_FOR_CLOSURE
CLASS_STATUS: CLOSED
CLASS_LEVEL_GO_WRITE: FORBIDDEN
BLOCKING_FINDINGS: NONE
OPEN_SAME_INVARIANT_CANDIDATES: 0

## ROOT_BUG

Owner-confirmed P1 pair on uncommitted Promobonus overlay work violated the
runtime overlay SSOT invariant at two causal paths:

1. **ROOT-001 (CH write boundary):** `PlanFactController.process_pre_adv`
   persisted `pre_adv.plan_data` (overlay Plan from
   `WBShopDataManager._build_pre_complex_adv`) into ClickHouse
   `plan_fact_stats` plan columns instead of base Plan from
   `PlanFactProvider.get_plan_data`.
2. **CHILD-001 (consumer wiring):** Keyword GOOD/BAD, telegram cost-activity,
   and `is_auto_campaign_active` still resolved thresholds from base
   `AdvSetting` or called `get_effective_plan_data` without `ComplexAdv`,
   collapsing overlay fraction to base.

## ROOT_CAUSE_PATTERN

**Split SSOT violation:** overlay Plan was both (a) written to durable CH
history at the wrong boundary and (b) not consistently consumed at runtime
read paths. Base Plan (`get_plan_data`) and effective overlay Plan
(`get_effective_plan_data` + `ComplexAdv`) were conflated or bypassed.

## ERROR_CLASS

`promobonus_overlay_ssot_boundary_violation`

Subclasses:

- `ch_persisted_overlay_instead_of_base_plan` (ROOT-001)
- `runtime_consumer_missing_effective_plan_overlay` (CHILD-001)

## ROOT_INVARIANT

ClickHouse plan_fact history MUST store base Plan only
(`PlanFactProvider.get_plan_data` / AdvSetting). Runtime CPO/plan overlay
MUST be a single SoT via `PlanFactProvider.get_effective_plan_data` /
promo overlay with `ComplexAdv`.

ROOT_FINGERPRINT:
`ch_plan_fact_stores_base_plan_only|runtime_overlay_ssot_get_effective_plan_data|process_pre_adv_writes_pre_adv.plan_data|consumers_must_pass_complexadv`

## SIBLING_VARIANTS

| FINDING_ID | RELATION_TO_ROOT | PATH | EPISODE_TERMINAL |
|---|---|---|---|
| ROOT-001 | root | CH `process_pre_adv` write | FIXED |
| CHILD-001 | same_invariant_different_path | keywords / telegram / menu consumers | FIXED |

No open SAME_INVARIANT hunt candidates. No adjacent/backlog/FP branches in
this case. Thematic overlap with HIGH6 FINDING-H4/H5 noted in packets but
not mutated (out-of-episode).

## FIX_PATTERNS

### ROOT-001

- **Pattern:** Resolve persisted plan at write boundary via canonical base
  source, not upstream overlay seed on DTO.
- **Change:** `process_pre_adv` uses
  `PlanFactProvider.get_plan_data(pre_adv.auto_adv.adv_setting)` (aligned
  with `process_adv`) instead of `pre_adv.plan_data`.
- **File:** `plan_fact_controller.py`
- **Evidence:** `results/FIX-ROOT-001.md`, `results/GREEN-ROOT-001.md`

### CHILD-001

- **Pattern:** Wire runtime consumers to `get_effective_plan_data(...,
  complex_adv=...)`; pass `ComplexAdv` into cost-activity / activity gates.
- **Change:** Keyword above-target gate, telegram cost-activity menu, and
  `is_auto_campaign_active` use effective overlay thresholds with attached
  `promo_fraction`.
- **Files:** `calculated_keywords_manager.py`,
  `auto_campaign_cost_activity.py`, `adv_setting_menu.py`
- **Evidence:** `results/FIX-CHILD-001.md`, `results/GREEN-CHILD-001.md`

## REGRESSION_TEST_PATTERN

| FINDING_ID | TEST_ID | SHA256 |
|---|---|---|
| ROOT-001 | `tests/unit/.../test_process_pre_adv_plan_source.py::test_process_pre_adv_persists_base_plan_not_overlay_on_write_boundary` | `9de02d7aa5a9ce0dc4fe20a87d8bea8f80d4ac6ce84df44c5252f63d6938f0e7` |
| CHILD-001 | `tests/unit/.../test_child_001_incomplete_overlay_wiring.py::test_keyword_above_target_gate_uses_effective_overlay_max_not_base_adv_setting` | `30d915f3b29ed2a6090cdfc65a645f2cafd1bc2939c14fa3362601bbc6e4be06` |

Pattern: RED authored before GO; exact `TEST_ID` unchanged through GREEN;
`TEST_CONTENT_SHA256` stable across RED→GREEN.

## PREVENTION_RULE_CANDIDATE

- **CH write paths:** Any `insert_plan_fact_stats` / `PlanFactStatDTO.create`
  MUST source plan columns from `get_plan_data`, never from overlay-seeded
  `PreComplexAdv.plan_data`.
- **Runtime consumers:** Any threshold/gate reading CPO/plan MUST use
  `get_effective_plan_data(..., complex_adv=...)` when overlay fraction lives
  on `ComplexAdv`; forbid bare `AdvSetting` max/target for overlay-active
  flows.

## REUSABLE_CHECK_CANDIDATE

- Static grep: `process_pre_adv` must not pass `pre_adv.plan_data` to plan
  columns.
- Static grep: cost-activity / keyword gates must not call
  `get_effective_plan_data` without `complex_adv` where overlay applies.
- Unit boundary tests per write/read surface (pattern established by this
  episode).

## REMAINING_EXCEPTIONS

- `RaisePlanOnPromobonuses` enablement: explicitly out of scope this episode.
- Leftover/P0 mix formula: not changed.
- HIGH6 FINDING-H4/H5 thematic overlap: backlog in separate case; not
  reopened or absorbed here.
- Classification/menu surfaces beyond CHILD-001 patch set: no open findings
  in this case after GREEN.

## BRANCH_SUMMARY

```text
HUNT_PASSES_EXECUTED: 0 (owner-materialized pair; no hunt pass)
MAX_DEPTH_SEEN: 1
ACTIVE_BRANCH_COUNT: 0

ROOT-001  DEPTH=0  PARENT=ROOT       EPISODE_TERMINAL=FIXED  STATUS=closed_fixed  RED+GO+GREEN=CLOSED_GREEN
CHILD-001 DEPTH=1  PARENT=ROOT-001   EPISODE_TERMINAL=FIXED  STATUS=closed_fixed  RED+GO+GREEN=CLOSED_GREEN
```

All started branches terminal. No active branches.

## REGRESSION_STATUS

| FINDING_ID | RED | GO/FIX | GREEN | CLOSE |
|---|---|---|---|---|
| ROOT-001 | `results/RED-ROOT-001.md` | `results/FIX-ROOT-001.md` | `results/GREEN-ROOT-001.md` | `results/CLOSE-ROOT-001.md` |
| CHILD-001 | `results/RED-CHILD-001.md` | `results/FIX-CHILD-001.md` | `results/GREEN-CHILD-001.md` | `results/CLOSE-CHILD-001.md` |

REGRESSION_STATUS: ALL_BRANCHES_GREEN

## LIMITS_CHECK

```text
HUNT_PASSES_EXECUTED (0) ≤ MAX_HUNT_PASSES (3): PASS
MAX_DEPTH_SEEN (1) ≤ MAX_DEPTH_FROM_ROOT (3): PASS
ACTIVE_BRANCH_COUNT (0) ≤ MAX_ACTIVE_BRANCHES (3): PASS
```

## CHECKS

```text
1_FIXED_HAVE_RED_GREEN_GO: PASS
2_NO_WEAKEN: PASS
3_NO_DOUBLE_FIX: PASS
4_NO_CONFLICTING_PRODUCTION_DIFFS: PASS
5_ONE_ROOT_INVARIANT_OR_EXPLICIT_OUTEPISODE: PASS
6_LIMITS_NOT_EXCEEDED: PASS
```

### Check notes

1. Both findings: RED → Owner GO (`/opsx-fix-bug GO`) → GREEN verify →
   `close=fixed` / `CLOSED_GREEN`.
2. GREEN receipts confirm `TEST_CONTENT_SHA256` matches RED; no assertion
   edits.
3. Separate fixes on disjoint file sets; no duplicate patch on same boundary.
4. ROOT-001 (CH write) and CHILD-001 (consumer read) patches are complementary,
   not conflicting.
5. Single root invariant; CHILD-001 is `same_invariant_different_path` branch
   under ROOT-001, now terminal.
6. Episode limits not exceeded; no hunt overrun.

## CASE_CLOSURE

CASE_CLOSED: yes
OPEN_FINDINGS: 0
READY_TO_CLAIM: 0
FINDINGS_CLOSED_FIXED: 2

## NEXT_COMMAND

```text
/opsx-learn-from-bug case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z FANIN_PATH=.opsx/runs/bug-cases/BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z/results/FANIN.md
```

MISSION_COMPLETE: no
LEARNING_READY: pending learn-from-bug hop

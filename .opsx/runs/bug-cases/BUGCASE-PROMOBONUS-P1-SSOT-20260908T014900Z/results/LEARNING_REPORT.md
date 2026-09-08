# LEARNING_REPORT — BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z

```text
LEARNING_STATUS: COMPLETE
LEARNING_VERDICT: CLASS_LESSON_CANDIDATE
PROMOTION_DECISION: KEEP_LESSON_CANDIDATE_ONLY
OWNER_FINAL: KEEP_LESSON_CANDIDATE_ONLY
OWNER_FINAL_AT: 2026-09-08T03:05:00Z
OWNER_FINAL_DISPATCH: D-017
CLASS_STATUS: CANDIDATE_RETAINED
CLASS_LEVEL_GO_WRITE: FORBIDDEN
FULL_PACKET_REQUIRED: true
DECISION_PATH: results/LEARNING_DECISION.json
PACKET_PATH: results/LEARNING_PACKET.json
WORKER_EXECUTION_ID: WEX_LEARN_P1/D-016
CLOSURE_WORKER: WEX_LEARN_KEEP_001/D-017
```

## Summary

Learning after `FANIN_READY` for owner-confirmed P1 promobonus overlay SSOT pair.
ROOT-001 (CH write boundary) and CHILD-001 (runtime consumer wiring) both
`closed_fixed` with RED→GO→GREEN chains. Single root invariant:
`ch_plan_fact_stores_base_plan_only|runtime_overlay_ssot_get_effective_plan_data`.

**Split SSOT violation:** overlay Plan was persisted to ClickHouse at the wrong
write boundary (`process_pre_adv` used `pre_adv.plan_data` seeded from
overlay) while runtime consumers still read base `AdvSetting` or called
`get_effective_plan_data` without `ComplexAdv`, collapsing overlay to base.

## Transferable process lesson

When introducing runtime overlay / effective-plan semantics:

1. **Write boundaries** (CH `plan_fact_stats`) MUST persist base Plan via
   `PlanFactProvider.get_plan_data` — never overlay-seeded DTO fields.
2. **Read/gate consumers** MUST use `get_effective_plan_data(..., complex_adv=...)`
   when overlay fraction lives on `ComplexAdv`.
3. **Regression tests** MUST exercise each boundary independently; a read-path
   test (`get_plan_data` stays raw) does not cover CH write paths.

## Promotion candidates (deferred — Owner FINAL required)

| Target | Proposed addition |
|---|---|
| `.cursor/commands/opsx-project-bug-hunt.md` | Checklist items under Persistence / overlay SSOT |
| `.cursor/rules/testing-rules.mdc` | Overlay plan write/read boundary test obligations |

Static grep candidates from FANIN: `process_pre_adv` must not pass
`pre_adv.plan_data` to plan columns; cost-activity/keyword gates must not call
`get_effective_plan_data` without `complex_adv` where overlay applies.

## Why not auto-promoted

- `LESSON_GATE_PASS` satisfied; class pattern confirmed across two branches.
- `CLASS_LEVEL_GO_WRITE: FORBIDDEN` until Owner FINAL
  (`PROMOTE_CLASS_LESSON` | `KEEP_LESSON_CANDIDATE_ONLY` |
  `CLOSE_EPISODE_NO_CLASS_LESSON`).
- No write to process sources in this hop (`WRITE_ALLOWED: false`).

## Closure gate

`LEARNING_STAGE_INVOKED=true`, `LEARNING_STATUS=COMPLETE`,
`PROMOTION_DECISION=KEEP_LESSON_CANDIDATE_ONLY`. Owner FINAL recorded
(D-017): lesson candidate retained case-local; class-lesson gate closed;
no process-source write. Canonical decision: `results/LEARNING_DECISION.json`.
`WRITE_ALLOWED=false`. `CLASS_LEVEL_GO_WRITE=FORBIDDEN`.

## Owner FINAL (D-017)

```text
OWNER_FINAL: KEEP_LESSON_CANDIDATE_ONLY
approval: NOT owner_approved for class promotion
GO: FORBIDDEN
CLASS_STATUS: CANDIDATE_RETAINED
LESSON_GATE_STATUS: LESSON_GATE_PASS (preconditions met; promotion declined)
```

Transferable lesson remains in `results/LEARNING_PACKET.json` →
`REUSABLE_LESSONS` and `PROPOSED_PROCESS_IMPROVEMENTS` for future reference
only. Not promoted to `.cursor/commands/**` or `.cursor/rules/**`.

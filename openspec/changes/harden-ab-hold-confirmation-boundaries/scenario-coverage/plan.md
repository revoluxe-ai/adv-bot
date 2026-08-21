# Scenario Coverage Plan

CHANGE_ID: harden-ab-hold-confirmation-boundaries
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-2032f579212ef33b
LIFECYCLE_STATUS: DERIVED

This is required-evidence planning only. It does not claim that any listed
test has been authored, executed, or passed.

## Lifecycle coverage

`design.md` provides the reviewed Owner Contract-derived lifecycle:

- L1 Callback entry and actor gate
- L2 Current durable phase and stale revision/generation gate
- L3 Live factual-position preview, invalid-key exclusion, and positive-input validation
- L4 Explicit target-place confirmation through the A/B Hold epoch write-path
- L5 Durable confirmed state or no-op on rejection
- L6 Existing EXIT and retry recovery

LIFECYCLE_COVERAGE:

- L1 → S01, S02, S03, S12, S13 — covered
- L2 → S01, S02, S03, S10, S11, S12 — covered
- L3 → S04, S05, S06, S07, S08, S09, S11, S12 — covered
- L4 → S01, S08, S09, S12 — covered
- L5 → S02, S03, S08, S09, S10, S11, S12, S13 — covered
- L6 → S03, S10, S12 — covered

The Spec includes both required already-true/reconcile-style cases:
confirmed target-place immutability on a later setup tick or retry (S10) and
ordinary factual-position drift without reopening confirmation (S11).
No `MISSING_STEADY_STATE_RECONCILE_SCENARIO` gap is planned.

## Architecture and evidence constraints

Architecture Decision References:

- `openspec/decisions/card-ab-hold-write-path-ownership/decision.md`
- `openspec/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md`
- `openspec/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md`

Ownership & Placement:

- Telegram A/B Hold handlers own actor/access gates, stale rejection, safe
  rendering, and triggering existing writers.
- `card_ab_hold.epoch_write` owns durable confirmed parameters, `FOR UPDATE`,
  generation, PENDING intent, and lifecycle writes.
- `_load_factual_positions` and `get_keywords_for_keyboard` remain the live
  factual-position read boundary; factual position is not durable confirmation
  state.
- Redis is only coordination/EXIT cleanup after an authorized action.
- WB synchronization remains the existing epoch/setup boundary; this change
  does not introduce another writer.

Shared evidence rules for every behavioral Scenario:

- At least one `scenario_seam` must enter the production handler or nearest
  runtime-reachable orchestration entry and execute the real guard and causal
  logic.
- Thin ends may be stubbed only after the business boundary is reached.
- Every used stub requires an executable stub-contract test plus its real
  boundary integration test.
- PG/CH write and read boundaries require separately attributable integration
  evidence when the Scenario depends on both.
- Assertions must prove the observable allowed and forbidden effects, not only
  mock call counts.
- No Scenario test may patch `_check_stale`, candidate selection, factual
  validation, `confirm_target_places`, epoch write logic, or lifecycle
  orchestration.

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: harden-ab-hold-confirmation-boundaries
SOURCE_SPEC_SHA: c8d8434154330503a424b3643a8539d52eca4f08a3b69c9e1313af0d385d6aa4
PLAN_STATUS: ready

### S01 — Associated user may continue confirmation

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Associated user may continue confirmation`
LIFECYCLE_STEPS: L1, L2, L3, L4, L5
GIVEN_WHEN_THEN: Associated Telegram user and current confirmation context; user confirms an A/B Hold parameter; confirmation follows the existing flow and explicit confirmation remains required.
PRODUCTION_ENTRYPOINT: `card_ab_hold.telegram.confirm_handlers.on_tp_confirm_all` (or the corresponding confirmation callback) → actor/access gate → `_check_stale` → `_load_factual_positions` → `epoch_write.confirm_target_places`.
CAUSAL_PATH: Resolve `AdvSetting` → verify existing Telegram-user/cabinet relation → validate current phase/revision → load live factual positions → build valid target map → durable epoch write → re-read/render the next confirmation step.
THIN_ENDS: Existing relation/PG read; CH+PG factual-position read model; PG epoch write/read-after-write; Telegram notification/render transport.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `authorized-confirmation` seam with real actor gate, stale gate, factual-position filtering, and epoch writer; assert next phase and durable positive target map.
  CONTRACT_CASES: `CAH-OWN-ASSOCIATED-001`, `CAH-TP-POSITIVE-001`.
  STUB_CONTRACT: Relation helper response, factual-position loader response, PG write result, and Telegram render response must match production DTO/exception/async shapes.
  BOUNDARY_INTEGRATION_WRITE: PG `AdvSetting` epoch confirmation write via production write session and row-lock path; assert persisted target map and phase.
  BOUNDARY_INTEGRATION_READ: PG `AdvSetting` read-after-write plus CH+PG factual-position read model.
  BOUNDARY_INTEGRATION_OTHER: Telegram message/notification contract; no user-facing send in the scenario run.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Use an associated test Telegram identity and campaign relation; no production credentials or live seller data.
MOCKING_CONSTRAINTS: Do not patch actor gate, stale gate, target-map construction, or epoch writer; stub only thin transport/provider ends after the causal boundary.

### S02 — Foreign confirmation is rejected without side effects

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Foreign confirmation is rejected without side effects`
LIFECYCLE_STEPS: L1, L2, L5
GIVEN_WHEN_THEN: Telegram user is not associated with the campaign cabinet; user submits confirmation; neutral rejection is returned and no campaign, confirmation, coordination, or lifecycle state changes.
PRODUCTION_ENTRYPOINT: `card_ab_hold.telegram.confirm_handlers` confirmation callback → actor/access gate before `_check_stale` or writer invocation.
CAUSAL_PATH: Load campaign by callback address → evaluate existing relation helper with foreign identity → neutral rejection → stop before stale redraw, FSM mutation, PG write, Redis cleanup, or lifecycle transition.
THIN_ENDS: Existing relation/PG read; Telegram neutral-notification transport.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `foreign-confirmation-no-side-effects` seam with real handler entry and real actor gate; assert neutral text and unchanged durable/FSM/coordination state.
  CONTRACT_CASES: `CAH-OWN-FOREIGN-CONFIRM-001`.
  STUB_CONTRACT: Foreign relation result and neutral Telegram response must match the relation helper and notification boundary contracts, including async/exception behavior.
  BOUNDARY_INTEGRATION_WRITE: not_applicable — the forbidden write path must not be reached.
  BOUNDARY_INTEGRATION_READ: PG campaign load and existing relation-helper read contract.
  BOUNDARY_INTEGRATION_OTHER: Telegram neutral-notification contract.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Prove unchanged state by reading the same durable campaign/epoch fields and coordination state before and after; do not assert only `not_called`.
MOCKING_CONSTRAINTS: Do not patch the handler, actor gate, or writer to manufacture the rejection; only thin relation/notification ends may be substituted with parity evidence.

### S03 — Foreign disable is rejected without side effects

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Foreign disable is rejected without side effects`
LIFECYCLE_STEPS: L1, L2, L5, L6
GIVEN_WHEN_THEN: Telegram user is not associated with the campaign cabinet; user submits A/B Hold disable; neutral rejection is returned and no database write, Redis cleanup, or lifecycle transition occurs.
PRODUCTION_ENTRYPOINT: `card_ab_hold.telegram.handlers.disable_card_ab_hold` and `card_ab_hold.telegram.confirm_handlers.on_confirm_disable` → actor/access gate.
CAUSAL_PATH: Load campaign → verify foreign relation → neutral rejection → stop before `disable_card_ab_hold_in_session`, `clear_epoch_on_exit`, Redis signal cleanup, FSM reset, or redraw of foreign state.
THIN_ENDS: Existing relation/PG read; Telegram neutral-notification transport.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `foreign-disable-no-side-effects` seam through both direct EXIT and confirm-flow EXIT handlers; assert durable PG, FSM, Redis, and lifecycle state remain unchanged.
  CONTRACT_CASES: `CAH-OWN-FOREIGN-DISABLE-001`.
  STUB_CONTRACT: Foreign relation result and neutral response parity with production helper/notification contracts.
  BOUNDARY_INTEGRATION_WRITE: not_applicable — authorized EXIT write/cleanup must not be reached.
  BOUNDARY_INTEGRATION_READ: PG campaign load and relation-helper read contract.
  BOUNDARY_INTEGRATION_OTHER: Redis state read contract for proving no cleanup; Telegram neutral-notification contract.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Test with a campaign that has non-empty epoch and Redis coordination state so a silent cleanup cannot pass.
MOCKING_CONSTRAINTS: Do not patch EXIT handlers or use `assert_not_called()` as the sole proof; execute the real foreign gate and compare durable/coordination state.

### S04 — Post-warm-up display shows factual position and proposed target place separately

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Post-warm-up display shows valid factual position and proposed target place separately`
LIFECYCLE_STEPS: L3
GIVEN_WHEN_THEN: WARM_UP completed and a keyword has finite factual position greater than zero; post-warm-up screen is viewed; fact and proposed target are separate fields and the keyword remains confirmable.
PRODUCTION_ENTRYPOINT: `confirm_handlers._render_for_adv` → `_load_factual_positions` → `_tp_rows_from_adv` → `build_w3_propose_text`.
CAUSAL_PATH: Load durable confirmed keyword set → read live CH+PG factual positions → filter/propose positive target → render two semantic fields and include keyword in the confirmable rows.
THIN_ENDS: CH+PG factual-position read model; Telegram screen render transport.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `w3-positive-fact-target-separation` seam with real row construction and screen formatting; assert distinct fact/target labels and confirmable membership.
  CONTRACT_CASES: `CAH-TP-POSITIVE-001`, `CAH-TP-FIELD-SEPARATION-001`.
  STUB_CONTRACT: Factual-position DTO and Telegram render response parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable.
  BOUNDARY_INTEGRATION_READ: CH+PG keyword/factual-position read contract.
  BOUNDARY_INTEGRATION_OTHER: Telegram screen-render contract.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Use a finite positive raw `cluster_stat.position`; do not prebuild target rows as the test input.
MOCKING_CONSTRAINTS: Do not patch `_tp_rows_from_adv`, `propose_target_places_from_positions`, or the formatter under test.

### S05 — Missing factual position excludes a keyword

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Missing factual position excludes a keyword`
LIFECYCLE_STEPS: L3
GIVEN_WHEN_THEN: WARM_UP completed and a confirmed keyword has no factual current position; screen is viewed; it is shown as excluded with unavailable-position reason and no zero fact/target is created.
PRODUCTION_ENTRYPOINT: `confirm_handlers._render_for_adv` → `_load_factual_positions` → `_tp_rows_from_adv`/positive-input validator → W3 renderer.
CAUSAL_PATH: Read keyword set and factual read model with missing key → classify exclusion → render reason → omit keyword from confirmable target map.
THIN_ENDS: CH+PG factual-position read model; Telegram screen render transport.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `w3-missing-fact-exclusion` seam; assert exclusion reason, absent confirmable row, and absence of target place `0`.
  CONTRACT_CASES: `CAH-TP-MISSING-001`.
  STUB_CONTRACT: Missing-position representation and render response parity, including empty/missing shape.
  BOUNDARY_INTEGRATION_WRITE: not_applicable.
  BOUNDARY_INTEGRATION_READ: CH+PG factual-position read contract proving missing-key shape.
  BOUNDARY_INTEGRATION_OTHER: Telegram screen-render contract.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Represent missing factual data as the production read-model absence, not as a fabricated numeric zero.
MOCKING_CONSTRAINTS: Do not patch the exclusion validator or insert a `0` fixture where the real boundary returns absence.

### S06 — Non-positive factual position excludes a keyword

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Non-positive factual position excludes a keyword`
LIFECYCLE_STEPS: L3
GIVEN_WHEN_THEN: WARM_UP completed and a keyword has factual position less than or equal to zero; screen is viewed; it is excluded with invalid-position reason and receives no proposed or saved target.
PRODUCTION_ENTRYPOINT: `confirm_handlers._render_for_adv` → `_load_factual_positions` → `_tp_rows_from_adv`/positive-input validator → W3 renderer.
CAUSAL_PATH: Read raw non-positive factual value → reject it as a candidate → render reason → prevent target-map construction and durable write.
THIN_ENDS: CH+PG factual-position read model; Telegram screen render transport.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `w3-non-positive-fact-exclusion` seam covering zero, negative, and non-finite input cases as ContractCases; assert no target proposal/save.
  CONTRACT_CASES: `CAH-TP-ZERO-001`, `CAH-TP-NEGATIVE-001`, `CAH-TP-NONFINITE-001`.
  STUB_CONTRACT: Raw numeric/empty input and render response parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable.
  BOUNDARY_INTEGRATION_READ: CH+PG factual-position read contract for zero/negative/non-finite representations.
  BOUNDARY_INTEGRATION_OTHER: Telegram screen-render contract.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Preserve raw boundary values until the production validator evaluates them; do not floor or clamp them to one.
MOCKING_CONSTRAINTS: Do not patch validation, target proposal, or epoch writer.

### S07 — Numeric coincidence does not merge the fields

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Numeric coincidence does not merge the fields`
LIFECYCLE_STEPS: L3
GIVEN_WHEN_THEN: Positive factual position and proposed target happen to be numerically equal after rounding/clamping; screen renders; fact and target remain distinct fields.
PRODUCTION_ENTRYPOINT: `confirm_handlers._render_for_adv` → `_load_factual_positions` → `_tp_rows_from_adv` → `build_w3_propose_text`.
CAUSAL_PATH: Read positive fact → compute proposal → render two labeled semantic values even when their numbers coincide.
THIN_ENDS: CH+PG factual-position read model; Telegram screen render transport.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `w3-coincident-values-stay-separate` seam; assert two field labels and independent values/metadata rather than only string equality.
  CONTRACT_CASES: `CAH-TP-FIELD-SEPARATION-002`.
  STUB_CONTRACT: Positive factual-position and render response parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable.
  BOUNDARY_INTEGRATION_READ: CH+PG factual-position read contract.
  BOUNDARY_INTEGRATION_OTHER: Telegram screen-render contract.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Choose a production-valid input whose proposal equals the rounded fact without collapsing source fields in the fixture.
MOCKING_CONSTRAINTS: Do not test only the formatter with handcrafted rows; reach it through live row construction.

### S08 — User confirms only the remaining valid target places

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: User confirms only the remaining valid target places`
LIFECYCLE_STEPS: L3, L4, L5
GIVEN_WHEN_THEN: Post-WARM_UP screen contains valid and excluded keywords; associated user explicitly confirms; only valid keywords receive durable target places and the existing flow continues.
PRODUCTION_ENTRYPOINT: `confirm_handlers.on_tp_confirm_all` → `_load_factual_positions` → `_tp_rows_from_adv` → `epoch_write.confirm_target_places`.
CAUSAL_PATH: Actor gate → stale/phase gate → live factual read → positive-only candidate construction → final epoch write validation under `FOR UPDATE` → phase advances for valid set.
THIN_ENDS: PG campaign read; CH+PG factual read; PG write/read-after-write; Telegram next-step rendering.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `tp-confirm-valid-subset` seam; assert persisted positive map contains exactly valid keywords, excluded keyword absent, and next phase is reached.
  CONTRACT_CASES: `CAH-TP-MIXED-001`.
  STUB_CONTRACT: Factual read, PG writer response, and next-step render parity.
  BOUNDARY_INTEGRATION_WRITE: PG `confirm_target_places_in_session` with `FOR UPDATE`; assert exact persisted subset and phase.
  BOUNDARY_INTEGRATION_READ: PG precondition/read-after-write plus factual CH+PG read.
  BOUNDARY_INTEGRATION_OTHER: Telegram screen-render contract.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Use mixed valid/missing/non-positive inputs and verify persisted JSON, not only in-memory `tp_map`.
MOCKING_CONSTRAINTS: Do not patch subset construction or `confirm_target_places`; external transport only may be stubbed.

### S09 — Empty valid set cannot be confirmed

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Empty valid set cannot be confirmed`
LIFECYCLE_STEPS: L3, L4, L5
GIVEN_WHEN_THEN: All confirmation keywords have missing or non-positive factual positions; user attempts target confirmation; confirmation stops, no target is saved, and the reason is shown.
PRODUCTION_ENTRYPOINT: `confirm_handlers.on_tp_confirm_all` → factual read/positive-input validation → empty-set guard before `epoch_write.confirm_target_places`.
CAUSAL_PATH: Actor/phase gate → factual read → exclude every keyword → explicit empty-valid-set guard → neutral/actionable user message; no PG update, phase transition, FSM reset, or Redis cleanup.
THIN_ENDS: PG campaign read; CH+PG factual read; Telegram notification/render transport.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `tp-confirm-empty-valid-set` seam; assert no durable write and no phase/lifecycle change while proving the real empty-set guard was reached.
  CONTRACT_CASES: `CAH-TP-EMPTY-001`.
  STUB_CONTRACT: Empty/missing factual read shape and user message response parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable — the writer must not be reached.
  BOUNDARY_INTEGRATION_READ: PG campaign state and CH+PG all-invalid factual read contract.
  BOUNDARY_INTEGRATION_OTHER: Telegram empty-set message contract.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Snapshot durable phase and target map before/after; no call-count-only proof.
MOCKING_CONSTRAINTS: Do not patch the empty-set guard or writer; do not pre-return an empty map from the function under test.

### S10 — Confirmed target place is not recalculated on a later setup tick or retry

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Confirmed target place is not recalculated on a later setup tick or retry`
LIFECYCLE_STEPS: L2, L3, L5, L6
GIVEN_WHEN_THEN: Current epoch has a confirmed target place; later setup tick or activation retry runs; confirmed target is neither recalculated nor overwritten.
PRODUCTION_ENTRYPOINT: Existing A/B Hold epoch/setup retry path → durable PG generation/intent read → WB sync retry using the same generation and confirmed payload.
CAUSAL_PATH: Read durable PENDING/WB_SYNC state → acquire existing epoch row lock → reuse stored generation/idempotency/confirmed parameters → perform only existing retry sync → preserve durable target.
THIN_ENDS: PG read/write lifecycle boundary; WB/HTTP synchronization transport; Telegram status/read transport if surfaced.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `retry-reuses-confirmed-epoch-parameters` seam through real retry orchestration; assert same generation/idempotency key/target map and no recalculation.
  CONTRACT_CASES: `CAH-EPOCH-RETRY-001`, `CAH-EPOCH-PARTIAL-SYNC-001`.
  STUB_CONTRACT: WB request/response/failure shape, PG lifecycle DTO, and retry exception/async parity.
  BOUNDARY_INTEGRATION_WRITE: PG persisted intent/status transition with `FOR UPDATE`; assert no target overwrite.
  BOUNDARY_INTEGRATION_READ: PG durable generation/intent read and read-after-retry.
  BOUNDARY_INTEGRATION_OTHER: WB sync boundary contract; authorized provider execution is a later certification concern.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Simulate partial/failed provider response only at the thin WB boundary; retain the real retry/generation logic.
MOCKING_CONSTRAINTS: Do not patch generation, pending-intent construction, retry selection, or target proposal; provider stub must match boundary contract.

### S11 — Ordinary position drift after confirmation does not reopen confirmation

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Ordinary position drift after confirmation does not reopen confirmation`
LIFECYCLE_STEPS: L2, L3, L5
GIVEN_WHEN_THEN: Epoch has confirmed target; factual position later drifts; observation occurs; confirmation is not reopened and durable target is unchanged.
PRODUCTION_ENTRYPOINT: `confirm_handlers._render_for_adv`/`_render_w3_confirmed` with live factual read model, plus normal observe/reconcile path.
CAUSAL_PATH: Read durable confirmed epoch → read changed factual position → render current fact separately → retain durable target and generation; no confirm callback or target write is triggered.
THIN_ENDS: PG durable read; CH+PG factual-position read; Telegram render transport.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `fact-drift-does-not-reopen-confirmation` seam with before/after durable snapshots; assert changed fact, unchanged target/generation, and no new confirmation phase.
  CONTRACT_CASES: `CAH-EPOCH-FACT-DRIFT-001`.
  STUB_CONTRACT: Drifted factual read and render response parity.
  BOUNDARY_INTEGRATION_WRITE: not_applicable — observation must not write confirmed parameters.
  BOUNDARY_INTEGRATION_READ: PG durable confirmed-state read and CH+PG factual-position read.
  BOUNDARY_INTEGRATION_OTHER: Telegram read-only screen contract.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Change only the live factual read-model value; do not mutate durable confirmed columns as setup.
MOCKING_CONSTRAINTS: Do not patch the no-reopen behavior or writer; use real rendering and reconciliation decision logic.

### S12 — Valid confirmation preserves the existing lifecycle

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Valid confirmation preserves the existing lifecycle`
LIFECYCLE_STEPS: L1, L2, L3, L4, L5, L6
GIVEN_WHEN_THEN: Associated user confirms a non-empty valid positive set; existing A/B Hold flow continues; WARM_UP, generation, durable confirmation, PG/Redis coordination, and later transitions retain semantics without an extra epoch.
PRODUCTION_ENTRYPOINT: Full Telegram confirmation sequence → `epoch_write.confirm_*` → `create_pending_intent_for_generation` → existing WB sync → ACTIVE/retry state.
CAUSAL_PATH: Actor/stale gates → factual validation → explicit TP/Auto confirmations → one durable PENDING intent → existing WB sync and Redis coordination → ACTIVE only after complete sync.
THIN_ENDS: PG writes/reads; CH+PG factual read; Redis ENTER/coordination; WB synchronization; Telegram rendering.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `authorized-full-confirmation-lifecycle` seam covering all confirmation phases and asserting existing phase/generation/side-effect boundaries.
  CONTRACT_CASES: `CAH-LIFECYCLE-POSITIVE-001`, `CAH-LIFECYCLE-RETRY-001`.
  STUB_CONTRACT: PG session/DTO, CH+PG factual rows, Redis signal, WB sync response, and Telegram output must use shared contract sources.
  BOUNDARY_INTEGRATION_WRITE: PG confirmation and pending-intent writes with row lock; assert one generation and durable parameters.
  BOUNDARY_INTEGRATION_READ: PG phase/generation/status read-after-write and factual read model.
  BOUNDARY_INTEGRATION_OTHER: Redis coordination contract and WB sync boundary contract; provider receipt required only for later certify if applicable.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Exercise the existing lifecycle writer; do not create a second test-only lifecycle or new ownership adapter.
MOCKING_CONSTRAINTS: Stub only thin Redis/WB/Telegram ends with parity tests; do not patch confirmation or epoch orchestration.

### S13 — Hardening does not authorize unrelated writes

SCENARIO_ID: `openspec/changes/harden-ab-hold-confirmation-boundaries/specs/card-ab-hold-mode/spec.md::#### Scenario: Hardening does not authorize unrelated writes`
LIFECYCLE_STEPS: L1, L5
GIVEN_WHEN_THEN: Campaign is in A/B Hold confirmation or hold; hardening checks are evaluated; unrelated whitelist, blacklist/minus, keyword-status, bid, budget, ordinary-updater, and external WB writes remain governed by existing ownership.
PRODUCTION_ENTRYPOINT: A/B Hold confirmation/disable callback handlers plus existing writer ownership guards from `card-ab-hold-write-path-ownership`.
CAUSAL_PATH: Evaluate hardening gate → allow only the owned A/B Hold confirmation/EXIT path → verify ordinary/shared/Excel writer paths remain excluded or independently governed.
THIN_ENDS: PG campaign read; Telegram response; optional external writer boundary only for forbidden-path observation.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: `hardening-does-not-authorize-unrelated-writers` seam through real callback and writer-selection logic; assert owned effect only and forbidden writers remain untouched without relying solely on call counts.
  CONTRACT_CASES: `CAH-OWN-UNRELATED-WRITERS-001`.
  STUB_CONTRACT: Telegram output and any observed external-writer response must match production shapes.
  BOUNDARY_INTEGRATION_WRITE: PG owned A/B Hold write-path contract; unrelated writers are out of the allowed path.
  BOUNDARY_INTEGRATION_READ: PG phase/mode read contract.
  BOUNDARY_INTEGRATION_OTHER: Redis/WB/Telegram contracts only where the allowed path reaches them.
  LOAD_OR_PERFORMANCE: not_applicable.
REALITY_CONSTRAINTS: Include paired forbidden writer assertions for ordinary V3/shared defaults/Excel/bid/budget paths; do not broaden this change's write inventory.
MOCKING_CONSTRAINTS: Do not replace writer ownership selection with a mock; use probes at thin write boundaries and prove no forbidden durable effect.

## Open questions and gaps

OPEN_QUESTIONS: []
UNRESOLVED_GAPS: []
PLANNING_NOTES:

- Local validator/helper names and neutral rejection copy remain implementation
  details explicitly allowed by the Owner Contract; they do not alter evidence
  semantics.
- Required tests, boundary integrations, stubs, and provider receipts are
  intentionally not asserted to exist in this plan.
- Product Acceptance remains pending until later authored/evaluated side-effect
  evidence and the independent scenario coverage report exist.

## Generated from

GENERATED_FROM:

- owner-contract.md: `2810e901dfd3b693ace36906730ed90a2b777c81c1daa68e79e3fa841cd5eec1`
- design.md: `14a485231da95d280bab16ac3e79d71c442a0449abe1f415700ba0678e41c216`
- specs/card-ab-hold-mode/spec.md: `c8d8434154330503a424b3643a8539d52eca4f08a3b69c9e1313af0d385d6aa4`
- decisions/card-ab-hold-write-path-ownership/decision.md: `03853d9403b8e180aa2df4158b543206d7dbde07e1b2bc2875156e4929df7811`
- decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md: `eb4b6de99b3825c970459b0f74849e1bb7c95046f00a93e79a531a9942dca071`
- decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md: `ae2f148974e2f9369b028a03663cd1d363c8b78beaea75934e390cc9a2349633`
- SCENARIO_TEST_COVERAGE.md: `fe3a98e0711555e02a2fd7847dc9f74dbd22e7799bcd36cfb5df26c37257a53d`
- worktree snapshot fingerprint before materialization: `878f5cb3292e2a58724294dab63ad3c56ff6c22b4bba86d3b62ec5a6ce3e64e8`

SOURCE_RESOLUTION:

- mode: exact_path | canonical_id | referenced_source
- primary_path: `openspec/changes/harden-ab-hold-confirmation-boundaries/`
- fallback_used: false
- search_operations: 0 after exact artifact resolution; one bounded exact-symbol lookup for production path confirmation
- search_scope: change artifacts, referenced decisions, named A/B Hold handlers/writer/read-model symbols
- unresolved_gap: none

EXECUTION_PREFLIGHT:

- git_branch: deferred_not_required
- git_status: ok (required for worktree fingerprint)
- other_ops: `openspec status --change harden-ab-hold-confirmation-boundaries --json`
- blocked_on_preflight: false

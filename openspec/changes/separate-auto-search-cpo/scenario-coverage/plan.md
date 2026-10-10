# Scenario Coverage Plan

CHANGE_ID: separate-auto-search-cpo
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPLAN-49f4ee71d860e462b991
LIFECYCLE_STATUS: not_required_non_temporal

## LIFECYCLE_COVERAGE

Change не вводит новый temporal/state-machine lifecycle. Acceptance относится к steady-state routing фактического CPO между существующими Auto/Search consumers.

- LIFECYCLE_GAPS: none
- TEMPORAL_TRANSITIONS_REQUIRED: no

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
SOURCE_SPEC_SHA: 19b3c335e5f8d13d94f2617300af5abcf5086e905e26a3521f8cc667b76b13e4

### LEG-CPO-001 — Auto и Search имеют разную экономику

GIVEN_WHEN_THEN: раздельные spend/orders двух ног дают два независимых CPO.
PRODUCTION_ENTRYPOINT: shared leg-CPO provider / shop-runner attach path.
CAUSAL_PATH: exact adv_id stats -> pure CPO calculation -> LegCpoSnapshot.
THIN_ENDS: ClickHouse read.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: provider returns distinct Auto/Search values from one window.
- CONTRACT_CASES: different spend/orders; zero orders denominator floor.
- BOUNDARY_INTEGRATION_READ: CH grouping by concrete adv_id preserves leg identity.
REALITY_CONSTRAINTS: Auto=anchor adv_id; Search=linked search_adv_id.
MOCKING_CONSTRAINTS: calculator/provider causal logic MUST NOT be mocked away.

### LEG-CPO-002 — Search-нога отсутствует

GIVEN_WHEN_THEN: unpaired Auto -> Search CPO unavailable, без synthetic fallback.
PRODUCTION_ENTRYPOINT: shared leg-CPO provider.
CAUSAL_PATH: structural pair resolution -> snapshot.
THIN_ENDS: none beyond read provider.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: missing search_adv_id produces search_cpo=None.
- CONTRACT_CASES: Auto value remains available independently.
REALITY_CONSTRAINTS: missing Search is valid production shape.
MOCKING_CONSTRAINTS: MUST preserve real structural pair mapping.

### LEG-CPO-003 — Auto плохой, Search хороший

GIVEN_WHEN_THEN: Auto CPO above threshold, Search CPO below -> Search CPO-dependent decisions use Search only.
PRODUCTION_ENTRYPOINT: paid V3/Search orchestration entrypoints.
CAUSAL_PATH: attached Search CPO -> V3/Search decision state -> existing Search candidate/write boundary.
THIN_ENDS: WB Search bid/keyword write adapters may be stubbed after decision boundary.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: paired good-Search/bad-Auto case stays on Search economics.
- CONTRACT_CASES: V3 keyword state/calibration; common Search bid; bidder cap; cluster-bid cap; A/B Hold overspend.
- STUB_CONTRACT: existing WB adapters receive unchanged command shape.
REALITY_CONSTRAINTS: every runtime-reachable Search CPO consumer is inventoried.
MOCKING_CONSTRAINTS: MUST NOT inject precomputed decision result after the CPO-selection seam.

### LEG-CPO-004 — Search CPO недоступен

GIVEN_WHEN_THEN: Search CPO unavailable -> no Auto/common fallback for destructive Search decision.
PRODUCTION_ENTRYPOINT: same Search orchestration seams as LEG-CPO-003.
CAUSAL_PATH: search_cpo=None -> consumer missing-data branch -> no cross-leg substitute.
THIN_ENDS: existing Search write adapters.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: at least one destructive Search path proves no sibling/common fallback.
- CONTRACT_CASES: all migrated consumers handle None explicitly.
REALITY_CONSTRAINTS: None is distinct from numeric zero.
MOCKING_CONSTRAINTS: real missing-data branch must execute.

### LEG-CPO-005 — Search плохой, Auto хороший

GIVEN_WHEN_THEN: Search CPO above threshold, Auto CPO below -> Auto CPO-dependent decisions use Auto only.
PRODUCTION_ENTRYPOINT: Auto Shelf Bid Control and Auto activity-control orchestration.
CAUSAL_PATH: attached Auto CPO -> Auto decision/read model -> existing Auto boundary.
THIN_ENDS: WB Auto bid/pause adapter may be stubbed after decision boundary.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: bad-Search/good-Auto does not alter Auto solely due to Search.
- CONTRACT_CASES: shelf fact-CPO input/view; Auto cost/activity confirmation.
- STUB_CONTRACT: existing Auto adapter command shape unchanged.
REALITY_CONSTRAINTS: accepted Auto write-path ownership remains unchanged.
MOCKING_CONSTRAINTS: MUST NOT bypass Auto CPO selection by prebuilding a decision.

### LEG-CPO-006 — Auto CPO недоступен

GIVEN_WHEN_THEN: Auto CPO unavailable -> no Search/common fallback for Auto decision.
PRODUCTION_ENTRYPOINT: Auto shelf/activity orchestration.
CAUSAL_PATH: auto_cpo=None -> existing safe missing-data behavior.
THIN_ENDS: existing Auto write adapters.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: Auto path does not substitute Search/common CPO.
- CONTRACT_CASES: shelf and activity consumers distinguish None.
REALITY_CONSTRAINTS: Auto leg exists structurally even when usable stats do not.
MOCKING_CONSTRAINTS: execute real missing-data branch.

### LEG-CPO-007 — Общий CPO отличается от leg CPO

GIVEN_WHEN_THEN: aggregate differs -> aggregate remains aggregate and cannot impersonate leg value.
PRODUCTION_ENTRYPOINT: runtime DTO construction/projection.
CAUSAL_PATH: common plan/fact plus attached leg snapshot -> explicit separate fields.
THIN_ENDS: none.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: ComplexAdv/WBAdvDTO retain common and leg values independently.
- CONTRACT_CASES: common value intentionally different from both legs.
REALITY_CONSTRAINTS: backward-compatible common property remains present.
MOCKING_CONSTRAINTS: use production DTO shape, not phantom fields.

### LEG-CPO-008 — UI показывает обе ноги

GIVEN_WHEN_THEN: both leg CPO available -> paid UI displays labeled Auto and Search values.
PRODUCTION_ENTRYPOINT: paid campaign/keyword message rendering.
CAUSAL_PATH: already-loaded exact-leg stats/snapshot -> view state -> text render.
THIN_ENDS: Telegram transport outside render.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: rendered output contains both distinct labeled values.
REALITY_CONSTRAINTS: existing paid screen shape and message length constraints preserved.
MOCKING_CONSTRAINTS: rendering input must use production leg snapshot/stat shape.

### LEG-CPO-009 — UI не подставляет соседнее значение

GIVEN_WHEN_THEN: one leg CPO unavailable -> UI marks that leg unavailable while preserving the other.
PRODUCTION_ENTRYPOINT: paid campaign/keyword message rendering.
CAUSAL_PATH: partial leg snapshot -> view state -> text render.
THIN_ENDS: Telegram transport.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: no duplicated/sibling/common CPO under missing leg label.
REALITY_CONSTRAINTS: unavailable is explicit, not numeric zero unless source returned valid zero.
MOCKING_CONSTRAINTS: use production rendering path.

### LEG-CPO-010 — UI и runtime согласованы

GIVEN_WHEN_THEN: one snapshot/window -> displayed leg value equals value routed to that leg's CPO consumer.
PRODUCTION_ENTRYPOINT: shared leg provider projection to DTO/UI and control.
CAUSAL_PATH: one calculation contract -> runtime carrier -> consumer + renderer.
THIN_ENDS: none required for equality proof.
REQUIRED_EVIDENCE:
- SCENARIO_SEAM: shared helper/snapshot drives both projections without second formula.
- CONTRACT_CASES: Search projection and Auto projection.
REALITY_CONSTRAINTS: observation window metadata is identical per snapshot.
MOCKING_CONSTRAINTS: MUST NOT hardcode expected UI number independently of provider calculation.

## OPEN_QUESTIONS

None.

## UNRESOLVED_GAPS

None at planning time. Test existence/execution is deliberately not claimed by mode=plan.

## GENERATED_FROM

- design.md: 39f3083a2b13510152b3d2ea53b229ac174c846d07413ec9b9b709b4eac802e8
- specs/leg-cpo-economics/spec.md: 19b3c335e5f8d13d94f2617300af5abcf5086e905e26a3521f8cc667b76b13e4
- owner-contract.md: 673cadf71b1bc4090a30bb2874d5faac45165ca4320ce2a86898287c5460a59a

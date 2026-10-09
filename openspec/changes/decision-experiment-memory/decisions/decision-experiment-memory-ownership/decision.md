# Decision: Decision and experiment memory ownership

## Status

Accepted (promoted to `openspec/decisions/decision-experiment-memory-ownership/decision.md`)

## Context

WB Sky separates settings snapshots (`campaign-settings-history`), ChangeSet
validation (`wb_sky_control_plane` dry-run), and (planned) Apply Authority.
`ChangeSetMetadataV1` already carries optional `decision_id` / `experiment_id` but
no durable semantic store exists. AI Package and future MCP agents need a single
read contract for WHY / EXPECT / OUTCOME without becoming mutation authority.

No accepted decision in `openspec/decisions/` assigns this ownership today.

## Decision

1. **Decision-experiment memory** is a dedicated domain module
   `app/modules/decision_experiment_memory/` (Slice A+: vocabulary first).

### Owns (semantic memory authority)

- Decision semantics (`DecisionMemoryRecord` / `decision_id`)
- Preregistered **`ExperimentPlan`** revisions and freeze/deviation semantics
- Experiment lifecycle semantics (`ExperimentRecordV1` / `experiment_id`, execution vs outcome)
- `treatment_mode` (`LIVE` | `SHADOW`) distinct from `experiment_design`
- Evaluation and **data validity** semantics
- **Factual** experiment-result history (`FactualResult`)
- **Interpretation** records and **provenance** linkage (refs/digests, not source payloads)
- Append-only memory events and `DecisionMemoryReader` projections

### Does not own (reference only)

- Campaign / settings truth → `campaign-settings-history`, settings registry
- Product / catalog truth → respective domain authorities
- **Apply execution truth** → future Apply Authority (`ApplyEvidenceRef` only in memory)
- **Factual source metric truth** → CH/PG/export metric authorities (`MetricSpecRef`)
- **Attribution truth** → `attribution-facts-contract` when deployed

No authoritative payload duplication in memory SoT.

2. It is **not** write authority for campaign settings, WB API, or Apply. It MAY
   append metadata events only; Apply Authority remains sole production mutation
   truth.
3. It MUST reference — not copy — authoritative payloads:
   - settings: `state_token` / history snapshot ids (`campaign-settings-history`);
   - intent: `changeset_id` + `semantic_digest` (`ChangeSetV1`);
   - validation: `dry_run_receipt_id` + digest;
   - execution: `ApplyEvidenceRef` (`apply_evidence_id` + optional digest; no receipt body);
   - attribution: `attribution_fact_set_ref` when `attribution-facts-contract`
     is deployed (optional; validity degrades if missing).
4. **PostgreSQL** is the V1 authoritative store for events and projections;
   ClickHouse MAY receive derived analytics later but MUST NOT be SoT for memory.
5. AI Package export (`ai_package_v1`) MAY consume `DecisionMemoryReader` in a
   separate change; exporter MUST stay `READ_ONLY_NO_MUTATION`.
6. Card A/B Hold durable state remains owned by A/B Hold decisions; memory MAY
   store optional opaque `product_experiment_ref` but MUST NOT re-implement hold
   write-path or epoch lifecycle.

## Applies to

- AI/human/system decision capture and experiment outcome recording.
- Future Apply receipt ingest hooks.
- AI Package `decision_memory_v1` block (future slice).

## Allowed

- Decision without experiment.
- Append-only correction events and superseding records.
- Deterministic `intervention_signature` for experiment similarity; `decision_fingerprint`
  for coarse decision-class hints only.
- LLM narrative only in `Interpretation` / decision prose fields (not factual outcome).
- Frozen `ExperimentPlan` with `PLAN_FROZEN` before confirmatory outcome inspection.

## Forbidden

- Using decision memory to authorize apply or bypass Apply Authority.
- Duplicating campaign settings history rows or ChangeSet bodies as canonical memory.
- Labeling apply confirmed or LIVE exposure without `ApplyEvidenceRef` / effective-state evidence.
- Enforcing `experiment_id = decision_id` as identity invariant.
- Shop-runner or WB API calls from reader/export paths.
- Silent UPDATE of historical reasoning events.

## Examples

Good:

- Record decision with hypothesis + link dry-run receipt → status `VALIDATED`.
- Experiment concludes `INCONCLUSIVE` when metric coverage below `min_coverage`.

Bad:

- Storing full AdvSetting JSON in decision row as authority for current settings.
- Creating second decision on duplicate apply receipt id.

## References

- `openspec/specs/campaign-settings-history/spec.md`
- `openspec/specs/campaign-settings-changeset-contract/spec.md`
- `openspec/decisions/campaign-settings-contract-ownership/decision.md`
- `openspec/decisions/ai-package-v1-exporter-ownership/decision.md`
- `openspec/changes/decision-experiment-memory/design.md`

# Decision: decision-experiment-memory-ownership

## Status

Proposed

> **Not promoted** to `openspec/decisions/` until Owner Contract Review GO.

## Context

WB Sky needs durable, transport-independent memory of decision semantics and
experiment outcomes. Settings history, Apply audit, attribution facts, and metric
pipelines each own different truths. A new module must own decision/experiment
**semantics and result history** without becoming a write authority or duplicating
foreign payloads.

## Decision

**Owner:** `app/modules/decision_experiment_memory/` for:

- decision semantics (`DecisionMemoryRecord`);
- preregistered experiment plan (`ExperimentPlanV1`, freeze/deviation semantics);
- experiment lifecycle semantics (`ExperimentRecordV1`, execution_state);
- validity and evaluation semantics (outcome vocabulary, deterministic rules);
- result history and provenance linkage (refs/digests only);
- reader ports and (Slice B+) PostgreSQL event/projections.

**AI Package exposure (Slice E):** `app/modules/ai_package_v1/decision_memory/`
read-only assembler calling the reader port (`READ_ONLY_NO_MUTATION` per
`ai-package-v1-exporter-ownership`).

## Applies to

- AI-first control loop memory;
- future ChatGPT/API/MCP read surfaces;
- ingest adapters from ChangeSet metadata, dry-run, Apply audit, settings history.

## Allowed

- Append-only events + projections in PostgreSQL (Slice B+).
- Optional `ApplyEvidenceRef` in domain without concrete Apply payload (Slice A).
- Multiple `experiment_id` per `decision_id` in storage; V1 API may limit creates.
- Separate `experiment_design` and `treatment_mode` axes.

## Forbidden

- Treating decision/experiment records as Apply permission.
- Owning campaign settings truth (reference `campaign_settings_history` / contract).
- Owning Apply execution truth (reference Apply audit).
- Owning attribution or raw metric SoT (reference external bundles).
- Copying full ChangeSet bodies or settings payloads when digest/id suffices.
- Placing memory owner in `wb_sky_control_plane`, `campaign_settings_history`,
  `shop_runner`, or shop-runner write paths.
- Equating `experiment_id` and `decision_id` as invariant.
- Encoding `SHADOW` as `experiment_design`.

## Examples

**Good:** `ExperimentRecordV1` stores `changeset_semantic_digest` + `ApplyEvidenceRef`
with `binding_status=BOUND` after Slice C ingest.

**Bad:** `DecisionMemoryRecord` triggers `validate_changeset` apply or WB PATCH.

**Bad:** `experiment_id` defaulted to `decision_id` in schema primary key.

## Related specs

- `openspec/changes/decision-experiment-memory/specs/decision-experiment-memory/spec.md`

## Related changes

- `decision-experiment-memory` (this change)
- `changeset-apply-authority` (future linkage consumer)
- `campaign-settings-changeset-contract` (ChangeSet metadata reuse)

## Review checklist

- [ ] Existing decisions searched before implementation.
- [ ] Relevant decisions cited by path in design.md.
- [ ] Ownership and placement match this decision.
- [ ] No forbidden layer performs memory ownership.
- [ ] Slice A ships without PostgreSQL and without Apply payload types.

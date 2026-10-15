---
cursor:
  subagentId: "bc-0395eb9d-4481-5d61-b4c2-2ed562b540c3"
---

# decision-experiment-memory — planning (worker verification)

Planning-only. Independent inventory on cloud `adv-bot` checkout (2026-10-07). Aligns with [planning-report-bc-2bbf6418.md](./planning-report-bc-2bbf6418.md); code paths re-verified in-repo.

## Architecture decision lookup (context-first, budget ≤3 fallbacks)

| Path | Role |
|------|------|
| `openspec/decisions/campaign-settings-contract-ownership/decision.md` | Settings SoT; evidence via registry + `state_hash` |
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | Slice D read-only export boundary |
| `openspec/changes/archive/2026-10-07-campaign-settings-changeset-contract/` | ChangeSetV1 + dry-run ownership |
| `openspec/changes/archive/2026-10-05-campaign-settings-history/` | CH `006` history grain |
| Store: `docs/changeset-apply-authority-planning.md` | Apply audit + durable dry-run receipts (**not in repo code**) |
| Store: `docs/attribution-facts-contract.md` | Economics facts — reference only (**no `attribution_facts` module in repo**) |

**Architecture Decision Missing (accepted):** `decision-experiment-memory-ownership` — module placement, PG authority, forbidden write-path. Propose under `openspec/changes/decision-experiment-memory/decisions/`.

---

## RETURN (canonical)

**FEATURE:** `decision-experiment-memory`

**STATUS:** Planning contract defined; **no** OpenSpec change folder in `adv-bot` yet; implementation blocked on ownership ADR + durable apply/dry-run audit (apply-authority change).

### EXISTING_REUSABLE_COMPONENTS

| Component | Class | Evidence |
|-----------|-------|----------|
| `ChangeSetV1`, `ChangeSetMetadataV1` (`decision_id`, `experiment_id`) | **REUSE** | `app/modules/wb_sky_control_plane/models/changeset.py` — metadata excluded from `semantic_digest` |
| `compute_semantic_digest` / `sd1` | **REUSE** | `kernel/semantic_digest.py` |
| `DryRunResultV1`, `ChangeSetValidationResult`, `PlanV1` | **REFERENCE** | `models/plan.py` — in-process only; no durable receipt ID |
| `PriorChangeSetRecord` | **REFERENCE** | Injected idempotency hint; not persisted |
| `wb_sky_control_plane` pipeline | **REFERENCE** | Read-only validate; link-only owner |
| `campaign_settings_history` (`HistorySnapshotRow`) | **REFERENCE** | `snapshot_id`, `state_hash`, `observed_at` |
| `campaign_settings_contract` | **REFERENCE** | Registry + normalize for evidence snapshots |
| `ai_package_v1` manifest/assemblers | **EXTEND** (Slice D) | New datasets via reader port |
| `keyword_decisions.jsonl` / `decision_assembler.py` | **DO_NOT_USE** | CH `bid_decision_log` telemetry |
| `ai_package_v1/analysis/*` | **REFERENCE** | Metric IDs for evaluation; not decision SoT |
| `card_ab_hold` epoch PG | **DO_NOT_USE** | Product Hold A/B; optional external `experiment_id` cross-ref only |
| `changeset_apply_*` / dry-run receipt tables | **EVIDENCE_GAP** | Planned in apply-authority store doc only |
| DRR settings hierarchy in AI Package | **REFERENCE** | Do not duplicate or own inside decision memory |

### DOMAIN_AGGREGATES

**V1 (revised):** two transport-independent typed records:

| Aggregate | Key | Role |
|-----------|-----|------|
| **`DecisionMemoryRecord`** | `decision_id` | Actor, evidence, rationale, execution linkage, supersession |
| **`ExperimentRecordV1`** | `experiment_id` + `decision_id` FK | Plan freeze, design/treatment_mode, validity, results, outcome |

- **Cardinality:** Decision 1 → 0..N Experiments; **MUST NOT** equate `experiment_id` and `decision_id`.
- V1 API **may** limit one experiment create per decision; storage/contracts allow 1:N.
- **`experiment_design`** ⊥ **`treatment_mode`** (`LIVE` | `SHADOW`).
- **`ApplyEvidenceRef`** in domain; Slice A not blocked by Apply Authority.
- Repo OpenSpec: `openspec/changes/decision-experiment-memory/`.

#### `ExperimentRecordV1` (canonical sections)

**identity**

| Field | Rule |
|-------|------|
| `experiment_id` | Same as linked `decision_id` unless explicit split (future); indexed |
| `schema_version` | Contract version (e.g. `1`) |
| `plan_revision` | Monotonic int; bump on preregistered-plan amendment event |
| `plan_digest` | `hash(canonical_json(preregistered_plan))` at registration — **identity for plan freeze**, not hypothesis alone |

**scope**

| Field | Rule |
|-------|------|
| `shop_id` | Required |
| `physical_adv_ids[]` | WB adv ids in scope (nullable empty = shop-wide policy experiment) |
| `nm_ids[]` | SKU grain when applicable |
| `category_ids[]` | **OPTIONAL V1** — only if stable category id exists in evidence refs; else omit |

**design**

| Field | V1 notes |
|-------|----------|
| `experiment_design` | Enum: `BEFORE_AFTER`, `SWITCHBACK`, `HOLDOUT`, `SHADOW`, `COUNTERFACTUAL` (no fake RCT) |
| `randomization_unit` | Enum: `SHOP`, `CAMPAIGN`, `NM_ID`, `KEYWORD` — honesty: many V1 paths are deterministic assignment |
| `control_definition` / `treatment_definition` | Structured refs (policy labels + `intervention_class`), not free text alone |
| `allocation` / `schedule` | Optional windows, traffic share — machine-readable |
| `timezone` | IANA; all windows interpreted in this zone |

**preregistered_plan** (immutable after `PLAN_REGISTERED` for that `plan_revision`)

| Field | Rule |
|-------|------|
| `registered_at` | UTC timestamp of registration event |
| `hypothesis` | Human text — **not** used for dedup |
| `primary_metric_ids[]` / `secondary_metric_ids[]` / `guardrail_metric_ids[]` | Registry IDs (align `ai_package_v1/analysis` catalog where possible) |
| `baseline_window` / `observation_window` | UTC bounds; map to prior `evaluate_after` = `observation_window.end` |
| `burn_in` / `burn_out` | Optional sub-intervals inside observation |
| `minimum_effect_of_interest` | Optional scalar + unit per primary metric |
| `success_criteria[]` / `failure_criteria[]` | Machine predicates on metric refs (deterministic evaluator input) |
| `stopping_rule` | Optional; V1 may be `FIXED_HORIZON` only |
| `analysis_method` | Enum + version string (e.g. `DIFF_IN_MEANS/v1`); statistics optional |

**intervention**

| Field | Rule |
|-------|------|
| `changeset_id`, `changeset_semantic_digest` | Link to ChangeSet body identity |
| `previous_state_token` / `applied_state_token` | From dry-run / apply audit — per `cmp_*` map |
| `apply_receipt_id` | Apply audit SoT id (**EVIDENCE_GAP** until apply-authority) |
| `effective_from` | When intervention considered live (≥ apply evidence time) |
| settings before/after | **`SettingsSnapshotRef[]` only**: `{adv_setting_id, snapshot_id, state_hash, observed_at, field_paths?}` — no full payload duplication |

**validity** (factual gates before trusting SUCCEEDED/FAILED)

| Field | Rule |
|-------|------|
| `source_complete_through` | From shop-data-source / package cutoff semantics |
| `attribution_coverage` | From attribution-facts refs + `coverage_status` |
| `reconciliation_status` | Settings history vs apply tokens aligned / mismatch codes |
| `assignment_integrity` / `exposure_integrity` | **V1 partial** — document known gaps; `UNKNOWN` fail-closed for INVALID only when hard violation recorded |
| `concurrent_interventions[]` | Other `experiment_id`s overlapping scope+window |
| `protocol_deviations[]` | Append-only coded events (e.g. `METRIC_WINDOW_SHORTENED`) |
| `validity_status` | `VALID` \| `DEGRADED` \| `INVALID` |
| `validity_reason_codes[]` | Stable codes |

**results**

| Field | Rule |
|-------|------|
| `metric_definition_versions[]` | Per metric id used in evaluation |
| `baseline_values[]` / `treatment_values[]` / `deltas[]` | Factual numbers at `evaluation_cutoff` |
| uncertainty / statistics | **Optional V1** — if present, must not override deterministic `outcome` |
| `evaluation_cutoff` / `evaluated_at` | Cutoff ≤ now for terminal outcome |

**outcome**

| Status | When |
|--------|------|
| `SUCCEEDED` | `validity_status ∈ {VALID,DEGRADED}` + complete criteria → success |
| `FAILED` | Validity OK + failure criteria met |
| `INCONCLUSIVE` | Partial/missing metrics, window open, attribution unavailable, denominator zero |
| `INVALID` | `validity_status=INVALID` or hard protocol violation — **not** guessable as success/failure |
| `ABORTED` | Stopped before evaluation |
| `deterministic_reason_codes[]` | Machine codes (parallel to human `decision` text) |
| `decision` | Short human conclusion (non-authoritative over codes) |
| `follow_up` | Optional next `decision_id` / action hint — reference only |

**provenance**

| Field | Rule |
|-------|------|
| `ai_package_id` / digest | Package used for evidence |
| `input_dataset_refs[]` | Dataset card ids + cutoff |
| `settings_snapshot_refs[]` | Same as intervention refs, deduped |
| `analysis_code` / `producer` / `version` | Evaluator identity for audit |

### DECISION_VS_EXPERIMENT_BOUNDARY

| | Decision-only | Experiment (`ExperimentRecordV1` required) |
|---|---------------|------------------------------------------|
| Semantics | observation + rationale + intended_action | + preregistered_plan + design + validity + results |
| Plan freeze | N/A | `PLAN_REGISTERED` locks `plan_digest` for `plan_revision` |
| Terminal without apply | `execution_status` closed / `NOT_APPLIED` | `outcome=ABORTED` or `INCONCLUSIVE` |
| Outcome field | `NOT_APPLICABLE` | `SUCCEEDED` / `FAILED` / `INCONCLUSIVE` / `INVALID` / `ABORTED` |

### IDENTITIES

| Key | Rule |
|-----|------|
| `decision_id` | Opaque UUID/ULID; primary key |
| `experiment_id` | Optional; V1 default = `decision_id` when experiment |
| `revision` | Monotonic per `decision_id` (event sequence) |
| `semantic_intent_digest` | Hash of normalized intent (ops + targets + direction) — **not** hypothesis text |
| `intervention_class` | Stable enum (`BUDGET_POLICY`, `BID_POLICY`, …) |
| `experiment_fingerprint` | `hash(shop_id, scope_ref, intervention_class, semantic_intent_digest)` |
| `evidence_cutoff_digest` | Hash of evidence pointer bundle at record time |

### LIFECYCLE

**Execution linkage (all records):** `DRAFT` → `READY` → `LINKED` (changeset + `semantic_digest`) → `DRY_RUN_RECORDED` → `APPLY_EVIDENCE_PENDING` → `APPLY_RECORDED` (only with apply audit) → `CLOSED` (rejected/superseded without observe).

**Experiment overlay:** `DESIGNED` → `OBSERVING` (after `APPLY_RECORDED` or explicit `SHADOW`/`COUNTERFACTUAL` start) → `EVALUATION_DUE` → `OUTCOME_SET`.

**Hard rules:** no `APPLY_RECORDED` without apply audit SoT; no `SUCCEEDED`/`FAILED` without criteria or `OUTCOME_OVERRIDE` correction; open window → `INCONCLUSIVE`.

### EVIDENCE_REFERENCES

Pointers only: `ai_package_id`, manifest digest, cutoff; `analysis_windows[]`; `settings_evidence[]` (`snapshot_id`, `state_hash`); `state_tokens`; `capabilities_snapshot_digest`; `attribution_refs[]` with `coverage_status`. No full ChangeSet/settings payloads; no DRR hierarchy recomputation here.

### CHANGESET_LINKAGE

`changeset_id`, `semantic_digest` (`sd1`), contract version; reverse index from `ChangeSetMetadataV1.decision_id`.

### DRY_RUN_LINKAGE

**EVIDENCE_GAP:** planned `dry_run_receipt_id` / digest, status, preview digest, capability snapshot, `state_tokens`, TTL; dedup `(dry_run_receipt_digest)` or `(changeset_id, semantic_digest, attempt_no)`.

### APPLY_RECEIPT_LINKAGE

Consume apply audit: `apply_request_id`, idempotency key, terminal outcome, `apply_plan_digest`, linked dry-run receipt. `APPLY_RECORDED` only for terminal `{APPLIED, NO_EFFECT}` with matching `changeset_id` + `semantic_digest`.

### SETTINGS_HISTORY_LINKAGE

Pre-decision: latest `snapshot_id` + `state_hash` per campaign (read-only). Post-apply: optional `post_apply_snapshot_id`. History ≠ experiment outcome.

### EVALUATION_CONTRACT

Deterministic `FactualOutcomeV1`: `coverage` (`COMPLETE|PARTIAL|MISSING`), `criteria_results`, derived `outcome_status`. AI explanation optional; cannot be sole source of status. Denominator zero / attribution missing / window open → `INCONCLUSIVE`.

### OUTCOME_STATUSES

**Experiment (`ExperimentRecordV1.outcome`):** `SUCCEEDED` | `FAILED` | `INCONCLUSIVE` | `INVALID` | `ABORTED`

**Decision-only:** `NOT_APPLICABLE` (no experiment outcome block)

**Rule:** `INVALID` when validity or protocol integrity fails; `INCONCLUSIVE` when evidence insufficient but protocol not invalidated.

### APPEND_ONLY_MODEL

Events: `CREATED`, `SEMANTICS_PATCHED`, `PLAN_REGISTERED`, `PLAN_AMENDED` (bumps `plan_revision`), `CHANGESET_LINKED`, `DRY_RUN_INGESTED`, `APPLY_INGESTED`, `VALIDITY_ASSESSED`, `EVALUATION_INGESTED`, `OUTCOME_COMPUTED`, `PROTOCOL_DEVIATION`, `SUPERSEDED`. Immutable first `decision_context_digest` and per-revision `plan_digest`; materialized `decision_memory_projection` + `experiment_record_projection`.

### CORRECTION_MODEL

`CORRECTION` with `HUMAN_RATIONALE_FIX`, `OUTCOME_OVERRIDE`, `LINKAGE_FIX`; references `supersedes_event_id`. Late metrics via `EVALUATION_INGESTED`; status flips require new `OUTCOME_COMPUTED` or correction — no silent UPDATE.

### IDEMPOTENCY_MODEL

| Operation | Dedup key |
|-----------|-----------|
| Create decision | `(shop_id, semantic_intent_digest, evidence_cutoff_digest, client_request_id?)` |
| Register experiment plan | `(experiment_id, plan_revision, plan_digest)` |
| Link ChangeSet | `(decision_id, semantic_digest)` |
| Ingest dry-run | `dry_run_receipt_digest` |
| Ingest apply | `apply_request_id` or `apply_attempt_digest` |
| Evaluation | `(decision_id, evaluation_batch_id)` |
| Late metrics | `(decision_id, metric_source_digest, window_end)` |

Never dedupe on hypothesis free text.

### READER_PORT

`DecisionMemoryReaderPort`: recent decisions, active experiments, completed outcomes, by changeset, by scope, similar experiments (`experiment_fingerprint` + `plan_digest` family), full timeline; `get_experiment_record_v1(experiment_id)` returns full section bundle. **Forbidden:** WB/PG settings writes, apply triggers.

### AI_PACKAGE_FUTURE_CONTRACT

Schema bump (e.g. `1.2.0`); datasets `recent_decisions`, `active_experiments`, `experiment_results` (jsonl); manifest `decision_memory_schema_version`; assembler under `ai_package_v1/decision_memory/` calling reader only.

### PHYSICAL_STORAGE_CANDIDATE

PostgreSQL append-only `decision_memory_event` + indexed `decision_memory_projection`. ClickHouse remains settings/metrics sources — not decision semantics SoT in V1.

### IMPLEMENTATION_SLICES

| Slice | Scope |
|-------|--------|
| **A** | Domain, PG events, projection, reader port, unit tests |
| **B** | ChangeSet / dry-run / apply ingest adapters + idempotency |
| **C** | `ExperimentRecordV1` validity + results + outcome (`INVALID` vs `INCONCLUSIVE`), preregistration freeze, corrections |
| **D** | AI Package datasets (no MCP transport) |

### Risk register

| Level | Item |
|-------|------|
| **CRITICAL** | Decision record treated as apply authority |
| **CRITICAL** | `APPLY_RECORDED` without apply audit |
| **HIGH** | Duplicating settings payloads vs snapshot refs |
| **HIGH** | Conflating `bid_decision_log` / keyword_decisions with this memory |
| **HIGH** | Missing ownership ADR |
| **MEDIUM** | Premature outcome before `evaluate_after` |
| **MEDIUM** | Similar-experiment false positives without `intervention_class` |
| **MEDIUM** | Treating `INVALID` as `FAILED` or inferring success when validity is `INVALID` |
| **MEDIUM** | Preregistered plan mutated without `PLAN_AMENDED` + new `plan_revision` |
| **LOW** | AI narrative overwriting factual outcome |

### IMPLEMENTATION_READY

**no**

### FINAL_STATUS

**READY_FOR_OWNER_CONTRACT_REVIEW** — proposed ADR not promoted; implementation blocked until Owner accepts ADR + slice GOs.

---

## Proposed ADR placement (draft)

| Layer | Path |
|-------|------|
| Domain + events + projection + reader | `app/modules/decision_experiment_memory/` |
| Ingest | `decision_experiment_memory/ingest/` |
| AI Package | `ai_package_v1/decision_memory/` |

**Forbidden owners:** `campaign_settings_history`, `wb_sky_control_plane` (link only), `shop_runner`, any production writer.

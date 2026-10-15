---
cursor:
  subagentId: "bc-2bbf6418-a914-50df-90fc-51fc7c099fb6"
---

# decision-experiment-memory — planning report (verified inventory)

Planning-only. Repository evidence: `origin/stage` cloud checkout (2026-10-07). Cross-check prior note: [planning-report.md](./planning-report.md) (sibling worker).

## Architecture decision lookup (context-first)

| Path | Use |
|------|-----|
| `openspec/decisions/campaign-settings-contract-ownership/decision.md` | Settings SoT; evidence via `state_hash` / registry |
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | Read-only export; Slice D |
| `openspec/decisions/shop-data-source-strategy/decision.md` | Cutoff / provenance for evidence refs |
| `openspec/changes/archive/2026-10-07-campaign-settings-changeset-contract/` | ChangeSetV1, dry-run, metadata hooks |
| `openspec/changes/archive/2026-10-05-campaign-settings-history/` | CH `006` history shape |
| `openspec/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md` | **DO_NOT_USE** as generic memory |
| Store: `internal/changeset-apply-authority-planning-bc-b1403ae8.md` | Apply audit + dry-run receipt persistence (planned, not in repo) |
| Store: `docs/attribution-facts-contract.md` | Economics facts — reference only |

**Architecture Decision Missing (accepted):** reusable ownership for `decision-experiment-memory` (module, PG authority, forbidden write-path). Proposed: `openspec/changes/decision-experiment-memory/decisions/decision-experiment-memory-ownership/decision.md`.

---

## RETURN (canonical)

**FEATURE:** `decision-experiment-memory`

**STATUS:** Planning contract complete on store; repo OpenSpec change not scaffolded; implementation blocked on ownership ADR + Apply/dry-run durable receipts.

### EXISTING_REUSABLE_COMPONENTS

| Component | Class | Notes |
|-----------|-------|-------|
| `ChangeSetV1`, `ChangeSetMetadataV1.decision_id` / `experiment_id` | **REUSE** | Audit metadata; excluded from `semantic_digest` (`changeset.py`) |
| `compute_semantic_digest` / `sd1` | **REUSE** | Stable body identity |
| `DryRunResultV1`, `ChangeSetValidationResult`, `PlanV1` | **REFERENCE** | In-memory dry-run; no durable receipt ID in code today |
| `PriorChangeSetRecord` | **REFERENCE** | Injected idempotency hint only (#449 design) |
| `app/modules/wb_sky_control_plane/` pipeline | **REFERENCE** | Read-only validate; link only, not owner |
| `app/modules/campaign_settings_history/` + CH `campaign_settings_history` | **REFERENCE** | `HistorySnapshotRow`: `snapshot_id`, `state_hash`, `observed_at` |
| `app/modules/campaign_settings_contract/` | **REFERENCE** | Registry + `normalize_value` for evidence snapshots |
| `app/modules/ai_package_v1/` manifest + assemblers | **EXTEND** (Slice D) | New datasets via reader port; `READ_ONLY_NO_MUTATION` |
| `keyword_decisions.jsonl` / `decision_assembler.py` | **DO_NOT_USE** | CH `bid_decision_log` bid telemetry — not AI decision semantics |
| `app/modules/ai_package_v1/analysis/*` (DRR metrics) | **REFERENCE** | Evaluation may cite metric IDs; not decision SoT |
| `card_ab_hold` epoch/generation PG | **DO_NOT_USE** | Product A/B Hold; optional cross-ref `experiment_id` only |
| `changeset_apply_*` / `changeset_dry_run_receipt` (planned) | **EVIDENCE_GAP** | Defined in apply-authority planning store, not implemented |
| `openspec/changes/attribution-facts-contract/` | **REFERENCE** | Attribution bundle IDs for evidence section |

### DOMAIN_AGGREGATES

**V1:** single aggregate **`DecisionMemoryRecord`** + optional **`ExperimentSection`**.

- Avoid separate top-level `ExperimentRecord` service — every experiment is a decision; many decisions are not experiments.

Fields (logical, transport-independent):

- **Identity / scope:** `decision_id`, optional `experiment_id` (default `decision_id` when 1:1), `shop_id`, `ScopeRefV1` (shop | `cmp_*` / campaign | `nm_id` | optional keyword grain)
- **Actor:** `principal_kind` ∈ `AI` | `HUMAN` | `SYSTEM`, `actor_ref`, optional `on_behalf_of`
- **Semantics:** observation, hypothesis (experiments), rationale, intended_action, expected_effect, assumptions/risks
- **Evidence refs:** pointers only (see below)
- **Execution linkage:** ChangeSet / dry-run / apply digests
- **Evaluation:** baseline, window, metrics spec, criteria, factual outcome

### DECISION_VS_EXPERIMENT_BOUNDARY

| | Decision-only | Experiment |
|---|---------------|------------|
| `record_kind` | `DECISION` | `EXPERIMENT` |
| Required semantics | observation + rationale + intended_action | + hypothesis, `evaluate_after`, `baseline_ref` |
| Terminal without apply | `execution_status=NOT_APPLIED` / `CLOSED` | `outcome_status=ABORTED` or `INCONCLUSIVE` |
| Outcome | N/A (`NOT_APPLICABLE`) | `SUCCEEDED` / `FAILED` / `INCONCLUSIVE` / `ABORTED` after window |

### IDENTITIES

| Key | Rule |
|-----|------|
| `decision_id` | Opaque UUID/ULID; primary key |
| `experiment_id` | Optional; V1 default = `decision_id` when experiment |
| `revision` | Monotonic event sequence per `decision_id` |
| `semantic_intent_digest` | Hash of normalized intent (op kinds + target fields + direction) — **not** hypothesis text |
| `intervention_class` | Stable enum for intervention type (e.g. `BUDGET_POLICY`, `BID_POLICY`, …) |
| `experiment_fingerprint` | `hash(shop_id, scope_ref, intervention_class, semantic_intent_digest)` |
| `evidence_cutoff_digest` | Hash of evidence pointer bundle at record time |

### LIFECYCLE

**Execution linkage (all records):**

1. `DRAFT` — persisted semantics; ChangeSet optional  
2. `READY` — schema/policy valid; still non-authority  
3. `LINKED` — `changeset_id` + `semantic_digest`  
4. `DRY_RUN_RECORDED` — receipt digest + terminal dry-run status  
5. `APPLY_EVIDENCE_PENDING` — approved path, no apply audit yet  
6. `APPLY_RECORDED` — apply audit terminal `APPLIED` or idempotent `NO_EFFECT` replay (**only** state implying production execution)  
7. `CLOSED` — terminal without observation (rejected dry-run, superseded decision-only)

**Experiment overlay:**

- `DESIGNED` — hypothesis + `evaluate_after`  
- `OBSERVING` — after `APPLY_RECORDED` **or** explicit `execution_mode=SHADOW|COUNTERFACTUAL` with `observation_started_at`  
- `EVALUATION_DUE` — `now >= evaluate_after` and completeness computed  
- `OUTCOME_SET` — deterministic evaluator finished  

**Hard rules:**

- No `APPLY_RECORDED` without apply audit SoT (`changeset_apply_request` terminal + `apply_plan_digest` / audit event).  
- No `SUCCEEDED`/`FAILED` without evaluable criteria or explicit `OUTCOME_OVERRIDE` correction event.  
- Open observation window → `INCONCLUSIVE`, not premature success.

### EVIDENCE_REFERENCES

Immutable pointers (no full payload duplication):

- `ai_package_id`, `ai_package_manifest_digest`, `package_cutoff` / `generated_at`  
- `analysis_windows[]` (multi-window analysis dataset IDs)  
- `settings_evidence[]`: `{adv_setting_id, snapshot_id, state_hash, observed_at}` from campaign-settings-history  
- `state_tokens`: `cmp_*` → `st1_*` at decision time (from dry-run or history read)  
- `capabilities_snapshot_digest` (align with planned dry-run receipt)  
- `attribution_refs[]`: attribution-facts bundle IDs or `{adv_id, nm_id, period}` + `coverage_status`  
- **Exclude:** DRR hierarchy recomputation inside this module

### CHANGESET_LINKAGE

- Store: `changeset_id`, `semantic_digest` (`sd1`), `changeset_contract_version`  
- Reverse index: `changeset_id` → `decision_id` (from `ChangeSetMetadataV1.decision_id` when present)  
- Body: digest + id only unless no external store

### DRY_RUN_LINKAGE

Planned durable shape (apply-authority planning, **EVIDENCE_GAP** in repo):

- `dry_run_receipt_id`, `dry_run_receipt_digest`  
- `dry_run_status`, `preview_digest`, `capability_snapshot_digest`, `state_tokens`, `issued_at`, `expires_at`  
- Idempotent ingest: unique `dry_run_receipt_digest` or `(changeset_id, semantic_digest, attempt_no)`

### APPLY_RECEIPT_LINKAGE

Consume **Apply audit** (not decision memory):

- `apply_request_id`, `idempotency_key`, terminal `outcome` (`APPLIED`, `REJECTED`, `FAILED`, `UNKNOWN_OUTCOME`, `NO_EFFECT`)  
- `apply_plan_digest`, `semantic_digest`, `dry_run_receipt_id`  
- `before_state_tokens` / post-apply history pointer when settings history observes change  
- Unique `apply_attempt_digest` (canonical hash of audit minimum fields)

Decision memory maps `APPLY_RECORDED` only when terminal outcome ∈ `{APPLIED, NO_EFFECT}` with matching `changeset_id` + `semantic_digest`.

### SETTINGS_HISTORY_LINKAGE

- At decision: latest known `snapshot_id` + `state_hash` per affected campaign (read-only CH/PG reader).  
- After apply: optional `post_apply_snapshot_id` when collector emits new row.  
- History rows are **not** experiment outcomes.

### EVALUATION_CONTRACT

Deterministic `FactualOutcomeV1`:

- Inputs: `baseline_ref`, `evaluation_window` (UTC), `metrics_spec[]` (registry IDs), `success_criteria` (machine predicates)  
- Outputs: `coverage` (`COMPLETE|PARTIAL|MISSING`), `metric_values`, `criteria_results[]` (`PASS|FAIL|UNEVALUABLE`), derived `outcome_status`  
- AI `outcome_explanation_text` optional; **must not** be sole source of `outcome_status`

| Situation | `outcome_status` |
|-----------|------------------|
| Complete + all criteria PASS | `SUCCEEDED` |
| Complete + any FAIL | `FAILED` |
| Partial / missing / attribution unavailable / window open | `INCONCLUSIVE` |
| Denominator zero | `INCONCLUSIVE` + `ZERO_DENOMINATOR` |
| Abort before window end | `ABORTED` |
| Decision-only | `NOT_APPLICABLE` |

### OUTCOME_STATUSES

`SUCCEEDED` | `FAILED` | `INCONCLUSIVE` | `ABORTED` | `NOT_APPLICABLE`

### APPEND_ONLY_MODEL

Event types: `CREATED`, `SEMANTICS_PATCHED`, `CHANGESET_LINKED`, `DRY_RUN_INGESTED`, `APPLY_INGESTED`, `EVALUATION_INGESTED`, `OUTCOME_COMPUTED`, `SUPERSEDED`.

- Immutable first `decision_context` blob (`decision_context_digest`); patches append events.  
- Materialized `decision_memory_projection` for queries (rebuild from events).

### CORRECTION_MODEL

`CORRECTION` events: `HUMAN_RATIONALE_FIX`, `OUTCOME_OVERRIDE`, `LINKAGE_FIX` — reference `supersedes_event_id`, reason code, actor. Effective projection shows `effective_outcome` + full `history[]`.

Late metrics: merge via `EVALUATION_INGESTED`; flipping `SUCCEEDED` → `INCONCLUSIVE` requires `CORRECTION` or new `OUTCOME_COMPUTED`, not silent UPDATE.

### IDEMPOTENCY_MODEL

| Operation | Dedup key |
|-----------|-----------|
| Create decision | `(shop_id, semantic_intent_digest, evidence_cutoff_digest, client_request_id?)` |
| Link ChangeSet | `(decision_id, semantic_digest)` |
| Ingest dry-run | `dry_run_receipt_digest` |
| Ingest apply | `(apply_request_id)` or `apply_attempt_digest` |
| Evaluation batch | `(decision_id, evaluation_batch_id)` |
| Late metrics | `(decision_id, metric_source_digest, window_end)` |

Never dedupe on free-text hypothesis.

### READER_PORT

`DecisionMemoryReaderPort` (async, transport-independent):

- `list_recent_decisions(shop_id, scope?, limit, since?)`  
- `list_active_experiments(shop_id, scope?)`  
- `list_completed_outcomes(shop_id, scope?, outcome_status?)`  
- `get_by_decision_id(decision_id)`  
- `find_by_changeset(changeset_id | semantic_digest)`  
- `find_similar_experiments(shop_id, experiment_fingerprint, limit)`  
- `get_decision_timeline(decision_id)`  

Forbidden: WB writes, PG settings writes, apply triggers.

### AI_PACKAGE_FUTURE_CONTRACT

Bump `package_schema_version` (e.g. `1.2.0`). New optional datasets:

| `dataset_id` | File | Grain |
|--------------|------|-------|
| `recent_decisions` | `recent_decisions.jsonl` | decision |
| `active_experiments` | `active_experiments.jsonl` | experiment |
| `experiment_results` | `experiment_results.jsonl` | experiment outcome |

Manifest cards: `decision_memory_schema_version`, shop binding, cutoff, row caps. Assembler: `app/modules/ai_package_v1/decision_memory/` (reader port only).

### PHYSICAL_STORAGE_CANDIDATE

**PostgreSQL** (Alembic, forward-only):

- `decision_memory_event` (append-only; monthly partition optional)  
- `decision_memory_projection` (indexed: `shop_id`, `experiment_fingerprint`, `changeset_id`, `outcome_status`, `evaluate_after`)  

ClickHouse remains settings history + metrics sources — not decision semantics SoT in V1.

### IMPLEMENTATION_SLICES

| Slice | Scope |
|-------|--------|
| **A** | Domain types, events, PG repo, projection builder, reader port, unit tests |
| **B** | Ingest: ChangeSet metadata, dry-run receipt, apply audit adapters; idempotency integration tests |
| **C** | Evaluation scheduler, deterministic evaluator, late metrics, corrections |
| **D** | AI Package datasets + contract tests (MCP transport out of scope) |

### Risk register

| Level | Item |
|-------|------|
| **CRITICAL** | Treating decision record as apply authority |
| **CRITICAL** | `APPLY_RECORDED` without apply audit SoT |
| **HIGH** | Duplicating settings payloads instead of snapshot refs |
| **HIGH** | Conflating `keyword_decisions` / `bid_decision_log` with this memory |
| **HIGH** | Missing ownership ADR → wrong module placement |
| **MEDIUM** | Premature outcome before `evaluate_after` |
| **MEDIUM** | Similar-experiment false positives without `intervention_class` |
| **LOW** | AI narrative overwriting factual outcome |

### IMPLEMENTATION_READY

**no** — accept `decision-experiment-memory-ownership` ADR; implement `changeset-apply-authority` dry-run/audit tables; scaffold OpenSpec change in repo.

### FINAL_STATUS

**ARCHITECTURE_DECISION_REQUIRED**

(Planning semantics: **PLANNING_READY** — store docs complete; ownership ADR required before Slice A.)

---

## Proposed module placement (for ADR)

| Layer | Owner |
|-------|--------|
| Domain + events + projection + reader | `app/modules/decision_experiment_memory/` |
| Ingest adapters | `decision_experiment_memory/ingest/` |
| AI Package export | `ai_package_v1/decision_memory/` (read-only) |

**Forbidden owners:** `campaign_settings_history`, `wb_sky_control_plane` (link only), `shop_runner`, writers.

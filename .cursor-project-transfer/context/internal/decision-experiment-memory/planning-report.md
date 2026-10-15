---
cursor:
  subagentId: "bc-eaa8d21d-7a91-501b-a7be-5687b648fa3f"
---

# decision-experiment-memory — planning report

Planning-only. No migrations, production writes, or deploy.

## Architecture decision lookup (context-first)

| Path | Relevance |
|------|-----------|
| `openspec/decisions/campaign-settings-contract-ownership/decision.md` | Settings SoT vs history projections; link `state_hash` / registry |
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | Read-only export boundary; future `recent_decisions` datasets |
| `openspec/decisions/shop-data-source-strategy/decision.md` | Evidence cutoff / provenance; not decision semantics |
| `openspec/changes/archive/2026-10-07-campaign-settings-changeset-contract/` | ChangeSetV1, dry-run, `decision_id`/`experiment_id` metadata hooks |
| `openspec/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md` | Product experiment lifecycle — **orthogonal** (DO_NOT_USE as generic memory) |

**Architecture Decision Missing (accepted):** reusable ownership for `decision-experiment-memory` module, storage authority, and forbidden write-path. Proposed artifact: `openspec/changes/decision-experiment-memory/decisions/decision-experiment-memory-ownership/decision.md` (not yet in repo).

---

## RETURN (canonical)

**FEATURE:** `decision-experiment-memory` — canonical WB Sky memory of decision semantics (why / hypothesis / expected effect) and factual experiment outcomes, transport-independent, separate from settings history, apply audit, attribution facts, and DRR hierarchy.

**STATUS:** Planning package complete; implementation blocked on accepted ADR + future Apply receipt contract.

### EXISTING_REUSABLE_COMPONENTS

| Component | Classification | Notes |
|-----------|----------------|-------|
| `ChangeSetV1`, `ChangeSetMetadataV1.decision_id` / `experiment_id` | **REUSE** | Non-semantic audit metadata; linkage keys only |
| `semantic_digest` / `compute_semantic_digest` | **REUSE** | Stable ChangeSet body identity (sd1) |
| `DryRunResultV1`, `ChangeSetValidationResult`, `PriorChangeSetRecord` | **REFERENCE** | Dry-run shape; `canonical_hash` ≡ semantic digest in tests |
| `app/modules/wb_sky_control_plane/` dry-run pipeline | **REFERENCE** | No durable receipt ID yet — contract gap |
| `app/modules/campaign_settings_history/` + CH `campaign_settings_history` | **REFERENCE** | Authoritative **settings** timeline via `snapshot_id`, `state_hash`, `observed_at` |
| `app/modules/campaign_settings_contract/` | **REFERENCE** | Field registry / `normalize_value` for evidence snapshots |
| `app/modules/ai_package_v1/` manifest + readers | **EXTEND** (future Slice D) | New read-only datasets; must stay `READ_ONLY_NO_MUTATION` |
| CH `bid_decision_log` + `keyword_decisions.jsonl` export | **REFERENCE** | **Operational bid telemetry**, not AI decision semantics |
| `card_ab_hold` epoch / generation / PG fields | **DO_NOT_USE** | Domain-specific A/B Hold lifecycle; may **reference** `experiment_id` later, not generic SoT |
| `strict-single-nmid-read-only-audit` / attribution readers | **REFERENCE** | Economics evidence pointers only |
| Apply audit / Apply receipt (production) | **EVIDENCE_GAP** | Not present in codebase; Slice B depends on sibling change |

### DOMAIN_AGGREGATES

**V1 recommendation:** one logical aggregate **`DecisionMemoryRecord`** (single persistence row or event stream keyed by `decision_id`), with an **optional embedded `ExperimentSection`**. Do not split into two top-level domain services.

- **`DecisionMemoryRecord`** — always created when semantics are recorded (AI or human).
- **`ExperimentSection`** — present when `record_kind=EXPERIMENT`; carries hypothesis, baseline, evaluation window, success criteria, outcome.

Rationale: every experiment is a decision; many decisions are not experiments (policy fix, rollback explanation). One aggregate avoids orphan experiments and simplifies reader queries.

### DECISION_VS_EXPERIMENT_BOUNDARY

| | Decision | Experiment |
|---|----------|------------|
| Purpose | Capture observation, rationale, intended action | Test a hypothesis with scheduled evaluation |
| Required | `decision_id`, actor, scope, `decision_semantics` | + `hypothesis`, `evaluate_after`, `baseline_ref`, optional `success_criteria` |
| Outcome | `execution_status` only | + `outcome_status` after observation window |
| Lifecycle terminal without apply | Allowed (`execution_status=NOT_APPLIED`) | Allowed → `outcome_status=ABORTED` or `INCONCLUSIVE` |

### IDENTITIES

| ID | Rule |
|----|------|
| `decision_id` | Opaque, client- or server-issued UUID/ULID; **primary** aggregate key |
| `experiment_id` | Optional; if omitted for experiments, defaults to `decision_id` (1:1 V1) |
| `shop_id` | Canonical `LogicalScopeV1.shop_id` |
| `scope` | `ScopeRefV1`: shop-wide \| campaign (`cmp_*` / `adv_setting_id`) \| SKU (`nm_id`) \| keyword grain optional |
| `revision` | Monotonic per `decision_id` (append-only events) |
| `semantic_intent_digest` | Deterministic hash of normalized intent (operation kinds + target fields + direction), **not** free-text hypothesis |
| `experiment_fingerprint` | `hash(scope_ref + intervention_class + semantic_intent_digest)` for “similar experiment” queries |
| `linkage_digest` | Optional bundle hash over linked foreign IDs |

### LIFECYCLE

**Decision semantics (execution linkage):**

1. `DRAFT` — persisted proposal; may lack ChangeSet
2. `READY` — passed local validation (schema + policy); still no production authority
3. `LINKED` — `changeset_id` + `semantic_digest` attached
4. `DRY_RUN_RECORDED` — dry-run receipt digest stored (status `NO_OP|OK|REJECTED`)
5. `APPLY_EVIDENCE_PENDING` — approved for apply path but no apply receipt yet
6. `APPLY_RECORDED` — apply receipt digest present (**only** state that implies production execution occurred)
7. `CLOSED` — terminal without experiment observation (e.g. rejected dry-run, superseded)

**Experiment overlay** (subset of records with `ExperimentSection`):

- `DESIGNED` — hypothesis + `evaluate_after` set
- `OBSERVING` — `APPLY_RECORDED` **or** explicit `execution_mode=SHADOW|COUNTERFACTUAL` + start timestamp
- `EVALUATION_DUE` — `now >= evaluate_after` and window completeness computed
- `OUTCOME_SET` — deterministic evaluator finished

**Hard rules:**

- No `APPLY_RECORDED` without apply receipt artifact (future contract).
- No `OUTCOME_SET` with `SUCCEEDED|FAILED` unless success criteria evaluable or explicit human `OUTCOME_OVERRIDE` correction event (logged).
- Insufficient metrics → `INCONCLUSIVE`, never guessed pass/fail.

### EVIDENCE_REFERENCES

Immutable pointers (no payload duplication):

- `ai_package_id` + `ai_package_manifest_digest`
- `package_cutoff` / `generated_at` (from AI Package export)
- `analysis_windows[]` (e.g. multi-window IDs)
- `settings_evidence`: `{snapshot_id, state_hash, observed_at}` from campaign-settings-history
- `state_tokens`: map `cmp_*` → token at decision time
- `capabilities_snapshot_id` / version (control-plane capabilities)
- `attribution_refs[]`: strict-audit bundle IDs or `{adv_id, nm_id, period}` + source status — **not** recomputing attribution inside memory module

### CHANGESET_LINKAGE

- Store: `changeset_id`, `semantic_digest` (sd1), optional `changeset_contract_version`
- Join key for readers: either `decision_id` from `ChangeSetMetadataV1` or reverse index `changeset_id → decision_id`
- Body stored only if no durable apply/dry-run store yet; prefer digest + id

### DRY_RUN_LINKAGE

- `dry_run_receipt_id` (opaque) + `dry_run_receipt_digest`
- Payload summary: `dry_run_status`, `errors[]` codes, `plan_digest`
- Idempotent ingest: unique `(dry_run_receipt_digest)` or `(changeset_id, semantic_digest, dry_run_attempt_no)`

### APPLY_RECEIPT_LINKAGE

**EVIDENCE_GAP:** canonical Apply receipt type not in repo.

Planned fields:

- `apply_receipt_id`, `apply_receipt_digest`
- `applied_at`, `apply_status` (`FULL|PARTIAL|FAILED`)
- `post_apply_state_tokens` / settings `snapshot_id` after apply
- Unique `(apply_receipt_digest)`

Decision memory **consumes** apply audit; does not write production.

### SETTINGS_HISTORY_LINKAGE

- At decision time: capture latest known `snapshot_id` + `state_hash` per affected `adv_setting_id` (read-only query to CH history).
- After apply: optional second pointer `post_apply_snapshot_id` when history collector observes change.
- Never interpret history rows as decision outcomes.

### EVALUATION_CONTRACT

Deterministic evaluator input:

- `baseline_ref` (metrics snapshot digest or window spec)
- `evaluation_window` `{start, end}` (UTC)
- `metrics_spec[]` — named metrics + aggregation (from registry, not ad hoc strings in V1)
- `success_criteria` — machine-evaluable predicates (threshold, min delta, min sample)

Evaluator output `FactualOutcomeV1`:

- `coverage`: `COMPLETE|PARTIAL|MISSING`
- `metric_values` (deterministic numbers only)
- `criteria_results[]`: `PASS|FAIL|UNEVALUABLE`
- `outcome_status`: derived — see below

Behaviors:

| Situation | `outcome_status` |
|-----------|------------------|
| Complete evidence + all criteria PASS | `SUCCEEDED` |
| Complete evidence + any FAIL | `FAILED` |
| Partial / missing / attribution unavailable / window open | `INCONCLUSIVE` |
| Denominator zero | `INCONCLUSIVE` + reason `ZERO_DENOMINATOR` |
| User/system abort before window end | `ABORTED` |
| Decision-only (no experiment) | `NOT_APPLICABLE` |

AI narrative explanation is **optional attachment** (`outcome_explanation_text`) and must not be sole source of `outcome_status`.

### OUTCOME_STATUSES

`SUCCEEDED` | `FAILED` | `INCONCLUSIVE` | `ABORTED` | `NOT_APPLICABLE`

### APPEND_ONLY_MODEL

- Event log per `decision_id`: `CREATED`, `SEMANTICS_PATCHED`, `CHANGESET_LINKED`, `DRY_RUN_INGESTED`, `APPLY_INGESTED`, `EVALUATION_INGESTED`, `OUTCOME_COMPUTED`, `SUPERSEDED`
- **Immutable** first `decision_context` blob (hash stored); later patches add events, not overwrite blob
- Materialized **current projection** for queries (rebuilt from events)

### CORRECTION_MODEL

- `CORRECTION` event types: `HUMAN_RATIONALE_FIX`, `OUTCOME_OVERRIDE`, `LINKAGE_FIX`
- Each correction references `supersedes_event_id`, carries reason code, actor
- Original conclusion remains readable; projection shows `effective_outcome` + `history[]`

### IDEMPOTENCY_MODEL

| Operation | Dedup key |
|-----------|-----------|
| Create decision | `(shop_id, actor_ref, semantic_intent_digest, evidence_cutoff_digest, client_request_id?)` |
| Link ChangeSet | `(decision_id, semantic_digest)` |
| Ingest dry-run | `dry_run_receipt_digest` |
| Ingest apply | `apply_receipt_digest` |
| Ingest evaluation batch | `(decision_id, evaluation_batch_id)` |
| Late metrics | `(decision_id, metric_source_digest, window_end)` — merges into outcome, may flip to `INCONCLUSIVE` from premature `SUCCEEDED` via `CORRECTION` not silent update |

Never dedupe on hypothesis text.

### READER_PORT

Transport-independent `DecisionMemoryReaderPort` (async):

- `list_recent_decisions(shop_id, scope?, limit, since?)`
- `list_active_experiments(shop_id, scope?)`
- `list_completed_outcomes(shop_id, scope?, outcome_status?)`
- `get_by_decision_id(decision_id)`
- `find_by_changeset(changeset_id | semantic_digest)`
- `find_similar_experiments(shop_id, experiment_fingerprint, limit)`
- `get_decision_timeline(decision_id)` — events + corrections

Forbidden on reader path: WB writes, PG settings writes, apply triggers.

### AI_PACKAGE_FUTURE_CONTRACT

Schema bump (e.g. `package_schema_version` `1.2.0`) — optional datasets:

```json
{
  "dataset_id": "recent_decisions",
  "logical_name": "recent_decisions.jsonl",
  "grain": "decision",
  "max_rows": "bounded per export policy"
}
```

`active_experiments.jsonl`, `experiment_results.jsonl` — same pattern.

Manifest cards declare: coverage, cutoff, `decision_memory_schema_version`, shop_id binding.

Assembler lives in `app/modules/ai_package_v1/decision_memory/` (new subpackage) calling reader port only.

### PHYSICAL_STORAGE_CANDIDATE

**PostgreSQL** (Alembic-owned, forward-only):

- `decision_memory_event` — append-only (partition by month optional)
- `decision_memory_projection` — current state + indexed columns (`shop_id`, `experiment_fingerprint`, `changeset_id`, `outcome_status`, `evaluate_after`)
- No ClickHouse for V1 (CH remains settings **history** and metrics sources)

Rationale: transactional linkage with future apply audit, idempotent ingest, correction events.

### IMPLEMENTATION_SLICES

| Slice | Scope |
|-------|--------|
| **A** | Domain types, event model, PG repository, projection builder, reader port, unit tests |
| **B** | Ingest adapters: ChangeSet metadata, dry-run receipt, apply receipt (when exists); idempotency integration tests |
| **C** | Evaluation scheduler + deterministic outcome evaluator + late metrics + correction flows |
| **D** | AI Package datasets + contract tests; optional MCP later (out of V1) |

### Risk register

| Level | Item |
|-------|------|
| **CRITICAL** | Treating decision record as apply authority |
| **CRITICAL** | Writing `APPLY_RECORDED` without apply receipt SoT |
| **HIGH** | Duplicating campaign settings payloads instead of snapshot refs |
| **HIGH** | Conflating `bid_decision_log` with decision-experiment memory |
| **HIGH** | Missing accepted ADR → wrong module placement |
| **MEDIUM** | Premature outcome before `evaluate_after` |
| **MEDIUM** | Similar-experiment false positives without `intervention_class` |
| **LOW** | AI explanation overwriting factual outcome |

### IMPLEMENTATION_READY

**no** — requires accepted `decision-experiment-memory-ownership` ADR, Apply receipt contract, and OpenSpec change scaffold (`proposal` / `design` / `spec` / `tasks`).

### FINAL_STATUS

**ARCHITECTURE_DECISION_REQUIRED** (planning semantics resolved; reusable ownership decision must be accepted before Slice A).

---

## Proposed module placement (for ADR)

- Owner: `app/modules/decision_experiment_memory/` (new)
- Layering: domain + repository + reader; ingest adapters in `ingest/` subpackage
- Forbidden owners: `campaign_settings_history`, `wb_sky_control_plane` (link only), `shop_runner`, `ai_package_v1` (export adapter only)

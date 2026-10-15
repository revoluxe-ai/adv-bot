---
cursor:
  subagentId: "bc-05eab406-93cf-5242-bd1f-2e7d3c90122a"
---

# decision-experiment-memory — planning contract

Authority: read-only inventory on cloud VM `adv-bot` (`wb_sky_control_plane`, `campaign_settings_history`, `ai_package_v1` present). No code/migration changes.

Related (separate): `campaign-settings-history`, `changeset-apply-authority`, `attribution-facts-contract` (store doc only — `openspec/changes/attribution-facts-contract/` **not** in this clone; treat as **EVIDENCE_GAP** for normative attribution IDs until fetch/local).

---

## FEATURE

`decision-experiment-memory`

## STATUS

Planning complete. **No OpenSpec change folder created in repo** (coordinator assignment: store deliverable only).

---

## EXISTING_REUSABLE_COMPONENTS

| Artifact | Classification | Role for this feature |
|----------|----------------|----------------------|
| `ChangeSetV1` + `ChangeSetMetadataV1.decision_id` / `experiment_id` | **REFERENCE** | Correlation hooks only; metadata is non-semantic (excluded from `sd1` digest). Must not become decision SoT. |
| `semantic_digest` (`sd1`), `changeset_id`, `DryRunResultV1`, `ChangeSetValidationResult`, `PlanV1` | **REUSE** | Execution-intent linkage and dry-run evidence digests. |
| `PriorChangeSetRecord` | **REFERENCE** | In-memory idempotency observation for dry-run; **not** durable decision store. |
| `app/modules/wb_sky_control_plane/` dry-run pipeline | **REFERENCE** | Emits validation outcome; future dry-run **receipt store** (apply planning) feeds linkage events. |
| `changeset-apply-authority` planning (`DryRunBindingV1`, `ApplyRequestV1`, apply audit) | **REFERENCE** | Authoritative **execution** evidence; decision memory **indexes** receipts, never replaces Apply Authority. |
| `app/modules/campaign_settings_history/` (`HistorySnapshotRow`, `state_hash`, `snapshot_id`, timeline reader) | **REFERENCE** | Authoritative **settings state at observation time**; link via immutable `(snapshot_id, state_hash)` or time-bounded timeline query. |
| `app/modules/campaign_settings_contract/` + `state_token` (`st1`) | **REFERENCE** | Capabilities/normalization generation for evidence block `settings_state`. |
| `app/modules/ai_package_v1/` (manifest, `PackageCutoff`, export scope, analysis facts) | **EXTEND** | Evidence package identity; future manifest sections `recent_decisions` / `active_experiments` / `experiment_results`. |
| `ai_package_v1` `keyword_decisions` / CH `bid_decision_log` readers | **DO_NOT_USE** | Automation/analytics timeline; labels include `ANALYTICS_COMPUTED_NOT_VERIFIED_APPLIED`. Not semantic experiment memory. |
| Card A/B Hold epoch (`ab-hold-*` ADRs, `AdvSetting.card_ab_hold_*`) | **DO_NOT_USE** as canonical model | Product-specific WB-sync lifecycle on campaign row. May **emit** decision events later via adapter, not own the generic contract. |
| `family_gaps` / shop DRR analysis withhold reasons | **REFERENCE** | Economics metrics for evaluation must reuse same withhold semantics; DRR hierarchy stays in analysis/attribution, not duplicated. |
| Excel import / shop-runner feature dry-runs | **DO_NOT_USE** | Not transport-independent decision semantics. |

---

## DOMAIN_AGGREGATES

**V1 recommendation: one write aggregate + optional experiment lifecycle facet (not two peer SoT tables).**

| Aggregate | Purpose |
|-----------|---------|
| **`DecisionSemanticRecord`** | Canonical root. Immutable semantic context at capture time + append-only event stream for linkage, evaluation, correction. Always has `decision_id`. |
| **`ExperimentLifecycleFacet`** | Optional embedded facet (same aggregate row or child JSON column) when `record_kind=EXPERIMENT`. Holds `experiment_id`, windows, success criteria, observation schedule. Not a second authority for settings or apply. |

**Rationale:** Many decisions are one-shot (incident response, policy tweak) with no observation window. Experiments are decisions with `evaluate_after` and structured success criteria. Split tables prematurely duplicate identity and complicate “decision without experiment” vs “experiment outcome revision.”

**Event-sourced append model (logical):**

- `DecisionContextCaptured` — immutable WHY block (observation, hypothesis, rationale, intended action, expected effect, risks).
- `ExecutionLinked` — changeset / dry-run / apply references (partial allowed).
- `OutcomeEvaluated` — deterministic factual outcome + metrics snapshot refs.
- `RecordCorrected` — supersedes prior **interpretation** or adds late metrics; never mutates captured context bytes.
- `RecordAborted` — explicit cancel before/outside observation.

---

## DECISION_VS_EXPERIMENT_BOUNDARY

| | Decision | Experiment |
|---|----------|------------|
| Required | Always | Only when hypothesis + evaluation window (or explicit `record_kind=EXPERIMENT`) |
| `experiment_id` | Optional foreign grouping | Required on facet |
| Lifecycle terminal | May end at `EXECUTION_LINKED` if no evaluation configured | Must reach `OUTCOME_*` or `ABORTED` / `INCONCLUSIVE` |
| Similarity search | By scope + policy family | By `experiment_similarity_key` (structured, see idempotency) |

A single `experiment_id` MAY span multiple `decision_id` rows only via **explicit** `supersedes_decision_id` chain (correction), not duplicate inserts.

---

## IDENTITIES

| ID | Format | Authority |
|----|--------|-----------|
| `decision_id` | `dec_` + UUIDv7 or ULID (opaque) | Decision memory module |
| `experiment_id` | `exp_` + UUIDv7/ULID | Same module; only when facet present |
| `shop_id` | `LogicalScopeV1.shop_id` | Scope |
| `affected_scope` | `SHOP` \| `CAMPAIGN_RESOURCE` \| `SKU` (+ optional `physical_adv_id`, `nm_id`, `cmp_*`) | Normalized scope block |
| `event_id` | `dse_` + ULID per append event | Idempotency for ingestion |
| `similarity_key` | `sim_` + hash of canonical similarity struct | Dedup / “tried before” queries |

**Actor block:** `actor_kind: AI | HUMAN | SYSTEM`, `actor_ref` (opaque stable ref, e.g. `cursor_run:…`, `telegram_user:…`, `shop_runner:…`), optional `ai_package_digest` at capture.

---

## LIFECYCLE

**Derived status** (computed from events + clocks, not freely set by AI):

| Phase | Code | Entry rule |
|-------|------|------------|
| Captured | `CAPTURED` | `DecisionContextCaptured` persisted |
| Validated (optional) | `VALIDATED` | External validator acknowledged schema/policy (future; V1 may skip) |
| Execution pending | `EXECUTION_PENDING` | ChangeSet linked, apply not proven |
| Apply proven | `APPLY_CONFIRMED` | **Requires** `apply_receipt_id` + terminal `APPLIED` (or idempotent replay) from Apply Authority audit |
| Observing | `OBSERVING` | `evaluate_after` in future; apply confirmed or execution waived per policy |
| Outcome ready | `OUTCOME_READY` | Window elapsed + minimum evidence rules satisfied |
| Terminal success | `SUCCEEDED` | Deterministic criteria met |
| Terminal failure | `FAILED` | Deterministic criteria failed |
| Terminal unknown | `INCONCLUSIVE` | Insufficient/partial/conflicting evidence |
| Terminal cancel | `ABORTED` | Explicit abort event |

**Hard rules:**

- Never `APPLY_CONFIRMED` without apply audit evidence.
- Never `SUCCEEDED`/`FAILED` from LLM narrative alone.
- Window not finished → stay `OBSERVING` (not `INCONCLUSIVE`).
- Missing attribution / DRR withheld → metric-level `UNAVAILABLE`, outcome may still be `INCONCLUSIVE` if success criteria depended on those metrics.

---

## EVIDENCE_REFERENCES

Immutable **EvidenceBundleV1** on capture (digest `evd1_…`):

| Ref | Points to |
|-----|-----------|
| `ai_package_id` / `export_manifest_digest` | AI Package export used for reasoning |
| `package_cutoff_instant` | `PackageCutoff` |
| `analysis_windows` | e.g. multi-window analysis doc IDs / period tuples |
| `settings_snapshots[]` | `{snapshot_id, state_hash, observed_at}` from campaign-settings-history **or** `campaign_settings_snapshot_v1` digest from package |
| `state_tokens` | Map `cmp_*` → `st1_…` at decision time |
| `capabilities_digest` | Hash of capability evaluation snapshot (align with apply dry-run `capability_snapshot_digest`) |
| `attribution_fact_refs[]` | Opaque IDs into attribution-facts store (**EVIDENCE_GAP** in cloud clone) |
| `economics_refs[]` | Analysis metric keys + withhold reason codes (DRR/CPO), not recomputed store |

No full ChangeSet or settings payload if digest + IDs suffice.

---

## CHANGESET_LINKAGE

On `ExecutionLinked`:

- `changeset_id` (audit)
- `semantic_digest` (`sd1_…`) — **required** for identity
- Optional `metadata.decision_id` / `experiment_id` must match record IDs or linkage rejected at ingest

Query: by `(changeset_id)`, `(semantic_digest)`, or `(decision_id)`.

---

## DRY_RUN_LINKAGE

On dry-run receipt persistence (from apply slice / control plane):

- `dry_run_receipt_id`
- `preview_digest`
- `dry_run_status` (`OK` only links forward to apply intent)
- `issued_at`, `expires_at`
- Bind to same `changeset_id` + `semantic_digest`

Decision memory records **association** only; dry-run store remains owned by control plane / apply module per ADR.

---

## APPLY_RECEIPT_LINKAGE

On apply audit (Apply Authority):

- `apply_request_id`, `idempotency_key`
- `apply_receipt_id` / terminal status `APPLIED` \| `FAILED` \| `UNKNOWN_OUTCOME`
- `plan_digest`, `before_state_tokens`, resulting settings `state_hash` post-apply (from history snapshot or apply audit)

`APPLY_CONFIRMED` lifecycle transition **only** when receipt proves `APPLIED` (or deterministic idempotent replay).

---

## SETTINGS_HISTORY_LINKAGE

- **Before:** `settings_snapshots` at decision capture.
- **After apply:** optional `post_apply_snapshot_id` + `state_hash` on `ExecutionLinked` follow-up event.
- **Timeline queries:** delegate to `campaign_settings_history` reader; decision store holds pointers only.

---

## EVALUATION_CONTRACT

**`OutcomeEvaluationV1`** (factual, deterministic layer):

| Input | Behavior |
|-------|----------|
| `baseline` | Metric vector + snapshot refs at `baseline_at` |
| `evaluation_window` | `[start, end)` UTC; `evaluate_after` = `end` |
| `success_criteria` | Machine-readable predicates (threshold, delta vs baseline, min sample); optional absent → human-only conclusion forbidden for SUCCEEDED/FAILED |
| `metrics_observed` | Named metrics → `{value, unit, evidence_ref, quality: COMPLETE\|PARTIAL\|MISSING\|UNAVAILABLE\|DENOMINATOR_ZERO}` |
| `conclusion` | Derived by evaluator engine |
| `narrative_explanation` | Optional AI text; **non-authoritative** |

**Cases:**

| Case | Outcome |
|------|---------|
| Complete evidence + criteria evaluable | `SUCCEEDED` or `FAILED` |
| Partial metrics | `INCONCLUSIVE` unless criteria explicitly allow partial (V1: default **no**) |
| Missing required metric | `INCONCLUSIVE` |
| Denominator zero | Metric `DENOMINATOR_ZERO`; outcome `INCONCLUSIVE` if criterion needs it |
| Attribution unavailable | Metric `UNAVAILABLE`; same |
| Window open | Status `OBSERVING`; no outcome event |

Re-evaluation: new `OutcomeEvaluated` event with higher `evaluation_revision`; latest revision wins for read API; prior revisions retained.

---

## OUTCOME_STATUSES

Terminal: `SUCCEEDED`, `FAILED`, `INCONCLUSIVE`, `ABORTED`.

Non-terminal: `CAPTURED`, `VALIDATED`, `EXECUTION_PENDING`, `APPLY_CONFIRMED`, `OBSERVING`, `OUTCOME_READY`.

---

## APPEND_ONLY_MODEL

- **Immutable:** first `DecisionContextCaptured` payload bytes (hash stored).
- **Append:** all linkage, evaluation, abort, correction events.
- **Read model:** materialized view / projection table optional for queries; rebuildable from events.

---

## CORRECTION_MODEL

- `RecordCorrected` with `corrects_event_id`, `reason_code`, optional new evidence refs.
- **Forbidden:** UPDATE-in-place of hypothesis/rationale on original capture.
- **Supersedes:** optional `supersedes_decision_id` for “new decision replaces intent” (new `decision_id`, link back).

Late metrics: `MetricSupplement` sub-event under new `evaluation_revision`, not silent overwrite.

---

## IDEMPOTENCY_MODEL

| Ingestion | Dedup key |
|-----------|-----------|
| Decision capture | `(shop_id, client_capture_key)` if client supplies; else `(shop_id, evd_digest, semantic_intent_digest)` |
| Dry-run / apply linkage | `(dry_run_receipt_id)` / `(apply_request_id)` unique |
| Outcome evaluation | `(decision_id, evaluation_revision, evaluation_engine_version, metrics_digest)` |
| Similar experiment lookup | `experiment_similarity_key = H(sim1, shop_id, scope_kind, sorted_resource_ids, policy_op_fingerprint, hypothesis_class)` — **not** free-text hypothesis |

`hypothesis_class` = enum or structured code (`BUDGET_INCREASE_DAILY`, `BID_CONTROL_STRATEGY_SWITCH`, …); free text stored display-only.

---

## READER_PORT

Transport-independent `DecisionMemoryReaderPort` (async Protocol):

- `list_recent_decisions(scope, *, limit, since)`
- `get_decision(decision_id)`
- `list_active_experiments(shop_id, scope?)`
- `list_completed_outcomes(shop_id, scope?, outcome_status?, since)`
- `list_failed_or_inconclusive(shop_id, scope?, since)`
- `find_by_changeset(changeset_id | semantic_digest)`
- `find_by_campaign(resource_id | physical_adv_id, nm_id?)`
- `find_similar_experiments(similarity_key | structured query)`

No MCP/HTTP in V1 contract.

---

## AI_PACKAGE_FUTURE_CONTRACT

Package schema **1.2.0+** optional datasets (read-only projection):

| Section | Content |
|---------|---------|
| `recent_decisions.json` | Bounded list of `DecisionSemanticSummaryV1` |
| `active_experiments.json` | Experiments in `OBSERVING` / `OUTCOME_READY` |
| `experiment_results.json` | Terminal outcomes in window |

Each entry: IDs + digests + summary fields; full narrative via `get_decision`. Assembler lives in `ai_package_v1` **EXTEND** after memory module exists.

---

## PHYSICAL_STORAGE_CANDIDATE

**PostgreSQL** (align with apply audit + shop scope):

- `decision_semantic_event` (append-only, JSONB payload + typed columns for query)
- `decision_semantic_projection` (latest status, denormalized for indexes)
- Optional `experiment_similarity_index`

**Not** ClickHouse primary (history/analytics OK as read-only metric source). **No migration in planning.**

**Proposed module placement (pending ADR):** `app/modules/wb_sky_decision_memory/` — separate from `wb_sky_control_plane` (execution) and `campaign_settings_history` (settings snapshots).

---

## IMPLEMENTATION_SLICES

| Slice | Scope |
|-------|--------|
| **A** | Domain types, event schema, PG repository, projection, unit tests, `DecisionMemoryReaderPort` |
| **B** | Ingest hooks from dry-run receipt + apply audit + ChangeSet metadata validation |
| **C** | Evaluation engine, observation scheduler read, outcome revisions, similarity index |
| **D** | AI Package assembler sections + future MCP read adapter (thin wrapper over reader port) |

**Dependency order:** A → B → C → D. Apply Authority (separate change) should land **before** slice B production ingest.

---

## CRITICAL

- Decision record **never** grants write permission (Apply Authority only).
- Do not use `bid_decision_log` / keyword_decisions as decision SoT.
- Do not conflate with campaign-settings-history hash snapshots (WHAT) — this store is WHY/RESULT semantics.
- Outcome must be deterministic; AI explains, does not invent `SUCCEEDED`/`FAILED`.

## HIGH

- Accept ADR `decision-experiment-memory-ownership` (module + PG append store + reader port).
- Coordinate `changeset-apply-authority` receipt schema before slice B.
- Define `hypothesis_class` taxonomy minimal set for campaign policy ChangeSet ops.

## MEDIUM

- Attribution-facts contract not verified in cloud repo clone (`EVIDENCE_GAP`).
- Align capability_digest with dry-run binding from apply planning.
- Card A/B Hold may later publish events; keep adapter boundary.

## LOW

- MCP transport naming and auth.
- CH-backed metric cache for evaluation performance.

---

## IMPLEMENTATION_READY

**false** — ADR not accepted; apply audit store not implemented; attribution refs normative doc absent in clone.

---

## FINAL_STATUS

**ARCHITECTURE_DECISION_REQUIRED**

(Contract otherwise **PLANNING_READY** for OpenSpec `proposal` / `design` once ADR `decision-experiment-memory-ownership` is proposed.)

---

## Architecture Decision References

- `openspec/decisions/campaign-settings-contract-ownership/decision.md` — settings authority separate.
- `openspec/changes/archive/2026-10-07-campaign-settings-changeset-contract/decisions/campaign-settings-changeset-ownership/decision.md` — ChangeSet/dry-run ownership.
- Store: `internal/changeset-apply-authority-planning-bc-b1403ae8.md` — apply/dry-run receipts (proposed).
- **Architecture Decision Missing:** `decision-experiment-memory-ownership` (module, storage, event schema, boundary vs history/apply/attribution).

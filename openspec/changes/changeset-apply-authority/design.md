## Context

**Baseline:** `origin/stage` at planning time (see tasks / verify receipts).

**Merged dry-run foundation (evidence on stage):**

| Artifact | Location |
|----------|----------|
| `ChangeSetV1`, operations | `app/modules/wb_sky_control_plane/models/changeset.py` |
| `semantic_digest` `sd1_` | `kernel/semantic_digest.py` |
| `state_token` `st1_` | `kernel/state_token.py` |
| `validate_changeset` | `kernel/validate.py` |
| `dry_run` (PG resolve + WB read port) | `kernel/pipeline.py`, `read/resolver.py` |
| `PlanV1` / `DryRunResultV1` | `models/plan.py` |
| Dry-run idempotency (injected only) | `PriorChangeSetRecord.canonical_hash` == `semantic_digest` |
| Shop scope | `LogicalScopeV1` + `read/scope.resolve_wb_cabinet_id` |
| Capabilities | `TriStateCapability` in `models/enums.py`, `kernel/capabilities_eval.py` |

**Not in repo (apply introduces):** `preview_digest` (`pd1`), Apply persistence,
`ApplyAuthorityService`, writer adapters for apply.

**Legacy write inventory (bypass until migrated):**

- Excel: `apply_adv_excel_rows`
- Telegram: direct `AdvSetting` updates in handlers
- WB: shop-runner / activity-control modules per existing ADRs

**History boundary:** `campaign_settings_history` — CH snapshots of settings over
time; collector explicitly avoids settings writes (`runtime.py`).

## Goals / Non-Goals

**Goals:** Define transport-independent Apply contract, binding, lifecycle,
evidence, idempotency, transaction boundaries, verification, transport parity,
scenario plan S01–S20.

**Non-Goals:** Implementation, migrations, REST/MCP, WB apply (Slice D), legacy
removal, promoted ADR merge (proposed only).

## Architecture Decision References

- `openspec/decisions/campaign-settings-contract-ownership/decision.md`
- `openspec/specs/campaign-settings-changeset-contract/spec.md`
- Proposed: `decisions/changeset-apply-authority-ownership/decision.md`
- Archive (changeset ownership not in registry index yet):
  `openspec/changes/archive/2026-10-07-campaign-settings-changeset-contract/decisions/campaign-settings-changeset-ownership/decision.md`

## Ownership & Placement

| Concern | Owner |
|---------|--------|
| Apply domain types & service | `wb_sky_control_plane/apply/` (future) |
| Dry-run | existing `wb_sky_control_plane/kernel` |
| PG settings SoT | PostgreSQL `AdvSetting` (+ related policy tables via registry) |
| Apply evidence SoT | PG apply ledger + `ApplyEvidenceV1` |
| Settings history SoT | ClickHouse `campaign_settings_history` (separate) |
| Experiment / decision memory | Out of repo — may reference `apply_id` only |

Checklist:

- [x] context-first decision lookup
- [x] relevant decisions cited
- [x] new decision proposed
- [x] implementation layer matches decision (planned)

## Authority boundary

```text
AI / MCP / REST / Telegram  →  ApplyRequestV1 (intent)
Dry-run                     →  DryRunReceiptV1 (informative, non-authoritative)
Apply Authority             →  validate + authz + plan + writers + verify + evidence
Writer adapters             →  protocol translation only
```

Forbidden: MCP/REST/LLM → WB writer; dry-run OK → write; transport-owned domain fields.

## ApplyRequestV1 field classes

| Field | Class |
|-------|--------|
| `contract_version` (`apply_v1`) | authoritative input |
| `idempotency_key` | authoritative input |
| `changeset` (`ChangeSetV1` full body) | authoritative input |
| `dry_run_binding.dry_run_receipt_id` | reference (must resolve server-side) |
| `dry_run_binding.semantic_digest` | reference — server recomputes `sd1`, must match |
| `dry_run_binding.preview_digest` | reference — server recomputes `pd1`, must match |
| `dry_run_binding.dry_run_status` | reference — must be `OK` |
| `actor` (`PrincipalRefV1` + `transport_channel` audit label) | authoritative input |
| `authorization` (`capability_grants`, `shop_access_proof` opaque ref) | authoritative input — revalidated |
| `semantic_digest`, `preview_digest`, `state_token`, `capability_digest` on receipt | **server-owned** on persist |
| `ApplyPlanV1`, `ApplyEvidenceV1` | server-owned outputs |

Do not trust client-supplied tokens/digests without recompute.

## preview_digest (`pd1`)

Canonical hash (new; not yet in code) over:

```json
{
  "version": "pd1",
  "status": "OK",
  "semantic_digest": "<sd1_…>",
  "plan_effects": "<canonical PlanV1.effects normalized mutations>",
  "diffs": "<actionable SemanticDiffEntryV1 list>"
}
```

Use `kernel/canonical_json.canonical_sha256` with prefix `pd1_`.

## Dry-run binding

Apply MUST:

1. Load `DryRunReceiptV1` by id; reject missing/expired/consumed (unless idempotent replay).
2. Recompute `sd1` from `changeset`; reject mismatch (`CHANGESET_DIGEST_MISMATCH`).
3. Re-run `dry_run` or `validate_changeset` after authoritative resolve; recompute `pd1`; reject mismatch (`PREVIEW_DIGEST_MISMATCH`).
4. Reject `dry_run_status != OK` and `NO_OP` apply (`APPLY_REQUIRES_ACTIONABLE_PREVIEW`).
5. Re-evaluate capabilities; compare `capability_digest` to receipt if present (`CAPABILITY_DRIFT`).
6. Compare fresh `st1` to each operation `preconditions.state_token`; reject `STALE_STATE`.
7. Re-check `expected_current_value` when present.

No silent re-plan of a materially different ChangeSet inside Apply.

## Concurrency

V1: optimistic `st1` per `cmp_*` resource + shop-scoped serialization
(PG advisory lock or equivalent) + row locks on underlying `AdvSetting` during
apply transaction. No distributed lock product. Unknown lock state → fail closed.

## Idempotency

Store: `(scope.shop_id, idempotency_key)` → `semantic_digest` + terminal outcome + `apply_id`.

| Case | Behavior |
|------|----------|
| same key + same `semantic_digest` + completed success | replay `ApplyEvidenceV1`; no write |
| same key + different `semantic_digest` | `IDEMPOTENCY_CONFLICT`; no write |
| same key + in-flight | `APPLY_IN_PROGRESS` (deterministic) |
| failed before commit | retry allowed; failed after ambiguous commit | `UNKNOWN_INTERNAL_COMMIT` / `UNKNOWN_EXTERNAL_STATE` — no auto-retry write |

## Transaction boundary (topology)

| Phase | V1 PG-only | Future WB slice |
|-------|------------|-----------------|
| A. Validation + authz | in-memory / read-only PG+WB read | same |
| B. PG settings commit | **single DB transaction** (all plan steps) | PG txn separate from WB |
| C. External WB | **not in V1** | **not atomically joined** with PG |
| D. Verification readback | after commit, same session or new read | required |
| E. Audit / evidence persist | append in same txn as commit when possible; if audit fails after commit → `VERIFIED` settings but `EVIDENCE_PERSISTENCE_FAILED` (fail closed for *client success* — see spec) |

No claimed distributed atomicity across PG + WB.

## Apply lifecycle

Non-terminal: `RECEIVED` → `VALIDATING` → `AUTHORIZED` → `APPLYING` → `VERIFYING`

Terminal: `REJECTED`, `FAILED`, `VERIFIED`, `UNKNOWN_INTERNAL_COMMIT`, `UNKNOWN_EXTERNAL_STATE`

Invariant: `WRITE_ACCEPTED` (driver returned) ≠ `STATE_VERIFIED`. Client success only on `VERIFIED`.

## ApplyEvidenceV1 (immutable)

`apply_id`, `schema_version`, `scope`, `actor_ref`, `idempotency_key`, `changeset_id`,
`semantic_digest`, `preview_digest`, `dry_run_receipt_id`, `pre_state_tokens`,
`post_state_tokens`, `capability_digest`, `intended_mutations` (normalized),
`execution_status`, `writer_result_refs`, `failure_code`, `started_at`, `completed_at`.

Append-only; no updates except linkage fields forbidden.

## Post-apply verification

Re-resolve snapshots; recompute `st1`; compare normalized desired fields from plan
to `local_policy` projection (`read/local_policy.py`). Mismatch → `VERIFICATION_MISMATCH`
(not `VERIFIED`). Emit new `post_state_token` only on `VERIFIED`.

## Capability revalidation

Use `evaluate_capabilities` at apply time. `TriStateCapability.UNKNOWN` and
`INELIGIBLE` → fail closed. Record `capability_digest` = canonical hash of
per-resource capability projection + grant set.

## Actor / authorization

`PrincipalRefV1`: stable WB Sky principal (`wb_user_id` or service id) — transport
maps Telegram `from_user.id` / API subject to this ref via existing cabinet linkage
(pattern: `get_wb_user_cabinet_for_adv_and_telegram` family).

`capability_grants: frozenset[str]` — same catalog as dry-run preflight
(`KNOWN_CAPABILITIES` in `mutation_policy`). Possession of `preview_digest` alone
does **not** grant authority.

## Transport parity

```text
REST ─┐
      ├→ ApplyAuthorityService.apply(ApplyRequestV1)
MCP ──┘
```

## Multi-operation policy

`ChangeSetV1` allows N operations (main spec). V1 Apply: **multiple operations
allowed** within one shop if all are bounded policy ops; **one PG transaction**;
atomic all-or-nothing. No `PARTIALLY_APPLIED` success in V1.

## Failure / recovery

Fail closed codes include: `STALE_STATE`, `CAPABILITY_DRIFT`, `IDEMPOTENCY_CONFLICT`,
`UNAUTHORIZED`, `UNSUPPORTED_OPERATION`, `VALIDATION_REJECTED`, `WRITER_REJECTED`,
`VERIFICATION_MISMATCH`, `UNKNOWN_EXTERNAL_STATE`, `EVIDENCE_PERSISTENCE_FAILED`.

No automatic WB retry on unknown external outcome.

## Implementation slices (not authorized here)

| Slice | Content |
|-------|---------|
| A | Domain types, ports, pure idempotency/concurrency tests |
| B | PG ledger / receipt / idempotency tables |
| C | PG policy writer + txn + verification |
| D | WB writer behind authority (narrow op class) |
| E | REST/MCP → same service |
| F | History / decision-memory cross-links |

## Open Questions

- Promote archived `campaign-settings-changeset-ownership` into `openspec/decisions/`.
- Receipt TTL default (e.g. 15m / 24h).
- Exact `APPLY_IN_PROGRESS` visibility timeout for clients.
- Whether audit must be same-txn mandatory or compensating job acceptable.

```text
DESIGN_STATUS: READY_FOR_OWNER_CONTRACT_REVIEW
IMPLEMENTATION_READY: false
```

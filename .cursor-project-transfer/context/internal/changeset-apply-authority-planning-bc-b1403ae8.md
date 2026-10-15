---
cursor:
  subagentId: "bc-b1403ae8-ae4a-506d-9e84-1dc2946adc71"
---

# changeset-apply-authority — planning evidence

Evidence: draft PR [#449](https://github.com/revoluxe-ai/adv-bot/pull/449) `bf0abd01a` (`refs/tmp/pr449` fetched on cloud VM). Foundation change `campaign-settings-changeset-contract` is **dry-run only**; Apply is a **separate** OpenSpec change.

ADR context: `openspec/decisions/campaign-settings-contract-ownership/decision.md` (PG = current settings authority); proposed `campaign-settings-changeset-ownership` (control plane owns ChangeSetV1).

---

## FEATURE

`changeset-apply-authority`

## STATUS

**PLANNING_READY** — domain contract derivable from #449 + WB Sky invariants. **ARCHITECTURE_DECISION_REQUIRED** before implementation: accept a new proposed ADR `changeset-apply-authority-ownership` (placement under `wb_sky_control_plane/apply/`, sole production-write gate for bounded PG policy ops). **IMPLEMENTATION_READY: false** (#449 not merged; apply ADR not promoted).

---

## CANONICAL_APPLY_REQUEST

`ApplyRequestV1` (transport-independent, frozen Pydantic-style contract):

| Field | Required | Role |
|-------|----------|------|
| `contract_version` | yes | `"apply_v1"` |
| `apply_request_id` | yes | Unique attempt id (audit); **not** idempotency |
| `idempotency_key` | yes | Client-stable retry key; scoped with `scope.shop_id` in store |
| `scope` | yes | Same `LogicalScopeV1` as `ChangeSetV1` |
| `changeset` | yes | Full `ChangeSetV1` (reject digest-only apply — prevents confused deputy) |
| `dry_run_binding` | yes | `DryRunBindingV1` (see below) |
| `actor` | yes | `ActorContextV1` |
| `authorization` | yes | `AuthorizationContextV1` |
| `confirmation` | no | `HumanConfirmationV1` when policy requires reviewed preview |

**Rejected from blind hypothesis:**

- `dry_run_receipt_id` alone — insufficient; must bind receipt + inline checks.
- Transport request id as idempotency — forbidden.

`DryRunBindingV1`:

| Field | Required |
|-------|----------|
| `dry_run_receipt_id` | yes |
| `semantic_digest` | yes (`sd1_…` from #449) |
| `preview_digest` | yes | hash of canonical `{status, plan, actionable_diffs}` from dry-run |
| `dry_run_status` | yes | must be `OK` (not `NO_OP`, not `REJECTED`) |
| `changeset_id` | yes | must match `changeset.changeset_id` |
| `issued_at` | yes | from receipt |
| `receipt_expires_at` | yes | max skew enforced at apply |

Apply Authority **recomputes** `semantic_digest`, re-runs full validation pipeline, and **compares** binding fields. Mismatch → `REJECTED` before any writer.

---

## CANONICAL_APPLY_PLAN

`ApplyPlanV1` — **internal, authoritative output of Apply Authority** (not returned to AI as permission):

- `plan_id`, `apply_request_id`, `semantic_digest`, `preview_digest_at_authorize`
- `scope`, `changeset_id`
- `before`: per `resource_id`: `state_token` (`st1_…`), `snapshot_digest` (hash of authoritative projection used)
- `capability_decisions`: per resource, per required capability → `SUPPORTED` only proceeds
- `steps`: ordered list `ApplyPlanStepV1`:
  - `step_id`, `operation_id`, `op`, `resource_id`
  - `writer_adapter`: e.g. `pg.campaign_settings_policy_v1`
  - `mutation_spec`: normalized field writes (registry-canonical values only)
  - `pre_write_state_token`
- `execution_mode`: `ATOMIC_PG_TRANSACTION` (V1)
- `plan_digest`: canonical hash for audit + idempotency replay

Distinct from #449 `PlanV1` (semantic effects, no I/O). Apply Authority **derives** `ApplyPlanV1` from fresh validation + locks, not by trusting dry-run `PlanV1` without re-execution.

---

## AUTHORITY_MODEL

| Actor | Authority |
|-------|-----------|
| AI / ChatGPT / MCP | **NON_AUTHORITY** — proposes `ChangeSetV1` + `ApplyRequestV1` |
| Transport (UI, Telegram, MCP, HTTP) | **NON_AUTHORITY** — authenticates, forwards canonical request |
| `dry_run` / `validate_changeset` | **NON_AUTHORITY** — preview only; no durable permission |
| **WB Sky Apply Authority** | **SOLE WRITE AUTHORITY** for in-scope production mutations |
| Production writer adapters | Execute **only** steps in authorized `ApplyPlanV1` |

Forbidden: any transport or shop-runner path calling PG policy writers or WB writers for the same mutation domain without Apply Authority.

---

## DRY_RUN_BINDING

Binding prevents: stale state, altered ChangeSet, altered capabilities, cross-shop, replay of old preview, applying a different mutation than reviewed.

**Required binding checks at apply (all must pass):**

1. `changeset` canonical `semantic_digest` == `dry_run_binding.semantic_digest`
2. `changeset_id` consistent across changeset, binding, receipt
3. `scope.shop_id` consistent across changeset, receipt, actor authorization
4. Receipt exists, not expired, not already **consumed** (one successful apply per receipt unless idempotent replay)
5. Recomputed preview at apply (after fresh resolve) yields same `preview_digest` **or** fail closed if user binding required exact preview match (V1: **exact match required** when `confirmation` present; without confirmation, recomputed preview must still be `OK` with identical normalized mutations — digest equality)
6. Per-operation `preconditions.state_token` still present (mandatory at apply)
7. `dry_run_binding.dry_run_status == OK`

**Include in receipt at dry-run persist time (Apply V1 introduces store):**

- `dry_run_receipt_id`, `changeset_id`, `semantic_digest`, `preview_digest`, `dry_run_status`
- `scope`, `capability_snapshot_digest` (hash of evaluated capabilities + grants)
- `state_tokens` map per `resource_id` at dry-run time
- `issued_at`, `expires_at`
- `actor_fingerprint` (hash of `actor` without secrets)

**Not sufficient alone:** receipt id without full changeset body.

---

## CONCURRENCY_MODEL

1. Begin apply → load authoritative state (**PG**, same resolver as #449 `resolve_changeset_snapshots`)
2. Acquire **serialization**: V1 = shop-scoped advisory lock + row-level lock on touched `cmp_*` / underlying `AdvSetting` rows
3. Recompute `st1` `state_token` per targeted resource (operation-kind projection per #449 `state_token.py`)
4. Compare to operation `preconditions.state_token` → mismatch → `REJECTED`, no write
5. Optional `expected_current_value` re-checked after normalization

**Granularity V1:** optimistic generation at **campaign resource** (`cmp_*`) via `state_token`; shop lock prevents cross-campaign races within one shop apply batch.

No last-write-wins. No apply without token match.

---

## STATE_TOKEN_MODEL

Reuse #449 unchanged:

- Version `st1`, prefix `st1_`, operation-kind-dependent policy projection + legs/classification
- Per-operation precondition token (not envelope-level)
- Master rule: only concurrency contract; `expected_current_value` is semantic precondition under that generation

Apply adds: persist **authoritative** `before_state_token` + `snapshot_digest` on the apply attempt at authorize time.

---

## IDEMPOTENCY_MODEL

**Canonical identity:** `(scope.shop_id, idempotency_key)` → durable `idempotency_record`

| Case | Outcome |
|------|---------|
| Same key + same `semantic_digest` + same plan shape | Deterministic replay of stored terminal outcome + same `apply_request_id` mapping |
| Same key + different `semantic_digest` | **HARD CONFLICT** (`IDEMPOTENCY_KEY_CONFLICT`) — no write |
| Network retry after `APPLIED` | Replay success without duplicate PG mutation |
| Network retry after `UNKNOWN_OUTCOME` | **Do not** auto-retry write; return stored `UNKNOWN_OUTCOME` or force reconciliation endpoint (out of V1 auto) |

Store: request hash (`semantic_digest` + `preview_digest` + `plan_digest`), terminal status, writer receipts, timestamps.

Dry-run #449 `PriorChangeSetRecord` remains **in-memory/injected only** — not apply idempotency.

---

## APPLY_STATE_MACHINE

**Non-terminal:** `RECEIVED` → `VALIDATING` → (`AUTHORIZED` → `EXECUTING`)

**Terminal:**

| State | Meaning |
|-------|---------|
| `REJECTED` | Validation/auth/binding/concurrency failed; no write |
| `APPLIED` | PG commit confirmed + post-check passed |
| `FAILED` | Confirmed no durable effect (rollback or pre-write reject) |
| `UNKNOWN_OUTCOME` | Cannot prove success or failure after writer phase |
| `NO_EFFECT` | Optional terminal alias for idempotent replay of prior `APPLIED` |

**V1 excludes:** `PARTIALLY_APPLIED` as a success state. Reserved for future multi-writer WB changes with explicit non-atomic contract.

**Rules:**

- `UNKNOWN_OUTCOME` ≠ success; transports must not show “applied”
- `NO_OP` dry-run → apply **rejected** at validation (`APPLY_REQUIRES_ACTIONABLE_PREVIEW`)
- Atomic PG V1: no partial commit

---

## TERMINAL_STATES

`REJECTED`, `FAILED`, `APPLIED`, `UNKNOWN_OUTCOME`, `NO_EFFECT` (replay)

---

## WRITER_BOUNDARY

**Apply Authority** (`wb_sky_control_plane.apply` — proposed): authorization, binding, re-validation, concurrency, `ApplyPlanV1` construction, idempotency, audit emission, orchestration.

**Writer adapters** (`writers/`): implement `ApplyPlanStepV1` only.

---

## WRITER_RESPONSIBILITIES

| Apply Authority | Writer adapter |
|-----------------|----------------|
| Policy, authz, capability re-eval | Protocol translation to PG UPDATE/ORM |
| Plan construction | Execute single step payload |
| Idempotency + state machine | Normalize driver errors to `WriterResultV1` |
| Audit | **No** business decisions |
| Fail-closed classification | Classify `PRE_WRITE_REJECTED`, `WRITE_CONFIRMED`, `WRITE_FAILED_BEFORE_ACCEPTANCE`, `WRITE_OUTCOME_UNKNOWN` |

---

## MULTI_OPERATION_SEMANTICS

#449: ChangeSet atomic at validation. Apply V1:

- **All operations in one PG transaction** (sequential steps, single commit)
- Topological order: stable `operations` list order from `ChangeSetV1`
- Stop-on-first-failure inside txn → rollback → `FAILED`
- No compensating actions in V1

---

## PARTIAL_APPLY_POLICY

**V1: not allowed.** Either full commit or full rollback. `PARTIALLY_APPLIED` not emitted for PG-only V1.

---

## UNKNOWN_OUTCOME_POLICY

Per writer call classify result. If PG driver/connection lost after ambiguous commit:

- Mark attempt `UNKNOWN_OUTCOME`
- **No** automatic WB/PG retry in Apply Authority
- Reconciliation: read authoritative state, compare to `ApplyPlanV1` desired; manual or batch reconciler (future change)
- Idempotency record prevents blind duplicate until reconciled

---

## CAPABILITY_REVALIDATION

At apply (after fresh snapshot):

| Tri-state | Apply behavior |
|-----------|------------------|
| `SUPPORTED` | Proceed if grants OK |
| `UNSUPPORTED` | `REJECTED` |
| `UNKNOWN` | `REJECTED` (fail closed) |
| Temporarily unavailable (read/deps failure) | `REJECTED` or `FAILED` before write; **not** queued retry in V1 |

Dry-run capability approval is **not** cached as permission; `capability_snapshot_digest` in binding detects drift vs receipt.

---

## ACTOR_CONTEXT

`ActorContextV1`:

- `principal_id` (WB Sky user/service principal)
- `principal_kind`: `human` | `service` | `agent`
- `on_behalf_of_principal_id` optional (MCP/agent)
- `session_ref` opaque (audit only, no secrets)
- `transport_channel`: `ui` | `telegram` | `mcp` | `api` | `internal` — **non-domain** label for audit

Authentication at transport; **authorization** maps principal → `capability_grants` + shop scope.

---

## AUTHORIZATION_MODEL

Layers (strict order):

1. **Authentication** (transport) → principal
2. **Authorization** → shop scope + capability grants + role policy
3. **Domain validation** → `validate_changeset` pipeline (#449)
4. **Write authority** → Apply Authority emits `ApplyPlanV1`

All channels converge on same `ApplyRequestV1`.

---

## AUDIT_CONTRACT

Append-only `audit_event` stream (logical):

Minimum per attempt: `apply_request_id`, `changeset_id`, `idempotency_key`, `actor`, `scope`, `semantic_digest`, `dry_run_receipt_id`, `preview_digest`, `before_state_tokens`, `before_snapshot_digests`, `apply_plan_digest`, `writer_request_digests[]`, `writer_results[]`, `after_state_token` if confirmable, timestamps, terminal `outcome`.

No secrets/tokens/raw credentials.

---

## LOGICAL_PERSISTENCE_MODEL

PG-only Apply V1 (unless evidence later forces otherwise):

| Entity | Purpose |
|--------|---------|
| `changeset_dry_run_receipt` | Durable dry-run binding source |
| `changeset_apply_request` | One row per apply attempt, state machine |
| `changeset_apply_operation` | Per-step status (mirror plan steps) |
| `changeset_apply_idempotency` | `(shop_id, idempotency_key)` → outcome |
| `changeset_apply_execution_attempt` | Writer round-trips |
| `changeset_apply_audit_event` | Append-only audit |

No migration in this planning change.

---

## REPLAY_PROTECTION

- Receipt TTL + single-consumer semantics
- Binding digests + full changeset body
- Idempotency conflict detection
- Shop scope triple-check (changeset, receipt, authz)
- `apply_request_id` uniqueness
- Privileged writers callable only from Apply orchestrator (import/lint enforcement)

---

## CROSS_SHOP_PROTECTION

- `LogicalScopeV1.shop_id` must match receipt and authorized shops for principal
- Resolver refuses resources outside shop
- Idempotency keyed per shop

---

## REUSE_FROM_CHANGESET_V1 (#449)

Unchanged reuse:

- `ChangeSetV1`, bounded ops, `CampaignResourceRef` / `cmp_*`
- `validate_changeset` / `dry_run` pipeline phases A→resolve→C
- `semantic_digest` (`sd1_`), `state_token` (`st1_`)
- `mutation_policy`, `normalize_value`, domain validators, capability tri-state
- `expected_current_value` semantics
- `PlanV1` / `SemanticDiffEntryV1` as semantic preview inputs
- Atomic validation rejection rules

---

## NEW_APPLY_SEMANTICS

- `ApplyRequestV1`, `DryRunBindingV1`, `ActorContextV1`, `AuthorizationContextV1`
- Durable `DryRunReceipt` persistence (not in #449)
- `ApplyPlanV1` + writer orchestration
- Apply state machine + idempotency store
- PG transaction commit + post-check
- Writer result taxonomy + `UNKNOWN_OUTCOME`
- Audit + execution attempts
- Receipt consumption + replay controls
- Apply-time capability revalidation

---

## V1_SCOPE

- One `LogicalScopeV1` shop per request
- Operations: `campaign.set_budget_policy`, `campaign.set_sales_policy`, `campaign.set_bid_control_policy` only
- PG writers only (AdvSetting / related policy tables via existing ownership paths)
- Deterministic `st1` compare under lock
- Sequential steps, **single PG transaction**
- Strict idempotency table
- Durable dry-run receipt required before apply
- Explicit `UNKNOWN_OUTCOME`; no autonomous retry on ambiguous write
- Full audit trail

---

## V1_OUT_OF_SCOPE

- WB HTTP writers (deposit, bids, pause, etc.)
- `PARTIALLY_APPLIED` production semantics
- Compensating transactions
- Multi-shop atomic apply
- Transport APIs (REST/MCP/Telegram apply endpoints)
- Autonomous agent apply without human policy (unless Owner extends authz)
- Excel `apply_adv_excel_rows` replacement (separate migration change)
- Distributed cross-service 2PC
- Auto-retry on WB timeout (future WB apply)

---

## FAIL_CLOSED_INVARIANTS

1. Dry-run OK does not imply apply OK
2. Unknown capability/state → reject
3. `UNKNOWN_OUTCOME` never reported as `APPLIED`
4. Idempotency key conflict → no write
5. State token mismatch → no write
6. Missing/expired/consumed receipt → no write
7. Writer not in plan → forbidden
8. Cross-shop mismatch → reject

---

## OPEN_QUESTIONS

### CRITICAL

- Promote **apply ownership ADR** (module path, forbidden direct PG writes from transports)
- #449 merge + `LOCAL_FOUNDATION_ADOPTION_REQUIRED` checkpoint before shared types land on `stage`

### HIGH

- `preview_digest` canonical serialization (exact fields: status + normalized plan effects + actionable diffs only?)
- Receipt TTL default and whether consumed receipts allow idempotent replay only
- Shop advisory lock vs per-resource lock ordering with existing shop-runner

### MEDIUM

- Whether `HumanConfirmationV1` is mandatory for MCP/agent in V1
- Post-commit verification: full snapshot re-read vs field-level check

### LOW

- Naming: `apply_v1` vs `changeset_apply_v1` contract_version string

---

## PROPOSED_OPENSPEC_CHANGE

`openspec/changes/changeset-apply-authority/` — separate from `campaign-settings-changeset-contract`; depends on #449 merged; proposes `decisions/changeset-apply-authority-ownership/decision.md`.

---

## IMPLEMENTATION_READY

**false** — planning only; #449 draft; apply ADR not accepted; no migrations.

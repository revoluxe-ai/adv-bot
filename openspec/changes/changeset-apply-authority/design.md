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
AI / MCP / REST / Telegram  →  ApplyRequestV1 (client semantic intent only)
Trusted transport adapter   →  ApplyInvocationContext (server-resolved principal + shop authz)
Dry-run subsystem           →  DryRunReceiptV1 (server-issued, persisted; non-write authority)
Apply Authority             →  validate + authz + plan + writers + verify + evidence
Writer adapters             →  execution translation only
```

Forbidden: MCP/REST/LLM → WB writer; dry-run OK → write; client JSON as auth SoT;
transport-specific Apply semantics.

**Sole gate scope (V1):** Apply Authority is the only allowed production write path
for **in-scope `ChangeSetV1` apply protocol** operations. It is **not** yet global
exclusivity for all campaign settings mutations (Excel/Telegram/shop-runner legacy
paths remain until migrated).

## ApplyRequestV1 vs ApplyInvocationContext

Domain API (transport-independent types; trusted context is a **parameter**, not
client payload):

```text
ApplyAuthorityService.apply(
    request: ApplyRequestV1,
    context: ApplyInvocationContext,
) -> ApplyOutcomeV1
```

### ApplyRequestV1 — client intent (untrusted for identity/authz)

| Field | Class |
|-------|--------|
| `contract_version` (`apply_v1`) | client intent |
| `idempotency_key` | client intent |
| `changeset` (`ChangeSetV1` full body) | client intent |
| `dry_run_receipt_id` | reference id only (must resolve server row) |
| optional `binding_hints` (`semantic_digest`, `preview_digest`) | **non-authoritative** — server recomputes and compares; mismatch → reject |

**MUST NOT appear on ApplyRequestV1 as authoritative:** `principal_ref`,
`shop_access_proof`, `capability_grants`, `session_proof`. Fabrication of receipt
id or digests MUST NOT grant authority.

### ApplyInvocationContext — server-resolved (trusted adapter boundary)

| Field | Source |
|-------|--------|
| `principal_ref` | authenticated session (Telegram user → WB user/cabinet linkage, API subject, service account) |
| `shop_authorization` | server policy: principal may act on `request.changeset.scope.shop_id` |
| `permission_grants` | server-resolved mutation permissions for apply (distinct from domain capability tri-state) |
| `transport_channel` | audit label only (`ui` \| `telegram` \| `mcp` \| `api` \| `internal`) |
| `auth_proof_ref` | opaque internal handle (session id / token jti), never client-supplied proof bytes |

Transports differ in authentication mechanism; **domain types are shared**.

### Server-owned outputs

`ApplyAttemptRecord` (mutable lifecycle), `ApplyPlanV1`, `ApplyEvidenceV1` (immutable
terminal projection), receipt rows, idempotency rows.

## preview_digest (`pd1`)

Canonical hash (new; not yet in code) — binds **reviewed preview**, not auth.

```json
{
  "version": "pd1",
  "status": "OK",
  "semantic_digest": "<sd1_…>",
  "state_tokens": { "<resource_id>": "<st1_…>" },
  "capability_projection_digest": "<cpd1_… domain tri-state only, no client grants>",
  "plan_effects": "<canonical PlanV1.effects with resource_id + normalized mutations>",
  "diffs": "<actionable SemanticDiffEntryV1 incl. resource_id, field_path, normalized>"
}
```

`expected_current_value` preconditions are already bound via `sd1` operation
projection; do not duplicate. Use `kernel/canonical_json.canonical_sha256` with
prefix `pd1_`. `capability_projection_digest` (`cpd1_`) hashes per-resource
`evaluate_capabilities` outputs only — **separate** from `permission_grants`.

## DryRunReceiptV1 ownership (no circular Apply-only invention)

| Role | Owner |
|------|--------|
| Issue receipt after successful server `dry_run` → `OK` | **Dry-run subsystem** (`wb_sky_control_plane` dry-run port; same module family as `kernel/pipeline.dry_run`) |
| Persist `DryRunReceiptV1` rows | **Slice B** `DryRunReceiptStore` (PG); prerequisite for production apply, **not** for Slice A types |
| Consume / lifecycle | **Apply Authority** updates receipt state during apply attempt |

Receipt is created **only** from server `DryRunResultV1` + resolved snapshots at
issue time. Apply MUST NOT mint a receipt from client JSON. Client supplies
`dry_run_receipt_id` only.

Immutable receipt fields at issue: `receipt_id`, `issued_at`, `expires_at`, `scope`,
`changeset_id`, `semantic_digest`, `preview_digest`, `state_tokens`, `capability_projection_digest`,
`dry_run_status`.

**Slice A:** vocabulary + ports + in-memory fake store. **Not blocked** by PG persistence.

### Receipt lifecycle

| State | Meaning |
|-------|---------|
| `ISSUED` | valid for new apply if not expired |
| `CLAIMED` | bound to in-flight `apply_attempt_id` (short lease) |
| `CONSUMED` | successful `VERIFIED` apply committed |
| `EXPIRED` | past `expires_at` |
| `INVALIDATED` | superseded (e.g. new dry-run for same intent policy) |

**Consumption point:** atomically with successful apply transaction commit
(`CONSUMED`). **Claim** before writer phase; release claim on pre-write `REJECTED`/`FAILED` rollback.

Cases:

- **A** validation reject before claim/commit → receipt stays `ISSUED` (or claim released).
- **B** stale `st1` → reject; receipt remains unusable for changed state (new dry-run required).
- **C** verified apply → `CONSUMED`; cannot authorize second distinct apply.
- **D** `UNKNOWN_*` terminal → receipt `CONSUMED` or `INVALIDATED` (no fresh independent retry on same receipt).
- **E** idempotent replay → return prior `ApplyEvidenceV1` via **idempotency store**, not by reusing an open receipt.

## Dry-run binding (apply validation)

Apply MUST:

1. Load server `DryRunReceiptV1` by id; enforce lifecycle + expiry.
2. Recompute `sd1` from `changeset`; reject mismatch (`CHANGESET_DIGEST_MISMATCH`).
3. Re-run `dry_run` / `validate_changeset`; recompute `pd1` + `cpd1`; reject mismatch.
4. Reject `dry_run_status != OK` and `NO_OP` apply.
5. Re-evaluate domain capabilities; compare `cpd1` to receipt (`CAPABILITY_DRIFT`).
6. Compare fresh `st1` to operation preconditions (`STALE_STATE`).
7. Re-check `expected_current_value` when present.
8. Authorize `context` against `scope` (`UNAUTHORIZED` — distinct from capability drift).

No silent re-plan of a materially different ChangeSet inside Apply.

## Concurrency

| Mechanism | Role |
|-----------|------|
| `st1` per resource | optimistic stale-plan detection vs reviewed precondition |
| `SELECT … FOR UPDATE` on touched `AdvSetting` rows | serialize apply txn vs other Apply attempts on same rows |
| shop advisory lock | **optional V1** — omit unless profiling shows multi-resource ordering gaps; **does not** coordinate legacy writers |

**Legacy writer race:** Excel/Telegram/shop-runner may mutate `AdvSetting` without
participating in Apply locks → residual race until migration. Apply detects via
`st1` mismatch (`STALE_STATE`) at apply time, not global exclusion.

## Idempotency

**Store key:** `(scope.shop_id, idempotency_key)`

**Fingerprint (must match for replay):** `apply_contract_version` + `semantic_digest`
+ `preview_digest` (not `semantic_digest` alone).

| Case | Behavior |
|------|----------|
| same key + same fingerprint + `VERIFIED` | replay immutable `ApplyEvidenceV1`; no write |
| same key + different fingerprint | `IDEMPOTENCY_CONFLICT` |
| same key + in-flight attempt | `APPLY_IN_PROGRESS` |
| failed before commit | retry allowed with same receipt if still `ISSUED` |

**Replay authorization:** idempotent hit MUST still authenticate `context` and
authorize shop/evidence read. Same key + same fingerprint + **unauthorized**
principal → `UNAUTHORIZED`, **no** evidence disclosure.

## V1 PG transaction model (normative)

Single PostgreSQL transaction — **no** “when possible” split:

```text
BEGIN
  → insert/update ApplyAttemptRecord (in-flight)
  → claim idempotency slot / detect conflict
  → claim DryRunReceipt (CLAIMED)
  → FOR UPDATE touched AdvSetting rows
  → revalidate authoritative projection (st1, capabilities, domain validation)
  → apply all bounded PG mutations
  → read back same locked rows (transaction-local verification)
  → verify normalized intended fields
  → compute post_state_tokens from resulting projection
  → insert immutable ApplyEvidenceV1 row + terminal idempotency outcome
  → mark receipt CONSUMED
  → mark attempt VERIFIED
COMMIT
```

Client-visible success (`VERIFIED` + evidence) **only after COMMIT**.

`UNKNOWN_INTERNAL_COMMIT` — **only** when commit outcome is ambiguous (e.g.
connection dropped after possible commit). Ordinary SQL errors → rollback →
`FAILED` / `REJECTED`, not UNKNOWN.

External WB (Slice D): PG txn **not** atomic with WB; separate evidence fields.

## ApplyAttemptRecord vs ApplyEvidenceV1

| Artifact | Mutability |
|----------|------------|
| `ApplyAttemptRecord` | durable lifecycle (`RECEIVED` … `VERIFYING` → terminal) |
| `ApplyEvidenceV1` | **immutable** row inserted once at terminal success (`VERIFIED`) or terminal failure snapshot where required; never updated |

Do not mutate evidence rows through lifecycle states.

## Terminal outcomes (status vs reason_code)

| Terminal status | Typical reason_code |
|-----------------|---------------------|
| `REJECTED` | `VALIDATION_REJECTED`, `UNAUTHORIZED`, `STALE_STATE`, `CHANGESET_DIGEST_MISMATCH`, `PREVIEW_DIGEST_MISMATCH`, `CAPABILITY_DRIFT`, `RECEIPT_INVALID` |
| `FAILED` | `WRITER_REJECTED`, `VERIFICATION_MISMATCH`, `TRANSACTION_ROLLED_BACK` |
| `VERIFIED` | — |
| `UNKNOWN_INTERNAL_COMMIT` | commit acknowledgement lost |
| `UNKNOWN_EXTERNAL_STATE` | Slice D WB ambiguity only |

## Post-apply verification

Verification uses **transaction-local** read of locked rows before COMMIT (PG SoT).
`WRITE_ACCEPTED` (ORM flush) ≠ `STATE_VERIFIED` until field-level compare passes.

`post_state_tokens` MUST be recomputed from the post-mutation projection used for
`st1`. Because `st1` includes the mutated policy subtree for the operation kind,
any successful semantic mutation in that subtree MUST yield a different `st1` unless
the normalized desired value equals prior (then apply should have been `NO_OP` at
dry-run). Do not assert token difference without subtree coverage.

## Authorization vs domain capability

| Concern | Mechanism |
|---------|-----------|
| **Authorization** | `ApplyInvocationContext.shop_authorization` + `permission_grants` (server) |
| **Domain capability** | `evaluate_capabilities` tri-state + `cpd1` digest |

`UNAUTHORIZED` ≠ `CAPABILITY_DRIFT`. Unknown/ineligible domain capability → fail closed.

## Transport parity

```text
REST ─┐
      ├→ build ApplyInvocationContext (trusted)
      ├→ ApplyAuthorityService.apply(request, context)
MCP ──┘
```

## Multi-operation policy

`ChangeSetV1` allows N operations (main spec). V1 Apply: **multiple operations
allowed** within one shop if all are bounded policy ops; **one PG transaction**;
atomic all-or-nothing. No `PARTIALLY_APPLIED` success in V1.

## Failure / recovery

Fail closed codes include: `STALE_STATE`, `CAPABILITY_DRIFT`, `IDEMPOTENCY_CONFLICT`,
`UNAUTHORIZED`, `UNSUPPORTED_OPERATION`, `VALIDATION_REJECTED`, `WRITER_REJECTED`,
`VERIFICATION_MISMATCH`, `UNKNOWN_EXTERNAL_STATE`, `UNKNOWN_INTERNAL_COMMIT`.

No automatic WB retry on unknown external outcome.

## Implementation slices (not authorized here)

| Slice | Boundary |
|-------|----------|
| A | `ApplyRequestV1`, `ApplyInvocationContext`, ports, `pd1`/`cpd1` pure functions, idempotency decision logic, lifecycle enums, receipt lifecycle rules, unit tests — **no PG, no writers, no receipt PG** |
| B | PG: `ApplyAttemptRecord`, idempotency, `ApplyEvidenceV1`, **`DryRunReceiptStore`** |
| C | PG policy writer + **single-txn** apply + in-txn verification + atomic evidence |
| D | External WB writer + `UNKNOWN_EXTERNAL_STATE` |
| E | REST/MCP adapters → `apply(request, context)` |
| F | History / decision-memory reference links |

## Open Questions

- Promote archived `campaign-settings-changeset-ownership` into `openspec/decisions/`.
- Receipt TTL default (e.g. 15m / 24h).
- Exact `APPLY_IN_PROGRESS` visibility timeout for clients.
- Whether audit must be same-txn mandatory or compensating job acceptable.

```text
DESIGN_STATUS: READY_FOR_OWNER_CONTRACT_REVIEW
IMPLEMENTATION_READY: false
```

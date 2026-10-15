---
cursor:
  subagentId: "bc-c4341ba6-f46b-5711-929f-69574af8455d"
---

# CHANGESET_APPLY_AUTHORITY_PLANNING_REPORT

Read-only inventory of production mutation paths and a proposed transport-independent Apply Authority. No product code, no branch, no migrations, no production writes.

```text
BASELINE_SHA:
d2166b2d805b27a6656f46c6ccb8e56066b4e888
(local HEAD == origin/stage)

PR_449_STATE:
OPEN https://github.com/revoluxe-ai/adv-bot/pull/449
branch cursor/campaign-settings-changeset-contract-2398
head 3613cab827c59d38a1a0a1fabf102f99b0dd7d77
base stage
mergeable MERGEABLE
CI: migration-static FAIL, migration-ephemeral-pg FAIL
  (actions/runs/37389138152)
Foundation (wb_sky_control_plane + ChangeSetV1 + registry migration
e8a1b2c3d4e5) exists only on this branch. origin/stage does not contain
app/modules/wb_sky_control_plane.
Contract implementation (validation/diff product work beyond the adopted
foundation) is not started. Design still records
IMPLEMENTATION_BLOCKER=LOCAL_FOUNDATION_ADOPTION_REQUIRED and forbids an
apply executor. Not implementation-ready.

CANONICAL_CHANGESET:
ChangeSetV1
app/modules/wb_sky_control_plane/models/changeset.py on PR #449 head.
Bounded ops only:
  campaign.set_budget_policy
  campaign.set_sales_policy
  campaign.set_bid_control_policy
No second ChangeSet.

PRODUCT_CODE_CHANGED: NO
MIGRATIONS_CREATED: NO
PRODUCTION_WRITES: NONE
IMPLEMENTATION_READY: NO
FINAL_STATUS: PLANNING_READY
```

## PRODUCTION_WRITER_INVENTORY

Two classes. Current `ChangeSetV1` operations are **local policy** (PostgreSQL). Direct WB HTTP writers are **downstream runtime authorities** and must not be invoked by V1 Apply.

### A. Local policy writers (match current ChangeSetV1)

| ID | Caller | Writer | Semantics | Input | Endpoint | Idempotency | Concurrency | Error/ack | Post-check | Audit | Reuse under Apply |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | Telegram `campaign_activity` | `AdvSetting` columns `*_budget_*_limit`, `use_common_budget` | Set daily/total spend caps. 0 daily = pause-by-limit later. Does not deposit. | Telegram FSM int | none (PG) | last write wins | no `state_token`; session commit | exception / UI | none | none | Adapter: yes, as PG policy writer. Do not call WB. |
| P2 | Telegram `strategy_setting`, adv-setting handlers, `common_budget_mode_toggle` | `AdvSetting` sales/budget flags | Strategy, watchdog off, common-budget mode | callback/message | none (PG) | last write wins | none | exception | none | none | Same adapter as P1. Many handlers, one table. |
| P3 | Excel `apply_adv_excel_rows` | `AdvSetting` editable columns + `AutoShelfBidControlSettings` | Whole file fail-fast. Hold mode excluded (decision card-ab-hold §9). Max-CPO decrease can clear substitute flag. | Excel row dict | none (PG) | last write wins per row; file atomic only by exception (one session) | RO ids checked vs server; no generation token | `AdvExcelImportError` aborts | none | none | Reuse field assignment only behind ChangeSet normalization. Excel must stop being a writer. |
| P4 | `keyword_updater.update_keywords` | `KeywordSetting` hard_status / V3 strategy OFF | Bulk PG keyword policy. Skips A/B Hold freeze. | cabinet id | none (PG) | repeatable UPDATE | SQL filter, no token | exception | none | none | Not a V1 op. Future keyword op needs its own ChangeSet operation, same Apply protocol. |
| P5 | A/B Hold `epoch_write` | `AdvSetting` epoch/generation + PENDING intent | Durable intent **before** WB sync. `SELECT … FOR UPDATE`. | epoch confirmation | none (PG) then later WB | same-generation retry must not recompute | row lock + generation | commit then WB | partial-sync recovery in epoch decision | PG row | Do not fold into V1 policy apply. Separate owner (`ab-hold-epoch-lifecycle`). |

Accepted SoT: `openspec/decisions/campaign-settings-contract-ownership/decision.md` — PostgreSQL is current-settings authority. Registry does not write.

### B. Direct WB mutation paths (live callers on stage)

| ID | Caller | Writer / adapter | Semantics | Input | WB endpoint | Idempotency | Concurrency | Error/ack | Post-check | Audit | Safe reuse |
|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | `AutoBudgetService.ensure_budget` / `ensure_common_budget`; also activity-control start retry hook | `WBModifier.top_up_budget` → `PromotionManager.top_up_budget` → `finance/adapter.py` | Deposit campaign budget from shop wallet. Amount planned from limits. | adv_id, amount, balance type, optional cashback | `POST /adv/v1/budget/deposit` | **Not idempotent.** Retry can double-charge. Adapter retry limit 1. | PG topup row created **before** HTTP. No WB precondition. | exception → status `failed`. HTTP return `total` optional. | `_verify_budget` expected growth → `success` or `unverified` | `topup_log` row (not decision/changeset) | **No** for V1 policy ops. Reuse later only as a non-idempotent money adapter with UNKNOWN-on-ambiguous-ack and no blind retry. |
| W2 | `auto_shelf_bid_setter`; A/B Hold `epoch_pipelines` | `WBModifier.patch_auto_adv_bids_kopecks` / `update_auto_adv_cpm` → `patch_adv_v1_bids` | Set Auto bid in kopecks. Placement from v2 `bid_type` (`combined`/`recommendations`). Unknown bid_type retries placement. | adv_id, nm→bid | `PATCH /api/advert/v1/bids` | Set-to-value (retry-safe if same body). Adapter retry limit 2. | Reads v2 then writes. No state_token. | raise on known bid_type mismatch | Redis bid cache after PATCH in shelf setter; no WB re-read contract | logs | Reuse later for a future bid op. Not a V1 policy writer. |
| W3 | `UpdateCommotBidInSearchAdvsManager`; Telegram `set_common_bid_manual`; A/B Hold `common_bid_enter_reset` | `WBModifier.update_search_adv_common_cpm` → `set_common_bids` → `common_bids/adapter.py` | Search/auction common CPM. Same HTTP as W2, search placement. | `SetCommonBidsCommand` | `PATCH /api/advert/v1/bids` | Set-to-value | none | raise | none observed | logs | Same adapter as W2 with placement discipline. Two product callers already share it. |
| W4 | shop-runner `update_cluster_bids` | `set_cluster_bids_for_adv` → `POST normquery/bids` | Per-cluster search bids | normquery bid items | `POST /adv/v0/normquery/bids` | Set-to-value; special errors swallowed by `catch_special_errors` | none | raise or special-case | none | logs | Reuse only behind a future keyword-bid operation. Error swallowing must not hide UNKNOWN. |
| W5 | `MinusPhraseManager` | `set_minus_phrases_with_fallback_for_adv` | Replace minus phrases; drops invalid phrases; skips unsupported campaign types | phrase list | `POST /adv/v0/normquery/set-minus` | Replace-set, but fallback mutates the requested set | none | fallback success with dropped phrases (partial semantic) | get-minus exists, not a mandatory post-check | logs | **Adapter required.** Fallback partial apply is incompatible with fail-closed whole-op ack. |
| W6 | `AutoAdvActiveControlService` | `pause_auto_campaign` / `pause_auction_campaign` / `start_*_campaign` | Pause/start one leg. Empty-keywords must use auction pause only. Shelf-exhausted must use auto pause only. Start may deposit once then retry start. | `ComplexAdv` + leg | `GET /adv/v0/pause`, `GET /adv/v0/start` | Pause/start of already-that-status is not specified; start+deposit is not idempotent | Redis intent + PG reasons; no WB etag | raise; low-budget start → one budget ensure + one retry | status read exists (`get_campaign_status`) but not a uniform post-check | logs / Redis | Reuse per leg with reason ownership from accepted pause decisions. Do not unify Auto and Search into one pause call. `stop_*` has **no live caller**. |
| W7 | Telegram `connect_existing_advs` | `set_auction_placement`, `rename_campaign` | One-shot placement + rename when binding an existing campaign | adv ids, flags, name | `PUT /adv/v0/auction/placements`, `POST /adv/v0/rename` | rename/placement set-to-value | none | logged failure | none | logs | Out of V1. Future placement/rename ops only. |
| W8 | shop-runner `update_cpm_bid` when `BidderCoroutineType.OLD_UPDATE_CPM_BIDDER`; Telegram `change_cpm` | `BidderWBApi` → `AdvMixin.update_cpm` | Legacy CPM. Shelf module documents this path as WB 404. Raises min-bid and retries once at WB min. | adv_id, nmid, rub bid | `PATCH /adv/v0/bids` | set-to-value, but min-bid rewrite changes the requested value | none | user-visible exception in Telegram | none | logs | **Do not reuse.** Dead/legacy authority. |
| W9 | `adv_creator` `MainAdvManager` | `AdvMixin.create_auto_adv` / `create_search_adv` | Creates WB campaigns then PG `AdvSetting` | nmids, name | `POST /adv/v2/seacat/save-ad` | **Not idempotent** (new id) | balance check then create | exception; partial Auto-created/Search-failed possible | none as a control-plane post-check | logs | Extension point only. Not a V1 operation. |

### C. Latent adapters (defined, no live caller found)

- `AdvMixin.set_search_cpm` → `POST /adv/v0/cpm` (also duplicated on `common_slaves` `wb_api.py` / `api.py`)
- `AdvMixin.update_nmids_in_adv` / `update_nmids_in_auto_adv` → `POST /adv/v1/auto/updatenm`
- `common_slaves` `pause_company` → `GET /adv/v0/pause`; `set_pluse_status_in_search_adv` → `GET /adv/v1/search/set-plus` (call site in `search_advs_manager` is commented)
- `WBModifier.stop_auto_campaign` / `stop_auction_campaign` → `GET /adv/v0/stop`
- Generated clients for save-ad / updatenm / set-excluded exist; live product path for create is W9 only

```text
DIRECT_WRITE_PATHS_FOUND:
9 live WB mutation paths (W1–W9) plus 5 live PG policy paths (P1–P5).
Latent unused adapters listed in section C (not counted as live).

REUSABLE_WRITERS:
- PG AdvSetting / AutoShelfBidControlSettings assignment (P1–P3) as the V1
  Apply target, after ChangeSet normalization. Not the Excel/Telegram entry.
- W2/W3 shared PATCH /api/advert/v1/bids adapter for a future bid operation.
- W6 pause/start leg methods, only with existing reason ownership
  (empty-keywords → auction; shelf-exhausted → auto).
- W4 set-to-value cluster bids, after UNKNOWN handling is made explicit.

WRITERS_REQUIRING_ADAPTER:
- W1 deposit: money, non-idempotent, needs explicit ack/UNKNOWN. Not V1.
- W5 minus-phrases fallback: partial phrase drop is not a clean ack.
- W8 legacy /adv/v0/bids: retire, do not wrap.
- W9 create: extension point, separate operation later, same protocol.
- P5 epoch write: different owner and generation lock; not a policy op.

DUPLICATE_AUTHORITIES:
- Budget policy: Telegram campaign_activity + Excel + (future) Apply all
  write the same AdvSetting columns. Shop-runner then deposits (W1) and
  pauses (W6) from those columns. Three policy writers, one downstream WB.
- Sales policy: Telegram strategy/settings + Excel.
- Bid-control policy: Excel shelf columns + Telegram/shop-runner flag
  `auto_shelf_bid_control_enabled` (bidder skips legacy Auto CPM when on).
- Bids: modern PATCH v1 (W2/W3) AND legacy PATCH v0/bids (W8) AND cluster
  POST (W4). Telegram manual common bid and shop-runner share W3.
- Pause: only W6 is live, but Auto vs Search are separate legal writers
  (accepted decisions). stop_* is a second unused verb.
- Create: adv_creator only (W9), outside control plane.
```

## PROPOSED_APPLY_BOUNDARY

Owner: `app/modules/wb_sky_control_plane` apply module (future). Not `campaign_settings_contract`. Not a new ChangeSet type.

```text
AI / JSON / Excel / API / MCP
        → parse into ChangeSetV1 only (reject raw AI JSON at the boundary)
        → existing dry_run (resolve, capability, validate, semantic diff)
        → Apply Authority accepts DryRunResult status OK only
        → normalized PlanEffectV1 list
        → one PostgreSQL transaction for V1 policy ops
        → ack = PG commit
        → deterministic re-read post-check
        → audit seam event (no new table in this change)
        → existing shop-runner WB writers stay downstream and are not called
```

Apply request (transport-independent):

- `changeset: ChangeSetV1` already validated by the same models (`extra=forbid`)
- `dry_run: DryRunResultV1` with `status=ok`, same `changeset_id`, same `semantic_digest`
- `state_tokens` from that dry-run, one per touched `cmp_*`
- no free-form payload, no Excel row, no MCP tool args

Normalized operations: `PlanEffectV1` (`resource_id`, `operation`, `operation_index`, `semantic_changes`). Apply writes only fields present in `semantic_changes`. `NO_OP` never calls a writer.

Execution ordering: preserve ChangeSet `operations` order. V1 effects for one resource commute inside one PG transaction (budget, sales, bid-control are different columns). Order is still recorded for the audit seam.

Per-operation status (V1, all inside one transaction): `pending | committed | rolled_back | skipped_no_op`. No `applied_unconfirmed` in V1 because there is no WB call.

Whole-ChangeSet vs partial: **whole ChangeSet commits or whole rolls back.** One invalid or one DB error → zero policy rows changed. This matches #449 dry-run atomic `REJECTED`.

## PREWRITE_INVARIANTS

All must hold before the first `INSERT/UPDATE` of Apply (and, later, before any WB HTTP):

1. Envelope is `ChangeSetV1` / `contract_version=v1`. Unknown op → reject. `campaign.create` is unknown in V1.
2. `dry_run.status == ok` and `semantic_digest` equals recomputed digest. `rejected` and `no_op` do not write. Stale digest → reject.
3. Every touched resource has a fresh snapshot. `MappingStatus` not `ok`, missing snapshot, `UNKNOWN` capability → reject whole set. Tri-state `UNKNOWN` is never write-eligible (`enums.TriStateCapability`).
4. `state_token` is present and equals the token recomputed from the current snapshot for the targeted op kinds (`st1`). Omitting `preconditions` does **not** skip this. Foundation `validate_changeset` checks the token only when `preconditions` is set; Apply is stricter and must not inherit that hole.
5. Resource id is `cmp_*` resolved in-registry. No apply by raw `adv_id`.
6. Normalized values only (registry `normalize_value` where the field is registered). Requested raw value is audit-only.
7. Shop scope matches the resolved resource cabinet. Cross-shop ChangeSet → reject.
8. No mix of V1 policy ops with any WB-effect op in one ChangeSet until a later contract explicitly allows it.
9. A/B Hold structural freeze and accepted pause-reason ownership are not bypassed. Apply does not pause, deposit, or set bids.
10. Idempotency: duplicate `operation_id` already rejected by the model. Same `changeset_id` + same digest already committed → return the prior ack, do not write again. Same id + different digest → reject.
11. PostgreSQL row lock (`SELECT … FOR UPDATE` on the settings rows) taken after token check and before update. Token mismatch after lock → rollback.

## EXECUTION_ATOMICITY

`V1_POLICY_PG_TRANSACTION`

Current three operations commit in one PostgreSQL transaction. WB has no transaction, and these operations are not WB effects. Partial execution is forbidden.

Future WB-effect operations (not enabled now): `SEQUENTIAL_STOP`. After the first successful WB ack, earlier ops stay applied. Later ops do not run. No silent compensate. Ambiguous ack → `UNKNOWN` and stop. That class is a later ChangeSet extension, not a second protocol.

## STATE_TOKEN_ENFORCEMENT

`st1` per resource from `kernel/state_token.py`: hash of resource id, cabinet, both legs (wb id, role, bid type, payment, placements, status, membership, nm ids), classification, and only the local policy subtree for the ops in the ChangeSet.

Apply recomputes under row lock immediately before write. Mismatch → `STATE_TOKEN_MISMATCH`, whole rollback, no writer call. Token is not a field-level lock; it is the only optimistic generation. `expected_current_value` is not in the adopted model; do not add a second lock.

## IDEMPOTENCY_BOUNDARY

Boundary is `(changeset_id, semantic_digest)` plus per-op `operation_id` uniqueness inside the set.

- Same id + same digest + prior `committed` → replay ack.
- Same id + different digest → reject.
- In-flight duplicate → one winner (PG advisory lock or unique constraint on changeset_id when a future ledger exists). Until that ledger feature, Apply must still refuse a second in-process attempt and fail closed if it cannot prove the first attempt's outcome.
- WB deposit (W1) is outside this boundary. Replaying a policy ChangeSet must not replay a deposit.

No new idempotency table in this change. The seam below is the hook a later feature will persist.

## RETRY_SEMANTICS

V1: retry is re-run of dry-run + apply. If the first transaction committed, retry returns the prior ack. If it rolled back, retry is a new attempt against a new token. No WB retry.

Future money/WB: retry only when the prior attempt is proven not to have reached WB. Timeout / empty body / connection reset after send → `UNKNOWN`, no automatic retry. Adapter `@retry_decorator` on deposit (limit 1) and bids (limit 2) is an existing hazard; a future WB op must not stack decorator retries on top of Apply retries.

Crash: process dies before commit → PG rollback, no policy change. Process dies after commit before audit emit → policy is committed; audit gap is detectable by post-check re-read vs missing seam event. Do not "repair" by writing WB.

## WB_ACK_CONTRACT

V1: **no WB ack.** Apply ack is the PostgreSQL commit of the normalized policy rows. `wb_ack` on the seam is `not_applicable`.

Downstream shop-runner WB calls keep their current ack behavior and are not Apply acks. A later WB operation must record: HTTP status, parsed body or empty, and one of `acknowledged | rejected | unknown`. Empty or unparsed success body is `unknown`, not success. Deposit `total` is an ack field only when present and numeric; absence is `unknown` (today W1 already distinguishes `unverified`).

## POSTCHECK_CONTRACT

V1: in the same transaction, re-read the written columns and compare to `PlanEffectV1.desired`. Mismatch → rollback (write never becomes visible). After commit, a read-only re-read may emit `postcheck_state=match|drift`. Drift after commit is an incident, not a silent second write.

WB post-check is out of V1. When added: re-read the authoritative WB field (budget total, v2 bid, campaign status) and compare to the normalized intent. Mismatch or read failure → `postcheck_state=unknown` or `mismatch`, no compensating write.

## UNKNOWN_STATE_POLICY

`FAIL_CLOSED`

Unknown capability, unknown mapping, missing snapshot, missing token, digest mismatch, unparsed WB body, or crash with unproven outcome → no further writes. Do not guess the current bid, budget, or status.

## AUDIT_SEAM

Interface only. No table, no migration, no experiment ledger.

One event per operation after post-check (and one ChangeSet envelope event):

```text
decision_id          metadata.decision_id (optional)
changeset_id
operation_id
requested            raw payload fields
normalized           values after normalize_value
previous_state       semantic diff current
applied_state        values committed, or null if rolled back
wb_ack               not_applicable in V1; later acknowledged|rejected|unknown
execution_status     committed|rolled_back|skipped_no_op|unknown
postcheck_state      match|mismatch|unknown|not_applicable
reason/source        operation.reason + metadata.origin
timestamps           validated_at, write_started_at, committed_at, postcheck_at
```

Sink is a port (`AuditSink.append`). Default implementation in the future feature may be a table. This change does not choose storage. Apply must not succeed by skipping the port call: if the port is not injected, fail closed before write. A no-op in-memory sink is allowed only in unit tests.

## CAMPAIGN_CREATE_EXTENSION_POINT

`campaign.create` is not a V1 operation and has no Apply implementation.

Extension: a later change adds one new member to `CanonicalOperationKind` and `CampaignOperationV1` on the **same** `ChangeSetV1`, then the same pipeline `validate → dry-run → apply → audit → post-check`. It must not grow a private writer protocol in `adv_creator`. W9 (`POST /adv/v2/seacat/save-ad`) may be the adapter behind that future op. Create stays non-idempotent: success returns the new WB id into `applied_state`; ambiguous HTTP is `UNKNOWN` and must not create a second campaign on retry.

## EXCEL_JSON_API_MCP_PARITY

Every transport parses to `ChangeSetV1` and calls the same `dry_run` then the same Apply. None of them write `AdvSetting` themselves.

- Excel: importer maps editable columns → `set_budget_policy` / `set_sales_policy` / `set_bid_control_policy`. File-level failure stays whole-ChangeSet reject. `apply_adv_excel_rows` becomes a parser, not a writer.
- JSON / public API: body is `ChangeSetV1` (`extra=forbid`). Arbitrary AI JSON that is not this model is rejected before dry-run.
- MCP: tool args build `ChangeSetV1` only. MCP does not receive a side door to WB adapters.
- AI Package export stays read-only (`ai-package-v1-exporter-ownership`). An AI **proposal** becomes a ChangeSet through this boundary; export code does not apply.

Shop-runner autonomous WB writers (W1–W6) remain separate runtime authorities until an Owner change explicitly moves each effect behind a new ChangeSet operation. V1 Apply does not replace them and does not call them.

## CONFLICTS_WITH_ACTIVE_CHANGES

- `#449` `campaign-settings-changeset-contract` (head `3613cab82`): owns `ChangeSetV1` and forbids apply, PG writes, and WB writes inside that change. This inventory does not edit the PR. Apply implementation waits until #449 is on `origin/stage` and its migration gates are green. Foundation is not on `d2166b2d`.
- `#449` design says missing `state_token` rejects the set; adopted `validate_changeset` enforces the token only when `preconditions` is present. Apply must not copy that gap. Fixing the validator belongs to #449 or a follow-up on that change, not to this planning task.
- `#450` AI package export repair: export must stay `READ_ONLY_NO_MUTATION`. No apply hook on the exporter.
- `separate-auto-search-cpo` clean branch `f6c18bb76` (not merged): touches search CPO/bid behavior. Future bid operations must rebase onto that writer (W3/W4), not the legacy v0 path.
- `campaign-attribution-facts`: read/grain planning only. No write overlap.
- Accepted decisions that stay in force and are not redesigned here:
  - `openspec/decisions/campaign-settings-contract-ownership/decision.md`
  - `openspec/decisions/empty-keywords-pause-write-path/decision.md`
  - `openspec/decisions/auto-shelf-exhausted-pause-write-path/decision.md`
  - `openspec/decisions/auto-bid-module-coexistence-write-path/decision.md`
  - `openspec/decisions/card-ab-hold-write-path-ownership/decision.md`
  - `openspec/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md`
  - `openspec/decisions/ai-package-v1-exporter-ownership/decision.md`

## OWNER_DECISIONS_REQUIRED

1. Confirm V1 Apply writes **only** PostgreSQL policy and does **not** call WB writers. Recommended above as `V1_POLICY_PG_TRANSACTION`.
2. Confirm shop-runner WB writers stay parallel authorities until each effect is a new ChangeSet operation.
3. Confirm legacy `PATCH /adv/v0/bids` (W8) is retirement, not an Apply adapter.
4. Confirm audit seam is a port with no table in the Apply change.
5. Confirm `state_token` is mandatory at Apply even when the client omits `preconditions` (stricter than current #449 validator).
6. When WB-effect ops are added later: accept `SEQUENTIAL_STOP` and no automatic compensate.

```text
IMPLEMENTATION_READY: NO
PRODUCT_CODE_CHANGED: NO
MIGRATIONS_CREATED: NO
PRODUCTION_WRITES: NONE
FINAL_STATUS: PLANNING_READY
```

## 1. Reconciliation gate (historical + resolved)

- [x] 1.1 Before any production edit, record the local `wb_sky_control_plane` WIP reconciliation result. If that WIP already contains a ChangeSet contract, stop and reconcile; do not invent a second contract.
  - **Evidence (2026-10-05):** Verdict **CONFLICT**. Only inspected worktree: `C:/Users/vkita/my_code/meta-repo/adv-bot`, branch `stage`, HEAD `751e7bd29`, dirty (not modified by this recording). Untracked WIP: `app/modules/wb_sky_control_plane/` (38 Python files), `tests/unit/wb_sky_control_plane/` (9 tests), Alembic `e8a1b2c3d4e5_add_wb_sky_campaign_resource_registry.py`. Local `ChangeSetV1` lives in that package (`models/changeset.py`, `validate_changeset` in `kernel/validate.py`), not in `campaign_settings_contract`. Forty-four other adv-bot worktrees: no `wb_sky_control_plane`. Local `stage` is 2 commits behind `origin/stage`. Full write-up: `/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/docs/changeset-local-wip-reconciliation.md` (mirror: `/cursor/stores/self/docs/changeset-local-wip-reconciliation.md`).
- [x] 1.2 Confirm `origin/stage` still has no committed `app/modules/wb_sky_control_plane/` and no `ChangeSetV1` in `campaign_settings_contract`.
  - **Evidence:** `origin/stage` at `23c0671f372f0435b13a3573ec8990b4303b3e4a` has no committed control-plane package. See reconciliation doc above.
- [x] 1.3 Owner reconciliation replan (2026-10-05): **REUSE_DECISION = EXTEND_EXISTING** — canonical `ChangeSetV1` and `validate_changeset` remain in `wb_sky_control_plane`; `campaign_settings_contract` is registry/normalization reuse only. Historical **CONFLICT** is no longer an unresolved blocker; **IMPLEMENTATION_BLOCKER = LOCAL_FOUNDATION_ADOPTION_REQUIRED**. Cite: `changeset-local-wip-reconciliation.md` (paths above).

## 2. Adoption gate (before any product code)

- [x] **LOCAL_FOUNDATION_ADOPTION_REQUIRED** — Preservation checkpoint is commit `2b9b4f1d2` (`chore(control-plane): adopt existing ChangeSetV1 foundation`) on this branch. It binds `app/modules/wb_sky_control_plane/**`, `tests/unit/wb_sky_control_plane/**`, and Alembic `e8a1b2c3d4e5_add_wb_sky_campaign_resource_registry.py` to change `campaign-settings-changeset-contract`. Sections 3–5 stay open; this checkbox does not mark product implementation done.

## 3. Extend control plane (after adoption only)

- [x] 3.1 Bind adopted WIP `ChangeSetV1` (`models/changeset.py`); do **not** create a second `ChangeSetV1` type or parallel package.
- [x] 3.2 Extend `mutation_policy` semantics for existing bounded operations (WIP examples include `SetBudgetPolicyOperation`; full set from `changeset.py` at adoption).
- [x] 3.3 Wire registered settings fields to `campaign_settings_contract.normalize_value`; control plane still owns ChangeSet and dry-run.
- [x] 3.4 Extend existing capability **tri-state**; unknown/unsupported tokens fail closed.
- [x] 3.5 Extend `validate_changeset` (`kernel/validate.py`) for dry-run only: injected snapshot, `state_token`, capability grant, `PriorChangeSetRecord | None`. **Do not** add `validate_changeset_v1` to `campaign_settings_contract`.
- [x] 3.6 Emit `SemanticDiffEntryV1` and statuses `NO_OP | OK | REJECTED`; implement idempotency contract (in-document duplicate `operation_id`; injected `changeset_id` hash conflict/replay) without durable store.
- [x] 3.7 Implement named domain validators for declared cross-field invariants; unimplemented declared invariant → atomic `REJECTED`.

## 4. Tests (after adoption only)

- [x] 4.1 Unit scenario seams for every `#### Scenario` in `specs/campaign-settings-changeset-contract/spec.md` against real `validate_changeset` and real `normalize_value` where applicable.
- [x] 4.2 Assert atomic mixed valid/invalid rejection; stale/missing `state_token`; capability unknown/unsupported; forbidden adapters not called (including MIXED `campaigns_info_v2/adapter.py`).
- [x] 4.3 No PostgreSQL, ClickHouse, WB, Excel, or shop-runner integration tests in this change.

## 5. Non-goals check

- [x] 5.1 Diff confirms no `apply_adv_excel_rows`, WB write clients, PostgreSQL settings writes, ClickHouse writes, or MIXED adapter use on the dry-run path.
- [x] 5.2 Telegram payload surfaces unchanged. Checklist N/A for this change.

## Telegram UI / Message Safety

This change does not create or modify Telegram bot UI text, captions, callback answers, inline keyboards, polls, invoices, or checklist text. The payload checklist does not apply.

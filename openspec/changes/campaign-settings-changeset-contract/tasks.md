## 1. Reconciliation gate

- [x] 1.1 Before any production edit, record the local `wb_sky_control_plane` WIP reconciliation result. If that WIP already contains a ChangeSet contract, stop and reconcile; do not invent a second contract.
  - **Evidence (2026-10-05):** Verdict **CONFLICT**. Only inspected worktree: `C:/Users/vkita/my_code/meta-repo/adv-bot`, branch `stage`, HEAD `751e7bd29`, dirty (not modified by this recording). Untracked WIP: `app/modules/wb_sky_control_plane/` (38 Python files), `tests/unit/wb_sky_control_plane/` (9 tests), Alembic `e8a1b2c3d4e5_add_wb_sky_campaign_resource_registry.py`. Local `ChangeSetV1` lives in that package (`models/changeset.py`, `validate_changeset` in `kernel/validate.py`), not in `campaign_settings_contract`. Forty-four other adv-bot worktrees: no `wb_sky_control_plane`. Local `stage` is 2 commits behind `origin/stage`. Implementation of tasks 2+ is **STOPPED** until a later reconciliation returns **NO_CONFLICT**; this recording is not NO_CONFLICT. Full write-up: project store doc `changeset-local-wip-reconciliation.md` (`/cursor/stores/self/docs/changeset-local-wip-reconciliation.md`).
- [x] 1.2 Confirm `origin/stage` still has no `app/modules/wb_sky_control_plane/` and no `ChangeSetV1` type. Do not create that package.
  - **Evidence:** `origin/stage` remains at `23c0671f372f0435b13a3573ec8990b4303b3e4a` with no `app/modules/wb_sky_control_plane/` and no `ChangeSetV1` in `campaign_settings_contract`. This OpenSpec change does not create that package. See `changeset-local-wip-reconciliation.md` (project store path above).

## 2. Domain types

- [ ] 2.1 Add `ChangeSetV1`, operation, target, and diff dataclasses or pydantic models in `app/modules/campaign_settings_contract/` with `schema_version=changeset.v1`.
- [ ] 2.2 Add `mutation_policy` entries only for registry fields whose `target_scope` is explicit. Leave unclassified settings non-mutable.
- [ ] 2.3 Add the closed capability catalog `settings_mutation` and `campaign_lifecycle`.
- [ ] 2.4 Export the pure `validate_changeset_v1` function. It MUST accept the changeset, an injected current snapshot, an injected capability grant, and `PriorChangeSetRecord | None`.

## 3. Pipeline and diff

- [ ] 3.1 Implement structural, identity, registry, normalization (`normalize_value`), domain, capability, and precondition steps in that order.
- [ ] 3.2 Implement atomic outcomes `NO_CHANGE`, `CHANGE`, and `REJECTED` with `field`, `old_value`, `requested_value`, and `normalized_value` only for actionable changes.
- [ ] 3.3 Implement in-document duplicate `operation_id` and duplicate target+field rejection.
- [ ] 3.4 Implement injected prior-record semantics for duplicate `changeset_id` without a database.
- [ ] 3.5 Keep cross-field invariants out of the policy table. An unimplemented declared invariant MUST reject.

## 4. Tests

- [ ] 4.1 Add unit scenario seams for every `#### Scenario` in `specs/campaign-settings-changeset-contract/spec.md`, including Auto versus Search separation and the paired assertion that forbidden adapters are not called.
- [ ] 4.2 Assert mixed valid/invalid operations reject the whole ChangeSet.
- [ ] 4.3 Assert missing snapshot, stale precondition, unknown capability, read-only field, and unsupported field.
- [ ] 4.4 Do not add PostgreSQL, ClickHouse, WB, Excel, or shop-runner integration tests in this change.

## 5. Non-goals check

- [ ] 5.1 Diff the change and confirm there is no call to `apply_adv_excel_rows`, WB write clients, PostgreSQL writes, or ClickHouse writes.
- [ ] 5.2 Confirm Telegram payload surfaces are unchanged. No bot text, callback, or keyboard edits.

## Telegram UI / Message Safety

This change does not create or modify Telegram bot UI text, captions, callback answers, inline keyboards, polls, invoices, or checklist text. The payload checklist does not apply.

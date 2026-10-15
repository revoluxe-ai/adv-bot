# ChangeSet local WIP reconciliation

Inventory verdict was **CONFLICT**. Owner reconciliation on HOME-PC then resolved it: **REUSE_REQUIRED**. Canonical `ChangeSetV1` stays in `app/modules/wb_sky_control_plane` (`models/changeset.py`). A second contract in `campaign_settings_contract` is not created.

Draft [#449](https://github.com/revoluxe-ai/adv-bot/pull/449) records that replan at `782d9f35d`. Still planning only. No product code. No merge.

Read-only check by [Reconcile local ChangeSet WIP](bc-bb6edb6e-3a4f-5bb3-ac71-2609e643cd50) on HOME-PC. Project store was not mounted there; this file is the retained copy.

## Where the WIP is

- Worktree: `C:/Users/vkita/my_code/meta-repo/adv-bot`
- Branch: `stage`
- HEAD: `751e7bd29` (2 commits behind `origin/stage` `23c0671f`, missing the #448 cloud-routing merge)
- Dirty: 16 porcelain lines
- Untracked: `app/modules/wb_sky_control_plane/` (38 Python files), `tests/unit/wb_sky_control_plane/` (9 tests), Alembic `e8a1b2c3d4e5_add_wb_sky_campaign_resource_registry.py`
- Tracked modify: `campaigns_info_v2/adapter.py` (raw fetch helper for the wb_sky reader)
- Other 44 adv-bot worktrees: no `wb_sky_control_plane`

## Why it conflicts

Local WIP already has a ChangeSet contract outside `campaign_settings_contract`:

- `ChangeSetV1` in `models/changeset.py` (resource / `cmp_*` model, typed ops such as `SetBudgetPolicyOperation`)
- `validate_changeset` in `kernel/validate.py`
- pipeline, planner, resolver

`origin/stage` `23c0671f` has no `wb_sky_control_plane/` and no `ChangeSetV1` in `campaign_settings_contract`.

[#449](https://github.com/revoluxe-ai/adv-bot/pull/449) (`c3e88b4b`) is OpenSpec planning only. Its design forbids creating `wb_sky_control_plane/**`. Tasks 1.1–1.2 stop when this WIP exists.

## Hold

- Do not edit, commit, or clean the local dirty worktree.
- Do not add a second ChangeSet implementation under `campaign_settings_contract`.
- Do not merge #449 as an implementation vehicle. Planning record of this conflict is allowed.

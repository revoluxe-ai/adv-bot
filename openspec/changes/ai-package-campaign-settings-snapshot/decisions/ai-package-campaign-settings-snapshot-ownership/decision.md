# Decision: AI Package campaign settings snapshot ownership and seam

## Status

Proposed

## Context

Three read-side representations touch campaign settings with overlapping fields
but different consumers and grains:

1. **AI Package v1** manifest card `campaign_settings_snapshot` — minimal PG
   inventory today; future detailed export for AI/analytics (`ai-package-v1-contract`
   D-002 deferred scope).
2. **`CampaignResourceSnapshotV1`** — WB Sky Control Plane A1 authoritative
   snapshot keyed by `cmp_*` resource for ChangeSet preview/apply
   (`app/modules/wb_sky_control_plane/models/snapshot.py`).
3. **`AdvSettingsSnapshotDTO`** — slim Redis tick payload for shop-runner /
   `snapshot_data_updater` with `bot_active`-only scope
   (`app/snapshot_data_updater/dto.py`).

Accepted `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` places
export in `app/modules/ai_package_v1/` with READ_ONLY_NO_MUTATION but does not
define the detailed settings contract or forbid accidental DTO aliasing. Without
an explicit seam decision, implementers may serialize A1 or Redis DTOs as the AI
Package dataset, breaking grain-preservation, scope filters, and fail-closed
unknown semantics.

## Decision

1. The AI Package detailed campaign settings export MUST own a dedicated domain
   contract **`CampaignSettingsSnapshotV1`** under `app/modules/ai_package_v1/`
   (exact module paths per change design). Manifest card id remains
   `campaign_settings_snapshot`.
2. **Primary export grain** MUST be `(shop_id, adv_setting_id)` with explicit
   separate `auto_leg` and `search_leg` sections. MUST NOT use `cmp_*`
   `resource_id` as primary row key. MAY attach optional `a1_resource_id`
   cross-reference when registry evidence exists.
3. **`CampaignResourceSnapshotV1` MUST NOT** be the AI Package export payload
   schema, JSON alias, or validator target. Control plane MAY continue to own WB
   live read + apply semantics independently.
4. **`AdvSettingsSnapshotDTO` / `AdvDataSnapshotDTO` MUST NOT** be the AI Package
   export contract. Redis tick snapshots remain operational shop-runner cache;
   export MUST NOT use `bot_active`-only warmup filter as shop scope.
5. **Primitive reuse** is allowed only for read-only, side-effect-free helpers
   (e.g. PG column projection lists mirroring `project_local_policy_from_adv_setting`,
   normalization **patterns** from `normalize_wb_campaign_leg`) when extracted or
   copied into `ai_package_v1` with export-owned tests. Importing control-plane
   apply/resolver/registry write paths on the default export path is forbidden.
6. Export path MUST remain `READ_ONLY_NO_MUTATION` per ai-package-v1-exporter
   ownership: no WB API, no collector triggers, no mode defaults / `bot_active`
   writes, no Redis snapshot writes.
7. Field-level **`authority_class`** and **`field_provenance`** MUST distinguish
   WB authoritative state, local AdvSetting policy, inventory relations, UNKNOWN,
   and UNSUPPORTED. Missing/null MUST NOT be replaced with generated-client or DTO
   constructor defaults.

## Applies to

- Change `ai-package-campaign-settings-snapshot` and AI Package exporter apply slices
- Contract tests under `tests/unit/ai_package_v1/` for settings snapshot
- Future archive promotion of this decision to `openspec/decisions/` (out of scope
  for this planning hop)

## Allowed

- `CampaignSettingsSnapshotV1` assembler reading PG via `get_async_session_maker(read_only=True)`
- Scope query aligned with `PgExportShopScopeReader` / `WBShopDataManager.__get_advs(..., only_bot_active=False)` **without** calling `WBShopDataManager`
- Optional shared read-only normalizer module extracted from A1 after explicit apply task (slice 2)
- Manifest card referencing domain JSON + sha256 (transport decoupled)

## Forbidden

- Serializing or validating `CampaignResourceSnapshotV1` as AI Package settings export
- Using `AdvSettingsSnapshotDTO` as export schema or defaulting unset fields from it
- Using A1 `cmp_*` identity as export primary grain
- Merging Auto and Search legs into one indistinguishable leg row
- Live WB HTTP reads on default export path
- `snapshot_data_updater` Redis namespace as settings source of truth for AI export
- Control-plane apply, registry mutation, or ChangeSet resolver on export path

## Examples

Хорошо:

- Export builds `CampaignSettingsSnapshotV1` from PG AdvSetting rows; auto and
  search legs nested; `wb_placement_search: null` with provenance `UNKNOWN`.
- Contract test asserts export payload type is not `CampaignResourceSnapshotV1`.

Плохо:

- `export_service` returns `resolver.resolve_changeset_snapshots()` dict for AI ZIP.
- Reusing `AdvSettingsSnapshotDTO.model_validate` for manifest payload rows.
- Single export row with `campaign_id = auto_id` silently absorbing search metrics/settings.

## Related specs

- `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md`
- Delta: `openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-exporter/spec.md`
- Canonical: `openspec/specs/grain-preservation`, `coverage-provenance`, `ai-package-v1-exporter`

## Related changes

- Archived: `openspec/changes/archive/2026-10-01-ai-package-v1-contract`
- Active overlap (implementation sequencing): WB Sky Control Plane A1 read layer

## Review checklist

- [x] Existing decisions searched (`ai-package-v1-exporter-ownership`, `shop-data-source-strategy`)
- [x] Relevant decisions cited by path
- [x] New decision proposed for seam not covered by exporter ownership alone
- [x] Implementation layer matches decision (`ai_package_v1` domain contract)
- [x] Tests must verify non-aliasing of A1 and Redis DTOs

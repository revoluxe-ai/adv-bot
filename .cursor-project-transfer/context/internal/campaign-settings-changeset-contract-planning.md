---
cursor:
  subagentId: "bc-e441fa59-fb59-5196-a454-454814dd2398"
---

# CAMPAIGN_SETTINGS_CHANGESET_CONTRACT_PLANNING_REPORT

BASELINE_SHA: `23c0671f372f0435b13a3573ec8990b4303b3e4a` (`origin/stage`, same as the confirmed baseline; not newer)

EXISTING_REUSABLE_COMPONENTS:

- `app/modules/campaign_settings_contract/registry.py` — `FieldPolicy`, `NormalizationPolicy`, `SemanticRole`, fail-closed registry
- `app/modules/campaign_settings_contract/canonical.py` — `normalize_value`
- `app/modules/campaign_settings_history/pg_reader.py` — `PostgresCampaignSettingsReader` (snapshot input only; not called by the pure validator)
- `app/modules/ai_package_v1/domain/settings_enums.py` — `CampaignLegRole` AUTO/SEARCH vocabulary
- `app/modules/ai_package_v1/domain/campaign_settings_snapshot_v1.py` — grain `(shop_id, adv_setting_id)` and separate legs; read-only, not the ChangeSet schema
- Excel import `apply_adv_excel_rows` is a production writer and is forbidden for this change
- Idempotency keys exist for card AB hold and auto-budget topup only; no settings ChangeSet store

POTENTIAL_OVERLAP_WITH_LOCAL_CONTROL_PLANE_WIP: YES

The archived AI snapshot design names `app/modules/wb_sky_control_plane/` as the future ChangeSet apply home. That package is absent on `origin/stage` and is the stated local WIP. This plan does not read or reconstruct that WIP. Placement for this increment is `campaign_settings_contract`, not that package.

OWNER_CONTRACT: READY

CHANGESET_V1_CONTRACT:

- `schema_version=changeset.v1`
- `changeset_id`, `shop_id`, source, actor, `created_at`, optional intent
- operations: `operation_id`, target (`source`, `adv_setting_id`, `leg_role` AUTO|SEARCH|ROW, child locator), `field`, `requested_value`, `expected_current_value`

MUTATION_POLICY_DESIGN:

Extension table beside the registry, not an Excel copy. Mutable only with an explicit entry: target scope, registry normalization, allowed domain, required capabilities (`settings_mutation`, `campaign_lifecycle`), precondition required. Unlisted and non-setting fields fail closed. Cross-field invariants stay in named domain validators.

VALIDATION_PIPELINE:

structural → identity → registry → normalization → domain → capability → precondition → diff. Unknown/unsupported = REJECTED.

DIFF_CONTRACT:

`NO_CHANGE` | `CHANGE` | `REJECTED`. Actionable change carries `field`, `old_value`, `requested_value`, `normalized_value`. No write.

ATOMICITY_DECISION: atomic. Mixed valid/invalid rejects the whole ChangeSet. No partial accept.

IDEMPOTENCY_SEMANTICS:

Duplicate `operation_id` or duplicate target+field inside one document → REJECTED. Same `changeset_id` with a different canonical hash, when a prior record is injected → REJECTED. Same id and hash → deterministic replay. No durable store in this change.

CONCURRENCY_PRECONDITION:

`expected_current_value` required and compared after normalization to an injected snapshot. Stale or missing snapshot → REJECTED. No distributed lock.

FAIL_CLOSED_RULES:

Unknown schema, field, source, campaign type, capability, omitted precondition, unimplemented declared invariant, and any read-only target → REJECTED for the whole set.

SCENARIO_PLAN:

`openspec/changes/campaign-settings-changeset-contract/scenario-coverage/plan.md` (18 scenarios). Receipt `plan.receipt.json`. PLAN_EVIDENCE_ID `495bd3ad403240413c2f26804814b941eb34d06c2b0db706aa36e102cea8cfee`.

OPEN_ARCHITECTURE_DECISIONS:

None that block this increment. A later change may re-home orchestration into `wb_sky_control_plane` after WIP reconciliation. That package is forbidden here.

OWNER_BLOCKERS:

None for planning. `docs/ai-control-loop-gap-report.md` is not on `origin/stage` (EVIDENCE_GAP for the path). The gap matrix used here is the one quoted in the task.

IMPLEMENTATION_READY_AFTER_LOCAL_WIP_RECONCILIATION: YES

Only if reconciliation finds no conflicting ChangeSet. Tasks 1.1–1.2 stop implementation when a conflict exists. Production code was not written in this task.

PRODUCTION_WRITES: NONE

PLANNING_READY: YES

---
cursor:
  subagentId: "bc-0ca53fc6-b480-59e2-a269-f41753335343"
---

# Task 4.2 — UI Advertising Control + Diagnostics

Read-only architecture packet. No production code, no OpenSpec edits, no PR.

Verified on `adv-bot` `HEAD` `a2e8453e773411eab989b08fa1358f2195c2dee4` (`stage` = `origin/stage`, merge of PR #473).

Ownership cited:

- `openspec/changes/hierarchical-ad-control-settings/design.md` — resolver and persistence in `app/modules/ad_control_settings/`; ChangeSet dry-run in `wb_sky_control_plane`; Apply unwired.
- `openspec/changes/hierarchical-ad-control-settings/decisions/hierarchical-ad-control-settings-ownership/decision.md` — campaign identity `(shop_id, advert_id)`; INHERIT must not copy shop values onto campaign rows; future UI is in scope of that module.
- `openspec/changes/hierarchical-ad-control-settings/owner-contract.md` — diagnostics UI uses the same resolver and performs no writes.
- `openspec/changes/hierarchical-ad-control-settings/decisions/ad-control-settings-persistence/decision.md` — `expected_revision=None` means the slot is absent.

Prior note `internal/architecture/hierarchical-ad-control-settings-slice-c-ui-design.md` is stale (baseline `065509c11`, price semantics recorded as not accepted). This packet supersedes it for task 4.2.

## START_STAGE

`a2e8453e773411eab989b08fa1358f2195c2dee4`

Slice A and Slice B are on this SHA: registry, resolver, DRR triple, headroom types, `AdControlDiagnosticsReportV1`, PG repository, `AdControlChangeSetV1`, `validate_ad_control_changeset`. Tasks 4.1 and 4.2 are unchecked one-liners in `tasks.md`. No Advertising Control screen exists.

## EXISTING_UI_STACK

Product UI is **Telegram / aiogram 3**.

- Entrypoint: `client_bot_run.py` → `dispatcher_factory.create_client_bot_dispatcher` → `global_router` → `common_routers.py`.
- FastAPI in that process is webhook, polling, and health. There is no Jinja/Vue settings app and no FastAPI settings router.
- Shop shell: `ShopMenu` / `ShopMenuState`, handlers under `app/client_bot/user_interface/handlers/`.
- Campaign list: `AdvCompanyChoicing` + `get_advs_keyboard_with_paginator` (`app/client_bot/user_interface/views/keyboards.py`). In-memory page size **20** (`messages.py` `on_page`). The handler loads every `AdvSetting` for the cabinet, then pages. Each render calls Redis `check_last_24_hours` per row.
- Campaign screen: `AdvSettingMenu` (`adv_setting_menu.py`). V3 controls already hang off this menu when `bot_active` and paid access: tick report, calibration FSM, rollout aggressiveness, sales-plan V3 Raise MAX, keyword diagnostics.
- Closest diagnostics pattern: `KeywordV3DecisionTraceScreen` (loader → formatter, access denial copy) and `v3_tick_report_ui` (read Redis, refresh).
- Permissions today: cabinet/adv ownership denials in `adv_setting.py`; feature gating via `UiAccessResolver` (FREE vs PAID); `is_bot_admin` / `IsBotAdminFilter` for admin traces. Seller settings are not admin-only.
- Validation copy is handler `message.answer` / `bot.send_message`, not a shared form-error component.
- HTTP campaign-table API: absent.

## REUSABLE_UI_PATTERNS

| Pattern | Where | Reuse for 4.2 |
|---|---|---|
| Shop shell | `ShopMenu` | Entry «Advertising Control» per cabinet/`shop_id` |
| Campaign identity list | `AdvCompanyChoicing`, page 20, label = name + `adv_id` | Page size and label-only name. Do not copy full-list reload or per-row Redis |
| Per-campaign menu | `AdvSettingMenu` | Drill-down after a table row, not the place that owns shop policy |
| V3 read-only trace | keyword decision trace, tick report | Diagnostics mode: load → domain call → format |
| Paid gate | `UiAccessResolver` | Same gate as other V3 controls |
| Cabinet denial | `adv_setting.py` ownership checks | Shop/campaign must belong to the Telegram user |

No existing screen binds `ad_control_settings`. Grep of `app/client_bot` for `ad_control` / `AdControl` is empty.

## SHOP_UI_READ_MODEL

UI renders `AdControlDiagnosticsReportV1` plus configured projection. It does not compute DRR, headroom, or CPO.

Source types:

- `ConfiguredShopFeatureState` — `project_configured_shop_features` (`configured_state.py`)
- `ResolvedFeaturePolicy` — `effective_features`
- `ConfiguredTargetDrr`, `ActualDrrObservation`, `ShopEffectiveControlDrr`, `ShopHeadroomState`
- `ProvenanceEntry` — `provenance_index`
- `decision: str`, `reason_codes: tuple[AdControlReasonCode, ...]`, `blockers: tuple[str, ...]`

| UI label | Domain field | Class |
|---|---|---|
| Feature + shop activation | `configured_shop_features[].feature_id`, `.activation` (`ENABLED`/`DISABLED`) | configured policy |
| Configured payload | `configured_shop_features[].payload` | configured policy |
| Effective policy | `effective_features[]` where `feature_id` matches: `active`, `payload` | effective configured |
| Provenance | matching `ProvenanceEntry.source_kind` + `source_scope` | provenance |
| Configured target DRR | `configured_target_drr.target_drr_percent` (and `max_drr_percent`) | resolved configured policy for `DRR_POLICY` |
| Effective target DRR | `shop_effective_control_drr.effective_control_drr_percent` | derived |
| Actual DRR | `actual_drr.actual_drr_percent` | observed. Not an input control |
| Measurement window | `actual_drr.measurement_window_id` | observed |
| Sufficiency | `actual_drr.data_sufficiency` (`DataSufficiency`) | observed |
| Freshness | **no timestamp field** | render `data_sufficiency` (`STALE` and the rest) plus `attribution_lag_days`. Do not invent a clock |
| Headroom | `shop_headroom.headroom_rub`, `control_pressure` | derived, shop-scoped |
| Status | `decision` | free string. Known builder values: `DIAGNOSTIC_READ_ONLY`, `BLOCKED`. Any other string is fail-closed display |
| Blockers | `blockers` | free strings from domain (`not_enrolled`, `legacy_passthrough`, …) |
| Reasons | `reason_codes` | `AdControlReasonCode` |

Shop has no `INHERIT`. Shop control is `ShopFeatureActivation` only.

`actual_drr` is an **input** to `AdControlDiagnosticsBuilder.build`. Nothing in this tree loads it. Task 4.1 must supply `ActualDrrObservation`. Until then the shop panel shows configured policy and provenance, and shows actual / effective-control DRR / headroom as missing facts, not as zeros.

## CAMPAIGN_UI_READ_MODEL

Authority key: `CampaignRef(shop_id, advert_id)` (`campaign_ref.py`). `AdvSetting.name` / `main_nmid` are labels from the existing campaign list, never keys.

`ResolverContext.campaign` is one campaign. `AdControlDiagnosticsBuilder.build` returns one report. A table is a composition of reports, not a new aggregate type.

Per feature (`FEATURE_REGISTRY` order), from `configured_campaign_overrides` + `effective_features`:

| UI column | Domain | Class |
|---|---|---|
| `advert_id` | `report.campaign.advert_id` | identity |
| Campaign label | existing `AdvSetting` name | display only |
| Feature | `AdControlFeatureId` | policy |
| Mode | `ConfiguredCampaignFeatureState.mode` ∈ `INHERIT` \| `OVERRIDE` \| `DISABLED` | configured. `INHERIT` means the feature key is absent from `campaign_features` (`project_configured_campaign_features` default) |
| Configured value | `override_payload` only when `mode == OVERRIDE`; otherwise empty | configured. Must stay empty on `INHERIT` even if shop payload exists |
| Effective value | `ResolvedFeaturePolicy.payload` + `active` | effective configured |
| Provenance | `ResolvedFeaturePolicy.provenance` (`EffectiveSourceKind`) | provenance. Shop inheritance shows `SHOP_POLICY` / `SHOP_DISABLED`, not a copied campaign payload |

Shop-level observed/derived fields repeated as context, not as per-campaign settings:

| UI column | Domain | Status on this SHA |
|---|---|---|
| Actual campaign DRR | none | **MISSING_DOMAIN_SYMBOL**. Report `actual_drr` is the shop observation passed into the builder |
| DIRECT attributed GMV | none | **MISSING_DOMAIN_SYMBOL** |
| DIRECT attributed orders | none | **MISSING_DOMAIN_SYMBOL** |
| Expected order value | none | **MISSING_DOMAIN_SYMBOL** |
| Current CPO | `current_max_cpo_rub` and `proposed_cpo.current_max_cpo_rub` | caller input, not computed |
| Target CPO proposal | `proposed_cpo.proposed_max_cpo_rub` | domain currently sets `None` and `decision="NO_PROPOSAL_PRICE_SEMANTICS_NOT_ACCEPTED"` (`diagnostics_builder.py`). UI prints that. It does not substitute a number |
| Campaign effective control DRR | `campaign_effective_control_drr` | derived copy of shop effective DRR when the builder fills it; `inherits_shop_control` is a flag |
| Freshness / sufficiency | same `ActualDrrObservation` as the shop | no per-campaign fact |
| Eligibility | `CampaignHeadroomEligibility` | computed inside the builder and **folded into** `reason_codes` / `blockers`. Not a separate report field. UI reads those codes (`NOT_ENROLLED_FAIL_CLOSED`, `LEGACY_PASSTHROUGH_ACTIVE`, stale/insufficient codes) |
| Blockers / reasons | report `blockers`, `reason_codes` | domain |

Capabilities: no ad-control capability model. Do not bind `CampaignCapabilitiesV1` (`wb_sky_control_plane` A1 budget/bid) to this screen.

## DIAGNOSTICS_READ_MODEL

Diagnostics / Test mode is read-only and calls the production pure functions:

1. `load_resolver_shop_features` / `load_resolver_campaign_features` (`context_loader.py`) → `ResolverContext`.
2. `AdControlDiagnosticsBuilder.build(context, actual_drr, *, current_max_cpo_rub, allowed_spend_rub, spend_rub, dry_run_diff_available)` → `AdControlDiagnosticsReportV1`.
3. Optional preview only: `validate_ad_control_changeset(...)` → `AdControlValidationResult`.

The report flag `dry_run_diff_available` is a boolean the caller sets. The diff itself is **not** inside the report. Diff rows are `AdControlSemanticDiffV1`: `target_key`, `intent` (`AdControlMutationKind`), `field_path`, `current`, `desired`, `effective_source_after`.

Show, and only from those objects:

- configured policy (`configured_shop_features`, `configured_campaign_overrides`)
- effective policy (`effective_features`, `configured_target_drr`, `shop_effective_control_drr`, `campaign_effective_control_drr`)
- provenance (`provenance_index` / `ResolvedFeaturePolicy.provenance`)
- actual DRR, measurement window, sufficiency (`actual_drr`)
- shop headroom (`shop_headroom`)
- eligibility as reason codes and blockers already merged by the builder
- current CPO (`current_max_cpo_rub`)
- target CPO proposal (`proposed_cpo`, including a null proposal and its reason)
- `decision`, `reason_codes`, `blockers`
- dry-run diff (`AdControlValidationResult.diffs`) when a preview ChangeSet was validated

Edit controls are disabled while diagnostics mode is on. No second formula, no UI-side headroom math, no reinterpretation of `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`.

Stale / insufficient / unknown measurement is already fail-closed in `control_action_allowed` (`headroom_eval.py`): `DataSufficiency.STALE|INSUFFICIENT|UNSUPPORTED|UNKNOWN` appends `ACTUAL_DRR_*` or `MEASUREMENT_UNKNOWN` plus `NO_CONTROL_ACTION_STALE_OR_UNKNOWN`. UI displays those codes.

Missing `actual_drr` (4.1 not wired): builder skips headroom, effective control DRR, eligibility, and proposal (`diagnostics_builder.py` only derives them when both `configured_target` and `actual_drr` are present). UI shows «runtime facts absent» from that empty report. It does not fabricate sufficiency.

## WRITE_FLOW

Future committed writes:

```text
UI intent
→ AdControlChangeSetV1
→ validate_ad_control_changeset (deterministic)
→ AdControlValidationResult diff
→ future Apply Authority
→ AdControlSettingsRepository mutation
```

Ops (`ad_control_changeset.py`):

- `shop.set_ad_control_feature` → `SetShopAdControlFeatureOperation`
- `campaign.set_ad_control_override` → `SetCampaignAdControlOverrideOperation`
- `campaign.disable_ad_control_feature` → `DisableCampaignAdControlFeatureOperation`
- `campaign.clear_ad_control_feature` → `ClearCampaignAdControlFeatureOperation`

Each op carries `AdControlRevisionPreconditionV1.expected_revision`. `state_token` is a fingerprint on the row (`acs_` prefix). It is **not** the CAS precondition (`spec.md`).

**What 4.2 can implement without Apply**

- Read-only shop panel and campaign policy table.
- Diagnostics mode bound to the builder.
- In-memory ChangeSet + `validate_ad_control_changeset` as a preview, only after a revision-preserving snapshot read exists (see blockers). Preview must not call `upsert_*` or `clear_campaign_feature`.

**What 4.2 must not implement**

- Repository writes, Apply wiring, WB mutations, bulk ops, copying shop payloads into campaign overrides.

`load_shop_slots` / `load_campaign_slots` return `ShopFeatureSlot` / `CampaignFeatureSlot` and **drop** `revision` and `state_token`. Rows have both (`persistence/models.py`). Dry-run snapshots `AdControlShopFeatureSnapshotV1` / `AdControlCampaignFeatureSnapshotV1` exist only as validator inputs. No production mapper from rows to snapshots. A preview path needs a read adapter that copies row fields into those snapshots and then calls `validate_ad_control_changeset`. That adapter is mapping, not a second validator.

Revision conflict UX, when preview is built:

- `ControlPlaneError.code == "REVISION_CONFLICT"`.
- `details` carry `expected` / `actual` (or absent-vs-present messages in `ad_control_validate.py`).
- UI shows expected vs actual, refuses confirm, reloads snapshots.
- Unknown `DryRunStatus` or unknown error code: fail closed, no confirm.
- Do not CAS on `state_token`. Do not silent-retry.

## RETURN_TO_INHERIT_FLOW

User action «return to inheritance» on one campaign feature:

1. UI intent is clear-authority, not «set campaign value = shop value».
2. Build `ClearCampaignAdControlFeatureOperation` (`op=campaign.clear_ad_control_feature`) with `expected_revision` equal to the campaign row revision when the row exists, or `None` when it is already absent.
3. Dry-run (`_validate_campaign_clear`): existing row → `intent=CLEAR_TO_INHERIT`, `desired="absent"`, `effective_source_after="SHOP_POLICY_OR_INHERIT"`. Already absent → `NO_OP`.
4. Future Apply calls `AdControlSettingsRepository.clear_campaign_feature`, which **DELETEs** the campaign row and bumps the slot ledger. Result revision and state token are `None`.
5. After a successful clear, configured mode is `INHERIT`, `override_payload` is empty, effective value and provenance come from the shop policy on the next resolve.

Forbidden: `campaign.set_ad_control_override` populated with the shop payload.

## PAGINATION_MODEL

- Page size **20**, matching `get_advs_keyboard_with_paginator`.
- Stable order: see sort below, then `advert_id` ascending.
- One shop-slot read per page view. Campaign slots for the **page** (or one shop-scoped batch read — required, not present) then one `build()` per visible campaign.
- Do not load every campaign's diagnostics to paint page 1.
- Do not call Redis `check_last_24_hours` or WB status per row on this screen.
- FSM holds `shop_id`, page, filter, sort, selected `advert_id`. Do not put revision integers into callback data if they blow Telegram's 64-byte limit; keep them in FSM keyed by `(advert_id, feature_id)`.
- Max campaigns per shop: unknown in repo. WB list paging uses 100, so shops above 100 must be assumed.

## FILTER_MODEL

Filters are predicates over domain fields. They are not new statuses.

| Filter | Predicate |
|---|---|
| overridden | selected feature `ConfiguredCampaignFeatureState.mode == OVERRIDE` (or any feature, if the filter is shop-wide) |
| disabled | campaign `mode == DISABLED`. Shop `ShopFeatureActivation.DISABLED` is a shop banner (`FEATURE_DISABLED_AT_SHOP`), not a campaign-mode filter |
| inherited | `mode == INHERIT` (no campaign row) |
| blocked | `decision == "BLOCKED"` or `blockers` non-empty. Unknown `decision` values are treated as blocked |
| actionable | UI predicate only: `enrollment == ENROLLED` and `control_path == HIERARCHICAL` and not blocked and feature supports `CAMPAIGN`. `NOT_ENROLLED` and `LEGACY_PASSTHROUGH` are not actionable. No domain enum named actionable |

Sort:

1. Blocked first (`decision == "BLOCKED"` or non-empty `blockers`).
2. Headroom / proposal only where the value is per campaign and non-null. Shop `headroom_rub` is one number for the shop — do not sort campaigns by it. `proposed_max_cpo_rub` is null in the current builder, so this key is a no-op until the domain fills it.
3. `advert_id` ascending as the stable identity sort.

No bulk-write control in V1. Do not copy `turn_adv_off_all`, `apply_defaults_for_shop`, or shop-wide phrase reset.

## RUNTIME_4_1_DEPENDENCIES

Task text in tree is only: `4.1 Runtime shop-runner integration` (unchecked). No shop-runner import of `ad_control_settings` exists.

UI cannot show these until 4.1 (or an explicit read port with the same types) supplies them:

- `ActualDrrObservation` for the shop (builder input)
- `allowed_spend_rub`, `spend_rub` (headroom inputs)
- `current_max_cpo_rub` if «current CPO» is shown
- campaign actual DRR, DIRECT GMV, DIRECT orders, expected order value — **types do not exist**; 4.1 must add them in the domain before the table columns are real
- a real `BoundedCpoProposal.proposed_max_cpo_rub` if the builder stops hard-blocking CPO

UI reads those results. It does not query ClickHouse itself and does not define sufficiency.

## SLICE_B_DEPENDENCIES

Already on this SHA and required by the screen:

- `AdControlFeatureId`, `AdControlFeatureMode`, `ShopFeatureActivation`, `EffectiveSourceKind`, `DataSufficiency`, `AdControlReasonCode`
- `AdControlSettingsRepository.load_shop_slots`, `load_campaign_slots`
- `AdControlChangeSetV1` and `validate_ad_control_changeset`
- `clear_campaign_feature` semantics (for the return-to-inherit story; not called by a read-only 4.2)
- CAS errors `REVISION_CONFLICT` / `RevisionConflictError`
- Fail-closed: unknown `feature_id` rejected by the enum; dry-run code `UNKNOWN_FEATURE`; resolver `AdControlReasonCode.UNKNOWN_FEATURE`, `UNSUPPORTED_SCOPE_FOR_FEATURE`, `NOT_ENROLLED_FAIL_CLOSED`

Not on this SHA:

- Apply Authority for these ops
- Batch `load_campaign_slots` by `shop_id`
- Loader that returns `revision` / `state_token`
- Production row → `AdControl*SnapshotV1` mapper

## NEW_UI_SERVICE_REQUIRED

**YES.** A read composer under `app/modules/ad_control_settings/` (placement follows the ownership decision; not inside aiogram handlers).

Responsibilities:

- build `ResolverContext` from repository reads
- call `AdControlDiagnosticsBuilder.build` once per campaign in the page
- project view rows (mode, configured payload, effective payload, provenance, decision, codes)
- optionally map rows that still carry `revision` into validator snapshots and call `validate_ad_control_changeset`

Handlers format Telegram text and keyboards only.

Also required before a large table or an honest dry-run preview:

- shop-scoped campaign slot read (one query)
- revision-preserving read (current loaders drop revision)

Those are read methods on the existing repository, not new persistence rules.

## NEW_API/ROUTE_REQUIRED

**YES, as Telegram callbacks and FSM states. No new HTTP route.**

- Entry on `ShopMenu`: Advertising Control.
- States: section root, feature drill-down, campaign page, diagnostics toggle.
- Register on the existing client-bot router next to other shop handlers.

There is no web admin to extend.

## WHY

The domain module has no Telegram adapter. `AdvSettingMenu` is per-campaign legacy settings and cannot show shop policy plus a campaign authority table without mixing write paths. Diagnostics must call `AdControlDiagnosticsBuilder` and `validate_ad_control_changeset`, which handlers must not reimplement. A composer keeps PG and resolver calls out of the UI layer so tests can prove the UI does not write.

## DIRECT_DB_WRITE_ALLOWED

**NO**

## SECOND_CALCULATION_ENGINE_ALLOWED

**NO**

## TEST_PLAN

Unit tests only (mocks, no DB), under `tests/unit/`. Formatter/composer tests take domain objects in and assert view models out. Handler tests mock the composer and assert it is the only domain call.

**CRITICAL**

- Return to inherit builds `ClearCampaignAdControlFeatureOperation` and expects dry-run `CLEAR_TO_INHERIT` / `desired=absent`. It never builds an override whose payload equals the shop payload.
- Configured vs effective: `INHERIT` shows empty configured value and effective value from `ResolvedFeaturePolicy` with `source_kind=SHOP_POLICY`.
- `OVERRIDE` shows `override_payload` as configured and provenance `CAMPAIGN_OVERRIDE`.
- `DISABLED` shows mode `DISABLED` and provenance `CAMPAIGN_DISABLED` (shop disabled stays a shop activation, code `FEATURE_DISABLED_AT_SHOP`).
- Actual DRR is rendered from `ActualDrrObservation` and is not present on any ChangeSet op.
- Unknown `decision`, unknown `feature_id`, unknown `DryRunStatus`: fail closed, actions hidden.
- `NOT_ENROLLED` / `LEGACY_PASSTHROUGH`: blocked, not actionable.
- Composer tests: repository mutation methods (`upsert`, `clear_campaign_feature`) are not called on read or diagnostics paths.
- Revision conflict preview surfaces `REVISION_CONFLICT` expected vs actual and does not confirm.

**HIGH**

- Provenance labels for `SHOP_POLICY`, `SHOP_DISABLED`, `CAMPAIGN_OVERRIDE`, `CAMPAIGN_DISABLED`.
- Stale / insufficient / unknown: `ACTUAL_DRR_STALE`, `ACTUAL_DRR_INSUFFICIENT`, `MEASUREMENT_UNKNOWN`, `NO_CONTROL_ACTION_STALE_OR_UNKNOWN` render as blocked diagnostics.
- Missing `actual_drr`: headroom, effective control DRR, and proposal render as absent, not zero.
- Unsupported scope: `UNSUPPORTED_SCOPE_FOR_FEATURE` visible, no edit.
- Diagnostics mode issues no ChangeSet.
- Preview ChangeSet, when enabled, is passed only to `validate_ad_control_changeset`.

**MEDIUM**

- Filter predicates: overridden, disabled, inherited, blocked, actionable (actionable false when not enrolled).
- Sort: blocked first, then `advert_id`. Proposal sort stays inactive while `proposed_max_cpo_rub is None`.
- Page of 20 does not request slots for campaigns outside the page.
- Label `AdvSetting.name` is not used as `advert_id`.
- Shop panel has no INHERIT control (`ENABLED`/`DISABLED` only).

**LOW**

- Paid-access gate matches `UiAccessResolver` (deny copy, no composer call).
- Cabinet ownership denial matches existing shop/adv denial, no composer call.
- `state_token` may be shown as a fingerprint and is absent from preconditions.
- Empty shop (no campaign rows): five features render as `INHERIT` / shop defaults.

## FILES_LIKELY_TO_CHANGE_IN_4_2

When implementation is authorized (not in this chat):

- `app/client_bot/user_interface/handlers/` — new Advertising Control handlers
- `app/client_bot/user_interface/states.py` — FSM
- `app/client_bot/user_interface/views/messages/` and keyboards — section text
- client-bot router registration (`common_routers` or the shop router that already includes `ShopMenu`)
- `app/modules/ad_control_settings/` — new read composer module
- `app/modules/ad_control_settings/persistence/repository.py` — shop-scoped campaign read and revision-preserving read only
- `tests/unit/ad_control_settings/` and `tests/unit/client_bot/` — composer and handler tests

Do not change `diagnostics_builder.py` formulas, `headroom_eval.py`, or Apply wiring as part of painting the screen. If target CPO must become numeric, that is a domain change owned by 4.1 / price semantics, not by the UI.

## IMPLEMENTATION_READY

**PARTIAL.**

Ready to specify and, in a later implementation chat, build:

- Telegram section Advertising Control on the shop shell
- shop feature panel from configured + effective + provenance
- campaign table of mode / configured / effective / provenance / blockers / reasons
- diagnostics mode on `AdControlDiagnosticsBuilder`
- fail-closed unknown state
- return-to-inherit as a clear op in preview only

Not ready to build as if the data existed:

- campaign actual DRR, DIRECT GMV, DIRECT orders, expected order value
- a numeric target CPO (builder forces null + price-semantics block)
- persisted writes / Apply
- honest dry-run revision checks until a revision-preserving snapshot read exists
- a large-shop table until a shop-scoped campaign slot read exists

## BLOCKERS

1. **4.1 facts absent.** No loader for `ActualDrrObservation`, spend, or campaign economics. Those columns stay empty rather than UI-computed.
2. **CPO proposal hard-blocked in the builder** (`proposed_max_cpo_rub=None`, `NO_PROPOSAL_PRICE_SEMANTICS_NOT_ACCEPTED`) even though `owner-contract.md` records V1 order-value price semantics as accepted. UI must show the builder result. A numeric proposal waits on a domain change.
3. **Revision stripped by current loaders.** Dry-run CAS preview is not honest until reads return `revision`.
4. **No shop-wide campaign slot query.** Per-campaign `load_campaign_slots` will N+1 on real cabinets.
5. **Apply unwired.** 4.2 must not commit settings.
6. **Report is single-campaign.** Table composition is allowed; a second calculator is not.
7. **`decision` and `blockers` are untyped strings.** Unknown values fail closed in the UI.

## CRITICAL

See test plan CRITICAL, plus blockers 1–5. The semantic critical path is: INHERIT is absence of a campaign row; actual DRR is observed; UI never writes PG.

## HIGH

Provenance must be visible next to configured and effective. Stale facts block action display. Diagnostics and production proposal share `AdControlDiagnosticsBuilder`.

## MEDIUM

Pagination 20, filters as predicates, no bulk write, display name is not identity.

## LOW

Admin-trace patterns (`is_bot_admin`) are the wrong gate for this seller screen. Token display is optional.

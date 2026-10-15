---
cursor:
  subagentId: "bc-f86c56e2-5c73-54eb-8244-0e98437f0cf7"
---

# WAVE 1D — Scale / UX analyst (task 4.2 UI Advertising Control)

**Repo:** `/agent/repos/adv-bot` (read-only)  
**OpenSpec:** `openspec/changes/hierarchical-ad-control-settings`  
**Scope:** Facts constraining future campaign-list UX at scale (no product policy invented).

---

## OpenSpec quotes (UI / diagnostics / 4.2 only)

`design.md` does **not** describe UI tables, pagination, or scale; it ends at Slice A/B domain + persistence + dry-run.

`tasks.md`:

- `- [ ] 4.2 UI Advertising Control + Diagnostics`

`owner-contract.md`:

- **Campaign identity:** «Authority: `(shop_id, advert_id)`. `main_nmid` is not campaign authority.»
- **Diagnostics:** «Mandatory future UI: Advertising Control + Diagnostics/Test using same resolver; no writes.»
- **Persistence:** «CAS `revision` + `expected_revision` preconditions; … Campaign INHERIT = no campaign row (`campaign.clear_ad_control_feature`).»

`proposal.md` (historical slice note): «UI / Excel / API / MCP transport» listed out of scope for foundation slice; task 4.2 is explicitly future work in `tasks.md`.

`specs/hierarchical-ad-control-settings/spec.md`:

- «runtime shop-runner and **UI remain out of scope**» (purpose).
- Ad control ChangeSet: «Concurrency authority MUST be `expected_revision` only; `state_token` MUST remain a semantic fingerprint … MUST NOT be a second CAS precondition.»
- Dry-run scenarios: stale / absent / mismatched `expected_revision` → `REJECTED` with `REVISION_CONFLICT`.

---

## PAGINATION FACTS (existing constants and APIs)

### Telegram campaign picker (primary “campaign list” today)

| Fact | Location |
|------|----------|
| **Full cabinet load, no SQL LIMIT** | `_load_adv_settings_for_wb_user_cabinet_in_session` / `_load_adv_settings_for_cabinet` — `select(AdvSetting)` joined to cabinet; `start.py` orders by `AdvSetting.name`; `adv_setting.py` has no `order_by` | `app/client_bot/user_interface/handlers/start/start.py` L388–400; `adv_setting.py` L259–271 |
| **UI page size = 20** | `AdvCompanyChoicing.on_page` → `get_advs_keyboard_with_paginator(..., on_page)` | `messages.py` L408–410; `keyboards.py` L265–292 |
| **Pagination callback** | `ChoiceAdvPaginator` — reloads full list each page | `adv_setting.py` L462–486; `callbacks.py` (`ChoiceAdvPaginator`) |
| **In-memory filter** | FSM `filter_advs` — substring match on name, nmids, `adv_id`; excludes some inactive DONE+bot_off | `messages.py` L363–386 |
| **In-memory sort** | Active (`active_status` + `bot_active`) before inactive; keyboard re-sorts `bot_active` first | `messages.py` L334–342; `keyboards.py` L276–287 |
| **Auction-leg filter** | Keyboard drops rows where `auction_adv_id is None` | `keyboards.py` L272–274 |
| **Per-row Redis on render** | `check_last_24_hours(adv.id)` loop for **every** campaign before paginating slice | `messages.py` L358–359 |

### Other list page sizes (patterns, not campaign control)

| Constant | Value | Path |
|----------|-------|------|
| `SHOPS_PER_PAGE` | 20 | `shop_choice_message.py` L31 |
| `_PARTNER_LIST_PAGE_SIZE` | 8 | `admin_panel.py` L49 |
| Keyword campaign UI `_on_page` | 24 | `adv_keyword_messages.py` (via grep) |
| `TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE` | 10 | `bid_units.py` |
| Card A/B confirm `PAGE_SIZE` | 10 | `confirm_pagination.py` L11 |

### WB API listing (connect / sync paths, not ad-control UI)

| API | Page / chunk | Path |
|-----|----------------|------|
| `GET /adv/v1/adverts` cabinet list | `PAGE_SIZE = 100`, offset loop | `cabinet_adverts_list/adapter.py` L35–61 |
| `GET /api/advert/v2/adverts` by ids | Chunks of **50**, 0.25s between chunks | `campaigns_info_v2/adapter.py` L32–66 |

### HTTP “campaign list” endpoints

**UNKNOWN / ABSENT** for a dedicated REST campaign table: user settings are Telegram-first (`client_bot`); no `APIRouter` campaign list found under typical `app/**/api` patterns for adv settings.

### Ad control persistence reads

- `load_campaign_slots(campaign)` — **per `(shop_id, advert_id)`**, all feature rows for one campaign only (`repository.py` L135–160).
- **No** `load_all_campaign_slots_for_shop(shop_id)` API in codebase.

---

## IDENTITY MODEL

| Layer | Identity | Display / join fields |
|-------|----------|------------------------|
| **Ad control authority** | `(shop_id, advert_id)` — `CampaignRef`; `main_nmid` explicitly **not** authority | `campaign_ref.py` L8–23; `owner-contract.md`; `AdControlCampaignFeatureRow` unique `(shop_id, advert_id, feature_id)` — `models.py` L76–108 |
| **Telegram / PG `AdvSetting`** | Internal PK `AdvSetting.id` (`adv_original_id` in callbacks); WB id `adv_id` (unique, nullable in model); human `name`, `active_status`, `bot_active`, `nmids`, `auction_adv_id` | `models.py` L421–479; keyboard shows `name`, `adv_id`, status — `keyboards.py` L297–303 |
| **ChangeSet resource** | `AdvertCampaignRefV1(shop_id, advert_id)` | `ad_control_changeset.py` + validate tests |

UI list rows will almost certainly **join** `AdvSetting` (name, status, bot) with `CampaignRef(shop_id, adv_id)` for ad-control state.

---

## FILTER / SORT FEASIBILITY (domain fields today)

Future filters (product concepts) vs **computable without new semantics**:

| Filter | Feasible from existing fields? | Basis |
|--------|--------------------------------|--------|
| **overridden** | **Yes** (per feature or rollup) | `AdControlFeatureMode.OVERRIDE` on campaign slot; `EffectiveSourceKind.CAMPAIGN_OVERRIDE` in `ResolvedFeaturePolicy.provenance` (`resolver.py` L95–113) |
| **disabled** | **Yes** | Campaign `DISABLED` → `CAMPAIGN_DISABLED`; shop `ShopFeatureActivation.DISABLED` → `SHOP_DISABLED` / reason codes `FEATURE_DISABLED_AT_*` (`enums.py`, `resolver.py`) |
| **inherited** | **Yes** | Campaign slot default / `INHERIT`; effective from shop/product tiers (`resolver.py` L115+); configured projection uses INHERIT without copied payload (`configured_state.py` L80–99) |
| **blocked** | **Yes** | `AdControlDiagnosticsReportV1.blockers`, `decision == "BLOCKED"` (`diagnostics_builder.py` L172–174); `ResolverBlocked.blockers`; `campaign_headroom_eligibility` blocker strings (`headroom_eval.py` L104–138) |
| **actionable** | **Partial** | Dry-run: diffs with `intent != NO_OP` (`ad_control_validate.py` L184–185). Diagnostics: `control_action_allowed(actual_drr)` + eligibility — **not** a single list-column enum yet; **no** shop-wide “actionable” aggregate API |

Sort concepts:

| Sort | Feasible? | Notes |
|------|-----------|--------|
| **blocked first** | **Yes** | Sort key from non-empty `blockers` / `decision == "BLOCKED"` / priority on `NOT_ENROLLED_FAIL_CLOSED`, `NO_CONTROL_ACTION_*`, etc. |
| **headroom / proposal** | **Partial** | `ShopHeadroomState`, `BoundedCpoProposal` exist **per diagnostic report** (`diagnostics.py`); production ranking formula **not accepted** (`owner-contract.md` Headroom allocation); proposal often `NO_PROPOSAL_PRICE_SEMANTICS_NOT_ACCEPTED` in builder |
| **advert_id / name** | **Yes** | `CampaignRef.advert_id`; `AdvSetting.name` / `adv_id` for display sort (existing list uses name order in `start.py`) |

**Gap:** `ActualDrrObservation` is only constructed in **unit tests** today — no production loader for per-campaign actual DRR at list time (`grep ActualDrrObservation(` → tests only). List-level “blocked/stale DRR” sort/filter needs a **batch facts** source (Slice 4.1 / unknown reader) — **UNKNOWN** wiring.

---

## UX RISKS (concrete, code-tied)

1. **Unbounded PG load + in-memory pagination** — Every campaign page turn re-fetches all `AdvSetting` rows (`adv_setting.py` L480–483) and `AdvCompanyChoicing` may Redis-hit **all** campaigns (L358–359). Scales poorly for “many campaigns.”
2. **Hidden campaigns in picker** — `auction_adv_id is None` rows never appear in keyboard (`keyboards.py` L272–274); ad-control list must decide whether authority legs match this filter or show all PG rows.
3. **Dual ID confusion** — Callbacks use `adv_original_id` (PG id); authority uses `advert_id` / `adv_id`. Mis-link breaks CAS writes.
4. **No shop-scoped ad-control row loader** — N× `load_campaign_slots` or N× snapshot assembly if UI builds diagnostics per row without new batch SQL.
5. **Bulk write precedents without owner check** — `turn_adv_off_all` checks `_load_wb_user_cabinet_for_owner_in_session` (good); `apply_defaults_for_shop` and `reset_shop_non_relevant_phrases` mutate by `wb_user_cabinet_original_id` only (**no** `user_telegram_id` check in handler) — `adv_setting.py` L976–1006, L1024–1047. **Do not copy** for ad-control bulk apply.
6. **WB per-campaign status loop** — `_sync_adv_status_from_wb` calls `get_campaign_status` per id (`connect_existing_advs.py` L134–135) — anti-pattern for large N; prefer batched `get_adverts_v2_by_ids` (chunk 50).
7. **Read-only token gate** — Paid bot writes blocked when shop has only read-only tokens (`turn_adv_on_in_session` L210–215); ad-control writes should align with same token policy when Apply is wired.
8. **Enrollment fail-closed** — Default hierarchical UX shows blocked diagnostics until enrollment is explicit (`NOT_ENROLLED_FAIL_CLOSED`).
9. **No ad-control UI yet** — Misleading to reuse V3 tick report/keyboards as canonical; task 4.2 is empty in code.

---

## PERFORMANCE REQUIREMENTS

| Must batch | Evidence |
|------------|----------|
| PG ad-control campaign rows for shop | Only per-campaign queries exist; for N campaigns need `WHERE shop_id = ?` (not implemented) or join from `AdvSetting` |
| WB advert metadata | `get_campaigns_info` / `get_adverts_v2_by_ids` already chunk **50** (`campaigns_info_v2/adapter.py`) |
| Cabinet advert id discovery | WB v1 list pages **100** (`cabinet_adverts_list/adapter.py`) |
| Redis `check_last_24_hours` | Today **N sequential** calls in `AdvCompanyChoicing` — should not replicate for diagnostics list |

| Must not N+1 | |
|--------------|--|
| `load_campaign_slots` per campaign on each list page | |
| `get_campaign_status` per row | `connect_existing_advs.py` |
| Full reload of all `AdvSetting` on every paginator callback | `choice_adv_paginator` |

**Page size recommendation (grounded):** **20** matches `AdvCompanyChoicing.on_page` and `SHOPS_PER_PAGE`; Telegram inline keyboards also strain with large button counts. Admin partner list uses **8** for denser rows — optional for “diagnostics-heavy” rows. **No** documented max campaign count in repo configs/tests for production cabinets — **UNKNOWN** upper bound; WB list adapter implies cabinets can exceed **100** WB-side ids.

**Actual DRR / ClickHouse:** No production `ActualDrrObservation` builder found — **UNKNOWN** whether list diagnostics would hit ClickHouse per campaign; Slice A diagnostics are **pure** (`diagnostics_builder.py` — no I/O).

---

## BULK WRITE

**Confirm:** V1 ad-control UI should **not** add unsafe bulk-write (per assignment). Owner contract diagnostics path is **no writes**.

**Existing bulk patterns to avoid copying:**

| Pattern | Write path | Risk |
|---------|------------|------|
| `turn_adv_off_all` | ORM loop all `AdvSetting`, commit | Mass `bot_active`/mode side effects; mitigated by owner check |
| `apply_defaults_for_shop` | All `bot_active` campaigns, ORM defaults | No telegram owner check in handler |
| `reset_shop_non_relevant_phrases` | SQL mass keyword updates via `update_keywords` | No telegram owner check |
| `AdControlChangeSetV1` multi-op | Dry-run only; rejects duplicate slot in one changeset (`DUPLICATE_TARGET`) | Future UI must not “bulk apply” multiple campaigns without Apply Authority + per-slot CAS |
| Campaign settings Apply (`ChangeSetV1`) | `apply_plan_to_adv_settings` via WB Sky Apply | Uses `state_token` STALE_STATE — **different** contract from ad-control `expected_revision` |

Ad-control mutations are **one slot per operation** with `expected_revision` CAS (`repository.py` module docstring L1–11; `AdControlRevisionPreconditionV1`).

---

## State token / revision conflict (what UI would show)

### Ad control (`AdControlChangeSetV1` / persistence)

- **CAS authority:** `expected_revision` only (`spec.md`; `AdControlRevisionPreconditionV1` — `ad_control_changeset.py` L67–84).
- **Dry-run rejection:** `ControlPlaneError` code **`REVISION_CONFLICT`** with messages e.g. «stale revision precondition», details `expected` / `actual` (`ad_control_validate.py` L276–309).
- **Repository apply (future):** `RevisionConflictError` strings e.g. «stale campaign revision», «shop row absent but revision expected» (`repository.py` L198–261, L387).
- **`state_token`:** Content fingerprint for audit/display; `compute_ad_control_state_token` includes revision in canonical JSON (`state_token.py` L10–18) — **not** second CAS precondition per spec.

**UI implication:** On conflict, show **stale revision** (reload snapshots, refresh `expected_revision` per feature slot). No `STATE_TOKEN_STALE` on ad-control changeset model (no `state_token` in preconditions).

### Campaign settings Apply (related WB Sky, not ad-control)

- Dry-run: `STATE_TOKEN_STALE` / `STATE_TOKEN_MISSING` (`test_changeset_dry_run.py` L196–204).
- Apply: `ApplyReasonCode.STALE_STATE` → receipt `INVALIDATED` (`apply_authority_service.py` L82–85; `openspec/specs/changeset-apply-authority/spec.md`).

---

## Typical / max campaign counts

| Source | Finding |
|--------|---------|
| Repo configs / comments | **UNKNOWN** explicit max campaigns per shop for UI |
| Tests | `test_apply_defaults_for_shop_multiple_campaigns` — small fixture (few campaigns), not scale test |
| WB cabinet list | Paginates at **100** — implies **>100** ids possible on WB |
| PG queries | No LIMIT — list size = all `AdvSetting` for cabinet |

---

## Existing filter/sort helpers (reuse)

| Helper | Use |
|--------|-----|
| `get_advs_keyboard_with_paginator` + FSM `filter_advs` | Campaign substring filter + page slice |
| `admin_panel._apply_partner_filter` / `_apply_partner_sort` / `_slice_partner_rows` | Redis-backed admin list state pattern (`admin_panel.py` L551–573) |
| `confirm_pagination.paginate` | Generic in-memory page slice (size 10) |
| `AdControlSettingsResolver` + `AdControlDiagnosticsBuilder` | Per-campaign diagnostic semantics (not list) |

---

## Permission / role checks (settings writes)

| Check | Where |
|-------|--------|
| Cabinet owner | `_load_wb_user_cabinet_for_owner_in_session` — `User.user_telegram_id` (`adv_setting.py` L335–352) |
| Adv belongs to cabinet | `_load_adv_for_owner_cabinet_in_session` |
| Read-only WB token | `_shop_has_read_only_only_tokens` blocks bot on (`L210–215`) |
| Admin impersonation | `get_shop_for_admin.py` — `const.ADMINS`, shop UUID / adv_id lookup |
| Admin panel | `IsBotAdminFilter()` on partner/payout flows (`admin_panel.py`) |
| Ad control Apply | **Unwired** in Slice B — no Telegram handler yet |

---

*End WAVE 1D report.*

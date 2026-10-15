---
cursor:
  subagentId: "bc-abb663b6-db62-5a4f-87c6-a888f1c03dc5"
---

# Campaign list scale / UX archaeology (Advertising Control context)

Repo: `/agent/repos/adv-bot`. READ ONLY. Thoroughness: medium.

## CURRENT_LIST_MECHANISM

### Production campaign picker (Telegram — today’s “settings UI” entry)

| Step | Mechanism | Paths |
|------|-----------|--------|
| Entry | Shop menu → «Автоматические рекламные кампании» (`ChoiceAdvPaginator`, `page=1`) | `app/modules/shop_menu/message.py`, `app/client_bot/user_interface/handlers/start/start.py` (`select_shop` @ `ChoiceAdvPaginator`) |
| Load | **All-at-once** PG: `select(AdvSetting)` joined to `WBUserCabinet`, **no `LIMIT`/`OFFSET`** | `_load_adv_settings_for_wb_user_cabinet_in_session` (`start.py` ~388–400), duplicate `_load_adv_settings_for_cabinet` (`adv_setting/adv_setting.py` ~259–271) |
| Render | `AdvCompanyChoicing` → sort/filter in Python → `get_advs_keyboard_with_paginator` slices list | `app/client_bot/user_interface/views/messages/messages.py` (`AdvCompanyChoicing`, `on_page = 20`), `app/client_bot/user_interface/views/keyboards.py` (`get_advs_keyboard_with_paginator`) |
| Pagination | **Offset by page number** in callback: `start_index = (page - 1) * on_page`, `on_page = 20` | `ChoiceAdvPaginator` (`callbacks.py`), keyboard prev/next (`keyboards.py` ~313–340) |
| Redis | **Per-campaign** `check_last_24_hours(adv.id)` in loop before keyboard build | `messages.py` ~358–359, `app/utils/redis_manager/__init__.py` ~104–114 |
| ClickHouse | **Not used** for campaign list | — |
| WB API | Not on list open; optional «Полностью обновить мета-данные от WB» runs `ShopDataUpdater.update_advs_data()` (batched `get_advs(adv_ids)` for IDs already in PG) | `start.py` `update_company_from_wb` ~1297+, `shops_data_updater.py` `update_advs_data` ~128–154 |

**Pagination is presentation-only:** every page change re-fetches the full `AdvSetting` list and re-runs sort, keyword filter, and Redis N+1.

### Adjacent list patterns (not ad-control, but same scale class)

| Surface | Load | Page size | Paths |
|---------|------|-----------|--------|
| «Мои магазины» | All cabinets in memory, slice | `SHOPS_PER_PAGE = 20` | `shop_choice_message.py` |
| Admin partners | In-memory sort/filter | `_PARTNER_LIST_PAGE_SIZE = 8` | `admin_panel.py` |
| Excel export (shop) | All `AdvSetting` for `wb_cabinet_id`, filter `is_active_adv` in memory; **per-row** `_fact_snapshot` / `load_total_spend_snapshot` | Progress ticks per row | `export_build.py` |
| WB cabinet discovery (background) | `get_cabinet_adv_ids()` — full list from `GET /adv/v1/promotion/count` (types 8+9), no adapter pagination | — | `promotion_count/adapter.py`, `promotion_manager.discover_cabinet_campaigns` |
| Connect-existing status sync | **Per `adv_id`** `get_campaign_status` in a `for` loop | — | `connect_existing_advs.py` `_sync_adv_status_from_wb` ~134–159 |

### Hierarchical Advertising Control UI (planned, not shipped)

- OpenSpec: task **4.2 UI Advertising Control + Diagnostics** still open (`openspec/changes/hierarchical-ad-control-settings/tasks.md`).
- Domain list contract: campaign authority `(shop_id, advert_id)` (`owner-contract.md`); persistence loads **per-campaign slots** via `load_resolver_campaign_features` — no shop-wide list API yet (`context_loader.py`, `repository.py`).
- Diagnostics snapshot is **single-campaign** `AdControlDiagnosticsReportV1` (`diagnostics.py`, `diagnostics_builder.py`) — no multi-campaign list handler in `app/`.

## CARDINALITY_EVIDENCE

- **No `MAX_*` campaigns-per-shop** constant found for UI list or PG loader.
- **UI page sizes (constants):** campaigns `20` (`AdvCompanyChoicing.on_page`), shops `20` (`SHOPS_PER_PAGE`), admin partners `8`.
- **Cardinality = count of `AdvSetting` rows per `wb_cabinet_id`** (includes legacy search rows; keyboard filters `auction_adv_id is not None` only for display ordering split, not DB limit).
- **WB promotion count** returns **entire** cabinet advert id sets in one response (`promotion_count/adapter.py` — iterates all groups, no limit).
- **Excel export** explicitly iterates all active campaigns and may call stats/plan-fact per row (`export_build.py` ~220–244) — implicit signal that shops with many campaigns are handled sequentially, not paginated at source.
- **Shop update timeout** env-driven (`SHOP_UPDATE_TIMEOUT_MINUTES` in `update_company_from_wb`) — operational hint that full-cabinet WB refresh can be long-running, not that list is capped.

## Existing filter / sort patterns

| UI | Filter | Sort | Transport |
|----|--------|------|-----------|
| Campaign catalog | FSM `filter_advs`: newline keywords, substring match on `name` + `nmids` + `str(adv_id)`; skips `!bot_active` && `active_status == done` when filtering | Active (`active_status` && `bot_active`) before inactive; keyboard re-orders `bot_active` true before false | Telegram message + `ChoiceAdvPaginator` |
| Campaign catalog reset | `reset_filter` on paginator clears `filter_advs` | — | `adv_setting.py` `reset_filter`, `start.py` paginator handler |
| Admin partners | Filter + sort keys in memory | Earned / paid / invited | `admin_panel.py` |
| Ad control domain | Modes: `INHERIT`, `OVERRIDE`, `DISABLED` (`enums.py`); provenance `EffectiveSourceKind.*` (`resolver.py`) | N/A (no list UI) | Pure domain |
| Diagnostics | `decision` `BLOCKED` vs `DIAGNOSTIC_READ_ONLY` when `blockers` non-empty (`diagnostics_builder.py` ~172–174) | N/A | Domain only |

**Note:** Product filter label **«actionable»** does not appear in `ad_control_settings` or campaign list code (grep). Closest domain signals: `CampaignHeadroomEligibility.eligible`, `decision != "BLOCKED"`, `BoundedCpoProposal` / headroom blockers (`headroom_eval.py`, `diagnostics_builder.py`).

## Bulk-write campaign controls (dangerous — do not copy for ad-control v1)

| Pattern | What it does | Path |
|---------|----------------|------|
| `TurnBot` `off_all` | Loads **all** cabinet `AdvSetting`, loop `apply_free_mode_transition` + disable watchdog | `adv_setting.py` ~730–765 |
| `ApplyDefaultsForShop` | All `bot_active` campaigns, per-row ORM defaults | `adv_setting.py` ~976–1006 |
| `ResetShopNonRelevantPhrases` | Shop-wide keyword SQL mass update (skips A/B hold) | `keyword_updater.py`, `adv_setting.py` ~1024+ |
| Excel import | `apply_adv_excel_rows` — multi-campaign settings write | `adv_excel_roundtrip.py`, `import_apply` |
| Ad control ChangeSet | **Single-op** mutations (`shop.set_*`, `campaign.set/disable/clear_*`); validator exposes **actionable** diffs vs NO_OP (`ad_control_validate.py` ~184–190) — **not** a bulk shop sweep; **Apply unwired** (`design.md` Slice B) |

## API / transport — which is the real settings UI?

| Channel | Role today | Evidence |
|---------|------------|----------|
| **Telegram (aiogram)** | **Canonical end-user settings UI**: shop menu, `AdvCompanyChoicing`, `AdvSettingMenu`, mass ops, Excel roundtrip | `client_bot/user_interface/**`, `shop_menu/message.py` |
| **HTTP / FastAPI** | No `ad_control` routes under `app/` | Search negative |
| **MCP / WB Sky** | `TransportChannel` enum includes `UI`, `TELEGRAM`, `MCP`, `API` for **apply audit** (`apply/enums.py`); control-plane dry-run exists; **ad control not wired to Telegram** | `wb_sky_control_plane/**`, `grep ad_control` in `client_bot` empty |
| **Future «Advertising Control»** | Owner contract: mandatory UI + diagnostics, same resolver, **no writes** in diagnostics view (`owner-contract.md` §Diagnostics); task 4.2 not implemented | `openspec/changes/hierarchical-ad-control-settings/` |

**Conclusion:** Telegram is the live settings surface; hierarchical ad control list UI is spec-only. Writes for ad control are intended to go through WB Sky Apply (`AdControlChangeSetV1`), not through legacy Telegram mass loops.

## Performance constraints (observed)

- Telegram handlers **await** full PG load + Python processing on each paginator callback (no server-side page cache).
- **N+1 Redis:** one `GET` per campaign on every list render (`AdvCompanyChoicing.__call__`).
- **N+1 stats on export:** `_fact_snapshot` per active campaign (`export_build.py`).
- **N+1 WB:** `get_campaign_status` per id in connect-existing sync (`connect_existing_advs.py`).
- **Telegram inline keyboard limits:** 20 buttons/page is a practical cap; long labels include name, `adv_id`, `active_status` (`keyboards.py` ~297–303).
- **Full-cabinet WB refresh** can hit `asyncio.wait_for` timeout (`update_company_from_wb`).

---

## Design-only proposals (no code)

### PAGINATION_RECOMMENDATION

| Topic | Recommendation | Rationale (from archaeology) |
|-------|----------------|------------------------------|
| Strategy | **Prefer keyset (cursor) on stable identity** `(shop_id, advert_id)` or `(sort_key, advert_id)` over naive offset | Offset pagination re-loads and re-sorts entire cabinet today; breaks if rows shift while paging. |
| Page size | **~20** default (align Telegram keyboard + `AdvCompanyChoicing.on_page`) | Existing UX constant. |
| Server-side required | **Filter, sort, and page slice** for Advertising Control list | Domain diagnostics/headroom per row is too heavy to materialize for all campaigns client-side (Excel export pattern is the anti-pattern). |
| Client-side OK | Label formatting, emoji, Telegram button text | Current `get_advs_keyboard_with_paginator` scope. |
| Cursor payload | Encode `shop_id`, `feature_id` (if scoped), last-seen `(blocked_rank, headroom_rank, advert_id)` | Supports «blocked first» without re-scanning full shop on page 2. |

### FILTER_MODEL

| Filter (product) | Domain-owned predicate | Presentation-only |
|----------------|------------------------|-------------------|
| **overridden** | Campaign row / resolver: `AdControlFeatureMode.OVERRIDE` or `EffectiveSourceKind.CAMPAIGN_OVERRIDE` for selected feature(s) | Badge text, which feature tab is active |
| **disabled** | `AdControlFeatureMode.DISABLED` or `CAMPAIGN_DISABLED` / `SHOP_DISABLED` provenance (`enums.py`, `resolver.py`) | — |
| **inherited** | No campaign authority row + effective policy from shop/product/system (`INHERIT` live read — `resolver.py`, `owner-contract.md` §Live inheritance) | — |
| **blocked** | `AdControlDiagnosticsReportV1.decision == "BLOCKED"` or non-empty `blockers` / eligibility blockers (`diagnostics_builder.py`, `headroom_eval.py`) | Collapse reason codes for Telegram |
| **actionable** | **EVIDENCE_GAP for product token:** not named in repo. Proposed domain mapping (for design review only): `eligible=True` in `CampaignHeadroomEligibility` **and** `decision != "BLOCKED"` **and** (future) non–`NO_PROPOSAL_*` proposal when allocator exists (`headroom_eval.py`, `diagnostics_builder.py` ~162–170) | «Show only rows Owner can act on» toggle |

Filters on **`bot_active` / WB `active_status`** belong to **legacy Telegram catalog**, not ad-control domain (unless explicitly cross-linked in spec).

### SORT (design)

1. **Blocked first:** `decision == BLOCKED"` or `len(blockers) > 0` (diagnostics contract).
2. **Headroom / proposal:** use `ShopHeadroomState` + `BoundedCpoProposal` when present; owner-contract notes **no accepted production ranking formula** — sort key should be deterministic placeholder (e.g. `proposed_max_cpo_rub` desc, nulls last) until allocator GO.
3. **Tie-break:** `advert_id` ascending (`owner-contract.md` campaign identity).

Legacy catalog sort (active bot campaigns first) should **not** be implied for ad-control list unless spec says so.

### UX_RISKS

- Reusing **full-shop load + in-memory paginate** for ad control will duplicate `AdvCompanyChoicing` scalability ceiling (Redis N+1, handler latency).
- **Telegram 20-button pages** with multi-feature badges may overflow message size if each row shows diagnostics prose.
- **Mixed row types:** `AdvSetting` includes legacy search-only rows (`CONNECT_EXISTING_SPEC.md`); ad-control identity is `(shop_id, advert_id)` — list must not double-count legs.
- **Filter state in FSM** (`filter_advs`) is fragile across handlers (`start.py` vs `adv_setting.py` paginator); ad-control should use explicit callback state or server-stored cursor.
- **Diagnostics per row** without batching may reproduce Excel export **per-campaign stats** cost.
- Users may confuse **Telegram «bot_active»** with **ad-control DISABLED** — different domains.

### PERFORMANCE_REQUIREMENTS

- Shop-wide list endpoint must **not** call WB per row on read path (contrast `connect_existing_advs.py`).
- Batch Redis / PG for «last checked» style flags if similar UX needed (contrast `check_last_24_hours` loop).
- Cap work per page: resolve diagnostics only for **page rows**, not full cabinet.
- Keyset pagination must be **stable** under concurrent campaign row inserts (PG `AdvSetting` / inventory).
- Apply path: keep **one campaign per ChangeSet op** (`KNOWN_AD_CONTROL_OPS` in `ad_control_validate.py`) — no shop-wide override sweep in v1.

### BULK_WRITE_FORBIDDEN_V1

**Confirmed:** hierarchical ad control v1 must not ship shop-wide bulk mutation loops. Existing bulk paths to **avoid reusing** for ad-control settings:

- `TurnBot` / `off_all` (`adv_setting.py`)
- `ApplyDefaultsForShop` (`adv_setting.py`)
- `ResetShopNonRelevantPhrases` / `update_keywords` (`keyword_updater.py`)
- Excel `apply_adv_excel_rows` (`adv_excel_roundtrip` pipeline)

Authorized write shape: **`AdControlChangeSetV1`** single logical operations + future WB Sky Apply (`owner-contract.md` persistence / CAS); dry-run only today (`tasks.md` 3.2 done, Apply unwired).

---

## Cross-links

- Related internal UI design: `internal/architecture/hierarchical-ad-control-settings-slice-c-ui-design.md`
- OpenSpec: `openspec/changes/hierarchical-ad-control-settings/owner-contract.md`, `design.md`

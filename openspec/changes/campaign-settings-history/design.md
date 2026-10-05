## Context

WB Sky currently has no single machine-readable contract for the current advertising configuration. Campaign settings are spread across `AdvSetting`, `KeywordSetting`, `AutoShelfBidControlSettings`, `AdvTimeSettings`, and `AdvTimeWeekMask`. The same models also contain WB-observed facts, derived values, workflow state, and technical persistence fields. The main campaign Excel workbook and the keyword target-place workbook maintain separate manual field lists.

The reviewed baseline in `field-policy-baseline.md` classifies all current mapped fields of the five registered sources (129 fields total) and preserves current Excel editability. It is upstream semantic input, not an implementation-generated guess.

`snapshot_data_updater` already has a 300-second process cadence, but its live discovery is tied to active shops/campaigns and its `AdvSettingsSnapshotDTO` is intentionally slim. It therefore MUST NOT become the canonical settings contract and MUST NOT be the history discovery authority.

The accepted ClickHouse migration lifecycle currently owns corpus `001`–`005`. The history table requires reviewed version `006`, so this change modifies the lifecycle spec and proposes an explicit corpus-extension decision rather than running DDL from application startup.

## Goals / Non-Goals

**Goals:**
- One versioned canonical settings aggregate per campaign.
- Exhaustive field/source classification that fails closed when a setting is added, removed, renamed, or moved to a new source without policy.
- Append-only, change-only history in ClickHouse with deterministic state hashes.
- Approximate five-minute observation cadence independent of campaign bot-active/WB-active status.
- Existing Excel write behavior derived from or parity-checked against the same field registry.
- Reviewed migration `006` applied only through the ClickHouse migration control plane.
- Cross-process duplicate prevention without storing applied history state in PostgreSQL.

**Non-Goals:**
- Event sourcing every individual settings write between polling ticks.
- History of WB physical status/bid/placement, plan/fact, spend, metrics, diagnostics, or transient workflow state.
- New WB API writes or changes to bidder/V3 behavior.
- Making ClickHouse or Excel an authority for current settings.
- AI/API/MCP settings control in this change.
- Deleting historical rows when current PostgreSQL settings rows disappear.

## Architecture Decision References

- `openspec/changes/campaign-settings-history/decisions/campaign-settings-contract-ownership/decision.md` — Proposed; canonical field-registry ownership and fail-closed source/field coverage.
- `openspec/decisions/clickhouse-migration-lifecycle-ownership/decision.md` — Accepted; migration lifecycle/control-plane ownership.
- `openspec/changes/campaign-settings-history/decisions/clickhouse-migration-corpus-006/decision.md` — Proposed; reviewed `006` extends the immutable corpus without weakening `005` privilege separation.
- `openspec/decisions/clickhouse-sql-database-qualification/decision.md` — Accepted; working ClickHouse SQL uses `default_db.<object>`.

## Design Readiness

DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: yes
NORMATIVE_CONFLICTS: none
PRODUCT_ACCEPTANCE_REQUIRED: true
DESIGN_STATUS: READY

## Ownership & Placement

Current configuration authority remains PostgreSQL settings tables. The canonical domain classification is owned by a new settings-contract module, not by ORM serialization, Excel, Redis snapshots, or ClickHouse.

Allowed placement:
- `app/modules/campaign_settings_contract/`: source registry, field policies, canonical DTO/normalizers, schema version and state hash.
- `app/modules/campaign_settings_history/`: PostgreSQL readers/discovery, collector/coordinator, ClickHouse history repository/query service.
- existing Excel workbook services: consumers of registry projection metadata; existing settings write paths remain their current PG writers.
- `scripts/clickhouse_migrations/006_create_campaign_settings_history.sql`: reviewed DDL only; execution remains owned by `scripts.clickhouse_migration_control_plane`.

Forbidden placement:
- `snapshot_data_updater.dto.AdvSettingsSnapshotDTO` as canonical settings SoT.
- Redis as settings/history authority.
- DDL in application startup or history collector.
- history collector writes to PostgreSQL settings rows or WB API.
- separate manually maintained history and Excel field whitelists.

SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
TARGET_ENTITY_OR_LEG: append-only `default_db.campaign_settings_history` rows; migration `006` only via ClickHouse migration control plane; current PostgreSQL settings are read-only inputs
ALLOWED_ADAPTERS: campaign-settings PostgreSQL readers; dedicated PgBouncer-safe transaction-scoped PostgreSQL advisory-lock coordinator for history collection (`pg_try_advisory_xact_lock` inside the same explicit transaction that encloses PG read → CH compare/insert interval); campaign-settings-history ClickHouse select/insert repository; existing Excel PG writers constrained by registry projection; migration control-plane isolated target adapter for `006`
FORBIDDEN_ADAPTERS: WB API writers from history collector; PostgreSQL settings mutation from history collector; Redis history store; application startup DDL; raw application ClickHouse DDL execution; Excel as canonical settings source
## Decisions

### 1. One exhaustive source/field registry

The registry contains explicit `SourcePolicy` entries for every registered settings-owned ORM source and `FieldPolicy` entries for every mapped field. Minimum field dimensions are semantic role, history policy, Excel policy, normalization/type policy, and exclusion reason when excluded.

Source coverage is also fail-closed. A deterministic source-discovery test scans every ORM class declared in every Python module under `app/modules/common_slaves/wildberries/models/`. Every discovered source MUST be either registered or present in an explicit `EXCLUDED_SOURCE` registry with a reason. The file set is discovered dynamically, so adding a new model file cannot bypass the gate. This prevents a new settings table from escaping history/Excel classification merely because the developer forgot to register the whole source.

`field-policy-baseline.md` is the reviewed version-1 classification. Implementation MUST materialize it without changing product semantics during coding. A future classification change is a contract change, not an opportunistic refactor.

### 2. Canonical payload and deterministic normalization

Canonical schema version 1 has this logical shape:

```text
{
  schema_version,
  identity: {adv_setting_id, wb_cabinet_id, adv_id, search_adv_id, name, nmids, type},
  campaign: {history-state AdvSetting fields},
  keywords: [{text, hard_status, strategy_mode, relevant, target_place}, ...],
  auto_shelf_by_nmid: [{nmid, settings...}, ...],
  schedule: {schedule_enabled, date_enabled, date_start, date_end, timezone, week_mask:[...] }
}
```

Normalization rules:
- object keys are serialized in stable lexical order;
- keywords are sorted by `text`; duplicate text inside one campaign is invalid rather than guessed;
- `auto_shelf_by_nmid` is sorted by `nmid`; duplicate rows for one nmid are invalid;
- week-mask rows are sorted by `dow`; duplicate `dow` is invalid;
- `nmids` is normalized as a deterministic integer list preserving set semantics (sorted unique);
- enums serialize to stable symbolic string values defined by the registry, never Python repr;
- dates use ISO `YYYY-MM-DD`; timezone names remain canonical strings;
- integer/boolean/null remain typed JSON values; no locale formatting;
- JSON is UTF-8 with deterministic separators and sorted keys;
- `schema_version` is part of the hashed payload;
- collection timestamps, run ids, diagnostics, database timestamps, and excluded fields are outside the hash.

`state_hash = SHA-256(canonical_json_bytes)` encoded as lowercase 64-character hex. Any semantic shape/normalization change requires a schema-version bump and a reader capable of identifying old snapshots by version.

### 3. Polling history is observational, not an event log

A dedicated `CampaignSettingsHistoryUpdater` runs with default interval 300 seconds. It may reuse the existing project's async daemon patterns, but it MUST NOT reuse `snapshot_data_updater` active-shop discovery or its slim DTO as authority.

Discovery comes from PostgreSQL settings ownership: distinct `wb_cabinet_id` values with current `AdvSetting` rows, regardless of `bot_active`, WB `active_status`, or Redis active-shop membership. This ensures inactive campaigns remain observable while settings rows exist.

Because this is polling, states that change and revert entirely between two observations are not guaranteed to be recorded. That is an explicit trade-off of this change; it is not presented as per-write audit logging.

### 4. Batch source loading

For each discovered cabinet, one collector pass loads campaign rows and related settings in bounded batches: campaign settings, keyword settings keyed by campaign, shelf-bid settings keyed by all campaign nmids, and time settings/week masks. N+1 per-field/per-keyword database calls are forbidden.

A source-load failure that prevents a complete canonical campaign snapshot fails that campaign (or the entire cabinet when the shared batch is unusable). The collector MUST NOT hash/persist partial guessed data.
### 5. Cross-process collection coordination and duplicate prevention

In-process tick locks are insufficient because deploy-level singleton is not proven. Collection therefore uses a dedicated transaction-scoped PostgreSQL advisory lock per cabinet.

Lock contract:
- namespace key: signed int32 constant `1129531441` (`CSH1`), owned only by campaign settings history;
- object key: `wb_cabinet_id`, required to fit PostgreSQL int32; an out-of-range id fails closed and is surfaced rather than rehashed silently;
- because the repository uses PgBouncer transaction pooling, session-level advisory locks are forbidden for this collector;
- acquire non-blocking `pg_try_advisory_xact_lock(namespace_key, wb_cabinet_id)` inside one explicit PostgreSQL transaction;
- keep that transaction open from before settings read through latest-hash read and history insert completion;
- commit/rollback ends the transaction and releases the advisory lock automatically; there is no separate unlock call;
- lock contention skips that cabinet with an observable `lock_contended` result; it does not queue duplicate work;
- this namespace MUST NOT reuse Alembic key `731984123` or ClickHouse migration-control lock identity.

The transaction-scoped advisory lock is coordination only; PostgreSQL stores no history-applied marker. After a crash following a successful ClickHouse insert, the next tick reads the latest stored hash and skips an unchanged state. A failed/uncertain write never permits mutation of current settings.

Before each ClickHouse insert batch the collector MUST still be inside the same live PostgreSQL transaction that acquired the xact lock; transaction/session loss prevents the next history write.

### 6. Change-only ClickHouse repository

Migration `006_create_campaign_settings_history.sql` creates:

```text
default_db.campaign_settings_history
  observed_at       DateTime64(3, 'UTC')
  snapshot_id       UUID
  adv_setting_id    UInt64
  wb_cabinet_id     UInt64
  shop_id           String
  adv_id            Nullable(UInt64)
  search_adv_id     Nullable(UInt64)
  schema_version    UInt16
  state_hash        FixedString(64)
  payload_json      String
```

Engine: `MergeTree`. Partition: `toYYYYMM(observed_at)`. Order key: `(wb_cabinet_id, adv_setting_id, observed_at, snapshot_id)`. All working SQL MUST qualify the table as `default_db.campaign_settings_history`.

`payload_json` stores the canonical UTF-8 JSON exactly corresponding to `state_hash`. `snapshot_id` is a record identity/tie-breaker and is not part of the state hash.

For each locked cabinet the repository performs one batch latest-state query for all current `adv_setting_id` values using deterministic latest ordering `(observed_at, snapshot_id)`. The collector inserts only campaigns whose current `state_hash` differs from their latest stored hash, plus campaigns with no prior row. Changed rows are inserted in one batch where practical.

History read service supports campaign/time-range queries ordered by `(observed_at, snapshot_id)` and always returns `schema_version`, `state_hash`, and canonical payload. Reads are pure read-only operations.

Deleting a current PostgreSQL settings row does not delete ClickHouse history and does not create a tombstone in this change.

### 7. Migration 006 is controlled by the existing migration control plane

`006` is an immutable reviewed schema migration, not startup DDL. The change updates corpus fingerprints/catalog/tests from exact `001`–`005` to exact `001`–`006`, classifies `006` as schema DDL, and expands schema-writer eligibility from `001`–`004` to `001`–`004` plus `006`.

`005` remains privileged GRANT and retains `blocked_privileged_grant`. Unknown numeric successors remain unreviewed and block apply. Acceptance tests use only the isolated recording target/coordinator seams; this change does not authorize production migration apply.

### 8. Excel consumes registry projection metadata

`adv_excel_roundtrip/schema.py` no longer owns a hand-written editable field truth. Compatibility constants/functions may remain public for callers/tests, but they are generated from registry projection entries and must equal the reviewed version-1 projection.

The initial main-workbook editable field set remains byte-for-byte/semantically equivalent to the current v8 behavior in `field-policy-baseline.md`; merely adding history MUST NOT make another field editable. Shelf-bid aliases retain their existing RUB/minor-unit conversion semantics.

The keyword target-place workbook registers `KeywordSetting.target_place` as editable and keyword id/text/current value as read-only aliases. Other keyword settings remain excluded from current Excel projections.

Synthetic RO workbook diagnostics (snapshot time, offer id, plan/fact/deviation/spend) remain adapter-owned display columns. They MUST NOT become canonical settings fields or enter `state_hash`.

A workbook header/projection change that alters external Excel format requires an explicit `EXCEL_TEMPLATE_VERSION` bump. Internal migration from manual lists to registry with identical emitted headers does not by itself require a version bump.
### 9. Failure reporting and recovery

Each tick returns/logs structured counts: cabinets discovered, lock acquired/contended, campaigns read, unchanged, inserted, invalid-contract, PG-read failures, ClickHouse-read failures, ClickHouse-write failures, and duration. A cabinet/campaign failure is observable and MUST NOT be reported as history success.

Recovery rules:
- field/source inventory mismatch is a startup/test blocker; production collector MUST fail closed rather than invent a policy;
- normalization failure skips only the invalid campaign when isolation is possible and preserves its latest valid history;
- PostgreSQL read failure causes no ClickHouse writes for the affected scope;
- ClickHouse latest-hash read failure causes no history inserts for the affected cabinet because change-only comparison is unknown;
- ClickHouse insert failure leaves PostgreSQL settings untouched and is retryable on a later tick;
- coordinator loss before a write prevents that write;
- no automatic deletion or rewrite of previous history rows is used as recovery.

## Derived Lifecycle

LIFECYCLE_STATUS: DERIVED

### L1 — Discover observable settings scope
`SOURCE: owner-contract.md Required semantics; proposal Scope In`
The updater discovers PostgreSQL cabinets/campaigns that own settings rows without filtering on bot/WB active status.

### L2 — Acquire collection ownership
`SOURCE: owner-contract.md change-only/no duplicates; proposed settings-contract decision`
For each cabinet the updater obtains the dedicated PgBouncer-safe transaction-scoped advisory lock inside the explicit PostgreSQL transaction. Contention means skip/degraded, not a second writer.

### L3 — Read complete current settings
`SOURCE: owner-contract.md canonical aggregate`
The locked collector batch-reads all registered source data required for the campaigns in that cabinet. Partial/unsupported source state cannot be promoted to canonical history.

### L4 — Normalize and validate contract
`SOURCE: owner-contract.md field classification/schema_version/fail-closed`
Every campaign is normalized under the registered schema version. Unknown source/field/value/type state fails closed. The canonical hash is computed only from the complete deterministic payload.

### L5 — Compare against durable history
`SOURCE: owner-contract.md snapshot only on changed hash`
The ClickHouse repository batch-loads latest hashes. No previous row means baseline needed; equal hash means no write; different hash means append candidate.

### L6 — Append changed snapshots
`SOURCE: owner-contract.md append-only history; proposal desired behavior`
While the coordinator is still held, changed/baseline snapshots are inserted into `default_db.campaign_settings_history`. Existing history is never updated in place or deleted.

### L7 — Release and report
`SOURCE: owner-contract.md observable failure and periodic collection`
The coordinator lock is released and the tick reports inserted/unchanged/degraded outcomes. The next approximately five-minute tick independently repeats observation.

## Risks / Trade-offs

- **Polling can miss A→B→A between ticks.** → Explicitly accepted observational-history semantics; this is not an event-sourced audit log.
- **Large shops could make a tick exceed five minutes.** → Batch PG/CH queries, per-cabinet locks, no N+1; overlapping tick skips/continues by cabinet rather than creating duplicate writers.
- **Registry classification can be semantically wrong even when exhaustive.** → Reviewed `field-policy-baseline.md`, explicit exclusion reasons, scenario tests, and future classification changes treated as contract changes.
- **JSON payload is less columnar for ad-hoc CH analytics.** → History's primary need is versioned complete state; identity/hash/version stay typed columns. Derived analytical views can be a later change without changing canonical payload.
- **Adding `006` could weaken migration safety.** → Separate proposed decision; only exact reviewed hash becomes schema DDL; all previous gates and `005` separation remain.
- **Advisory lock limits concurrent collection per cabinet.** → Intentional correctness trade-off; different cabinets can still be processed independently.

## Migration Plan

1. Materialize field/source registry and exhaustive contract tests before enabling history writes.
2. Refactor Excel schema consumers to registry-derived projection while proving emitted v8 headers/import behavior remain compatible.
3. Add canonical payload/normalizer/hash and pure unit tests.
4. Add reviewed immutable `006_create_campaign_settings_history.sql`; extend migration-control corpus/catalog/tests to `001`–`006`.
5. Use migration control plane only on an isolated target for acceptance evidence. Production application remains a separate operator/deployment action outside this change's verification.
6. Add ClickHouse history repository and PG settings readers/coordinator.
7. Add standalone history updater defaulted off behind explicit enable/config switch; run unit/integration/shadow collection against isolated/dev stores.
8. Enable scheduled collection only after migration exists on the target and collector health is observable.

Rollback:
- disable history updater; current settings behavior remains unchanged because PostgreSQL authority/write paths were not moved;
- keep existing history table/data read-only; do not drop it automatically;
- Excel can revert consumer wiring while preserving registry tests, but any actual workbook format rollback must respect template version compatibility;
- migration corpus `006` remains immutable once accepted/applied; rollback is forward-only, never file deletion/rewrite.

## Open Questions

None. Implementation naming may vary, but SoT, source coverage, field classification baseline, write authority, coordination, storage schema, migration ownership, recovery, and Excel projection semantics are fixed above.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [ ] implementation layer matches decision

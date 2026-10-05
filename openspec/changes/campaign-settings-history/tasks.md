## 1. Contract coverage вЂ” tests first

- [x] 1.1 Р”РѕР±Р°РІРёС‚СЊ characterization/inventory test РґР»СЏ РїСЏС‚Рё С‚РµРєСѓС‰РёС… registered settings sources Рё baseline 129 mapped fields; С‚РµСЃС‚ РѕР±СЏР·Р°РЅ СЃРІРµСЂСЏС‚СЊ exact field sets СЃ registry policy.
- [x] 1.2 Р”РѕР±Р°РІРёС‚СЊ negative regression: СЃРёРЅС‚РµС‚РёС‡РµСЃРєРѕРµ/РІСЂРµРјРµРЅРЅРѕРµ РЅРѕРІРѕРµ РїРѕР»Рµ Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅРЅРѕРіРѕ source Р±РµР· FieldPolicy РґРµР»Р°РµС‚ validation FAIL; РїРѕСЃР»Рµ СЏРІРЅРѕР№ policy paired positive case РїСЂРѕС…РѕРґРёС‚.
- [x] 1.3 Р”РѕР±Р°РІРёС‚СЊ negative regression РґР»СЏ СѓРґР°Р»С‘РЅРЅРѕРіРѕ/РїРµСЂРµРёРјРµРЅРѕРІР°РЅРЅРѕРіРѕ field Рё stale registry entry.
- [x] 1.4 Р”РѕР±Р°РІРёС‚СЊ source-discovery regression: РЅРѕРІС‹Р№ ORM settings candidate Р±РµР· REGISTERED/EXCLUDED_SOURCE(reason) РґРµР»Р°РµС‚ contract FAIL.
- [x] 1.5 Р”РѕР±Р°РІРёС‚СЊ tests, С‡С‚Рѕ excluded field/source policy Р±РµР· РЅРµРїСѓСЃС‚РѕРіРѕ reason РЅРµРІР°Р»РёРґРЅР°.
- [x] 1.6 Р”РѕР±Р°РІРёС‚СЊ characterization current Excel v8 EDIT/RO headers Рё keyword target-place workbook, С‡С‚РѕР±С‹ РїРµСЂРµС…РѕРґ РЅР° registry РЅРµ РјРµРЅСЏР» РІРЅРµС€РЅРёР№ workbook РЅРµР·Р°РјРµС‚РЅРѕ.

## 2. Canonical registry and normalization вЂ” tests first

- [x] 2.1 Р”РѕР±Р°РІРёС‚СЊ tests canonical payload v1 РґР»СЏ campaign, keyword, shelf-by-nmid Рё schedule/week-mask sections.
- [x] 2.2 Р”РѕР±Р°РІРёС‚СЊ determinism tests: РїРµСЂРµСЃС‚Р°РЅРѕРІРєР° keyword rows, nmids, shelf rows, week-mask rows Рё dict key order РЅРµ РјРµРЅСЏРµС‚ canonical JSON/state_hash.
- [x] 2.3 Р”РѕР±Р°РІРёС‚СЊ tests typed normalization enum/date/bool/int/null Рё fail-closed unsupported value/type.
- [x] 2.4 Р”РѕР±Р°РІРёС‚СЊ test, С‡С‚Рѕ collector timestamp/run id/diagnostics/WB-fact/runtime-excluded fields РЅРµ РјРµРЅСЏСЋС‚ state_hash.
- [x] 2.5 Р”РѕР±Р°РІРёС‚СЊ test schema-version discipline: schema_version РІС…РѕРґРёС‚ РІ hash; semantic contract change С‚СЂРµР±СѓРµС‚ РЅРѕРІРѕР№ РІРµСЂСЃРёРё reader/fixture.
- [x] 2.6 Р РµР°Р»РёР·РѕРІР°С‚СЊ `campaign_settings_contract` policy types/source registry Рё materialize reviewed `field-policy-baseline.md` Р±РµР· РёР·РјРµРЅРµРЅРёСЏ РєР»Р°СЃСЃРёС„РёРєР°С†РёРё.
- [x] 2.7 Р РµР°Р»РёР·РѕРІР°С‚СЊ deterministic source/field inventory validator Рё РїСѓР±Р»РёС‡РЅС‹Р№ contract-validation entrypoint.
- [x] 2.8 Р РµР°Р»РёР·РѕРІР°С‚СЊ canonical DTO/normalizers/JSON serializer/SHA-256 builder РґР»СЏ schema v1.

## 3. Excel projection parity

- [x] 3.1 РџРµСЂРµРІРµСЃС‚Рё РѕСЃРЅРѕРІРЅРѕР№ `adv_excel_roundtrip` editable AdvSetting set РЅР° registry-derived projection, СЃРѕС…СЂР°РЅРёРІ С‚РµРєСѓС‰РёР№ emitted v8 workbook header set.
- [x] 3.2 РџРµСЂРµРІРµСЃС‚Рё AutoShelf editable aliases Рё RUB/minor conversion mapping РЅР° registry projection metadata Р±РµР· РёР·РјРµРЅРµРЅРёСЏ С‚РµРєСѓС‰РµР№ СЃРµРјР°РЅС‚РёРєРё.
- [x] 3.3 РџРѕРґРєР»СЋС‡РёС‚СЊ `KeywordSetting.target_place` target-place workbook Рє registry policy Рё Р·Р°С„РёРєСЃРёСЂРѕРІР°С‚СЊ keyword_id/text/current_target_place РєР°Рє RO aliases.
- [x] 3.4 РЎРѕС…СЂР°РЅРёС‚СЊ synthetic plan/fact/spend/deviation/export diagnostics РєР°Рє Excel-only columns Рё РґРѕРєР°Р·Р°С‚СЊ test'РѕРј, С‡С‚Рѕ РѕРЅРё РЅРµ РІС…РѕРґСЏС‚ РІ canonical settings hash.
- [x] 3.5 Р”РѕР±Р°РІРёС‚СЊ parity test: РЅРё РѕРґРёРЅ Excel editable/read-only source field РЅРµ СЃСѓС‰РµСЃС‚РІСѓРµС‚ РІРЅРµ registry policy; registry Excel policy drift Р»РѕРјР°РµС‚ test.
- [x] 3.6 Р”РѕР±Р°РІРёС‚СЊ test: РёР·РјРµРЅРµРЅРёРµ С„Р°РєС‚РёС‡РµСЃРєРѕРіРѕ workbook format С‚СЂРµР±СѓРµС‚ `EXCEL_TEMPLATE_VERSION` bump; РІРЅСѓС‚СЂРµРЅРЅРёР№ refactor СЃ С‚РµРјРё Р¶Рµ headers version РЅРµ РјРµРЅСЏРµС‚.

## 4. Reviewed ClickHouse migration 006 вЂ” tests first

- [x] 4.1 Р”РѕР±Р°РІРёС‚СЊ corpus acceptance tests: reviewed exact `006_create_campaign_settings_history.sql` РІС…РѕРґРёС‚ РІ fingerprint РєР°Рє schema_ddl; exact corpus СЃС‚Р°РЅРѕРІРёС‚СЃСЏ 001вЂ“006.
- [x] 4.2 Р”РѕР±Р°РІРёС‚СЊ regression: `005` РїРѕ-РїСЂРµР¶РЅРµРјСѓ `blocked_privileged_grant`, Р° unreviewed numeric successor/alternate 006 Р±Р»РѕРєРёСЂСѓРµС‚ apply.
- [x] 4.3 Р”РѕР±Р°РІРёС‚СЊ isolated apply test РґР»СЏ 006 СЃ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёРјРё authorization/baseline/checksum/coordinator gates Рё statement event protocol.
- [x] 4.4 Р”РѕР±Р°РІРёС‚СЊ SQL-contract test РґР»СЏ `default_db.campaign_settings_history`, MergeTree partition/order, payload/hash/version typed columns Рё РѕС‚СЃСѓС‚СЃС‚РІРёСЏ production/runtime DDL path.
- [x] 4.5 РЎРѕР·РґР°С‚СЊ immutable `scripts/clickhouse_migrations/006_create_campaign_settings_history.sql`.
- [x] 4.6 РћР±РЅРѕРІРёС‚СЊ migration-control corpus catalog/fingerprints/eligibility СЃ 001вЂ“005 РЅР° 001вЂ“006, РѕСЃС‚Р°РІРёРІ 005 РµРґРёРЅСЃС‚РІРµРЅРЅС‹Рј privileged-grant member.
- [x] 4.7 РћР±РЅРѕРІРёС‚СЊ migration-control acceptance tests Рё scenario mappings РґР»СЏ reviewed successor Р±РµР· live/production ClickHouse execution.

## 5. PostgreSQL settings reader and coordination вЂ” tests first

- [x] 5.1 Р”РѕР±Р°РІРёС‚СЊ test discovery РїРѕ PostgreSQL: inactive shop/campaign settings rows РїРѕРїР°РґР°СЋС‚ РІ history scope РЅРµР·Р°РІРёСЃРёРјРѕ РѕС‚ Redis active_shops, bot_active Рё WB active_status.
- [x] 5.2 Р”РѕР±Р°РІРёС‚СЊ batch-loader tests РґР»СЏ AdvSetting + KeywordSetting + AutoShelfBidControlSettings + AdvTimeSettings/WeekMask Р±РµР· N+1 Рё СЃ РїРѕР»РЅРѕР№ campaign isolation.
- [x] 5.3 ???????? tests dedicated PgBouncer-safe transaction advisory lock (1129531441, wb_cabinet_id): success, contention skip, transaction liveness/loss prevents next history write; lock releases automatically on transaction end.
- [x] 5.4 Р”РѕР±Р°РІРёС‚СЊ regression, С‡С‚Рѕ history collector РЅРµ РІС‹РїРѕР»РЅСЏРµС‚ UPDATE/INSERT С‚РµРєСѓС‰РёС… PostgreSQL settings Рё РЅРµ РІС‹Р·С‹РІР°РµС‚ WB API writers.
- [x] 5.5 Р РµР°Р»РёР·РѕРІР°С‚СЊ PostgreSQL cabinet discovery Рё batch settings loader РїРѕ registry-owned sources.
- [x] 5.6 Р РµР°Р»РёР·РѕРІР°С‚СЊ dedicated per-cabinet advisory-lock coordinator СЃ fail-closed range/session checks.

## 6. ClickHouse history repository вЂ” tests first

- [x] 6.1 Р”РѕР±Р°РІРёС‚СЊ repository test first observation в†’ one baseline insert.
- [x] 6.2 Р”РѕР±Р°РІРёС‚СЊ repository test same latest hash в†’ zero inserts; Aв†’B appends B; later Bв†’A appends a new A observation.
- [x] 6.3 Р”РѕР±Р°РІРёС‚СЊ batch latest-hash test СЃ deterministic `(observed_at, snapshot_id)` tie-break and one query per cabinet batch.
- [x] 6.4 Р”РѕР±Р°РІРёС‚СЊ read timeline test ordered by `(observed_at, snapshot_id)` with schema_version/state_hash/payload.
- [x] 6.5 Р”РѕР±Р°РІРёС‚СЊ failure tests: latest-hash read failure causes zero inserts; insert failure leaves PG settings untouched and remains retryable.
- [x] 6.6 Р РµР°Р»РёР·РѕРІР°С‚СЊ ClickHouse history repository batch latest/select, changed-row insert Рё time-range query against qualified `default_db.campaign_settings_history`.

## 7. Collector and scheduler вЂ” tests first

- [x] 7.1 Р”РѕР±Р°РІРёС‚СЊ collector test complete source state в†’ canonicalize в†’ compare в†’ append only changed campaigns.
- [x] 7.2 Р”РѕР±Р°РІРёС‚СЊ collector test incomplete/unsupported one campaign fails closed without guessed/partial snapshot; unaffected campaigns may continue when batch isolation remains valid.
- [x] 7.3 Р”РѕР±Р°РІРёС‚СЊ concurrency test two collectors same cabinet: only lock owner reaches ClickHouse compare/insert; contender reports `lock_contended`.
- [x] 7.4 Р”РѕР±Р°РІРёС‚СЊ restart/crash recovery test: existing latest hash after prior successful insert prevents duplicate on next tick.
- [x] 7.5 Р”РѕР±Р°РІРёС‚СЊ cadence/overlap tests: default 300 seconds, in-process overlapping tick does not create a second same-process run.
- [x] 7.6 Р РµР°Р»РёР·РѕРІР°С‚СЊ standalone `CampaignSettingsHistoryUpdater` disabled by default, СЃ configurable 300-second cadence Рё PG-based discovery.
- [x] 7.7 Р РµР°Р»РёР·РѕРІР°С‚СЊ structured result/metrics/logging: discovered, lock acquired/contended, read, unchanged, inserted, invalid, PG/CH failures, duration.

## 8. Product acceptance and safety

- [x] 8.1 РћР±РЅРѕРІРёС‚СЊ proposed decisions checklist `implementation layer matches decision` С‚РѕР»СЊРєРѕ РїРѕСЃР»Рµ С„Р°РєС‚РёС‡РµСЃРєРѕРіРѕ placement review.
- [ ] 8.2 Р—Р°РїСѓСЃС‚РёС‚СЊ targeted unit/integration suite РґР»СЏ field registry, Excel parity, migration control plane, PG coordinator, CH repository Рё updater.
- [x] 8.3 Р—Р°РїСѓСЃС‚РёС‚СЊ strict type/static checks РґР»СЏ РЅРѕРІС‹С…/РёР·РјРµРЅС‘РЅРЅС‹С… modules Рё `git diff --check`.
- [x] 8.4 Р’С‹РїРѕР»РЅРёС‚СЊ `/opsx-spec-scenario-coverage mode=plan change=campaign-settings-history`, Р·Р°С‚РµРј independent audit РїРѕСЃР»Рµ implementation.
- [ ] 8.5 Р”РѕРєР°Р·Р°С‚СЊ `PRODUCT_ACCEPTANCE_STATUS=PASS`: MEANING_LOCK resolved, Derived Lifecycle L1вЂ“L7 scenario-mapped, side-effect proof С‚РѕР»СЊРєРѕ РґР»СЏ isolated history storage seams.
- [x] 8.6 РџРѕРґС‚РІРµСЂРґРёС‚СЊ, С‡С‚Рѕ change РЅРµ РІС‹РїРѕР»РЅСЏР» production ClickHouse migration/apply, РЅРµ РїРёСЃР°Р» WB Рё РЅРµ РјРµРЅСЏР» current PostgreSQL settings authority.
- [ ] 8.7 Р’С‹РїРѕР»РЅРёС‚СЊ `/opsx-verify mode=archive campaign-settings-history`; archive СЂР°Р·СЂРµС€С‘РЅ С‚РѕР»СЊРєРѕ РїСЂРё С„РёРЅР°Р»СЊРЅРѕРј `вњ… GO`.


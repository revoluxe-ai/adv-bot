# Owner Contract — ai-package-campaign-settings-snapshot

## Что хотим получить

Машинно-читаемый read-only снимок **настроек рекламных кампаний** для AI Package:
по каждой кампании магазина видно, что задаёт WB, что задаёт локальная политика
бота, какие поля неизвестны или не поддерживаются, и насколько данные свежие и
полные. Auto (полки) и Search (ключи) остаются разными ногами, без тихого слияния.

## Зачем

V1 пакета отдал только минимальный inventory (ids и связи). Для AI-аналитики и
диагностики нужен детальный snapshot, но он не должен перепутаться с control-plane
снимком A1 или с Redis-снимком для shop-runner.

## Что должно остаться неизменным

- Export и snapshot — **только чтение**; WB, Redis, очереди, lifecycle, ставки,
  бюджеты и `bot_active` не меняются.
- AI Package v1 остальные dataset cards и read-only boundary
  (`shop-data-source-strategy`, exporter ownership ADR).
- Auto и Search — отдельные `campaign_id` / legs; коды типа 8/9 не определяют пару.
- `UNKNOWN` не считается успехом; пустой успех не закрывает неполноту.

## Чего сейчас не делаем

- Запись в WB, apply/preview control plane, создание/остановка кампаний.
- Запуск collectors или live WB API на пути export (кроме отдельного future
  accumulation change, если Owner решит копить WB settings в PG).
- MCP/API transport, Telegram/GUI, миграции под snapshot.
- Подмена A1 `CampaignResourceSnapshotV1` или Redis `AdvSettingsSnapshotDTO`
  контрактом AI Package.
- §0.3 `openspec_guard.yaml` debt.

## Как поймём, что получилось

- В пакете есть dataset `campaign_settings_snapshot` с documented grain и
  field-level provenance; manifest не обещает FULL WB cabinet universe.
- Поля с неизвестным WB/local state помечены явно; нет подставленных default из
  generated client.
- Contract tests различают minimal v1 inventory claims и detailed settings rows;
  Auto и Search legs различимы в payload.
- Planning package проходит strict OpenSpec validate.

## Решения Owner

- **D-001 (наследуется из v1):** Detailed settings snapshot — **out of v1**, этот
  change закрывает отложенный scope (`ai-package-v1-contract` owner-contract D-002).
- **D-002:** Dataset identity AI Package — `CampaignSettingsSnapshotV1` / manifest
  card `campaign_settings_snapshot`; **не** `cmp_*` A1 resource id как primary key
  export row.
- **D-003:** Первый implementation slice MAY читать только PG (AdvSetting +
  WBCabinet) без зависимости от A1 landing; WB-authoritative поля — из PG sync
  columns и provenance, не live WB на export path.

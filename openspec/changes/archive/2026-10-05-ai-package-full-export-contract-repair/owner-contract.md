# Owner Contract — ai-package-full-export-contract-repair

## Что хотим получить

Восстановить контракт Full AI Package так, чтобы внешний AI мог читать пакет
без исходного кода: детерминированный `PACKAGE_SUMMARY.json`, единый канонический
статус семейств, явная идентичность кампаний и ключевых слов, семантика
missing/zero/null и валидатор, согласованный с картами и каталогом пробелов.

## Зачем

Текущий экспорт не даёт машиночитаемого сводного слоя; статусы разъезжаются между
картами, gaps и потребителями; ключевые слова не документируют `leg_role` в
primary/join key; shop product orders/sales остаётся UNKNOWN вместо GAP.
`FULL_AI_PACKAGE_ACCEPTANCE_REPORT` в репозитории отсутствует — принимаем
координаторские gap-лейблы и locked semantic contract как вход.

## В scope (locked)

- `PACKAGE_SUMMARY.json` в ZIP и manifest hashes; `zip_determinism_contract`:
  `PAYLOAD_HASH_ONLY` (byte-identical ZIP — follow-up, out of scope).
- Канонический enum семейств: `COMPLETE|PARTIAL|GAP|UNSUPPORTED|FAILED`; fail closed
  на неизвестных токенах; shop sales family — GAP, не UNKNOWN.
- Три семейства настроек: current PARTIAL; settings history GAP; change events GAP
  (без новых коллекторов).
- Блок `campaign_identity` с `campaign_id_equals_physical_adv_id: true` только если
  код это подтверждает.
- Keyword primary/join key: `adv_id`, `leg_role`, `nmid`, `norm_query`, `date` —
  согласованно в DATA_MAP, card grain, coverage identity keys.
- Per-family `missing_zero_null`; убрать silent zero-fill только если найден.
- Validator: summary vs cards/gaps; GAP/PARTIAL с reason; keyword key с leg_role.
- Unit-тесты: summary exists, enum, согласованность, campaign flag, leg_role key,
  settings/history/events GAP, determinism per-file sha256 (не ZIP archive).

## Out of scope (locked)

- Новые коллекторы, settings-history collector, change-event persistence.
- ChangeSet, apply, production WB writes, post-check, MCP/API, Store DRR.
- Нормализация ZIP timestamps / правки `encode.py` date_time.
- Подмена shop feed через `wb_common_stat` или funnel.

## Как поймём, что получилось

- Два билда с одинаковыми входами: совпадают per-file sha256 и manifest; summary
  объясняет семейства, ключи, gaps и zero/null без чтения Python.
- `poetry run pytest -m unit tests/unit/ai_package_v1/ -q` проходит.
- Validator отклоняет несогласованный summary/status/keys.

## Решения Owner

- **D-001:** Locked semantic contract `/tmp/ai-package-semantic-contract.md` —
  единственный источник семантики; не переоткрывать.
- **D-002:** Exporter ownership — `openspec/decisions/ai-package-v1-exporter-ownership/decision.md`;
  read-only под `app/modules/ai_package_v1/`.
- **D-003:** Shop-wide common sales collection ≠ AI Package shop feed export;
  `shop_product_orders_sales_feed` остаётся GAP по дизайну.

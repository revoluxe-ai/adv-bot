## Why

Стабильный A1 strict read-only collect и generic strict single-NMID audit
должны опираться на одни и те же Owner-bot read-only primitives. Discovery и
операционный t1048 показали, что расхождение async/resource orchestration и
несогласованные adapter seams дают section `RuntimeError`/`AttributeError` и
легитимный `PARTIAL`, хотя output contract и `write_budget.writes=0` сохраняются.
Нужен reusable shared evidence plane, а не параллельный ProKraft-specific stack.

## What Changes

- Вводится formal shared contract **Job-scoped read-only evidence plane** для
  collectors, использующих Owner-bot DI, WB adapters и PG reads.
- Выравнивается lifecycle: один совместимый event loop и deterministic cleanup
  на Job execution для shared async loading (без cross-loop reuse module-level
  SQLAlchemy engines).
- Strict single-NMID plane переводится на supported Fullstats/orders paths из
  `wb_api_readonly_ops` и official adapters; orphan API calls запрещены.
- PG read strategy становится Job-safe и reusable (общий с A1-stable asyncpg
  path или эквивалентный shared factory), без ProKraft-specific reader.
- Reader failures нормализуются в typed GAP/error provenance для collector output
  contracts.
- Добавляется focused test contract: async lifecycle, adapter seam, resource
  cleanup, A1 non-regression.
- **Не меняются** Registry/resolver semantics, не создаётся новый collector id,
  не изобретаются stock/full attribution catalogs без подтверждённого shared
  source.

## Capabilities

### New Capabilities

- `owner-bot-read-only-evidence-plane`: reusable Job-scoped read-only evidence
  loading contract (async lifecycle, shared WB/PG primitives, typed reader
  failures, zero writes).

### Modified Capabilities

- Нет delta к archived/main `strict-single-nmid-read-only-audit` requirements.
  Этот change stabilizes **implementation plane** под уже archived audit
  contract, не расширяя NMID audit semantics.

## Impact

- `scripts/strict_single_nmid_audit_owner_bot_plane.py` (primary consumer refactor)
- Potential shared module under `scripts/wb_api_readonly_ops/` or adjacent
  Owner-bot read facade (extract, not duplicate A1 collector body)
- `scripts/a1_strict_read_only_contract_collect.py` — regression-only verification
- Tests under `tests/unit/scripts/` (and optional Job harness fixtures)
- **Out of scope:** `scripts/REGISTRY.yaml`, resolver, new collector registration,
  production writes, mass migration of unrelated scripts.

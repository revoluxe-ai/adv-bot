## Why

Сейчас оператор и collect опираются на уже зашитые семьи клиентов и не имеют
воспроизводимой карты «что вообще умеет локальный swagger vN» — path × method ×
семья. Без явного inventory-артефакта следующий map-driven collect неизбежно
скатывается к угадыванию URL, что запрещено стеком scripts→WB API. Нужен
offline разбор уже сохранённых swagger, пока swagger sync и Stage B ещё не
owed.

## Evolution Context

```text
EVOLUTION_LINK: LINKED
STAR_ID: wb-safe-readonly-collect
STAR_TITLE: Безопасный постоянный сбор WB API-данных
CARD_PATH: openspec/evolution/wb-safe-readonly-collect.md
NORTH_STAR: read-only WB выгрузка по shop_id из карты API → локальный архив
INCREMENT_ID: INC-RO-03
CURRENT_INCREMENT: API Master map path×method×family from local vN swagger (no network, no client gen)
CONTRIBUTION_TO_NORTH_STAR: Explicit allowlist of API capabilities for later map-driven collect
```

**IN_SCOPE (owed):**

- разбор локальных `vN/swagger` → воспроизводимый inventory map
  (path × method × family)

**FORWARD_COMPATIBILITY_CONSTRAINTS:**

- не invent URL;
- не live download swagger в этом increment;
- не генерация клиента

**OUT_OF_SCOPE (этот change):**

- swagger status/sync (INC-RO-02);
- Stage B / Web CLEAN_DUMP / map-driven permanent collect (INC-RO-04);
- read-only token hardening (INC-RO-05);
- новый collect Job DoD / вызовы WB API;
- finance / mutation write

**FUTURE_INCREMENTS (context only, не DoD):**

- INC-RO-02 — только при доказанном client gap
- INC-RO-04 — map-driven permanent collect + Web Stage B
- INC-RO-05 — read-only token

## What Changes

- **Intent:** одна capability «API Master map» — offline inventory из
  локальных swagger без сети и без codegen.
- **Current behavior:** локальные swagger vN есть как артефакты codegen /
  inventory, но нет операторской команды и контракта на воспроизводимую
  карту path × method × family как allowlist для последующих increment.
- **Desired behavior:** оператор (или tooling) запускает разбор уже
  сохранённых swagger и получает детерминированный map-артефакт с
  привязкой к семействам API; отсутствие сети и отсутствие codegen —
  инварианты прогона.
- Появляется новая capability с требованиями к входу (локальные swagger),
  выходу (inventory map) и запретам (сеть, invent URL, client gen).
- Существующий read-only preflight/collect **не** меняет свои
  requirement'ы в этом change (API Master там уже в non-requirements).

## Capabilities

### New Capabilities

- `wb-api-master-map`: offline построение воспроизводимой карты
  path × method × family из локальных vN swagger; артефакт inventory как
  явный allowlist возможностей API для последующих increment (без сети,
  без codegen, без collect).

### Modified Capabilities

- _(нет)_ — `wb-api-read-only-preflight` и прочие main specs не меняют
  REQUIREMENTS; API Master остаётся отдельной capability.

## Impact

- **Затронутые зоны:** scripts/tooling вокруг локального swagger inventory;
  артефакт карты (формат и воспроизводимость — в design/specs). Живой WB
  API, Job collect, access plane и codegen **не** входят в owed scope.
- **Architecture:** опирается на accepted
  `openspec/decisions/scripts-wb-api-ops-stack/decision.md` (запрет invent
  URL / обхода swagger mapping). Этот increment сам WB не вызывает;
  placement CLI/парсера и формат map — уточняются в design; при необходимости
  reusable ownership/format decision — в `decisions/` change до apply-ready.
- **Risk:** неполный/нестабильный разбор YAML → ложный allowlist; смягчается
  детерминизмом, явной привязкой к версии swagger и честным gap при
  неразбираемых путях. Риск scope drift в sync/collect/codegen — fail-closed
  через Evolution Context.
- **Rollback:** удалить/не публиковать map-артефакт и CLI capability; на
  runtime collect и существующие клиенты не влияет (они не зависят от этой
  карты в INC-RO-03).

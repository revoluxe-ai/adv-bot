# V3-only: обесточить и выпилить updater v2

```text
STAR_ID: v3-only-retire-v2
STATUS: ACTIVE
OWNER: Owner
CREATED_AT: 2026-08-08T03:41:00Z
UPDATED_AT: 2026-08-08T03:41:00Z
DEPENDS_ON: none
```

## North Star

Paid auto-кампании работают только на updater v3: путь v2 больше не
исполняет автоматику, пользователи не переключаются на v2, а мёртвый код
`setting_auto_updater_v2` удалён после безопасной миграции и выноса
разделяемых типов, от которых ещё зависит V3.

## Capability Scope

- Aliases: retire v2, kill v2 updater, v3-only, выпилить v2, setting_auto_updater_v2
- Domains: shop-runner `auto_updater_version`; `AdvControlSystem` / v2 cascades;
  version toggle UI; migration `auto_updater_version` 2→3; shared `sales_state`
  imports used by V3; dead-code removal under `old_modules/setting_auto_updater_v2`
- Included outcomes:
  - все релевантные paid auto-кампании на v3 (нет «забытых» на v2);
  - runtime/entrypoints v2 не крутят рекламу; toggle на v2 недоступен;
  - shared types вынесены из v2-пакета, чтобы V3 не зависел от delete-target;
  - пакет v2 и dead tests удалены при зелёных gates;
  - при необходимости — краткая UX/comms «только V3».
- Excluded outcomes:
  - перепись логики V3 ladder / pause-on-empty / A/B Hold;
  - тариф 1000₽, channel-анонс affordable-звезды, free onboarding;
  - «удалить всё за один Change» без миграции и extract.

## Evolution Path

### INC-V2-MIGRATE-01 — Все paid auto на V3

```text
STATUS: ACTIVE
LINKED_CHANGES: none
```

Outcome: Все кампании, которые должны идти paid auto-updater’ом, имеют
`auto_updater_version=3` (или эквивалент «только v3»); новые не остаются на v2;
есть проверяемый критерий «0 (или allowlisted) кампаний на v2 в целевом scope».

Contribution to North Star: Без миграции cutover/delete ломают живые РК.

Scope boundary: data/version migration + guards «не создавать/не оставлять v2»;
не удаление пакета; не скрытие UI само по себе, если не нужно для миграции.

Evidence / completion: none yet.

### INC-V2-CUTOVER-01 — Обесточить v2 runtime + запретить toggle

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Shop-runner не вызывает v2 `AdvControlSystem` для auto; UI/API не
дают выбрать v2; попытка остаться на v2 безопасна (no-op / force v3).

Contribution to North Star: V2 перестаёт управлять рекламой.

Scope boundary: entrypoints/toggle; не `rm -rf` пакета; не extract sales_state
(если ещё нужны импорты — отдельный increment).

Evidence / completion: none yet.

### INC-V2-EXTRACT-01 — Вынести shared sales_state из v2-пакета

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Типы/`sales_state` (и прочие shared imports), от которых зависит V3,
живут вне `old_modules/setting_auto_updater_v2`; V3 импортирует новый путь.

Contribution to North Star: Разблокирует физическое удаление v2-дерева.

Scope boundary: move/re-export only; не менять семантику V3 ladder.

Evidence / completion: none yet.

### INC-V2-DELETE-01 — Удалить пакет setting_auto_updater_v2

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Пакет `setting_auto_updater_v2` и связанные dead tests удалены;
targeted/adjacent tests и import graph чисты.

Contribution to North Star: Legacy surface снят.

Scope boundary: delete после 0 callers; не rewrite V3 behavior.

Evidence / completion: none yet.

### INC-V2-COMMS-01 — Сообщить «только V3» (если нужно)

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Краткая коммуникация/in-bot copy: updater только V3, переключения на
v2 нет.

Contribution to North Star: Ожидания пользователей совпадают с runtime.

Scope boundary: copy only; не полный affordable-анонс (цена/pause).

Evidence / completion: none yet.

## Forward Compatibility Constraints

- Не удалять v2-пакет, пока V3 (или другие callers) импортируют из него.
- Cutover MUST предполагать миграцию или явный allowlist оставшихся v2.
- Не ломать `auto_updater_version` контракты биллинга/gates без отдельного
  решения (см. paid-regression bot_active / v2 path specs).
- Pause-on-empty и Hold остаются на v3-path; retire v2 не переписывает их DoD.

## Non-Goals

- Переписать V3 «заодно с delete».
- Смешать DoD с тарифом 1000 / empty-keywords pause / free onboarding.
- Трактовать EVOLUTION_PATH как обещанный backlog.

## Related North Stars

- Доступная автокампания… (`affordable-auto-pause-on-empty`) — соседняя
  продуктовая линия (pause/price); не дубликат. Soft: завершать pause на v3
  не блокирует migrate, но delete v2 не должен ломать pause wiring.

## History

- 2026-08-08T03:41:00Z — card created: Owner «выпилить v2» as nearest capability;
  separate star (not stuffed into affordable-auto-pause); Current =
  `INC-V2-MIGRATE-01` (migrate to v3 first).

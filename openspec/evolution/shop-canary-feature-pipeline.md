# Канареечный pipeline: новые фичи на ограниченном числе магазинов

```text
STAR_ID: shop-canary-feature-pipeline
STATUS: ACTIVE
OWNER: Owner
CREATED_AT: 2026-08-10T05:49:00Z
UPDATED_AT: 2026-08-10T05:49:00Z
DEPENDS_ON: none
```

## North Star

Новые продуктовые фичи сначала включаются и наблюдаются на ограниченном
Owner-наборе магазинов; остальные магазины остаются на прежнем безопасном
поведении до явного расширения allowlist или промоушена. Canary — способ
катить, а не замена DoD самих фич.

## Capability Scope

- Aliases: canary pipeline, shop canary, канарейка, limited shops rollout,
  canary allowlist, fail-closed feature gate, pilot shops
- Domains: shop-scoped enablement / allowlist SoT; per-feature canary id;
  fail-closed runtime gate; observe canary vs control; promote / expand /
  rollback with Owner GO; adoption pattern for subsequent product features
- Included outcomes:
  - durable allowlist магазинов для canary;
  - fail-closed gate: фича X только для canary-shops; вне списка — старое
    поведение;
  - явный per-feature canary membership contract (без ad-hoc копипасты);
  - наблюдаемость отличия canary vs control (минимально достаточный сигнал);
  - путь expand / rollback без silent flip-all;
  - подключение следующих product-фич к pipeline после foundation.
- Excluded outcomes:
  - реализация pause / price / billing / comms affordable-звезды как DoD
    этой звезды;
  - retire updater v2;
  - auto-broad enablement без Owner GO;
  - «катить всё подряд» или обязательный canary для локальных bugfix;
  - полноценный A/B эксперимент-фреймворк / speculative platform.

## Evolution Path

Owner achievement route (2026-08-10, advisory — not DoD):
`INC-CANARY-ALLOWLIST-01` → `INC-CANARY-CONTRACT-01` →
`INC-CANARY-OBSERVE-01` → `INC-CANARY-PROMOTE-01` →
`INC-CANARY-ADOPT-01`. Hypothesis order below matches that route.

### INC-CANARY-ALLOWLIST-01 — Shop allowlist + fail-closed gate

```text
STATUS: ACTIVE
LINKED_CHANGES: none
```

Outcome: Есть проверяемый durable SoT allowlist магазинов и fail-closed
gate: выбранная canary-фича включается только для магазинов из списка;
магазины вне списка сохраняют прежнее поведение; поведение доказано
тестами (in-list / out-of-list).

Contribution to North Star: Без SoT+gate канареечный pipeline не существует;
это foundation для всех следующих increments.

Scope boundary: allowlist SoT + gate helper/contract + tests; не per-feature
membership registry как отдельный product surface; не observability
dashboard; не promote/expand UX; не wiring конкретной pause/price фичи.

Evidence / completion: none yet.

### INC-CANARY-CONTRACT-01 — Per-feature canary membership contract

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: У каждой новой canary-фичи явный canary-id и правила membership
(как объявляется, где читается, default deny), без копипасты ad-hoc флагов
на каждую фичу.

Contribution to North Star: Единый способ подключать следующие фичи к
тому же allowlist/gate.

Scope boundary: contract / naming / registration pattern; не новый allowlist
SoT; не metrics; не auto-promote.

Evidence / completion: none yet.

### INC-CANARY-OBSERVE-01 — Canary vs control observability slice

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: По canary-shops виден отличимый сигнал от control (логи / метрики /
агрегат — выбрать в design Change) до решения о broad enable.

Contribution to North Star: «Проверить фичу» = не только включить, но и
увидеть эффект на ограниченном scope.

Scope boundary: minimal observe slice; не auto-promote; не полный
эксперимент-фреймворк.

Evidence / completion: none yet.

### INC-CANARY-PROMOTE-01 — Promote / expand / rollback + Owner GO

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Явный путь расширить allowlist, промоутнуть фичу шире или
откатить canary без silent flip-all; broad enable требует Owner GO.

Contribution to North Star: Безопасный выход из пилота и контролируемый
rollback.

Scope boundary: lifecycle promote/expand/rollback; не product-логика фич;
не обязательный UI, если достаточно ops/config path (уточнить в Change).

Evidence / completion: none yet.

### INC-CANARY-ADOPT-01 — Adopt canary на следующей product-фиче

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome: Конкретная следующая product-фича (например slice из
`affordable-auto-pause-on-empty` или иная Owner-выбранная) едет только
через canary-shops до Owner promote; foundation уже на месте.

Contribution to North Star: Первый реальный canary-run доказывает pipeline
на живой фиче.

Scope boundary: adoption одной выбранной фичи; не построение всей
canary-платформы «заодно»; DoD самой фичи остаётся в её звезде/Change.

Evidence / completion: none yet.

## Forward Compatibility Constraints

- Default deny: вне allowlist фича MUST NOT включаться «случайно».
- Per-feature canary id: один allowlist SoT MAY обслуживать много фич;
  membership на фичу явный.
- Promote ≠ silent flip-all: broad enable только после явного Owner GO /
  documented promote path.
- Не хардкодить shop ids внутри business-логики фичи; gate читает SoT.
- Локальный прецедент `card-ab-hold-mode` allowlist/flag — pattern donor,
  не обязан становиться общим SoT без явного Change.
- Canary не заменяет product acceptance / verify DoD самой фичи.

## Non-Goals

- Вшить canary в DoD текущих pause/price Changes без отдельного adopt
  increment / Owner pick.
- Сделать canary обязательным для каждого bugfix / refactor.
- Построить полный experimentation platform «на вырост».
- Трактовать EVOLUTION_PATH как обещанный backlog.

## Related North Stars

- Доступная автокампания: пауза при пустых ключах + тариф 1000₽
  (`affordable-auto-pause-on-empty`) — потребитель canary для осторожного
  rollout следующих pause/billing slices; не дубль DoD.
- V3-only: обесточить и выпилить updater v2 (`v3-only-retire-v2`) —
  соседняя линия миграции; canary MAY позже ограничивать cutover, но не
  входит в DoD этой звезды.

## History

- 2026-08-10T05:49:00Z — card created from Owner `/opsx-evolution` GO:
  near-term need — canary pipeline to validate new features on a limited
  shop set; ACTIVE `INC-CANARY-ALLOWLIST-01`; Related to affordable-pause
  and v3-only stars as consumers, not parents.

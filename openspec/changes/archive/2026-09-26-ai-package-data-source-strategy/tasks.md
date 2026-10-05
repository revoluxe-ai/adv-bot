# Tasks — ai-package-data-source-strategy

Планировочный architecture change: поставка — согласованный пакет
`owner-contract`, `proposal`, Proposed decision, `design` и четыре delta specs.
Product implementation (коллекторы, backfill, CSV poller, DDL, экспортёр ZIP,
запись в `app/`) **вне scope apply** этого change.

## 1. Границы scope и named future changes

- [x] 1.1 Зафиксировать inventory поставки этого change: только артефакты под
      `openspec/changes/ai-package-data-source-strategy/` (включая
      `decisions/shop-data-source-strategy/decision.md` со status `Proposed`);
      MUST NOT считать поставленными оперативные коллекторы, исполняемый
      backfill, CSV poller, схему хранения, экспортёр ZIP, JSON ответа AI,
      preview/apply, Telegram UI, создание/управление кампаниями и любые правки
      `app/`, миграций и k8s.
- [x] 1.2 Явно перечислить named future implementation changes (только граница,
      без задач на реализацию): оперативный сбор dataset; исторический backfill;
      асинхронные CSV и ожидание готовности; схема хранения накопленных dataset;
      чтение накопленного PostgreSQL/ClickHouse в пакет. MUST NOT дублировать
      `shop-wide-campaign-data-collection` (обнаружение кампаний вне инвентаря)
      и MUST NOT переопределять формат ZIP `ai-package-v1-contract`.
- [x] 1.3 Зафиксировать открытый пункт Owner: источник товарных заказов и продаж
      магазина остаётся неназначенным до evidence; этот change MUST NOT назначать
      supplier GET shop-контуром; будущее отдельное decision MAY выбрать источник
      по evidence (не задача apply текущего change).

## 2. Согласованность planning artifacts (read-only)

- [x] 2.1 Пройти traceability
      `owner-contract.md` → `proposal.md` →
      `decisions/shop-data-source-strategy/decision.md` → `design.md` →
      `specs/data-source-selection|grain-preservation|collection-modes|coverage-provenance/spec.md`:
      каждое Owner-решение 1–9 и граница «чего не делаем» отражены без
      ослабления MUST/MUST NOT.
- [x] 2.2 Подтвердить preservation условных веток lifecycle (design L3, L7):
      если допустим backfill/CSV → история MUST идти отдельным режимом; иначе →
      явный разрыв с периодом и `reason_codes`; успешный оперативный тик MUST NOT
      делать историю полной; период одного оперативного запроса MUST NOT
      расширяться.
- [x] 2.3 Подтвердить четыре независимых измерения полноты и fail-closed для
      `UNKNOWN` во всех четырёх specs `coverage-provenance` без схлопывания в
      пустой успех.
- [x] 2.4 Подтвердить границы capabilities: ни одна spec MUST NOT требовать
      выбора физической таблицы, DDL, коллекторов или назначения источника
      товарной ленты; decision остаётся `Proposed` до archive.

## 3. Accepted decisions — только цитирование, без ослабления

- [x] 3.1 Сверить ссылки на Accepted decisions в `design.md` и decision:
      `mode-defaults-policy-ownership` (сбор MUST NOT владеть `bot_active` и
      mode defaults); `orders-or-sales-reports-read-identity` (identity
      operator-семьи, не shop-источник); `clickhouse-sql-database-qualification`
      (будущий CH SQL — `default_db.<object>`, не в этом change).
- [x] 3.2 Убедиться, что planning package не ослабляет Accepted identity
      `ORDERS_OR_SALES_REPORTS_READ` и не назначает shop-контур supplier GET.

## 4. OpenSpec verification gates (pre-archive)

- [x] 4.1 Выполнить `openspec validate ai-package-data-source-strategy` — MUST
      PASS без правок product-кода.
- [x] 4.2 Выполнить `/opsx-planning-review change=ai-package-data-source-strategy`
      (read-only) — MUST PASS до apply/archive.
- [x] 4.3 Выполнить `/opsx-verify change=ai-package-data-source-strategy`
      (read-only) — MUST GO; при Task completion mismatch или modality drift —
      STOP, исправить planning artifacts через `/opsx-update`, не `app/`.
- [x] 4.4 Выполнить `git diff --check` по затронутым planning-файлам change;
      MUST NOT включать в apply секреты, `.env` и product-диффы вне scope.

## 5. Apply phase — planning closure only

- [x] 5.1 Apply этого change ограничить закрытием чеклиста `tasks.md` и
      опциональной синхронизацией delta specs; MUST NOT открывать work на
      коллекторах, poller, DDL, ZIP exporter или интеграционных тестах сбора WB.
- [x] 5.2 Если `/opsx-apply` предлагает product-задачи (миграции, `app/`,
      collectors, poller) — отклонить как OUT_OF_SCOPE; граница зафиксирована в
      proposal «Границы следующих независимых changes» и в design Non-Goals.
- [x] 5.3 После PASS verify: при необходимости выполнить
      `/opsx-sync-specs change=ai-package-data-source-strategy` для переноса
      четырёх capabilities в `openspec/specs/` по политике репозитория; MUST NOT
      смешивать sync с product implementation.

## 6. Archive и promotion decision

- [x] 6.1 Выполнить `/opsx-archive change=ai-package-data-source-strategy` только
      после закрытия секций 1–5 и verify GO.
- [x] 6.2 При archive: reusable Proposed decision
      `shop-data-source-strategy` MAY промотиться в
      `openspec/decisions/` со status `Accepted`; до archive decision MUST
      оставаться `Proposed` в каталоге change.
- [x] 6.3 После archive зафиксировать handoff для named future changes (секция 1.2):
      implementation teams открывают **отдельные** changes; инвариант этого
      decision/specs обязателен для всех будущих контуров накопления и чтения
      пакета.

## Telegram UI / Message Safety

N/A — change не затрагивает Telegram payloads.

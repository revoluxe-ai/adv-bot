# Design: telegram-ai-package-export

## Context

`PackageZipAssembler.assemble_zip(shop_id, period)` уже собирает Full AI
Package. Excel-выгрузка магазина показывает рабочий ownership seam
`verify_user_owns_wb_user_cabinet` и доставку `BufferedInputFile`, но её
callback и writer настроек нельзя перегружать. Бот ACK'ает callback в
middleware, поэтому handler не вызывает `callback.answer()`.

## Goals / Non-Goals

Goals:

- Одна кнопка и один callback.
- Серверный read-only export через канонический assembler.
- Понятные отказы: доступ, mapping, сборка, размер Telegram, повторный клик.

Non-Goals:

- Выбор периода в UI, object storage, второй exporter, WB/PG/CH writes.

## Architecture Decision References

- `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` (Accepted,
  пункт 5 сужен этим change: Telegram только transport).
- `openspec/changes/telegram-ai-package-export/decisions/telegram-ai-package-transport-adapter/decision.md` (Proposed).
- `openspec/decisions/clickhouse-sql-database-qualification/decision.md` не
  меняется: CH читает assembler, не handler.

## Ownership & Placement

| Слой | Роль |
|---|---|
| `ai_package_v1.export.PackageZipAssembler` | Единственный ZIP owner |
| `shop_ai_package_export.flow` | Период V1, read-only shop_id, имя/caption, in-process lock |
| `handlers/shop_ai_package_export.py` | Auth, сообщения, `send_document` |
| `shop_menu.message.build_shop_main_keyboard` | Кнопка |

Handler MUST NOT импортировать WB write hub, ClickHouse client или
`session.commit`.

## Decisions

- Период V1 зашит в `v1_shop_menu_export_period()` → `ExportPeriod`.
- Кнопка видна в FREE и PAID: это read-only value, не paid automation.
  Стоит сразу после блока Excel, отдельным callback.
- Lock — `asyncio.Lock` на `(telegram_user_id, wb_user_cabinet_id)` в
  процессе. Redis billing lock — чужой домен, новая job-система не нужна.
  Другие реплики бота lock не разделяют.
- Размер ZIP не сравнивается с захардкоженным лимитом. Отказ API
  (`TelegramBadRequest` с маркером размера) → явный текст. Пакет не режется.
- Caption режется по `TELEGRAM_CAPTION_LIMIT` из `app.client_bot.const`.

## Lifecycle

LIFECYCLE_STATUS: DERIVED

Источник шагов: `owner-contract.md` «Контракт поведения». Новых развилок нет.

1. Пользователь нажимает кнопку. SOURCE: owner-contract §1, кнопка меню.
2. Бот берёт `from_user.id` и проверяет владение `WBUserCabinet`. Чужой →
   отказ, assembler не вызывается. SOURCE: owner-contract §2.
3. Свой → in-process lock. Если занято → «уже формируется». SOURCE: §9.
4. Иначе «Формирую AI-пакет…», read-only resolve `shop_id`. Нет mapping →
   fail closed. SOURCE: §3, §6.
5. `ExportPeriod` 2026-09-21..2026-10-04 и `assemble_zip`. SOURCE: §4, §5.
6. Успех → `send_document`. Ошибка сборки или отправки → безопасный текст.
   Отказ по размеру → явный текст без урезания ZIP. SOURCE: §5, §7, §8, §10.

## Risks / Trade-offs

- [Lock только в процессе] → вторая реплика может собрать пакет параллельно.
  Для V1 это принято; общий Redis lock не вводится.
- [Долгий export держит worker] → пользователь видит ack сразу; таймаут
  callback закрывает middleware. Отдельной очереди нет.
- [Caption обрезает длинный shop_id] → период и факт успеха остаются.

## Migration Plan

Деплой не входит в change. Откат — убрать кнопку и handler. Данных миграций нет.

## Open Questions

Нет implementation-critical вопросов.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed (transport narrowing)
- [x] implementation layer matches decision

## Semantic write target

SEMANTIC_WRITE_TARGET_STATUS: NOT_APPLICABLE

Обоснование: нет external/destructive mutation бизнес-состояния. Один
доказанный read target — `PackageZipAssembler`. Telegram `send_document` —
доставка bytes, не конкурирующая write-нога WB/PG/CH.

## Product acceptance

PRODUCT_ACCEPTANCE_REQUIRED: true

Пользовательский временной поток кнопки (не write кампаний). MEANING_LOCK
закрыт `NOT_APPLICABLE` выше. Lifecycle DERIVED из reviewed owner-contract.
SIDE_EFFECT_PROOF: unit-тесты наблюдают `send_document` и отсутствие
assembler при отказе.

## DESIGN_READINESS

```text
PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: not_applicable
RECOVERY_SEMANTICS_RESOLVED: not_applicable
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
DESIGN_STATUS: READY
REASON: none
```

`WRITE_AUTHORITY_RESOLVED` / `RECOVERY_SEMANTICS_RESOLVED` = not_applicable:
change не пишет durable business state и не восстанавливает его. Единственный
side effect — сообщение Telegram.

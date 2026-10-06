# Proposal: telegram-ai-package-export

## Why

Локальный acceptance export AI-пакета зависит от туннелей к PostgreSQL и
ClickHouse на машине пользователя. Telegram-бот уже работает в инфраструктуре
WB Sky и должен отдавать тот же Full AI Package через штатные read-only
подключения сервера.

## What Changes

- В меню магазина появляется кнопка `📦 Выгрузить AI-пакет`.
- Отдельный callback несёт только `WBUserCabinet.id`.
- После проверки текущего владельца сервер резолвит `WBCabinet.shop_id` и
  вызывает существующий `PackageZipAssembler.assemble_zip`.
- ZIP уходит в чат через `send_document`. Повторный клик в том же процессе не
  запускает вторую сборку.
- Период V1 фиксирован: 2026-09-21..2026-10-04, через канонический
  `ExportPeriod`, в одном seam.

## Capabilities

### New Capabilities

- `telegram-ai-package-export`: human transport Full AI Package из меню
  магазина без второго exporter.

### Modified Capabilities

- Нет. Семантика `ai-package-v1-exporter` не меняется: Telegram не становится
  владельцем datasets или ZIP encoding.

## Impact

- Клавиатура `build_shop_main_keyboard`.
- Новый callback и handler в client bot.
- Read-only SELECT `WBUserCabinet` → `WBCabinet.shop_id`.
- Вызов `PackageZipAssembler` на штатных PG/CH соединениях процесса бота.
- Уточнение accepted decision `ai-package-v1-exporter-ownership`: Telegram
  допустим только как transport adapter.

## Out of Scope

- PR Full AI Package / MCP, multi-window analysis, ChangeSet / Apply Authority.
- Shop-wide collectors, DRR/CPO control.
- UI выбора дат, object storage, урезание ZIP под лимит Telegram.
- Merge и deploy.

# Tasks: telegram-ai-package-export

## 1. Transport contract

- [x] 1.1 Сузить accepted decision `ai-package-v1-exporter-ownership`: Telegram только transport к `PackageZipAssembler`
- [x] 1.2 Зафиксировать callback `ExportShopAiPackage` только с `wb_user_cabinet_original_id`

## 2. Menu and handler

- [x] 2.1 Добавить кнопку `📦 Выгрузить AI-пакет` рядом с Excel, отдельным callback, для FREE и PAID
- [x] 2.2 Реализовать handler: ownership seam, read-only shop_id, период V1, `assemble_zip`, `send_document`
- [x] 2.3 In-process lock на пару user+cabinet и безопасные тексты отказа, включая отказ Telegram по размеру

## 3. Tests

- [x] 3.1 Unit: клавиатура, 64 байта callback, период, shop_id, assembler seam, документ, отказы, duplicate click, отсутствие writers
- [x] 3.2 Telegram payload limits: caption по `TELEGRAM_CAPTION_LIMIT`, статические тексты, worst-case shop_id

## 4. Gates

- [x] 4.1 Прогнать targeted pytest, ruff, pyright-strict по затронутым файлам, `git diff --check` и сверить spec

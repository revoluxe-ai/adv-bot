## Генерация клиента Wildberries Marketing & Promotions

Скрипт `tools/generate_wb_api_client.py` знает, какие Swagger‑файлы за какие клиенты отвечают, и при каждом запуске:

1. Выбирает доступный маппинг из таблицы ниже (по умолчанию — `promotion`).
2. Скачивает оригинальную русскоязычную спецификацию и сохраняет её в новую папку `app/core/mp/wb/api/generated/promotion/vN/swagger/`.
3. Транслитерирует YAML через `scripts/translit_yaml.py` и передаёт результат в `openapi-python-client`.
4. Генерирует пакет `marketing_and_promotions_client` (или указанное имя) внутри `vN`, не трогая предыдущие версии (`v1`, `v2` и т.д.). Таким образом старые клиенты остаются в репозитории.

| Key | Спецификация | Папка клиента | Пакет внутри версии |
| --- | --- | --- | --- |
| `promotion` | `https://dev.wildberries.ru/yaml/ru/08-promotion.yaml` | `app/core/mp/wb/api/generated/promotion` | `marketing_and_promotions_client` |

```bash
python tools/generate_wb_api_client.py
```

### Опции, пригодные для отладки

- `--spec-key` — выбрать другой прописанный Swagger (там же добавляйте будущие секции).
- `--force-version N` — явно задать номер версии `vN`, если нужно повторно сгенерировать тот же каталог (новые версии автоматически (`v1`, `v2`, `v3`, …) создаются без удаления старых).
- `--spec-url`, `--spec-filename`, `--package-name`, `--target-root` — позволяют переопределить поведение маппинга.
- `--meta none` и `--python-cmd openapi-python-client` остаются по умолчанию, но можно указать свои значения для тестов.

### Ручная генерация (если вдруг нужно)

```bash
python scripts/translit_yaml.py \
  app/core/mp/wb/api/generated/promotion/vN/swagger/08-promotion.yaml \
  app/core/mp/wb/api/generated/promotion/vN/swagger/08-promotion-translit.yaml

openapi-python-client generate \
  --path app/core/mp/wb/api/generated/promotion/vN/swagger/08-promotion-translit.yaml \
  --meta none \
  --output-path /tmp/promotion-client \
  --overwrite
```

Затем перенесите содержимое `/tmp/promotion-client` внутрь нужной версии (`vN/marketing_and_promotions_client/`), как делает скрипт.

> Примечание: `scripts/translit_yaml.py` требует зависимости `transliterate`. Установите её командой `pip install transliterate`, если ещё не добавлена в окружение.

> Примечание: `scripts/translit_yaml.py` требует зависимости `transliterate`. Установите её командой `pip install transliterate`, если ещё не добавлена в окружение.
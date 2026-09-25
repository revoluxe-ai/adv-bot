## Генерация клиентов WB API

## Обязательные правила (критично)

1. Для `promotion` использовать только **англоязычную** спецификацию:
   - `https://dev.wildberries.ru/api/swagger/yaml/en/08-promotion.yaml`
2. Для каждой новой версии `vN` обязательно сохранять в `vN/swagger`:
   - исходный swagger-файл (`08-promotion.yaml`),
   - `spec.lock.json` (hash и метаданные источника),
   - при необходимости `*-translit.yaml` (для русскоязычных спецификаций, не для `promotion`).
3. Версия без `swagger`-артефактов (`yaml` + `spec.lock.json`) считается неполной и не должна использоваться как эталон.

> Историческая ошибка: в старых версиях мог отсутствовать сохранённый swagger (например, `v4`). Для всех новых генераций это недопустимо.

Скрипт `tools/generate_wb_api_client.py` знает, какие Swagger‑файлы за какие клиенты отвечают, и при каждом запуске:

1. Выбирает доступный маппинг из таблицы ниже (по умолчанию — `promotion`).
2. Скачивает спецификацию и сохраняет её в папку `app/core/mp/wb/api/generated/<key>/vN/swagger/`.
3. При необходимости транслитерирует YAML через `scripts/translit_yaml.py` (для русскоязычных спецификаций) и передаёт в генератор подходящий файл.
4. Генерирует пакет (имя из таблицы) внутри `vN`, не трогая предыдущие версии (`v1`, `v2` и т.д.). Таким образом старые клиенты остаются в репозитории.

| Key | Спецификация | Транслитерация | Папка клиента | Пакет внутри версии |
| --- | --- | --- | --- | --- |
| `promotion` | `https://dev.wildberries.ru/api/swagger/yaml/en/08-promotion.yaml` | нет (англ. спецификация) | `app/core/mp/wb/api/generated/promotion` | `marketing_and_promotions_client` |
| `products` | `https://dev.wildberries.ru/api/swagger/yaml/ru/02-products.yaml` | да | `app/core/mp/wb/api/generated/products` | `content_products_client` |
| `reports` | `https://dev.wildberries.ru/api/swagger/yaml/en/12-reports.yaml` | нет (англ. спецификация) | `app/core/mp/wb/api/generated/reports` | `reports_client` |

```bash
python tools/generate_wb_api_client.py
python tools/generate_wb_api_client.py --spec-key products
```

### Что хранится в `vN/swagger`

Для каждой версии клиента сохраняются:

- исходная спецификация, например `08-promotion.yaml`;
- (при необходимости) транслитерированная версия `*-translit.yaml`;
- `spec.lock.json` с fingerprint спецификации:
  - `spec_key`, `spec_url`, `spec_filename`
  - `sha256`, `size_bytes`
  - `downloaded_at_utc`
  - `generator`, `generator_meta`

Это позволяет проверять, менялась ли удалённая спека, и повторно генерировать клиент из локально зафиксированного YAML.

Для `promotion` транслитерация должна быть выключена, так как источник обязателен `en/08-promotion.yaml`.

### Опции, пригодные для отладки

- `--spec-key` — выбрать другой прописанный Swagger (там же добавляйте будущие секции).
- `--force-version N` — явно задать номер версии `vN`, если нужно повторно сгенерировать тот же каталог (новые версии автоматически (`v1`, `v2`, `v3`, …) создаются без удаления старых).
- `--spec-url`, `--spec-filename`, `--package-name`, `--target-root` — позволяют переопределить поведение маппинга.
- `--meta none` и `--python-cmd openapi-python-client` остаются по умолчанию, но можно указать свои значения для тестов.
- `--check-spec-changed` — режим проверки: не генерирует клиент, сравнивает удалённый Swagger с последним `spec.lock.json`.
- `--use-cached-spec` — генерирует клиент из уже сохранённой спеки (`vN/swagger/<spec>.yaml`) и не скачивает её повторно. Требует `--force-version N` и существующую `vN`.

### Проверка изменений Swagger в CI

```bash
python tools/generate_wb_api_client.py --spec-key promotion --check-spec-changed
```

Коды завершения:

- `0` — изменений нет;
- `10` — удалённая спека изменилась относительно последнего lock;
- `1` — ошибка (нет lock, сетевой сбой, некорректный lock и т.п.).

Пример воспроизводимой перегенерации без сети из зафиксированного YAML:

```bash
python tools/generate_wb_api_client.py --spec-key promotion --force-version 4 --use-cached-spec
```

### Транслитерация

Для целевого маппинга можно отключить транслитерацию (поле `skip_transliteration` в `SWAGGER_TARGETS`). Это используется для **promotion**, так как берётся англоязычная спецификация (`en/08-promotion.yaml`), в которой идентификаторы уже на латинице. Для русскоязычных спецификаций транслитерация включается, чтобы кириллица в тегах и описаниях не ломала генератор.

### Ручная генерация (если вдруг нужно)

Для promotion (англ. спецификация, без транслитерации):

```bash
# Скачайте 08-promotion.yaml в vN/swagger/, затем:
openapi-python-client generate \
  --path app/core/mp/wb/api/generated/promotion/vN/swagger/08-promotion.yaml \
  --meta none
```

Для русскоязычной спецификации (с транслитерацией):

```bash
python scripts/translit_yaml.py \
  app/core/mp/wb/api/generated/promotion/vN/swagger/08-promotion.yaml \
  app/core/mp/wb/api/generated/promotion/vN/swagger/08-promotion-translit.yaml

openapi-python-client generate \
  --path app/core/mp/wb/api/generated/promotion/vN/swagger/08-promotion-translit.yaml \
  --meta none
```

Затем перенесите содержимое `/tmp/promotion-client` внутрь нужной версии (`vN/marketing_and_promotions_client/`), как делает скрипт.

> Примечание: `scripts/translit_yaml.py` требует зависимости `transliterate`. Установите её командой `pip install transliterate` (или через `poetry`), если используете маппинги с транслитерацией.

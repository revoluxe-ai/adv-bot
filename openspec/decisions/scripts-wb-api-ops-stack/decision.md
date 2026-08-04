# Decision: Scripts WB API ops — existing stack ownership

## Status

Accepted

## Context

Операторские скрипты (`scripts/` + `/opsx-scripts` Job) начинают вызывать WB API
для read-only исследования и best-effort сбора данных с Owner-local архивом.
Без reusable правила легко появится параллельный HTTP-клиент, свой бесконечный
retry-цикл или вызов prod API с локального Cursor — в обход Owner-bot token
plane и production устойчивости shop-runner.

Accepted decisions в `openspec/decisions/` сейчас не покрывают ownership /
layering для scripts→WB API. Нужен reusable invariant до реализации
`wb-readonly-api-preflight` и следующих increment'ов North Star
`wb-safe-readonly-collect`.

## Decision

Операторские Job-скрипты, которые читают WB API, MUST:

1. Жить как entrypoint в `scripts/` и исполняться в Owner-bot Job runtime
   (контур `/opsx-scripts`), а не как local Cursor → prod API.
2. Получать доступ к кабинету через существующий Owner-bot access plane по
   `shop_id` (тот же контур, что shop-runner / cabinet access).
3. Вызывать WB только через существующий слой `app/core/mp/wb/api`
   (managers/adapters/generated clients) — без нового raw HTTP-клиента.
4. Переиспользовать production паттерны ретраев / rate-limit / timeout этого
   стека (как в shop-runner path): finite attempts, bounded pause, без hang /
   бесконечного poll. Исчерпание бюджета → честный отказ / PARTIAL + gap, не
   silent retry forever.
5. Для audit/preflight/collect scripts по умолчанию соблюдать
   `READ_ONLY_NO_MUTATION` (GET и POST-read допустимы; mutation write
   запрещены). Finance/wallet/payout — вне этого класса ops без отдельного
   change.
6. В outputs/logs/архиве MUST NOT оставлять tokens, Authorization headers,
   cookies (secret-strip). Owner-local research payload (бизнес-данные) —
   допустим. Web-grade L2 body/ID redaction этим decision **не** требуется
   (отдельный park / Future increment).

## Applies to

- Entrypoints в `scripts/`, запускаемые через `/opsx-scripts` Job для WB API
- Capability `wb-api-read-only-preflight` (modes `preflight` + `collect`) и
  будущие increment'ы safe readonly collect, если они остаются scripts/Job
- Любой новый operator script, который ходит в WB API из этого репозитория

## Allowed

- Orchestration/CLI + Owner-local research archive (payload + report) в
  `scripts/` / Job outputs
- Reuse `get_access_for_wb_cabinet` (или эквивалентный существующий access API)
  + managers/adapters из `app/core/mp/wb/api`
- Вызовы методов, уже обёрнутых production retry/rate-limit
- Дополнительный **верхний** finite budget на весь Job/run (не вместо stack
  retries, а как anti-hang ceiling)
- POST-read, если семантика read-only и метод уже в existing client
- Best-effort collect с PARTIAL + gap report
- Secret-strip only (не полный Web sanitize)

## Forbidden

- Новый raw HTTP client / прямой `httpx`/`aiohttp` к WB в обход `wb/api`
- Параллельный самописный retry loop без лимита попыток/паузы
- Исполнение WB API с локального Cursor/laptop как основной execution path
- Mutation write (создание/изменение/остановка РК, ставки, whitelist и т.п.)
  из audit/preflight/collect scripts этого класса
- Finance/wallet/payout endpoints без отдельного явного change
- Угадывание URL вне существующего client/swagger mapping
- Попадание token / Authorization / cookies в outputs, report или Job logs
- Объявление Web `READ_ONLY_PREFLIGHT_PASS` / Web CLEAN_DUMP accept из этого
  ops-класса без отдельного change

## Examples

Good:

- Job вызывает scripts entrypoint → access по `shop_id` → existing adapter с
  production retry → Owner-local research zip (payload + report) после
  secret-strip → `/opsx-scripts` cp на машину Owner

Bad:

- Скрипт делает `requests.get("https://advert-api.wildberries.ru/...")` с
  `while True: sleep; retry`
- Агент дергает WB API с локальной машины, копируя token в чат/логи
- Preflight «для удобства» вызывает write endpoint кампании
- Архив кладёт raw Authorization header «для отладки»

## Related specs

- `openspec/specs/wb-api-read-only-preflight/spec.md`

## Related changes

- `openspec/changes/wb-readonly-api-preflight` (INC-RO-01)
- North Star: `openspec/evolution/wb-safe-readonly-collect.md`

## Review checklist

- [x] existing decisions searched (`openspec/decisions/index.md` — mode-defaults,
      clickhouse SQL; не покрывают scripts WB API ops)
- [x] relevant decisions cited (нет applicable accepted; поэтому Proposed)
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision (apply 2026-08-04: scripts/wb_api_readonly_ops + existing hub/managers)

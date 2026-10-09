# Owner Contract

## Что хотим получить

Канонический контракт памяти решений и экспериментов WB Sky: почему предлагалось
изменение, на каких фактах оно основано, какой ChangeSet связан, было ли применение
подтверждено отдельным Apply-контуром, и чем закончилась проверка гипотезы.
Будущие ChatGPT / API / MCP агенты смогут отвечать на вопросы «что решили», «почему»,
«что ожидали», «применили ли», «сработало ли», «пробовали ли похожее раньше».

## Зачем

Сейчас есть снимки настроек, dry-run ChangeSet и отдельные контуры экспериментов
(A/B Hold), но нет единого семантического слоя «решение → ожидание → результат».
Без него AI повторяет гипотезы и не может аудировать прошлые рассуждения.

## Что должно остаться неизменным

- `campaign-settings-history` остаётся authority «какие настройки были / менялись».
- Apply Authority (PG-only V1 на `stage`) остаётся единственным authority production mutation;
  память хранит только `ApplyEvidenceRef` / `DryRunReceiptRef`, без копирования receipt body.
- A/B Hold lifecycle и write-path — отдельный продуктовый контур; эта память только
  ссылается на него, не подменяет.
- AI Package export остаётся read-only; новые поля — только после отдельного slice.

## Чего сейчас не делаем (post–Slice A merge scope)

- PostgreSQL persistence, миграции, production memory writes (Slice B+).
- Apply/exposure **ingest** runtime (Slice C) — ссылки только в домене.
- MCP transport и расширение ZIP AI Package (slice F).
- Слияние с campaign-settings-history, attribution-facts, shop-wide collection.
- LLM как единственный судья успеха эксперимента.

## Как поймём, что получилось

- Принят spec + design + proposed architecture decision с явными границами ownership.
- Описаны lifecycle, append-only corrections, idempotency и reader port.
- Implementation slices A–F согласованы с фактическим состоянием репозитория
  (Apply Authority V1 на stage; memory Slice A — domain+ports+test fake; AI Package — slice F).

## Решения Owner

- Память решений — семантический слой WHY / EXPECT / OUTCOME; не write authority.
- `decision_id` и `experiment_id` — разные идентичности (1 решение → 0..N экспериментов
  в контракте; в V1 можно ограничить 0..1 на создании).
- `treatment_mode` (LIVE/SHADOW) отдельно от `experiment_design`; Apply — только
  через `ApplyEvidenceRef`, без payload; Slice A не ждёт Apply Authority.
- attribution-facts — будущий authoritative evidence слой (контракт в проекте,
  может быть не на stage); память решений не блокируется его отсутствием на Slice A.

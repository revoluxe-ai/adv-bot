# Design: Режим обслуживания WB Sky и приём заявки с телефоном

## Context

WB Sky переводится в временный maintenance-only режим. На production уже остановлены пять рекламных Deployment и PostgreSQL WB Sky; старый `wb-sky-bot` продолжает запускать `client_bot_run.py` и может зависеть от остановленной БД. Задача — заменить runtime на минимальный процесс, принимающий заявки без рекламных и DB-зависимостей. Идентичность Telegram-бота и секреты сохраняются; MAX и Tiriel остаются отдельными runtime.

## Goals / Non-Goals

**Goals**
- Оставить существующий Telegram bot token, одно сообщение и кнопку «Оставить заявку».
- Собрать валидный телефон через native contact пользователя или текст, передать владельцу.
- Не загружать DI приложения, SQLAlchemy, WB-клиенты и блоки рекламного управления.
- Исключить конкурирующие polling-потребители и иметь проверяемый rollback.

**Non-Goals**
- Никаких рекламных writes, восстановления старого UI, CRM и долгосрочного хранения заявок.
- Не менять PostgreSQL schema, Redis, ClickHouse и межпроектные deployments.
- Не выполнять снижение ноды/удаление PVC в этом change.

## Architecture Decision References

- `openspec/decisions/callback-start-entry-write-path/decision.md` (Accepted): callback Start не является registration write-path; maintenance entrypoint не открывает ни read, ни write DB session.
- `openspec/decisions/changeset-apply-authority-ownership/decision.md` (Accepted): ChangeSet Apply имеет отдельную ограниченную ownership-зону; maintenance runtime не получает никакого campaign apply adapter.
- Новое reusable ADR не требуется: change не переносит ownership доменных writers, а временно заменяет внешнюю точку входа отдельным read-only/notification процессом.

## Ownership & Placement

Owner UI и контактного сценария: `maintenance_leads_bot.py` — отдельный процесс приёма Telegram updates без import из производственного `app`, кроме **чтения литералов** из `app/client_bot/const.py` через AST.

Разрешено: presentation-only Telegram updates, валидация формата телефона и Telegram `sendMessage` одному Owner chat ID.

Запрещено: `client_bot_run.py` и его маршрутизаторы одновременно с maintenance poller, любые WB API/PG/Redis/ClickHouse вызовы из maintenance процесса и обход owner identity guard.

OPSX DevOps остаётся единственным разрешённым путём production rollout/scale; код change не имеет прав изменять Kubernetes сам.

## Decisions

1. **Автономный stdlib entrypoint.** Изолирует режим обслуживания от остановленного PostgreSQL и полной Poetry DI загрузки. Альтернатива — новый handler внутри существующего бота — отклонена из-за сложных обязательных импортов и доступа к БД.
2. **Переиспользовать Owner identity из const.py.** Парсить только `_BASE_ADMINS` и `MAIN_PRESENTATION_NOTIFY_TELEGRAM_ID`, требуя совпадения Owner с первым администратором; fail closed при рассогласовании. Альтернатива — отдельный env ID — привела бы к двум источникам истины.
3. **Атомарная граница подтверждения заявки — Telegram API.** Уведомление Owner происходит раньше user success. Нет новой БД; при сбое до подтверждения update возможен повторный send, поэтому notice содержит update ID. Альтернатива — durable outbox — увеличивает расходы и вводит хранилище, но может понадобиться позже.
4. **Single-poller cutover.** Deployment сохраняет `replicas=1`, стратегия `Recreate`, старый poller останавливается до нового. Альтернатива RollingUpdate приводит к конфликту `getUpdates` для общего токена.
5. **Proxy compatibility.** Legacy `PROXY` берётся из текущего Deployment; при отсутствии явного `HTTPS_PROXY` маппится в переменные для stdlib urllib. Xray не останавливается, пока не доказана работоспособность без него.

## Affected components

- Новое `maintenance_leads_bot.py`; `tests/unit/test_maintenance_leads_bot.py`.
- Единственный production target для cutover: `Deployment/prod-adv-bot/wb-sky-bot`.
- Existing bot token Secret, envFrom, network policies — без изменений.
- Уже остановленные `postgres-db` и рекламные workers не включать в rollout.

## Risks / Trade-offs

- **Owner не получает уведомление** → не подтверждать заявку пользователю, оставить update для retry, предоставить статус и корректный rollback.
- **Telegram API вернул OK, но процесс умер до установки offset** → возможен дубль уведомления; update ID позволяет найти повтор.
- **Два poller одновременно** → стратегия Recreate и проверка ровно одного pod.
- **Proxy/NAT недоступен** → transport smoke с текущим `PROXY`; не масштабировать xray.
- **Старый бот опирается на выключенную БД** → rollback приложения без восстановления БД может быть неполным; точно фиксировать это ограничение.
- **Unknown/unsupported state** → fail closed; не объявлять production PASS без реального phone-delivery smoke.

## Migration Plan

1. Независимо валидировать OpenSpec и unit scenarios; проверить Ruff/Pyright/CI и состояние PR #480.
2. Merge в `stage` разрешать только после OPSX DoD: push может двигать tag `:stage`, но не является production rollout.
3. Дождаться immutable образа и проверить digest. Snapshot текущих Deployment strategy/image/command/args/resources и token references, без раскрытия секретов.
4. /opsx-devops PLAN_WRITE с точной конфигурацией, CONTROL/release gate согласно `DEVOPS_DB_MIGRATIONS.md`, immutable image CAS и Recreate/command patch в допустимом порядке.
5. Проверить ровно один Ready poller, `/start`, callback и доставку тестовой заявки Owner. Не создавать конкурирующий canary с тем же token.
6. При ошибке остановить rollout и rollback на зафиксированный образ и конфигурацию; восстановление полноценного старого режима может требовать отдельного GO на PostgreSQL.
7. Только после подтверждения owner smoke рассматривать сокращение proxy или другие infra-изменения отдельным планом.

## Open Questions

- Канонический immutable image/digest после stage CI — устанавливается после merge.
- Реальная доставка Owner Telegram сообщения — требует smoke и подтверждения.
- Возможен ли прямой Telegram transport без xray — отдельная проверка после запуска.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing — not needed for temporary deployment-only entrypoint
- [x] implementation layer matches decision

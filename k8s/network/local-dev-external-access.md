# Внешний доступ к PG и CH с локали (по IP)

**ClusterIP** (`10.x.x.x`) с ПК недоступен. Для локали без `port-forward` — **NodePort на External IP worker-ноды**.

## Важно: Timeweb LoadBalancer (Proxy)

Сервисы с `LoadBalancer Ingress: x.x.x.x **(Proxy)**` (preset 391) для **Postgres/PgBouncer не подходят**:
с тем же паролем из secret получаете `password authentication failed`, хотя через port-forward и NodePort всё OK.

| Путь | Результат |
|------|-----------|
| `217.25.92.218:5432` (LB Proxy pooler) | auth fail |
| `<worker-ip>:31024` (NodePort pooler) | OK |
| `<worker-ip>:30432` (NodePort direct PG) | OK |
| `kubectl port-forward` → pooler | OK |

Локально используйте **NodePort**, не IP LoadBalancer для PG.

## Критично: не смешивать LB IP и NodePort

| Неправильно (SSL timeout ~60s) | Правильно |
|--------------------------------|-----------|
| `217.25.92.218:31024` | `92.255.79.78:31024` |
| `217.25.92.218:5432` (часто auth fail) | `92.255.79.78:31024` или `127.0.0.1:15432` (port-forward) |

**217.x** — Timeweb Proxy LB. **31024** — NodePort на worker **92.255.79.78**.

Проверка `.env`:
```powershell
.\scripts\verify-local-env.ps1
.\scripts\sync-local-env-from-k8s.ps1
```

## Postgres (PgBouncer через NodePort)

```powershell
kubectl get nodes -o wide
kubectl get svc postgres-db-pooler-external -n prod-adv-bot
```

| Параметр | Пример |
|----------|--------|
| Host | External IP worker (напр. `92.255.79.78`) |
| Port | NodePort pooler (напр. `31024`, не `5432`) |
| User | `advupdater` |
| Password | Secret `advupdater.postgres-db.credentials.postgresql.acid.zalan.do` |
| SSL | `POSTGRES_SSL_MODE=require`, `POSTGRES_SSL_INSECURE=true` |

```env
RUN_LOCAL=false
POSTGRES_MASTER_HOST=92.255.79.78
POSTGRES_REPLICA_HOST=92.255.79.78
POSTGRES_PORT=31024
POSTGRES_USER=advupdater
POSTGRES_SSL_MODE=require
POSTGRES_SSL_INSECURE=true
PG_POOL_SIZE=1
PG_MAX_OVERFLOW=0
```

Аварийно direct Postgres (минуя pooler): NodePort `30432` на `postgres-db-external`.

## ClickHouse (HTTP через NodePort)

```powershell
kubectl get svc clickhouse-external -n prod-analytics
```

| Параметр | Пример |
|----------|--------|
| Host | External IP worker |
| Port | NodePort `http` (напр. `32450`) |
| User | `adv_bot_user` (ConfigMap `prod-wb-gram`) |
| Password | Secret `common-secrets` → `CLICK_HOUSE_PASSWORD` |

```env
CLICK_HOUSE_HOST=92.255.79.78
CLICK_HOUSE_USER=adv_bot_user
CLICKHOUSE_PORT=32450
```

LB IP `194.87.215.163` тоже **(Proxy)** — при проблемах с CH предпочитайте NodePort.

## Синхронизация `.env`

```powershell
.\scripts\sync-local-env-from-k8s.ps1
```

Скрипт подставляет worker IP и NodePort (не LB 217.x / 194.x).

## Redis (только локально)

**Не** подставляйте из `prod-wb-gram` значения вроде `redis-master.prod-analytics` — с ПК они недоступны.

```env
REDIS_HOST=127.0.0.1
REDIS_MASTER_HOST=127.0.0.1
REDIS_REPLICA_HOST=127.0.0.1
REDIS_PORT=6379
```

Нужны **все три** переменные: `REDIS_HOST` (DI/cashews), `REDIS_MASTER_HOST` / `REDIS_REPLICA_HOST` (legacy-клиенты).

Запуск Redis (Docker Desktop должен быть включён):

```powershell
# Обязательно -p 6379:6379 (без этого порт не виден с Windows)
docker run -d --name adv-bot-redis -p 6379:6379 redis:7-alpine
docker ps
# Должно быть: 0.0.0.0:6379->6379/tcp
```

Если контейнер уже есть без `-p`, пересоздайте:
```powershell
docker stop adv-bot-redis; docker rm adv-bot-redis
docker run -d --name adv-bot-redis -p 6379:6379 redis:7-alpine
```

Проверка:

```powershell
Test-NetConnection 127.0.0.1 -Port 6379
```

## Port-forward (не канон)

In-app / `scripts/dev-tunnels.ps1` удалены. Канон — публичный IP + NodePort из `.env`.
Ручной `kubectl port-forward` — только с явным Owner GO; `DEV_TUNNELS_ENABLED`
должен оставаться `false`/`unset` для destructive tests.

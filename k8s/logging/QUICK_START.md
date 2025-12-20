# Quick Start: Fluent Bit → Error Collector → Telegram

## Что сделано

1. ✅ **FastAPI error-collector** - сервис для агрегации ошибок
2. ✅ **Fluent Bit конфиг** - фильтр ошибок и отправка в webhook
3. ✅ **K8s манифесты** - Deployment, Service, ConfigMap, Secret, CronJob
4. ✅ **Скрипты для применения** - PowerShell скрипты для быстрого деплоя

## Быстрый старт

### 1. Создайте Secret с Telegram данными

```powershell
kubectl create secret generic error-collector-secrets `
  --from-literal=telegram_bot_token='YOUR_BOT_TOKEN' `
  --from-literal=telegram_chat_id='YOUR_CHAT_ID' `
  --from-literal=redis_password='' `
  -n logging
```

### 2. Соберите и опубликуйте Docker образ

```powershell
# Из корня проекта
docker build -t your-registry/error-collector:latest -f error_collector/Dockerfile .
docker push your-registry/error-collector:latest
```

Затем обновите `k8s/logging/error-collector/deployment.yaml`:
```yaml
image: your-registry/error-collector:latest
```

### 3. Примените манифесты

```powershell
cd k8s\logging
.\apply-all.ps1
```

### 4. Настройте Fluent Bit

**Вариант A (рекомендуется):** Ручное редактирование ConfigMap

```powershell
kubectl edit configmap fluent-bit -n logging
```

Добавьте в конец файла (после существующих OUTPUT):

```ini
[FILTER]
    Name grep
    Match kube.*
    Regex log (Traceback|Exception|ERROR|CRITICAL|FATAL)
    Logical_Op or

[OUTPUT]
    Name http
    Match kube.*
    Host error-collector.logging.svc.cluster.local
    Port 8000
    URI /ingest
    Format json
    Json_date_key timestamp
    Json_date_format %Y-%m-%dT%H:%M:%S.%L
    HTTP_User agent
    Retry_Limit 3
```

**Вариант B:** Использовать скрипт (требует доработки под ваш формат ConfigMap)

```powershell
.\apply-fluent-bit-config.ps1
```

## Проверка

```powershell
# Статус подов
kubectl get pods -n logging -l app=error-collector

# Логи
kubectl logs -n logging -l app=error-collector --tail=50

# Health check
kubectl port-forward -n logging svc/error-collector 8000:8000
# В другом терминале:
curl http://localhost:8000/health

# Ручной запуск дайджеста
kubectl create job --from=cronjob/error-collector-digest test-digest -n logging
kubectl logs -n logging job/test-digest
```

## Структура файлов

```
error_collector/
  ├── main.py              # FastAPI приложение
  ├── redis_client.py      # Redis клиент
  ├── requirements.txt      # Python зависимости
  ├── Dockerfile           # Docker образ
  └── __init__.py

k8s/logging/
  ├── error-collector/
  │   ├── deployment.yaml  # Deployment
  │   ├── service.yaml     # Service
  │   ├── configmap.yaml    # ConfigMap с настройками
  │   ├── secret.yaml      # Secret (skeleton)
  │   ├── cronjob.yaml     # CronJob для часового дайджеста
  │   └── README.md        # Подробная документация
  ├── fluent-bit-errors-to-webhook.yaml  # Конфиг для Fluent Bit
  ├── apply-all.ps1         # Скрипт применения всех манифестов
  ├── apply-fluent-bit-config.ps1  # Скрипт применения Fluent Bit конфига
  └── QUICK_START.md        # Этот файл
```

## Архитектура

```
Fluent Bit (DaemonSet)
  └── [FILTER grep] → только ошибки
      └── [OUTPUT http] → POST /ingest
          └── error-collector (FastAPI)
              ├── Redis (дедупликация)
              └── Telegram API (hourly digest)
                  └── CronJob (каждый час)
```

## Что дальше?

1. Настройте мониторинг для error-collector
2. Добавьте алерты на недоступность сервиса
3. Настройте retention политику в Redis (TTL уже настроен на 3 часа)
4. При необходимости добавьте фильтрацию по namespace/pod labels

## Проблемы?

См. подробную документацию: `k8s/logging/error-collector/README.md`





# Error Collector - Установка и настройка

## Описание
Сервис для агрегации ошибок из Fluent Bit и отправки часовых дайджестов в Telegram.

## Предварительные требования
- Kubernetes кластер с доступом к namespace `logging`
- Redis доступен (в данном случае `redis2-master.prod-analytics.svc.cluster.local:6379`)
- Telegram бот создан и известны `BOT_TOKEN` и `CHAT_ID`

## Установка

### 1. Подготовка секретов

Создайте Secret с данными Telegram:

```powershell
kubectl create secret generic error-collector-secrets `
  --from-literal=telegram_bot_token='YOUR_BOT_TOKEN' `
  --from-literal=telegram_chat_id='YOUR_CHAT_ID' `
  --from-literal=redis_password='' `
  -n logging
```

Если у Redis есть пароль, укажите его в `redis_password`.

### 2. Сборка и публикация Docker образа

```powershell
# Соберите образ (замените на ваш registry)
docker build -t your-registry/error-collector:latest -f error_collector/Dockerfile .
docker push your-registry/error-collector:latest
```

Затем обновите `deployment.yaml`, заменив `image: error-collector:latest` на ваш образ.

### 3. Применение манифестов

```powershell
# Примените все манифесты
kubectl apply -f k8s\logging\error-collector\configmap.yaml
kubectl apply -f k8s\logging\error-collector\secret.yaml
kubectl apply -f k8s\logging\error-collector\deployment.yaml
kubectl apply -f k8s\logging\error-collector\service.yaml
kubectl apply -f k8s\logging\error-collector\cronjob.yaml
```

### 4. Настройка Fluent Bit

Fluent Bit уже установлен в namespace `logging`. Нужно добавить дополнительный output для отправки ошибок в error-collector.

#### Вариант A: Добавить конфиг в существующий ConfigMap (рекомендуется)

```powershell
# Получите текущий конфиг
kubectl get configmap fluent-bit -n logging -o yaml > fluent-bit-current.yaml

# Добавьте в секцию [OUTPUT] новый блок из fluent-bit-errors-to-webhook.yaml
# Или примените патч через kubectl patch
```

#### Вариант B: Использовать дополнительный ConfigMap (если Helm поддерживает)

Если Helm chart Fluent Bit поддерживает `extraConfigMaps`, можно добавить конфиг через values.

#### Вариант C: Ручное редактирование ConfigMap

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

После редактирования Fluent Bit DaemonSet автоматически перезагрузит конфиг.

## Проверка работы

### 1. Проверка Deployment

```powershell
kubectl get pods -n logging -l app=error-collector
kubectl logs -n logging -l app=error-collector --tail=50
```

### 2. Проверка Service

```powershell
kubectl get svc -n logging error-collector
kubectl port-forward -n logging svc/error-collector 8000:8000
```

Затем в другом терминале:

```powershell
curl http://localhost:8000/health
```

### 3. Тестовая отправка ошибки

```powershell
$testPayload = @{
    log = "ERROR: Test error message"
    kubernetes = @{
        namespace_name = "default"
        pod_name = "test-pod"
        container_name = "test-container"
    }
} | ConvertTo-Json

curl -X POST http://localhost:8000/ingest -H "Content-Type: application/json" -d $testPayload
```

### 4. Ручной запуск CronJob

```powershell
# Создать Job из CronJob
kubectl create job --from=cronjob/error-collector-digest error-collector-digest-manual -n logging

# Проверить логи
kubectl logs -n logging job/error-collector-digest-manual

# Удалить Job после проверки
kubectl delete job error-collector-digest-manual -n logging
```

### 5. Проверка Redis

```powershell
# Если есть доступ к Redis pod
kubectl exec -it -n prod-analytics redis2-master-0 -- redis-cli
# В Redis CLI:
KEYS errors:bucket:*
HGETALL errors:bucket:2024121720:abc123
```

## Мониторинг

- Логи error-collector: `kubectl logs -n logging -l app=error-collector -f`
- Логи CronJob: `kubectl logs -n logging -l job=digest`
- Статус CronJob: `kubectl get cronjob -n logging error-collector-digest`

## Устранение неполадок

1. **Ошибки не приходят в error-collector:**
   - Проверьте, что Fluent Bit конфиг обновлен
   - Проверьте логи Fluent Bit: `kubectl logs -n logging -l app=fluent-bit`
   - Проверьте, что Service error-collector доступен: `kubectl get endpoints -n logging error-collector`

2. **Telegram не получает сообщения:**
   - Проверьте Secret: `kubectl get secret error-collector-secrets -n logging -o yaml`
   - Проверьте логи error-collector на ошибки отправки

3. **Redis недоступен:**
   - Проверьте доступность Redis: `kubectl get endpoints -n prod-analytics redis2-master`
   - Проверьте NetworkPolicy (если используется)

## Обновление

```powershell
# Обновить образ
kubectl set image deployment/error-collector error-collector=your-registry/error-collector:v2 -n logging

# Проверить rollout
kubectl rollout status deployment/error-collector -n logging
```





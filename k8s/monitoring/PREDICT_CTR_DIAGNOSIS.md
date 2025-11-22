# 🔍 Диагностика проблемы с прогнозом CTR

## 📋 Информация о проблеме

- **Shop ID:** `76ffadfc-b81e-4ff8-9611-29b7c1c867dc`
- **Adv ID:** `30554463`
- **Проблема:** Нет прогноза CTR по ключам

## ✅ Текущий статус инфраструктуры

### Namespace
- Все поды находятся в namespace **`prod-adv-bot`** (не `default`)

### Сервисы
- ✅ **predict-ctr-service** работает в `prod-adv-bot`
  - Pod: `predict-ctr-service-7c9b64f7f9-mkk7h` (Running)
  - Service: `predict-ctr-service` (ClusterIP: 10.100.25.57:50053)
  - Статус: ✅ Работает

- ✅ **run-shop-update-worker** работает
  - Deployment: 4 реплики (все Running)
  - Статус: ✅ Работает

## 🔧 Настройка KUBECONFIG

Для автоматического использования правильного конфига kubectl:

### Вариант 1: Установить переменную окружения (рекомендуется)

```powershell
# Для текущей сессии PowerShell
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'

# Для постоянной установки (всех сессий)
[System.Environment]::SetEnvironmentVariable('KUBECONFIG', 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml', 'User')
```

### Вариант 2: Использовать скрипт инициализации

```powershell
# Загрузить настройки перед работой
. .\k8s\monitoring\setup-kubectl-config.ps1
```

## 🔍 Диагностика проблемы

### Шаг 1: Запустить скрипт диагностики

```powershell
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'
.\k8s\monitoring\diagnose-predict-ctr.ps1 -ShopId "76ffadfc-b81e-4ff8-9611-29b7c1c867dc" -AdvId 30554463
```

### Шаг 2: Проверить переменные окружения

```powershell
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'
kubectl get deployment run-shop-update-worker -n prod-adv-bot -o yaml | Select-String -Pattern "PREDICT_CTR" -Context 2
```

**Ожидаемые значения:**
- `PREDICT_CTR_HOST`: `predict-ctr-service.prod-adv-bot.svc.cluster.local` (или `predict-ctr-service`)
- `PREDICT_CTR_PORT`: `50053`

### Шаг 3: Проверить логи воркеров

```powershell
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'
kubectl logs -n prod-adv-bot deployment/run-shop-update-worker --tail=500 | Select-String -Pattern "update_predict_ctr|PredictCTR|30554463|grpc|UNAVAILABLE" -CaseSensitive:$false
```

### Шаг 4: Проверить логи predict-ctr-service

```powershell
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'
kubectl logs -n prod-adv-bot deployment/predict-ctr-service --tail=100
```

## 🛠️ Возможные проблемы и решения

### Проблема 1: Переменные окружения не установлены

**Решение:**
```powershell
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'
kubectl set env deployment/run-shop-update-worker -n prod-adv-bot PREDICT_CTR_HOST=predict-ctr-service.prod-adv-bot.svc.cluster.local PREDICT_CTR_PORT=50053
kubectl rollout restart deployment/run-shop-update-worker -n prod-adv-bot
```

### Проблема 2: Service в неправильном namespace

Если Service находится в `default`, а поды в `prod-adv-bot`:

**Решение 1:** Переместить Service в правильный namespace
```powershell
# Создать Service в prod-adv-bot
kubectl apply -f k8s\predict-ctr-service.yaml -n prod-adv-bot
```

**Решение 2:** Использовать полное DNS имя
```powershell
kubectl set env deployment/run-shop-update-worker -n prod-adv-bot PREDICT_CTR_HOST=predict-ctr-service.prod-adv-bot.svc.cluster.local
```

### Проблема 3: gRPC ошибки подключения

Если в логах есть ошибки типа `UNAVAILABLE` или `DNS resolution failed`:

1. Проверить что Service существует в правильном namespace
2. Проверить что переменная `PREDICT_CTR_HOST` указывает на правильный адрес
3. Проверить что порт `50053` открыт

### Проблема 4: Нет ключевых слов для кампании

Если прогнозы не сохраняются, возможно нет ключевых слов:

1. Проверить что кампания активна (`bot_active = true`)
2. Проверить что есть ключевые слова в базе данных
3. Проверить логи на сообщения "Нет ключевых слов для кампании"

### Проблема 5: Режим predict_ctr_mode

Проверить режим прогноза CTR для кампании:
- **V1** - прогноз по `adv_id` (legacy)
- **V2** - прогноз по `nmids` (новый)

Ключи в Redis:
- V1: `predict_ctr:{adv_id}:{keyword}`
- V2: `predict_ctr_v2:{nmids}:{keyword}`

## 📊 Проверка данных в Redis

Для проверки прогнозов в Redis нужен доступ к базе данных:

```python
# Пример проверки через Python
import redis

r = redis.Redis(host='...', port=6379, decode_responses=True)

# Для V1 режима
key_v1 = f"predict_ctr:30554463:{keyword}"
value = r.get(key_v1)

# Для V2 режима (нужно знать nmids)
nmids_str = ",".join(sorted(map(str, nmids)))
key_v2 = f"predict_ctr_v2:{nmids_str}:{keyword}"
value = r.get(key_v2)
```

## 🔄 Процесс обновления прогнозов CTR

1. **Воркер** (`run-shop-update-worker`) вызывает `update_predict_ctr()`
2. Для каждой активной кампании:
   - Получает ключевые слова через `get_calculated_keywords()`
   - Формирует gRPC запрос с `nmids` и `phrases`
   - Отправляет запрос в `predict-ctr-service:50053`
3. **predict-ctr-service** обрабатывает запрос и возвращает прогнозы
4. Воркер сохраняет прогнозы в Redis через `PredictCTRRedisManager`

## 📝 Чеклист диагностики

- [ ] KUBECONFIG настроен правильно
- [ ] Namespace определен (`prod-adv-bot`)
- [ ] Pod predict-ctr-service работает
- [ ] Service predict-ctr-service существует в правильном namespace
- [ ] Переменные окружения PREDICT_CTR_HOST и PREDICT_CTR_PORT установлены
- [ ] В логах нет ошибок gRPC
- [ ] Кампания активна (bot_active = true)
- [ ] Есть ключевые слова для кампании
- [ ] Режим predict_ctr_mode определен правильно
- [ ] Прогнозы сохраняются в Redis

## 📞 Полезные команды

```powershell
# Установить KUBECONFIG
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'

# Проверить статус всех компонентов
kubectl get pods -n prod-adv-bot | Select-String "predict|worker"

# Проверить Service
kubectl get svc -n prod-adv-bot predict-ctr-service

# Проверить переменные окружения
kubectl get deployment run-shop-update-worker -n prod-adv-bot -o yaml | Select-String "PREDICT_CTR"

# Перезапустить воркеры
kubectl rollout restart deployment/run-shop-update-worker -n prod-adv-bot

# Следить за логами
kubectl logs -f deployment/run-shop-update-worker -n prod-adv-bot | Select-String "predict_ctr"
```

---

**Дата создания:** 2025-11-18  
**Статус:** В работе






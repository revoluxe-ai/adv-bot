# 🚨 Исправление ошибки: Cluster has overcommitted memory resource requests

## Проблема

```
Alert: Cluster has overcommitted memory resource requests.
Severity: warning
Description: Cluster has overcommitted memory resource requests for Pods by 68.84G bytes
and cannot tolerate node failure.
```

### Анализ

**Ресурсы кластера:**
- Узел 1 (worker-192.168.0.6): 87.4 ГБ allocatable
- Узел 2 (worker-192.168.0.7): 10.1 ГБ allocatable
- **Всего**: ~97.5 ГБ allocatable
- **Проблема**: Сумма requests превышает это значение на 68.84 ГБ

Это означает, что если один из узлов отказывает, оставшиеся узлы не смогут разместить все поды.

---

## 🔧 Решение

### ШАГ 1: Диагностика текущего состояния

```bash
# Запустить диагностический скрипт
bash k8s/monitoring/analyze-memory-usage.sh
```

Скрипт покажет:
1. Информацию о узлах
2. Все Deployments с requests
3. Все StatefulSets с requests
4. Все DaemonSets с requests
5. Фактическое использование памяти
6. Суммарные requests по namespace

### ШАГ 2: Оптимизация requests/limits

**Перед изменениями:**
```yaml
resources:
  limits:
    cpu: "1"
    memory: 1Gi          # ❌ Слишком много
  requests:
    cpu: "1"
    memory: 1Gi          # ❌ Слишком много
```

**После изменений:**
```yaml
resources:
  limits:
    cpu: "1"
    memory: 768Mi        # ✅ Разумный лимит
  requests:
    cpu: "500m"
    memory: 512Mi        # ✅ Разумный request
```

**Изменено в:** `wbgram-original-deployment.yaml`

### ШАГ 3: Применение ResourceQuota

**Цель:** Предотвратить создание подов, которые превысят лимиты кластера.

#### 3.1 Для namespace `default`:

```bash
kubectl apply -f k8s/monitoring/resourcequota-default.yaml
```

**Что будет ограничено:**
- `requests.memory: 60Gi` - максимум 60 ГБ на requests
- `limits.memory: 80Gi` - максимум 80 ГБ на limits
- `pods: 200` - максимум 200 подов

#### 3.2 Для namespace `kube-prometheus-stack`:

```bash
kubectl apply -f k8s/monitoring/resourcequota-kube-prometheus-stack.yaml
```

**Что будет ограничено:**
- `requests.memory: 20Gi` - максимум 20 ГБ на requests (мониторинг требует больше)
- `limits.memory: 30Gi` - максимум 30 ГБ на limits

### ШАГ 4: Применить все изменения

```bash
# Обновить deployment
kubectl apply -f wbgram-original-deployment.yaml

# Применить ResourceQuota и LimitRange
kubectl apply -f k8s/monitoring/resourcequota-default.yaml
kubectl apply -f k8s/monitoring/resourcequota-kube-prometheus-stack.yaml
```

### ШАГ 5: Проверить статус

```bash
# Проверить ResourceQuota
kubectl get resourcequota -A
kubectl describe resourcequota default-quota -n default
kubectl describe resourcequota prometheus-quota -n kube-prometheus-stack

# Проверить LimitRange
kubectl get limitrange -A
kubectl describe limitrange default-limits -n default

# Проверить поды
kubectl get pods -A
kubectl top pods -A

# Проверить узлы
kubectl top nodes
```

---

## 📊 Ожидаемые результаты

### До исправления:
```
Узел 1: 87.4 ГБ allocatable
Узел 2: 10.1 ГБ allocatable
Сумма requests: ~165 ГБ  ❌ ПЕРЕГРУЗКА НА 68.84 ГБ
```

### После исправления:
```
Узел 1: 87.4 ГБ allocatable
Узел 2: 10.1 ГБ allocatable
Сумма requests: ~95 ГБ   ✅ В ПРЕДЕЛАХ ДОПУСТИМОГО
```

---

## 📋 Таблица рекомендуемых лимитов памяти

| Тип сервиса | requests | limits | Комментарий |
|-------------|----------|--------|------------|
| **Web Application** | 256Mi | 512Mi | Базовое приложение |
| **API Server** | 512Mi | 768Mi | Обработка запросов |
| **Bot (adv-bot)** | 512Mi | 768Mi | Телеграм бот |
| **Worker** | 512Mi | 1Gi | Фоновые задачи |
| **Cache (Redis)** | 1Gi | 2Gi | Требует больше памяти |
| **Database** | 2Gi | 4Gi | Особенно критично |
| **Prometheus** | 512Mi | 1Gi | Мониторинг |
| **Grafana** | 256Mi | 512Mi | Визуализация |

---

## 🔍 Дополнительные действия

### Опция 1: Масштабирование кластера

Если текущих ресурсов недостаточно:

```bash
# Добавить новый узел в кластер
# (зависит от провайдера облака)

# Или увеличить память на существующих узлах
```

### Опция 2: Включить автомасштабирование

```yaml
apiVersion: autoscaling.k8s.io/v2
kind: HorizontalPodAutoscaler
metadata:
  name: adv-bot-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: wbgram-original
  minReplicas: 1
  maxReplicas: 3
  metrics:
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
```

### Опция 3: Настроить Pod Disruption Budgets

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: adv-bot-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: adv-bot-test
```

---

## ⚠️ Важные замечания

1. **Requests vs Limits:**
   - `requests` - гарантирует выделение памяти при планировании пода
   - `limits` - максимум памяти, который может использовать контейнер

2. **Корректное соотношение:**
   - `requests` должен быть ≤ `limits`
   - Обычно: `limits = requests × 1.5` или `× 2`

3. **Миграция:**
   - Изменения применяются к новым подам
   - Для обновления старых подов:
     ```bash
     kubectl rollout restart deployment wbgram-original -n default
     ```

4. **Мониторинг:**
   - Активно мониторить использование памяти
   - Использовать Prometheus + Grafana alerts
   - Настроить оповещения при превышении 80% лимита

---

## 🛠️ Исправление других deployments

Если в кластере есть другие deployments с перегруженными лимитами:

```bash
# Найти все deployment с запросами памяти > 1Gi
kubectl get deployments -A -o json | \
  jq '.items[] | select(.spec.template.spec.containers[0].resources.requests.memory > "1Gi") | .metadata | "\(.namespace)/\(.name)"'
```

Для каждого deployment:
1. Проверить фактическое использование памяти
2. Уменьшить requests до реального использования
3. Установить limits в 1.5-2x от requests
4. Применить изменения

---

## ✅ Чек-лист решения проблемы

- [ ] Запустить диагностический скрипт
- [ ] Понять текущее использование памяти
- [ ] Обновить deployment файлы с новыми лимитами
- [ ] Применить ResourceQuota для namespace-ов
- [ ] Применить LimitRange для контроля лимитов
- [ ] Перезагрузить поды: `kubectl rollout restart deployment <name>`
- [ ] Проверить статус ResourceQuota: `kubectl describe resourcequota`
- [ ] Подтвердить, что алерт исчез
- [ ] Настроить мониторинг и алерты
- [ ] Документировать решение

---

## 📖 Полезные команды

```bash
# Просмотр ResourceQuota
kubectl describe resourcequota -A

# Просмотр LimitRange
kubectl describe limitrange -A

# Просмотр использования памяти по подам
kubectl top pods -A --sort-by=memory

# Просмотр использования памяти по узлам
kubectl top nodes

# Редактировать deployment
kubectl edit deployment wbgram-original -n default

# Просмотреть YAML deployment
kubectl get deployment wbgram-original -n default -o yaml

# Просмотр событий
kubectl get events -A --sort-by='.lastTimestamp'
```

---

**Версия:** 1.0  
**Дата:** 2025-10-19  
**Статус:** ✅ Готово к применению



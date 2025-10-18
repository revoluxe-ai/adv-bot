# 📊 Полный Гайд: Мониторинг Ошибок в Kubernetes

**Дата**: 18 октября 2025  
**Статус**: Production Ready  
**Версия**: 1.0  

---

## 📋 Текущее Состояние Вашей Установки

### ✅ Что УЖЕ Установлено:

```
✓ Prometheus Stack (kube-prometheus-stack)
  - Prometheus (сервер метрик)
  - Grafana (визуализация)
  - AlertManager (управление алертами)
  - Node Exporter (метрики ноде)
  - Kube State Metrics (метрики Kubernetes)

✓ Prometheus Rules (32 правила):
  - Основные алерты Kubernetes
  - Алерты pod-health-alerts
  - Алерты service-endpoints-alerts

✗ Loki Stack (частично установлена):
  - ❌ Loki компоненты в ImagePullBackOff (ошибка загрузки образа)
  - ❌ Promtail НЕ установлен
  - ❌ Сбор логов НЕ настроен
```

---

## 🎯 Рекомендации: Что Использовать для Мониторинга Ошибок?

### 📊 **PROMETHEUS (метрики) - ИСПОЛЬЗУЙТЕ ЭТО** ✅

**Преимущества:**
- ✓ Уже полностью установлен и работает
- ✓ Метрики pod рестартов, статус, OOMKilled и т.д.
- ✓ Алерты уже настроены
- ✓ Хороший для трендов и аномалий

**Доступные метрики для ошибок:**
```promql
# Поды с рестартами за последний час
increase(kube_pod_container_status_restarts_total[1h]) > 0

# Поды в статусе Error/CrashLoopBackOff
kube_pod_status_phase{phase!="Running"}

# OOMKilled ошибки
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}

# Контейнеры с ошибками при старте
kube_pod_container_status_last_terminated_reason{reason="Error"}

# Количество рестартов контейнера
rate(kube_pod_container_status_restarts_total[5m]) > 0
```

---

### 📝 **LOKI (логи) - ТРЕБУЕТ ИСПРАВЛЕНИЯ** ⚠️

**Проблема:** Loki установлена но не работает (ImagePullBackOff)

**Решение:** Будет описано ниже (восстановление или переустановка)

---

## 1️⃣ ЧЕРЕЗ PROMETHEUS - Настройка Алертов на Ошибки

### Шаг 1: Проверить Существующие Алерты

Откройте AlertManager:
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-alertmanager 9093:9093
```
Откройте: **http://localhost:9093**

Там вы видите:
- Активные алерты
- История срабатываний
- Группировка и маршрутизация

### Шаг 2: Проверить Какие Алерты Уже Есть

Посмотрите в Prometheus:
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
```
Откройте: **http://localhost:9090**

Перейдите: **Alerts** → Видите все правила которые срабатывают

---

## 2️⃣ ДОБАВИТЬ СВОИ АЛЕРТЫ НА ОШИБКИ

### Создать PrometheusRule для мониторинга ошибок:

```bash
cat > k8s/monitoring/pod-error-alerts.yaml << 'EOF'
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pod-error-detection-alerts
  namespace: kube-prometheus-stack
spec:
  groups:
  - name: pod-errors
    interval: 30s
    rules:
    
    # АЛЕРТ 1: Pod рестартился более 3 раз за час
    - alert: PodRestartingTooOften
      expr: increase(kube_pod_container_status_restarts_total[1h]) > 3
      for: 5m
      labels:
        severity: warning
        component: pod-health
      annotations:
        summary: "Pod {{ $labels.pod }} frequently restarting"
        description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} restarted {{ $value }} times in last hour"
    
    # АЛЕРТ 2: Pod в состоянии CrashLoopBackOff
    - alert: PodCrashLoop
      expr: kube_pod_container_state_waiting_reason{reason="CrashLoopBackOff"} == 1
      for: 2m
      labels:
        severity: critical
        component: pod-health
      annotations:
        summary: "Pod {{ $labels.pod }} is in CrashLoop"
        description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} has been in CrashLoop for over 2 minutes"
    
    # АЛЕРТ 3: Pod с ошибкой при старте
    - alert: PodStartupError
      expr: kube_pod_container_state_waiting_reason{reason="Error"} == 1
      for: 5m
      labels:
        severity: warning
        component: pod-health
      annotations:
        summary: "Pod {{ $labels.pod }} has startup error"
        description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} failed to start"
    
    # АЛЕРТ 4: Pod убит OOMKilled
    - alert: PodOOMKilled
      expr: increase(kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}[1h]) > 0
      for: 1m
      labels:
        severity: critical
        component: pod-health
      annotations:
        summary: "Pod {{ $labels.pod }} OOMKilled"
        description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} was killed due to out of memory"
    
    # АЛЕРТ 5: Pod не Running более 10 минут
    - alert: PodNotReady
      expr: kube_pod_status_phase{phase!="Running"} == 1
      for: 10m
      labels:
        severity: warning
        component: pod-health
      annotations:
        summary: "Pod {{ $labels.pod }} not running"
        description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} has been in {{ $labels.phase }} state for 10+ minutes"

  # GROUP 2: Контейнер ошибки
  - name: container-errors
    interval: 30s
    rules:
    
    - alert: ContainerHighErrorRate
      expr: rate(kube_pod_container_status_restarts_total[5m]) > 0
      for: 15m
      labels:
        severity: warning
        component: container-health
      annotations:
        summary: "Container {{ $labels.container }} has high error rate"
        description: "Container {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container }} restarting frequently"
EOF

kubectl apply -f k8s/monitoring/pod-error-alerts.yaml
```

### Проверить что алерты загрузились:

```bash
kubectl get prometheusrule -n kube-prometheus-stack | grep pod-error
```

---

## 3️⃣ НАСТРОЙКА УВЕДОМЛЕНИЙ (Telegram, Email, Slack)

### Получить текущую конфигурацию AlertManager:

```bash
kubectl get secret -n kube-prometheus-stack alertmanager-kube-prometheus-stack-alertmanager -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d
```

### Пример конфигурации AlertManager с Telegram:

```bash
cat > /tmp/alertmanager-config.yaml << 'EOF'
global:
  resolve_timeout: 5m
  # Telegram settings
  telegram_api_url: 'https://api.telegram.org'

route:
  # Группировка алертов
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  
  # Основной receiver
  receiver: 'telegram-notifications'
  
  # Специальные маршруты
  routes:
  - match:
      severity: critical
    receiver: 'telegram-critical'
    repeat_interval: 4h

receivers:
- name: 'telegram-notifications'
  telegram_configs:
  - bot_token: 'YOUR_TELEGRAM_BOT_TOKEN'
    chat_id: YOUR_TELEGRAM_CHAT_ID
    send_resolved: true
    
- name: 'telegram-critical'
  telegram_configs:
  - bot_token: 'YOUR_TELEGRAM_BOT_TOKEN'
    chat_id: YOUR_TELEGRAM_CHAT_ID_CRITICAL
    send_resolved: true

inhibit_rules: []
EOF

# Создать Secret с конфигом
kubectl create secret generic alertmanager-config-custom \
  --from-file=/tmp/alertmanager-config.yaml \
  -n kube-prometheus-stack \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 4️⃣ ПРИМЕРЫ ЗАПРОСОВ И ДАШБОРДОВ

### Быстрые PromQL Запросы:

**В Prometheus (http://localhost:9090):**

```promql
# Все поды с ошибками за последний час
increase(kube_pod_container_status_restarts_total[1h]) > 0

# Самые проблемные поды (сортировка)
topk(10, increase(kube_pod_container_status_restarts_total[24h]))

# Поды в состоянии не Running
kube_pod_status_phase{phase!="Running"}

# Контейнеры которые нельзя запустить
kube_pod_container_state_waiting_reason

# Утечка памяти (OOM)
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}

# График рестартов за 24 часа
sum by (namespace, pod) (increase(kube_pod_container_status_restarts_total[24h])) > 0
```

### Пример Grafana Dashboard JSON:

Я создам файл `k8s/monitoring/pod-errors-dashboard.json` который показывает:
- ✅ График рестартов подов
- ✅ Таблица самых проблемных подов
- ✅ Тип ошибок (CrashLoop, OOMKilled, Error)
- ✅ Тренд ошибок за 24 часа

```bash
# Применить dashboard
kubectl apply -f k8s/monitoring/pod-errors-dashboard.yaml
```

---

## 5️⃣ ИСПРАВЛЕНИЕ LOKI (опционально, если нужны логи)

### Проблема:
Loki pods в ImagePullBackOff - не могут загрузить образ

### Вариант 1: Удалить Loki (если не нужна)

```bash
helm uninstall grafana-loki -n kube-prometheus-stack
```

### Вариант 2: Переустановить Loki + Promtail

```bash
# 1. Удалить старую установку
helm uninstall grafana-loki -n kube-prometheus-stack

# 2. Добавить чарт репо
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 3. Установить Loki
helm install loki grafana/loki-stack \
  -n kube-prometheus-stack \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=10Gi \
  --set promtail.enabled=true \
  --set promtail.config.clients[0].url=http://loki:3100/loki/api/v1/push

# 4. Проверить что запустилось
kubectl get pods -n kube-prometheus-stack | grep loki
```

### Вариант 3: Просто Promtail (если нужны логи без Loki)

```bash
helm install promtail grafana/promtail \
  -n kube-prometheus-stack \
  --set config.clients[0].url=http://loki:3100/loki/api/v1/push
```

---

## 📊 ИТОГОВЫЙ ЧЕКЕР: Что Настроить?

### ✅ МИНИМУМ (для контроля ошибок подов):

1. ✅ Prometheus уже работает → метрики доступны
2. ✅ AlertManager уже работает → алерты могут срабатывать
3. ⚠️ Нужно создать: PrometheusRule с алертами на ошибки (выше)
4. ⚠️ Нужно добавить: Receiver (Telegram/Email/Slack) в AlertManager

### 🎯 РЕКОМЕНДУЕМЫЙ ПОРЯДОК ДЕЙСТВИЙ:

1. **Понедельник - Prometheus Алерты:**
   - Создать `k8s/monitoring/pod-error-alerts.yaml` (скопировать выше)
   - Применить: `kubectl apply -f k8s/monitoring/pod-error-alerts.yaml`
   - Проверить в Prometheus http://localhost:9090 → Alerts

2. **Вторник - Notification Channel:**
   - Выбрать: Telegram или Email или Slack
   - Настроить Bot Token / API Key
   - Обновить AlertManager конфиг

3. **Среда - Dashboard:**
   - Создать красивый Dashboard в Grafana
   - Добавить 4 панели (рестарты, ошибки, OOM, тренды)

4. **Четверг - Loki (опционально):**
   - Если нужны логи → переустановить Loki + Promtail

---

## 🔗 БЫСТРЫЕ ССЫЛКИ:

| Компонент | URL | Статус |
|-----------|-----|--------|
| **Prometheus** | http://localhost:9090 | ✅ Running |
| **Grafana** | http://localhost:3000 | ✅ Running |
| **AlertManager** | http://localhost:9093 | ✅ Running |
| **Loki** | http://localhost:3100 | ❌ ImagePullBackOff |

---

## 💡 СЕКРЕТЫ И КОМАНДЫ:

```bash
# Посмотреть все алерты которые сейчас срабатывают
kubectl get alert -n kube-prometheus-stack

# Посмотреть все PrometheusRules
kubectl get prometheusrule -n kube-prometheus-stack

# Посмотреть логи AlertManager
kubectl logs -n kube-prometheus-stack -l app.kubernetes.io/name=alertmanager -f

# Посмотреть конфиг Prometheus
kubectl get prometheus -n kube-prometheus-stack -o yaml | head -100

# Рестарт AlertManager если вы изменили конфиг
kubectl rollout restart deployment -n kube-prometheus-stack kube-prometheus-stack-alertmanager
```

---

**Статус**: Ready to Deploy  
**Автор**: DevOps Assistant  
**Дата Обновления**: 2025-10-18

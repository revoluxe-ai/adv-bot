# 🚨 Система Быстрого Мониторинга Ошибок

Комплексное решение для мониторинга ошибок, падений подов и перегрузок в Kubernetes.

## 📋 Компоненты

### 1. **Grafana Dashboard** 📊
- **Файл**: `error-monitoring-dashboard.yaml`
- **Функции**:
  - Графики рестартов подов
  - Таблица статусов всех подов
  - Гистограмма типов ошибок
  - Метрики здоровья deployments

### 2. **Prometheus Alert Rules** 🔔
- **Файл**: `prometheusrule-error-alerts.yaml`
- **Группы правил**:
  - **Pod Health**: CrashLoop, OOM, частые рестарты, не готовые поды
  - **Deployment**: недостаток реплик, проблемы обновления
  - **Node Issues**: вытесненные поды, проблемы с нодами
  - **Application Logs**: высокий уровень ошибок, паники
  - **Resources**: переиспользование памяти и CPU

### 3. **CLI Tool (Bash)** 🛠️
- **Файл**: `pod-error-checker.sh`
- **Использование**:
  ```bash
  chmod +x k8s/monitoring/pod-error-checker.sh
  
  # Проверить default namespace
  ./pod-error-checker.sh
  
  # Проверить конкретный namespace
  ./pod-error-checker.sh kube-prometheus-stack
  ```

### 4. **Python Monitoring Tool** 🐍
- **Файл**: `error_monitor.py`
- **Использование**:
  ```bash
  chmod +x k8s/monitoring/error_monitor.py
  
  # Полный анализ
  python3 error_monitor.py -n default
  
  # С экспортом в JSON
  python3 error_monitor.py -n default -o errors.json
  
  # С логами критичных подов
  python3 error_monitor.py -n default -l
  ```

## 🚀 Быстрый Старт

### Шаг 1: Применить Prometheus Rules

```bash
kubectl apply -f k8s/monitoring/prometheusrule-error-alerts.yaml
```

### Шаг 2: Применить Grafana Dashboard

```bash
# Создать ConfigMap с dashboard
kubectl apply -f k8s/monitoring/error-monitoring-dashboard.yaml

# Импортировать dashboard в Grafana UI
# Settings → Dashboards → Import → Paste JSON
```

### Шаг 3: Использовать CLI Tools

```bash
# Bash скрипт - быстрый обзор
./k8s/monitoring/pod-error-checker.sh default

# Python скрипт - глубокий анализ
python3 k8s/monitoring/error_monitor.py -n default -l -o /tmp/errors.json
```

## 📊 Типы Ошибок, которые Мониторятся

### Критичные (CRITICAL) 🔴

| Ошибка | Причина | Действие |
|--------|---------|---------|
| **PodCrashLoopBackOff** | Pod падает и рестартуется | Проверить логи и ресурсы |
| **OOMKilled** | Недостаточно памяти | Увеличить limits или request memory |
| **ImagePullBackOff** | Не может загрузить образ | Проверить credentials и registry |
| **ErrImagePull** | Ошибка при загрузке образа | Проверить URL и доступность |
| **PodEvicted** | Под вытеснен с ноды | Проверить node pressure |

### Предупреждение (WARNING) 🟡

| Ошибка | Причина | Действие |
|--------|---------|---------|
| **PodFrequentRestarts** | Pod перезагружается часто | Проверить лаги и здоровье |
| **PodNotReady** | Pod не в Ready статусе | Проверить describe и events |
| **HighCPUUsage** | Pod использует много CPU | Оптимизировать код |
| **HighMemoryUsage** | Pod близок к лимиту памяти | Увеличить лимит или оптимизировать |
| **DeploymentReplicasUnavailable** | Недостаточно реплик | Проверить ресурсы ноды |

## 🔍 Примеры Использования

### Быстрая диагностика

```bash
# 1. Запустить bash скрипт
./k8s/monitoring/pod-error-checker.sh default

# Вывод покажет:
# - Поды в CrashLoopBackOff
# - Поды с рестартами
# - Проблемы с образами
# - Статусы подов
# - События ошибок
```

### Глубокий анализ с Python

```bash
# Запустить Python скрипт с логами
python3 k8s/monitoring/error_monitor.py -n default -l

# Вывод покажет:
# - Структурированный анализ ошибок
# - Серьезность каждой ошибки
# - Последние логи критичных подов
```

### Экспорт для дальнейшей обработки

```bash
# Экспортировать в JSON для парсинга
python3 k8s/monitoring/error_monitor.py -n default -o errors.json

# Можно обрабатывать через jq
cat errors.json | jq '.errors[] | select(.severity=="CRITICAL")'
```

### Интеграция с мониторингом

```bash
# Просмотреть Prometheus alerts
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090 → Alerts

# Просмотреть AlertManager
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-alertmanager 9093:9093
# http://localhost:9093

# Просмотреть Grafana dashboard
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000
```

## 📈 Метрики Для Мониторинга

### Pod Metrics

```promql
# Количество рестартов за час
increase(kube_pod_container_status_restarts_total[1h])

# Поды в CrashLoop
kube_pod_container_status_last_terminated_reason{reason="CrashLoopBackOff"}

# Поды не в Ready статусе
kube_pod_status_phase{phase=~"Failed|Unknown|Pending"}

# Использование памяти контейнером
container_memory_usage_bytes
```

### Deployment Metrics

```promql
# Доступные реплики
kube_deployment_status_replicas_available

# Обновленные реплики
kube_deployment_status_replicas_updated

# Желаемое количество реплик
kube_deployment_spec_replicas
```

## 🔧 Конфигурация

### Настройка Severity

Отредактируйте `prometheusrule-error-alerts.yaml` для изменения:

```yaml
- alert: PodFrequentRestarts
  expr: rate(kube_pod_container_status_restarts_total[1h]) > 1  # Изменить порог
  for: 5m  # Изменить duration
  labels:
    severity: warning  # Изменить severity
```

### Добавление Custom Alerts

Добавьте новое правило в `prometheusrule-error-alerts.yaml`:

```yaml
- alert: MyCustomAlert
  expr: my_metric > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "My custom alert triggered"
    description: "Details: {{ $value }}"
```

## 📝 Интеграция с Alerting

### Slack Integration

1. Отредактируйте `k8s/monitoring/prometheus-values.yaml`
2. Добавьте Slack webhook:

```yaml
alertmanager:
  config:
    receivers:
      - name: slack
        slack_configs:
          - api_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
            channel: '#alerts'
```

3. Обновите Helm release:

```bash
helm upgrade kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n kube-prometheus-stack \
  -f k8s/monitoring/prometheus-values.yaml
```

### Telegram Integration

Используйте alertmanager-telegram-bot для интеграции с Telegram.

## 🎯 Best Practices

### 1. Регулярные проверки
```bash
# Добавить cron job
0 * * * * /path/to/pod-error-checker.sh default >> /var/log/pod-monitor.log
```

### 2. Мониторинг критичных сервисов
```bash
# Создать отдельные alerts для важных deployments
kubectl label deployment critical-app="true"
```

### 3. Логирование
```bash
# Сохранять логи мониторинга
python3 error_monitor.py -n default -o /logs/errors-$(date +%Y%m%d-%H%M%S).json
```

### 4. Документирование
- Для каждого алерта должна быть runbook (игра с действиями)
- Указывать ожидаемые пороги
- Описывать steps для решения

## 🐛 Troubleshooting

### Prometheus не scrape метрики

```bash
# Проверить targets
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090/targets

# Проверить rules
http://localhost:9090/rules
```

### Alerts не срабатывают

```bash
# Проверить PrometheusRule
kubectl get prometheusrules -n kube-prometheus-stack

# Проверить логи
kubectl logs -n kube-prometheus-stack -l app.kubernetes.io/name=prometheus
```

### AlertManager не отправляет уведомления

```bash
# Проверить конфигурацию
kubectl get secret -n kube-prometheus-stack alertmanager-kube-prometheus-stack-alertmanager -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d

# Проверить логи
kubectl logs -n kube-prometheus-stack -l app.kubernetes.io/name=alertmanager
```

## 📚 Дополнительные Ресурсы

- [Kubernetes Events](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-application/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)

## ✅ Checklist для Setup

- [ ] Применить `prometheusrule-error-alerts.yaml`
- [ ] Применить `error-monitoring-dashboard.yaml`
- [ ] Сделать скрипты executable: `chmod +x *.sh *.py`
- [ ] Протестировать bash скрипт: `./pod-error-checker.sh default`
- [ ] Протестировать Python скрипт: `python3 error_monitor.py -n default`
- [ ] Настроить AlertManager notifications
- [ ] Импортировать Grafana dashboard
- [ ] Добавить в cron для регулярных проверок
- [ ] Документировать runbooks для каждого алерта
- [ ] Настроить доступ для team

## 🎓 Команды Для Быстрого Доступа

```bash
# Все ошибочные события
kubectl get events -n default --sort-by='.lastTimestamp' | grep -i error

# Все алерты в Prometheus
curl http://prometheus:9090/api/v1/alerts | jq '.data.alerts[]'

# Поды с рестартами
kubectl get pods -n default --sort-by='.status.containerStatuses[0].restartCount'

# Поды не в Ready статусе
kubectl get pods -n default -o jsonpath='{.items[?(@.status.conditions[?(@.type=="Ready")].status=="False")].metadata.name}'

# Logs для пода
kubectl logs -n default POD_NAME --tail=100 --timestamps=true
```

---

**Версия**: 1.0  
**Дата**: 2025-10-18  
**Статус**: Ready for Production



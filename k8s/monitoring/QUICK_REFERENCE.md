# 🚀 Quick Reference - Система Мониторинга Ошибок

**Для быстрого доступа к командам мониторинга**

## ⚡ Самые Используемые Команды

### 1. Срочная Проверка (30 сек)
```bash
./k8s/monitoring/pod-error-checker.sh default
```
**Что показывает**: Все проблемы в namespace за несколько секунд

### 2. Глубокий Анализ (2 мин)
```bash
python3 k8s/monitoring/error_monitor.py -n default -o /tmp/errors.json -l
```
**Что показывает**: Структурированные ошибки + логи критичных подов

### 3. Быстрый Статус
```bash
kubectl get pods -n default --sort-by='.status.containerStatuses[0].restartCount'
```
**Что показывает**: Поды отсортированные по количеству рестартов

### 4. Ошибочные События
```bash
kubectl get events -n default --sort-by='.lastTimestamp' | grep -i error
```
**Что показывает**: Все события с ошибками в namespace

---

## 📊 Просмотр Dashboards

### Prometheus Alerts
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090/alerts
```

### Grafana Error Monitoring
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000 (admin/admin)
# Найти dashboard: "Pod Error Monitoring"
```

### AlertManager
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-alertmanager 9093:9093
# http://localhost:9093
```

---

## 🔍 Диагностика Конкретного Пода

### Посмотреть логи
```bash
kubectl logs -n default POD_NAME --tail=100 --timestamps=true
```

### Описание пода (детали)
```bash
kubectl describe pod -n default POD_NAME
```

### События для пода
```bash
kubectl get events -n default --field-selector involvedObject.name=POD_NAME
```

### Статус контейнеров
```bash
kubectl get pod -n default POD_NAME -o jsonpath='{.status.containerStatuses[*]}'
```

---

## 🛡️ Разные Типы Проблем

### CrashLoop
```bash
# Найти поды
kubectl get pods -n default -o json | jq '.items[] | select(.status.containerStatuses[]?.state.waiting.reason=="CrashLoopBackOff") | .metadata.name'

# Смотреть логи
kubectl logs -n default POD_NAME --previous
```

### OOMKilled
```bash
# Найти поды убитые OOMKiller
kubectl get pods -n default -o json | jq '.items[] | select(.status.containerStatuses[]?.lastState.terminated.reason=="OOMKilled") | .metadata.name'

# Увеличить лимит памяти
kubectl set resources deployment -n default DEPLOYMENT --limits=memory=2Gi
```

### ImagePullBackOff
```bash
# Найти поды с проблемами образов
kubectl get pods -n default -o json | jq '.items[] | select(.status.containerStatuses[]?.state.waiting.reason=="ImagePullBackOff") | .metadata.name'

# Проверить образ
kubectl describe pod -n default POD_NAME | grep -A 5 "image:"
```

### Pending
```bash
# Найти зависшие поды
kubectl get pods -n default --field-selector=status.phase=Pending

# Проверить, почему Pending
kubectl describe pod -n default POD_NAME
```

### Pending (Insufficient cpu) — PowerShell
```powershell
# Быстро увидеть Pending во всём кластере
kubectl get pods -A --field-selector=status.phase=Pending -o wide

# Посмотреть Allocated resources (requests vs allocatable) на ноде
$node = kubectl get nodes -o jsonpath='{.items[0].metadata.name}'
kubectl describe node $node | Select-String -Pattern "^Allocated resources:" -Context 0,16

# Топ по cpu requests + фактическое потребление
.\k8s\monitoring\diagnose-cpu-scheduling.ps1 -Top 30
```

---

## 📈 Metрики в Prometheus

### PromQL запросы

```promql
# Поды с рестартами за последний час
increase(kube_pod_container_status_restarts_total[1h]) > 0

# Поды в CrashLoop
kube_pod_container_status_last_terminated_reason{reason="CrashLoopBackOff"}

# Поды не в Ready
kube_pod_status_phase{phase=~"Failed|Unknown|Pending"}

# CPU использование
rate(container_cpu_usage_seconds_total[5m])

# Память использование
container_memory_usage_bytes
```

### Использование в Grafana
1. Добавить panel
2. Выбрать данные source: Prometheus
3. Вставить PromQL запрос
4. Настроить визуализацию

---

## 🔧 Deployment Commands

### Применить Prometheus Rules
```bash
kubectl apply -f k8s/monitoring/prometheusrule-error-alerts.yaml
```

### Применить Grafana Dashboard
```bash
kubectl apply -f k8s/monitoring/error-monitoring-dashboard.yaml
```

### Проверить, что Rules применены
```bash
kubectl get prometheusrules -n kube-prometheus-stack
kubectl get prometheusrules -n kube-prometheus-stack error-monitoring-alerts -o yaml
```

### Перезагрузить Prometheus (если нужно)
```bash
kubectl rollout restart deployment -n kube-prometheus-stack kube-prometheus-stack-prometheus
```

---

## 🔔 AlertManager & Notifications

### Просмотреть конфигурацию
```bash
kubectl get secret -n kube-prometheus-stack alertmanager-kube-prometheus-stack-alertmanager -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d
```

### Проверить логи AlertManager
```bash
kubectl logs -n kube-prometheus-stack -l app.kubernetes.io/name=alertmanager --tail=50
```

### Отправить тестовый alert
```bash
# Через AlertManager webhook
curl -X POST http://localhost:9093/api/v1/alerts -H "Content-Type: application/json" -d '[{
  "labels": {"alertname": "TestAlert", "severity": "critical"},
  "annotations": {"summary": "Test alert"}
}]'
```

---

## 📊 Анализ Ошибок

### Экспортировать все ошибки
```bash
python3 k8s/monitoring/error_monitor.py -n default -o errors.json
```

### Фильтр: только CRITICAL
```bash
cat errors.json | jq '.errors[] | select(.severity=="CRITICAL")'
```

### Фильтр: только специфический тип
```bash
cat errors.json | jq '.errors[] | select(.error_type=="OOMKilled")'
```

### Статистика
```bash
cat errors.json | jq '.summary'
```

---

## 🐛 Troubleshooting

### Bash скрипт не работает
```bash
# Проверить, есть ли jq
which jq
apt-get install jq  # если нет

# Проверить, есть ли kubectl
which kubectl

# Проверить доступ
kubectl auth can-i get pods
```

### Python скрипт не работает
```bash
# Проверить Python версию (нужен 3.7+)
python3 --version

# Проверить, есть ли subprocess (встроенный модуль)
python3 -c "import subprocess; print('OK')"

# Проверить, есть ли json (встроенный модуль)
python3 -c "import json; print('OK')"
```

### Алерты не срабатывают
```bash
# Проверить, создалась ли PrometheusRule
kubectl get prometheusrules -n kube-prometheus-stack
kubectl describe prometheusrule error-monitoring-alerts -n kube-prometheus-stack

# Проверить логи Prometheus
kubectl logs -n kube-prometheus-stack -l app.kubernetes.io/name=prometheus --tail=100

# Проверить, что Prometheus scrape данные
# http://localhost:9090/targets
```

---

## 📝 Интеграция с CI/CD

### GitLab CI
```yaml
monitor_errors:
  stage: test
  image: alpine:latest
  before_script:
    - apk add --no-cache kubectl python3 jq bash
  script:
    - python3 k8s/monitoring/error_monitor.py -n prod -o error-report.json
    - cat error-report.json | jq '.summary'
  artifacts:
    reports:
      error_report: error-report.json
```

### Cron Job
```bash
0 * * * * python3 /app/k8s/monitoring/error_monitor.py -n prod -o /logs/errors-$(date +\%Y\%m\%d-\%H\%M\%S).json
```

---

## 📚 Документация

- 📖 **Полное руководство**: `ERROR_MONITORING_GUIDE.md`
- 📋 **Детали развертывания**: `DEPLOYMENT_SUMMARY.md`
- 🚀 **Быстрый старт**: этот файл

---

## 🎯 Рекомендуемый Workflow

### При Алерте
```bash
# 1. Срочная проверка
./k8s/monitoring/pod-error-checker.sh default

# 2. Если нужна подробность
python3 k8s/monitoring/error_monitor.py -n default -o /tmp/error-$(date +%s).json -l

# 3. Посмотреть конкретный pod
kubectl logs -n default PROBLEM_POD --tail=200

# 4. Описание проблемы
kubectl describe pod -n default PROBLEM_POD

# 5. События
kubectl get events -n default --sort-by='.lastTimestamp' | tail -20
```

### При Регулярной Проверке
```bash
# 1. Смотреть Grafana Dashboard
# http://localhost:3000 → Error Monitoring

# 2. Смотреть Prometheus Alerts
# http://localhost:9090/alerts

# 3. Если нужен отчет
python3 k8s/monitoring/error_monitor.py -n default -o /reports/daily-report.json
```

---

## ✅ Чек-лист для On-Call

- [ ] Запустить `pod-error-checker.sh` для быстрой диагностики
- [ ] Если критичные ошибки, запустить `error_monitor.py -l` для логов
- [ ] Посмотреть Prometheus алерты
- [ ] Если нужна история, смотреть Grafana dashboard
- [ ] Документировать проблему и решение

---

**Последнее обновление**: 2025-10-18  
**Версия**: 1.0



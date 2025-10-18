# 🚀 Мониторинг Ошибок Kubernetes - Быстрый Старт

**Статус**: ✅ ГОТОВО К ИСПОЛЬЗОВАНИЮ  
**Дата**: 18 октября 2025  

---

## 📊 ЧТО УСТАНОВЛЕНО И РАБОТАЕТ:

✅ **Prometheus** - сервер метрик  
✅ **Grafana** - визуализация (http://localhost:3000)  
✅ **AlertManager** - управление алертами  
✅ **Kube State Metrics** - метрики Kubernetes  
✅ **Prometheus Rules** - 32 правила, включая 5 новых алертов на ошибки  

---

## 🎯 НОВЫЕ АЛЕРТЫ (уже активны):

1. **PodRestartingTooOften** - Pod рестартился > 3 раз за час
2. **PodCrashLoop** - Pod в состоянии CrashLoop
3. **PodStartupError** - Pod не запускается (Error)
4. **PodOOMKilled** - Pod убит из-за нехватки памяти (OOMKilled)
5. **PodNotReady** - Pod не Ready более 10 минут
6. **ContainerHighErrorRate** - Контейнер часто рестартуется

---

## 🔍 ЧТО СМОТРЕТЬ:

### 1. Prometheus (Raw метрики и алерты):
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
```
Откройте: **http://localhost:9090**
- Вкладка **Alerts** → видите все алерты
- Вкладка **Status** → Targets (какие метрики собираются)
- В поле поиска вводите PromQL запросы

### 2. AlertManager (Управление алертами):
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-alertmanager 9093:9093
```
Откройте: **http://localhost:9093**
- **Alerts** → активные алерты
- **Status** → конфигурация channels (куда идут уведомления)

### 3. Grafana (Красивые графики):
```bash
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-grafana 3000:80
```
Откройте: **http://localhost:3000**
- Авторизуйтесь: **admin/admin**
- Меню → **Dashboards** → "Pod Error Monitoring" (уже есть)

---

## 📈 ПРИМЕРЫ PROMQL ЗАПРОСОВ:

Вводите в **http://localhost:9090** (поле поиска):

### Поды с ошибками за последний час:
```promql
increase(kube_pod_container_status_restarts_total[1h]) > 0
```

### Топ 10 самых проблемных подов:
```promql
topk(10, increase(kube_pod_container_status_restarts_total[24h]))
```

### Все поды которые не Running:
```promql
kube_pod_status_phase{phase!="Running"}
```

### OOMKilled ошибки:
```promql
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}
```

### Ошибки при старте:
```promql
kube_pod_container_status_last_terminated_reason{reason="Error"}
```

---

## ⚠️ ТЕКУЩИЕ ОШИБКИ В ВАШЕМ КЛАСТЕРЕ:

**Из логов мы нашли 17 подов с ошибками:**

### 🔴 КРИТИЧНЫЕ (более 10 ошибок):
- `adv-bot-updater` (100 ошибок!) ← СРОЧНО ПРОВЕРИТЬ
- `ingress-nginx-controller` (32-35 ошибок)
- `cert-manager` (25 ошибок)

### 🟡 ВАЖНЫЕ (5-10 ошибок):
- `update-wb-adv-phrases` (11 ошибок)
- `click-house-system-logs-table-cleaner` (10 ошибок)

### 🟢 НЕЗНАЧИТЕЛЬНЫЕ (1-2 ошибки):
- `run-shop-update-worker` (несколько копий по 1-2 ошибки)
- `csi-s3`, `metrics-server`, `kube-proxy` (по 1-2 ошибки)

---

## 🔧 КАК ПОСМОТРЕТЬ ДЕТАЛЬНЫЕ ЛОГИ ОШИБОК:

### Логи пода с наибольшим количеством ошибок:
```bash
# adv-bot-updater (100 ошибок)
kubectl logs -n default adv-bot-updater-6549df69f9-n78qf --tail=100 | grep -i error

# ingress-nginx (35 ошибок)
kubectl logs -n ingress-nginx ingress-nginx-controller-9mrjc --tail=100 | grep -i error

# cert-manager (25 ошибок)
kubectl logs -n cert-manager cert-manager-1744002826-59c6bbc478-x4d2s --tail=100 | grep -i error
```

### Посмотреть ВСЕ события в кластере (с ошибками):
```bash
kubectl get events -A --sort-by='.lastTimestamp' | grep -i "error\|failed\|crash"
```

---

## 📱 СЛЕДУЮЩИЙ ШАГ: Уведомления в Telegram

### Шаг 1: Создать Telegram Bot
1. Откройте Telegram
2. Найдите **@BotFather**
3. Команда: `/newbot`
4. Назовите бота, получите **TOKEN**

### Шаг 2: Получить Chat ID
1. Найдите бота **@userinfobot**
2. Получите **USER_ID**
3. Пишите боту любое сообщение
4. **USER_ID** = chat_id

### Шаг 3: Обновить AlertManager Config
```bash
# Получить текущий конфиг
kubectl get secret -n kube-prometheus-stack \
  alertmanager-kube-prometheus-stack-alertmanager \
  -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d > /tmp/alertmanager.yaml

# Отредактировать и добавить Telegram receiver
# ... (инструкции см. в MONITORING_SETUP_GUIDE.md)

# Применить новый конфиг
kubectl create secret generic alertmanager-config \
  --from-file=/tmp/alertmanager.yaml \
  -n kube-prometheus-stack \
  --dry-run=client -o yaml | kubectl apply -f -

# Перезагрузить AlertManager
kubectl rollout restart deployment -n kube-prometheus-stack kube-prometheus-stack-alertmanager
```

---

## 🎯 РЕКОМЕНДУЕМЫЙ ПЛАН ДЕЙСТВИЙ:

### День 1: Диагностика (ТУТ ВЫ)
- ✅ Посмотреть какие поды падают
- ✅ Создать алерты
- ✅ Проверить текущие ошибки

### День 2: Уведомления
- [ ] Создать Telegram Bot
- [ ] Настроить AlertManager → Telegram
- [ ] Проверить что уведомления работают

### День 3: Исправление
- [ ] Исправить проблемные поды
- [ ] Отслеживать новые ошибки

### День 4: Dashboard
- [ ] Создать красивый Dashboard в Grafana
- [ ] Добавить графики рестартов, ошибок и т.д.

---

## 💡 ПОЛЕЗНЫЕ КОМАНДЫ:

```bash
# Все поды с ошибками прямо сейчас
kubectl get pods -A --field-selector=status.phase!=Running

# Описание проблемного пода (события)
kubectl describe pod -n <namespace> <pod-name>

# Логи с фильтром
kubectl logs -n <namespace> <pod-name> --tail=50 | grep -i error

# Все алерты которые сейчас срабатывают
kubectl get alert -n kube-prometheus-stack

# Посмотреть какие метрики собираются
kubectl port-forward -n kube-prometheus-stack svc/kube-prometheus-stack-prometheus 9090:9090
# Затем перейти на http://localhost:9090 → Status → Targets
```

---

## 📚 ДОКУМЕНТАЦИЯ:

- **MONITORING_SETUP_GUIDE.md** - Полный гайд (все детали)
- **k8s/monitoring/pod-error-alerts.yaml** - Файл с алертами
- **k8s/monitoring/get-pod-errors-simple.sh** - Скрипт для поиска ошибок

---

## ✅ ЧЕКЕР: ВСЕ РАБОТАЕТ?

- [ ] Prometheus доступен на http://localhost:9090
- [ ] AlertManager доступен на http://localhost:9093
- [ ] Grafana доступна на http://localhost:3000 (admin/admin)
- [ ] В Prometheus → Alerts видны новые алерты (pod-error-*)
- [ ] Можно выполнять PromQL запросы
- [ ] Видны активные алерты в AlertManager

Если все галочки - **ВСЕ РАБОТАЕТ!** 🎉

---

**Созданные файлы:**
- ✅ MONITORING_SETUP_GUIDE.md
- ✅ MONITORING_QUICK_START.md (этот файл)
- ✅ k8s/monitoring/pod-error-alerts.yaml
- ✅ k8s/monitoring/get-pod-errors-simple.sh

**Статус**: Готово к боевому использованию  
**Дата**: 2025-10-18

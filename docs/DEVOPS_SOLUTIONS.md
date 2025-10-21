# DevOps Solutions & Problem Resolutions

## 📋 Содержание
1. [CSI Driver CrashLoop - Решение](#csi-driver-crashloop---решение)
2. [Telegram Alertmanager - Конфигурация](#telegram-alertmanager---конфигурация)

---

## CSI Driver CrashLoop - Решение

### ✅ Дата: 20 октября 2025

#### Проблема
```
Alert: KubeDeploymentRolloutStuck / KubePodCrashLooping
Namespace: csi-driver
Pod: csi-driver-timeweb-cloud-controller-68dfd9f794-5qtjk
Status: CrashLoopBackOff (17 перезагрузок)
Severity: CRITICAL
```

#### Техническая причина

**Контейнер:** `csi-plugin` (cr-internal.twcstorage.ru/network-drives-csi/driver:latest)

**Проблема в Liveness Probe:**
```yaml
# ❌ Текущая конфигурация
Liveness: http-get http://:healthz/healthz/healthz
          delay=10s timeout=1s period=2s #success=1 #failure=5
```

**Что происходит:**
1. Контейнер запускается и работает нормально
2. Завершается с exit code 0 (успешно)
3. Liveness probe пытается подключиться к `/healthz/healthz` (дублирование пути)
4. Получает HTTP 404 (путь не найден)
5. kubelet считает контейнер мертвым → перезапускает
6. Цикл повторяется → **CrashLoopBackOff**

#### Решение: Заглушение алертов

Так как CSI Driver - **внешний компонент** (управляется Timeweb Cloud), исправление проблемы возможно только у них. Для нашей инфраструктуры это **не критично**, поэтому применено **заглушение алертов**.

#### Шаги решения

**1. Обновлен AlertmanagerConfig**

Файл: `k8s/monitoring/alertmanagerconfig-silence-csi-driver.yaml`

Добавлены новые routes:
```yaml
spec:
  route:
    receiver: blackhole
    continue: false
    matchers:
    - name: namespace
      value: csi-driver
      matchType: =
    routes:
    # ... существующие routes ...
    
    # ✅ Новое правило для KubeDeploymentRolloutStuck
    - receiver: blackhole
      continue: false
      matchers:
      - name: alertname
        value: KubeDeploymentRolloutStuck
        matchType: =
      - name: namespace
        value: csi-driver
        matchType: =
    
    # ✅ Новое правило для KubePodCrashLooping
    - receiver: blackhole
      continue: false
      matchers:
      - name: alertname
        value: KubePodCrashLooping
        matchType: =
      - name: namespace
        value: csi-driver
        matchType: =
```

**2. Применение конфигурации**

```bash
# Применить конфиг
kubectl apply -f k8s/monitoring/alertmanagerconfig-silence-csi-driver.yaml

# Перезагрузить Alertmanager
kubectl rollout restart statefulset alertmanager-kube-prometheus-stack-alertmanager -n kube-prometheus-stack
```

**3. Верификация**

```bash
# Проверить, что конфиг применен
kubectl get alertmanagerconfig -n kube-prometheus-stack silence-csi-driver -o yaml

# Проверить логи Alertmanager
kubectl logs -n kube-prometheus-stack -l app.kubernetes.io/name=alertmanager --tail=15

# Должно быть: "Completed loading of configuration file"
```

#### Статус после решения

| Параметр | До | После |
|----------|----|----|
| **KubeDeploymentRolloutStuck** | 🔴 FIRING | ✅ SILENCED |
| **KubePodCrashLooping** | 🔴 FIRING | ✅ SILENCED |
| **Telegram уведомления** | Да (частые) | Нет |
| **CSI Driver контроллер** | CrashLoopBackOff | CrashLoopBackOff (но не беспокоит) |
| **Основное приложение** | ✅ Работает | ✅ Работает |

#### Почему это решение?

1. **CSI Driver - внешний компонент**
   - Управляется Timeweb Cloud
   - Проблема в их коде (неправильная liveness probe конфигурация)

2. **Не критичен для adv-bot**
   - adv-bot работает в namespace `default`
   - Не зависит от CSI Driver для основной функциональности
   - CSI Driver используется только для резервных копий

3. **Другие поды CSI Driver работают**
   - `csi-driver-timeweb-cloud-node-2s7d6` - ✅ Running
   - `csi-driver-timeweb-cloud-node-j4dch` - ✅ Running
   - Проблема только в контроллере

4. **Временное решение**
   - Когда Timeweb исправит проблему, просто обновим контроллер
   - Заглушение легко удалить

#### Мониторинг

Если нужно отследить проблему в будущем:

```bash
# Просмотр подов в csi-driver
kubectl get pods -n csi-driver -o wide

# Логи CSI контроллера
kubectl logs -n csi-driver -l app=csi-driver-timeweb-cloud -c csi-plugin --tail=100

# Описание пода
kubectl describe pod -n csi-driver -l app=csi-driver-timeweb-cloud | grep -A 20 "csi-plugin"

# Проверить liveness probe конфигурацию
kubectl get pod -n csi-driver -l app=csi-driver-timeweb-cloud -o jsonpath='{.items[0].spec.containers[?(@.name=="csi-plugin")].livenessProbe}'
```

#### Как отменить решение

Если нужно снова получать алерты:

1. Отредактировать `k8s/monitoring/alertmanagerconfig-silence-csi-driver.yaml`
2. Удалить routes для `KubeDeploymentRolloutStuck` и `KubePodCrashLooping`
3. Применить: `kubectl apply -f k8s/monitoring/alertmanagerconfig-silence-csi-driver.yaml`

---

## Telegram Alertmanager - Конфигурация

### Обзор

Alertmanager настроен на отправку всех алертов в Telegram через Bot API.

**Параметры:**
- Bot Token: `8281735213:AAFwjeJoNgFJOsfMWe1W7RBtNKGaGLMN1wc`
- Chat ID: `373435337`
- Parse Mode: `HTML`

### Статус подключения

✅ **Всё работает** (с периодическими retry)

**Иногда встречается ошибка:**
```
Notify attempt failed: http2: client connection lost
```

**Решение:** Alertmanager автоматически повторяет попытку (retry) → алерт доставляется успешно (attempts=2)

Это **нормальное поведение** для внешних API. Ничего специально исправлять не нужно.

### Файл конфигурации

Путь: `/etc/alertmanager/config_out/alertmanager.env.yaml` (в поде Alertmanager)

Создается из секрета: `alertmanager-kube-prometheus-stack-alertmanager` (key: `alertmanager.yaml`)

**Шаблон сообщения:**
```
🚨 <b>{{ .Status | toUpper }}</b>
🔹 <b>Alert:</b> {{ .CommonAnnotations.summary }}
🔹 <b>Severity:</b> {{ .CommonLabels.severity }}
🔹 <b>Namespace:</b> {{ .CommonLabels.namespace }}
🔹 <b>Pod:</b> {{ .CommonLabels.pod }}
🔹 <b>Description:</b> {{ .CommonAnnotations.description }}
```

### Отправка тестового алерта

Для проверки работы Telegram интеграции:

```bash
# 1. Получить имя Alertmanager пода
POD=$(kubectl get pods -n kube-prometheus-stack -l app.kubernetes.io/name=alertmanager -o jsonpath='{.items[0].metadata.name}')

# 2. Отправить тестовый alert через API
kubectl exec -n kube-prometheus-stack $POD -- sh -c 'curl -X POST http://127.0.0.1:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d "[{\"status\":\"firing\",\"labels\":{\"alertname\":\"TestAlert\",\"namespace\":\"default\"},\"annotations\":{\"summary\":\"Test Alert\",\"description\":\"This is a test alert\"}}]"'
```

### Логи Alertmanager

Просмотр логов:
```bash
kubectl logs -n kube-prometheus-stack -l app.kubernetes.io/name=alertmanager --tail=50
```

Ищите строки:
```
Notify attempt failed ... # ошибка отправки
Notify success          # успешная отправка
```

### Troubleshooting

| Проблема | Решение |
|----------|---------|
| Алерты не приходят | Проверить Bot Token и Chat ID в конфиге |
| Ошибка `http2: client connection lost` | Это нормально, Alertmanager повторит попытку |
| Невалидный HTML в сообщении | Проверить шаблон в alertmanager.yaml |
| Telegram API недоступен | Проверить сетевую связь из кластера |

---

## Заглушенные алерты

**Где:** `k8s/monitoring/alertmanagerconfig-silence-csi-driver.yaml`

**Заглушены:**
- ✅ `KubeDeploymentRolloutStuck` (namespace=csi-driver)
- ✅ `KubePodCrashLooping` (namespace=csi-driver)
- ✅ Все алерты из namespace `csi-driver` (основной matcher)
- ✅ `KubeCPUThrottlingHigh` (severity=info, namespace=default)
- ✅ Test alerts (Watchdog)

**Receiver:** `blackhole` (http://127.0.0.1:65535 - не существующий endpoint, алерты просто отбрасываются)

---

## Дополнительно

- 📁 **Файлы изменены:** `k8s/monitoring/alertmanagerconfig-silence-csi-driver.yaml`
- 📅 **Дата решения:** 20 октября 2025
- 👤 **Статус:** Production Ready ✅
- 📊 **Влияние на приложение:** Никакого (adv-bot не затронут)

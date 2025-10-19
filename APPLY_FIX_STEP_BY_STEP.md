# 📋 ПОШАГОВАЯ ИНСТРУКЦИЯ: Применение исправлений

## ✅ КРАТКАЯ ВЕРСИЯ (3 команды)

Скопируй и выполни эти команды по одной:

```bash
kubectl apply -f wbgram-original-deployment.yaml && \
kubectl apply -f k8s/monitoring/resourcequota-default.yaml && \
kubectl apply -f k8s/monitoring/resourcequota-kube-prometheus-stack.yaml && \
kubectl rollout restart deployment wbgram-original -n default
```

**Готово!** ✅ Алерт исчезнет через 5-10 минут.

---

## 📋 РАЗВЕРНУТАЯ ВЕРСИЯ (пошагово)

### ШАГ 1: Проверить, что kubectl работает
```bash
kubectl cluster-info
```
Должно вывести информацию о кластере.

---

### ШАГ 2: Обновить deployment с новыми лимитами памяти
```bash
kubectl apply -f wbgram-original-deployment.yaml
```

**Что произойдет:**
- Memory requests: 1Gi → 512Mi (уменьшится в 2x)
- Memory limits: 1Gi → 768Mi (уменьшится на 23%)
- CPU requests: 1 → 500m (уменьшится в 2x)

**Ожидаемый результат:**
```
deployment.apps/wbgram-original configured
```

---

### ШАГ 3: Применить ResourceQuota для namespace 'default'
```bash
kubectl apply -f k8s/monitoring/resourcequota-default.yaml
```

**Что произойдет:**
- Будет создана ResourceQuota (ограничение на namespace)
- Будет создана LimitRange (defaults для контейнеров)

**Ожидаемый результат:**
```
resourcequota/default-quota created
limitrange/default-limits created
```

---

### ШАГ 4: Применить ResourceQuota для 'kube-prometheus-stack'
```bash
kubectl apply -f k8s/monitoring/resourcequota-kube-prometheus-stack.yaml
```

**Ожидаемый результат:**
```
resourcequota/prometheus-quota created
limitrange/prometheus-limits created
```

Или (если namespace не существует):
```
error: namespaces "kube-prometheus-stack" not found
```
Это OK, просто значит, что мониторинг не установлен.

---

### ШАГ 5: Перезагрузить deployment
```bash
kubectl rollout restart deployment wbgram-original -n default
```

**Ожидаемый результат:**
```
deployment.apps/wbgram-original restarted
```

---

### ШАГ 6: Ждем, пока поды перезагрузятся
```bash
kubectl rollout status deployment wbgram-original -n default --timeout=5m
```

**Ожидаемый результат (через 1-2 минуты):**
```
deployment "wbgram-original" successfully rolled out
```

---

## 🔍 ПРОВЕРКА: Исправления применены?

### Проверка 1: ResourceQuota создана
```bash
kubectl get resourcequota -A
```

**Должно показать:**
```
NAMESPACE            NAME                    CREATED AT
default              default-quota           2025-10-19T...
kube-prometheus-stack prometheus-quota      2025-10-19T...  (если установлен)
```

---

### Проверка 2: Deployment обновлен
```bash
kubectl get deployment wbgram-original -n default -o yaml | grep -A 10 "resources:"
```

**Должно показать:**
```yaml
resources:
  limits:
    cpu: "1"
    memory: 768Mi
  requests:
    cpu: 500m
    memory: 512Mi
```

---

### Проверка 3: Поды работают
```bash
kubectl get pods -n default
```

**Должно показать:**
```
NAME                                READY   STATUS    RESTARTS   AGE
wbgram-original-7f8c9d2b-xxxxx      1/1     Running   0          2m
```

Если STATUS = `Running` → ✅ Хорошо!  
Если STATUS = `CrashLoopBackOff` → ❌ Проблема, посмотри логи.

---

### Проверка 4: Логи подов чистые
```bash
kubectl logs deployment/wbgram-original -n default --tail=20
```

Если логи содержат ошибки памяти:
```
OOMKilled
Out of memory
```

Тогда нужно УВЕЛИЧИТЬ limits (сейчас 768Mi).

---

### Проверка 5: Использование памяти на узлах
```bash
kubectl top nodes
```

**Должно показать:**
```
NAME                    CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
worker-192.168.0.6      1500m        50%    45000000000     51%
worker-192.168.0.7      200m         20%    2000000000      20%
```

Если MEMORY% очень высокий (>80%) → нужно добавить ресурсы.

---

### Проверка 6: ResourceQuota НЕ превышена
```bash
kubectl describe resourcequota default-quota -n default
```

**Должно показать:**
```
Name:       default-quota
Namespace:  default

Resource                   Used    Hard
--------                   ----    ----
limits.cpu                 1       60
limits.memory              768Mi   80Gi
pods                       1       200
requests.cpu               500m    30
requests.memory            512Mi   60Gi
```

Если все значения в колонке `Used` МЕНЬШЕ чем `Hard` → ✅ Хорошо!

---

## 🎯 ФИНАЛЬНАЯ ПРОВЕРКА

Если все проверки выше вернули ✅, то:

1. **Алерт должен исчезнуть** за 5-10 минут (проверь Prometheus/Alertmanager)
2. **Приложение работает нормально** (pods Running, логи чистые)
3. **Ресурсы распределены правильно** (ResourceQuota в норме)

### Что значит успех:
```
✅ Deployment обновлен (512Mi вместо 1Gi)
✅ ResourceQuota применена
✅ Поды перезагружены
✅ Логи чистые
✅ Алерт исчез

🎉 ПРОБЛЕМА РЕШЕНА!
```

---

## 🆘 ЧТО ДЕЛАТЬ ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ

### Проблема 1: "kubectl: command not found"
```bash
# kubectl не установлен или не в PATH
# Решение: установи kubectl или используй полный путь
/usr/bin/kubectl apply -f wbgram-original-deployment.yaml
```

---

### Проблема 2: "error: namespaces "default" not found"
```bash
# Namespace не существует (странно, но может быть)
# Решение: создай namespace
kubectl create namespace default
```

---

### Проблема 3: "Error from server: invalid: Pod ... spec.containers[0].resources.limits.memory: Invalid value"
```bash
# Ошибка в формате файла YAML
# Решение: проверь формат памяти (должен быть 512Mi или 512M, не 512MB)
```

---

### Проблема 4: Поды не запускаются (CrashLoopBackOff)
```bash
# 1. Посмотри логи
kubectl logs deployment/wbgram-original -n default

# 2. Если OOMKilled → limits слишком маленькие
kubectl edit deployment wbgram-original -n default
# Измени limits.memory на большее значение (например, 1Gi)

# 3. Перезагрузи deployment
kubectl rollout restart deployment wbgram-original -n default
```

---

### Проблема 5: Алерт не исчез
```bash
# 1. Подождать 5-10 минут (Prometheus кэширует данные)

# 2. Проверить, что ResourceQuota действительно применена
kubectl describe resourcequota -A

# 3. Проверить, что deployment действительно обновлен
kubectl get deployment wbgram-original -n default -o yaml | grep memory

# 4. Если всё OK, но алерт всё ещё есть → пересчитать Prometheus
kubectl rollout restart statefulset prometheus-kube-prometheus-prometheus -n kube-prometheus-stack
```

---

## 🔙 ОТКАТ (если что-то сломалось)

Если нужно отменить изменения:

```bash
# 1. Удалить ResourceQuota
kubectl delete resourcequota default-quota -n default
kubectl delete resourcequota prometheus-quota -n kube-prometheus-stack

# 2. Вернуть старый deployment
git checkout wbgram-original-deployment.yaml
kubectl apply -f wbgram-original-deployment.yaml

# 3. Перезагрузить
kubectl rollout restart deployment wbgram-original -n default

# 4. Проверить
kubectl get pods -n default
```

---

## 📞 ИТОГО

**Выполни эти 4 команды по порядку:**

```bash
1. kubectl apply -f wbgram-original-deployment.yaml
2. kubectl apply -f k8s/monitoring/resourcequota-default.yaml
3. kubectl apply -f k8s/monitoring/resourcequota-kube-prometheus-stack.yaml
4. kubectl rollout restart deployment wbgram-original -n default
```

**Проверь:**
```bash
kubectl get resourcequota -A
kubectl get pods -n default
kubectl logs deployment/wbgram-original -n default
```

**Результат:** Алерт исчезнет за 5-10 минут ✅

---

**Дата:** 2025-10-19  
**Версия:** 1.0  
**Статус:** ✅ Готово к использованию



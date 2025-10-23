# Redis Helm Deployment Guide for New Cluster

**Дата:** 2025-10-20  
**Версия:** 1.0  
**Статус:** Ready for Review

---

## 📋 Описание

Redis развертывается через Helm chart Bitnami с использованием существующего PVC для хранения данных.

### Конфигурация:
- **Chart:** `bitnami/redis`
- **Версия Redis:** 7.4.0-debian-12-r3
- **Реплики:** 1 (single master, no replicas)
- **Хранилище:** 8Gi на существующем PVC `redis-pvc`
- **Storage Class:** `nvme.network-drives.csi.timeweb.cloud`
- **Registry:** Harbor (внутренний реестр)
- **Namespace:** `default`

---

## ✅ Предварительные требования

### 1. Helm установлен
```powershell
helm version
```

### 2. Добавить Bitnami репозиторий
```powershell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 3. Проверить существование PVC
```powershell
kubectl get pvc -n default | Select-String "redis"

# Если PVC не существует, создать его:
kubectl apply -f redis-pvc.yaml
```

**PVC манифест (`redis-pvc.yaml`):**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: nvme.network-drives.csi.timeweb.cloud
  resources:
    requests:
      storage: 8Gi
```

### 4. Проверить ImagePullSecret
```powershell
kubectl get secret harbor-login-secret -n default

# Если секрета нет, создать его:
kubectl create secret docker-registry harbor-login-secret `
  --docker-server=harborskyline.duckdns.org/bitnami-cache `
  --docker-username=admin `
  --docker-password="<password>" `
  -n default
```

---

## 🚀 Развертывание Redis

### Шаг 1: Dry-run проверка
```powershell
# Проверить конфигурацию перед применением
helm install redis bitnami/redis `
  -f .\k8s\new-cluster\redis-values.yaml `
  -n default `
  --dry-run=client
```

### Шаг 2: Установка Redis
```powershell
# Установить Redis с values файлом
helm install redis bitnami/redis `
  -f .\k8s\new-cluster\redis-values.yaml `
  -n default
```

**Ожидаемый результат:**
```
NAME: redis
LAST DEPLOYED: Mon Oct 20 2025 ...
NAMESPACE: default
STATUS: deployed
REVISION: 1
```

### Шаг 3: Проверка статуса
```powershell
# Подождать 30-60 секунд, затем проверить
kubectl get pods -n default | Select-String "redis"
kubectl describe pod redis-master-0 -n default

# Должны увидеть statuses:
# - Pod phase: Running
# - Ready: 1/1
# - Restarts: 0
```

### Шаг 4: Проверить подключение
```powershell
# Проверить что Redis слушает на 6379
kubectl port-forward svc/redis-master 6379:6379 -n default

# В другом терминале:
redis-cli ping
# Ответ: PONG
```

---

## 📊 Мониторинг и Диагностика

### Проверка логов
```powershell
# Логи Redis пода
kubectl logs redis-master-0 -n default --tail=50

# Если есть ошибки, поиск последних логов
kubectl logs redis-master-0 -n default --tail=100 --timestamps=true
```

### Проверка использования ресурсов
```powershell
# Использование памяти и CPU
kubectl top pod redis-master-0 -n default

# Детальная информация о поде
kubectl describe pod redis-master-0 -n default
```

### Проверка хранилища
```powershell
# Размер используемого PVC
kubectl exec -it redis-master-0 -n default -- du -sh /data

# Показатели Redis
kubectl exec -it redis-master-0 -n default -- redis-cli info stats
```

---

## 🔧 Обновление конфигурации

### Изменить values и обновить deployment
```powershell
# Обновить Helm release с новыми values
helm upgrade redis bitnami/redis `
  -f .\k8s\new-cluster\redis-values.yaml `
  -n default

# Проверить статус обновления
kubectl rollout status statefulset/redis-master -n default
```

### Откатить на предыдущую версию
```powershell
# Посмотреть историю релизов
helm history redis -n default

# Откатить на версию 1
helm rollout undo redis 1 -n default

# Или через kubectl
kubectl rollout undo statefulset/redis-master -n default
```

---

## 🗑️ Удаление Redis

### ⚠️ ВАЖНО
При удалении Redis через Helm:
- PVC останется на месте (protect retention policy)
- Данные будут сохранены
- Можно переустановить с тем же PVC

### Удалить только Redis pod'ы и сервисы
```powershell
helm uninstall redis -n default

# Проверить что удалено
kubectl get pods -n default | Select-String "redis"
```

### Проверить что PVC остался
```powershell
kubectl get pvc -n default | Select-String "redis"
```

### Полное удаление (включая PVC)
```powershell
# ⚠️ ОСТОРОЖНО - УДАЛЯЕТ ДАННЫЕ
kubectl delete pvc redis-pvc -n default
```

---

## 📝 Параметры Values файла

### Основные настройки для изменения:

| Параметр | Текущее значение | Описание |
|----------|------------------|---------|
| `master.persistence.size` | `8Gi` | Размер PVC |
| `master.persistence.existingClaim` | `redis-pvc` | Имя существующего PVC |
| `master.resources.requests.memory` | `512Mi` | Minimum памяти |
| `master.resources.limits.memory` | `768Mi` | Maximum памяти |
| `master.resources.requests.cpu` | `250m` | Minimum CPU |
| `master.resources.limits.cpu` | `1000m` | Maximum CPU |
| `replica.enabled` | `false` | Включить репликацию (master-slave) |
| `sentinel.enabled` | `false` | Включить Sentinel для HA |
| `auth.enabled` | `false` | Включить аутентификацию |
| `tls.authClients` | `true` | Включить аутентификацию TLS клиентов |

---

## 🆘 Troubleshooting

### Проблема: Pod CrashLoopBackOff
```powershell
# Посмотреть события и логи
kubectl describe pod redis-master-0 -n default
kubectl logs redis-master-0 -n default --previous

# Возможные причины:
# 1. PVC не существует → создать через redis-pvc.yaml
# 2. Image pull failed → проверить harbor-login-secret
# 3. Resources недостаточно → увеличить в values.yaml
```

### Проблема: PVC stuck in Pending
```powershell
# Посмотреть события
kubectl describe pvc redis-pvc -n default

# Если storage class недоступен:
kubectl get storageclass | Select-String "nvme"

# Может потребоваться создать PV вручную
```

### Проблема: Не может подключиться к Redis
```powershell
# Проверить что pod запущен
kubectl get pods -n default

# Проверить что service exists
kubectl get svc redis-master -n default

# Проверить port-forward
kubectl port-forward svc/redis-master 6379:6379 -n default

# Проверить что Redis слушает
kubectl exec -it redis-master-0 -n default -- redis-cli ping
```

### Проблема: Out of Memory
```powershell
# Проверить использование
kubectl exec -it redis-master-0 -n default -- redis-cli info memory

# Увеличить лимиты в values.yaml:
master:
  resources:
    limits:
      memory: 1Gi
    requests:
      memory: 768Mi

# Применить обновление
helm upgrade redis bitnami/redis -f redis-values.yaml -n default
```

---

## ✅ Чеклист после развертывания

- [ ] Pod `redis-master-0` статус `Running`
- [ ] PVC `redis-pvc` статус `Bound`
- [ ] Service `redis-master` существует
- [ ] Можно подключиться через port-forward
- [ ] `redis-cli ping` возвращает `PONG`
- [ ] Память и CPU в норме (`kubectl top pod`)
- [ ] Нет ошибок в логах (`kubectl logs`)
- [ ] Примечания добавлены в документацию

---

## 📞 Дополнительная информация

- **Bitnami Redis Helm Chart:** https://hub.helm.sh/charts/bitnami/redis
- **Redis Документация:** https://redis.io/documentation
- **Kubernetes Persistent Volumes:** https://kubernetes.io/docs/concepts/storage/persistent-volumes/

---

**Создатель:** AI DevOps Assistant  
**Статус:** Production Ready  
**Последнее обновление:** 2025-10-20

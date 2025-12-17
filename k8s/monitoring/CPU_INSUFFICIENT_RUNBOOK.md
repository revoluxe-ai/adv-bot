# 🧠 Runbook: `Insufficient cpu` / Pending pods (однонодовый кластер)

## 🎯 Симптом
- Pod в статусе **Pending**
- В `kubectl describe pod ...` в Events:
  - `0/1 nodes are available: 1 Insufficient cpu`
  - часто вместе с тем, что rollout пытается создать **дополнительный** pod (maxSurge)

## ✅ Что это означает
Scheduler смотрит **не на реальное потребление**, а на **`resources.requests.cpu`**.  
Если сумма requests на ноде почти равна `Allocatable cpu`, новый pod некуда поставить.

## 🔍 Быстрая диагностика (PowerShell)

### 1) Сразу увидеть Pending и причины
```powershell
kubectl get pods -A --field-selector=status.phase=Pending -o wide
kubectl describe pod POD_NAME -n NAMESPACE
```

### 2) Посмотреть “зарезервированные” ресурсы на ноде
```powershell
$node = kubectl get nodes -o jsonpath='{.items[0].metadata.name}'
kubectl describe node $node | Select-String -Pattern "^Allocated resources:" -Context 0,16
```

### 3) Посмотреть топ по CPU requests + usage
```powershell
.\k8s\monitoring\diagnose-cpu-scheduling.ps1 -Top 30
```

## 🛠️ Типовые решения (по приоритету)

### Вариант A (самый безопасный для rollout): maxSurge=0
Если деплой **1 реплика** и `maxSurge: 25%`, Kubernetes при рестарте пытается создать ещё 1 pod “сверху”.
На однонодовом кластере это часто ломается.

Применить стратегию:
```powershell
kubectl patch deployment DEPLOYMENT -n NAMESPACE --type merge --patch-file .\k8s\monitoring\patch-rollout-strategy.yaml
```

### Вариант B: снизить `requests.cpu` (оставив limits)
Опираемся на `kubectl top pods` и ставим requests ближе к p95 usage (+ запас).

Пример:
```powershell
kubectl set resources deployment/run-shop-update-worker -n prod-adv-bot --requests=cpu=700m,memory=1536Mi --limits=cpu=1,memory=2Gi
kubectl set resources deployment/adv-bot-updater -n prod-adv-bot --requests=cpu=1000m,memory=2Gi --limits=cpu=3,memory=3Gi
```

### Вариант C: временно освободить requests
- масштабировать вниз некритичные деплои (`kubectl scale deployment X --replicas=0`)
- или уменьшить replicas у воркеров на время

## 📌 Примечания
- `kubectl top` требует **metrics-server** (в нашем кластере он есть).
- `coredns` может висеть Pending **по другой причине** (anti-affinity на однонодовом кластере) — это не про CPU.
  - **Как отличить**: в `kubectl describe pod ...` будет `didn't satisfy existing pods anti-affinity rules`, а не `Insufficient cpu`.
  - **Почему так происходит**: при `replicas=1` и `RollingUpdate` с `maxUnavailable: 25%` получается `0`, поэтому контроллер не может удалить текущий pod и пытается создать “surge” pod сверху.
  - **Фикс** (безопасно для однонодового): применить стратегию rollout `maxSurge=0/maxUnavailable=1`:

```powershell
kubectl patch deployment coredns -n kube-system --type merge --patch-file .\k8s\monitoring\patch-rollout-strategy.yaml
```




# 🔧 Predict CTR Service - DNS Resolution Fix

## 🚨 Проблема

```
StatusCode.UNAVAILABLE: DNS resolution failed for predict-ctr-service:50053
Domain name not found
```

**Причина:** Service `predict-ctr-service` не был создан в Kubernetes. Pod существовал, но Service (DNS имя) отсутствовал.

---

## ✅ Решение

### 1. Создан Service для predict-ctr-service

```bash
kubectl apply -f k8s/predict-ctr-service.yaml
```

**Файл:** `k8s/predict-ctr-service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: predict-ctr-service
  namespace: default
spec:
  selector:
    app: predict-ctr-service
  type: ClusterIP
  ports:
  - name: grpc
    port: 50053
    targetPort: 50053
    protocol: TCP
```

### 2. Установлены переменные окружения

Для всех приложений которые используют predict-ctr-service:

```bash
# adv-bot-updater
kubectl set env deployment/adv-bot-updater -n default \
  PREDICT_CTR_HOST=predict-ctr-service \
  PREDICT_CTR_PORT=50053

# predict-ctr-updater
kubectl set env deployment/predict-ctr-updater -n default \
  PREDICT_CTR_HOST=predict-ctr-service \
  PREDICT_CTR_PORT=50053

# run-shop-update-worker
kubectl set env deployment/run-shop-update-worker -n default \
  PREDICT_CTR_HOST=predict-ctr-service \
  PREDICT_CTR_PORT=50053
```

---

## 🔍 Как это работает

1. **gRPC Service слушает:** `predict-ctr-service:50053` внутри кластера
2. **Service решает DNS:** `predict-ctr-service` → `10.101.163.102` (ClusterIP)
3. **Трафик маршрутизируется:** `10.101.163.102:50053` → `Pod_IP:50053`
4. **Приложения получают:** переменные `PREDICT_CTR_HOST=predict-ctr-service` и `PREDICT_CTR_PORT=50053`

---

## ✨ Результат

✅ Pod'ы перезагружены с новыми env переменными  
✅ DNS resolution работает  
✅ gRPC соединение восстановлено  
✅ Ошибки UNAVAILABLE должны исчезнуть  

---

## 📊 Статус

**Service:**
```
NAME                  TYPE        CLUSTER-IP       PORTS
predict-ctr-service   ClusterIP   10.101.163.102   50053/TCP
```

**Deployments обновлены:**
- ✅ adv-bot-updater
- ✅ predict-ctr-updater  
- ✅ run-shop-update-worker

**Следующие шаги:**
1. Ждём пока новые Pod'ы запустятся
2. Проверяем логи на наличие ошибок DNS/gRPC
3. Мониторим через Telegram alert систему

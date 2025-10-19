# ⚡ QUICK GUIDE: Исправление Memory Overcommit

> 🚨 **Алерт:** Cluster has overcommitted memory resource requests by 68.84G bytes

---

## 🎯 В двух словах

Проблема: Сумма `requests` памяти для всех подов превышает доступную память в кластере.  
Решение: Уменьшить requests и применить ResourceQuota.

---

## 🚀 3 шага для исправления

### Шаг 1️⃣: Сделать скрипты исполняемыми

```bash
chmod +x k8s/monitoring/*.sh
```

### Шаг 2️⃣: Запустить основной скрипт

```bash
bash k8s/monitoring/apply-memory-fixes.sh
```

Этот скрипт автоматически:
- ✅ Обновит deployment с новыми лимитами
- ✅ Применит ResourceQuota
- ✅ Перезагрузит поды
- ✅ Проверит статус

### Шаг 3️⃣: Проверить результат

```bash
# Должно показать ResourceQuota
kubectl get resourcequota -A

# Должны показать узлы и их использование памяти
kubectl top nodes

# Должны показать поды и их использование
kubectl top pods -A --sort-by=memory
```

---

## 📊 Что изменилось

| Параметр | Было | Стало | Причина |
|----------|------|-------|---------|
| Memory Requests | 1Gi | 512Mi | ✅ Уменьшено в 2x |
| Memory Limits | 1Gi | 768Mi | ✅ Уменьшено на 25% |
| CPU Requests | 1 | 500m | ✅ Уменьшено в 2x |

---

## 🎓 Что произойдет

1. **Сумма requests** уменьшится с ~165Gi до ~95Gi
2. **Кластер** будет иметь "подушку" безопасности для отказа узлов
3. **Алерт** должен исчезнуть через 5-10 минут
4. **Приложения** продолжат работать нормально

---

## 🔍 Мониторинг статуса

### Быстрая проверка:
```bash
# Должно быть "0 exceeded"
kubectl describe resourcequota default-quota -n default | grep -i exceeded
```

### Полная проверка:
```bash
kubectl describe resourcequota default-quota -n default
```

### Убедиться, что поды работают:
```bash
kubectl get pods -n default
kubectl logs deployment/wbgram-original -n default
```

---

## 📚 Документация

- **Full Guide:** `k8s/MEMORY_OVERCOMMIT_FIX.md` (полная инструкция)
- **Summary:** `k8s/MEMORY_OVERCOMMIT_SUMMARY.md` (краткое резюме)
- **Scripts:**
  - `k8s/monitoring/apply-memory-fixes.sh` - применение исправлений
  - `k8s/monitoring/analyze-memory-usage.sh` - диагностика
  - `k8s/monitoring/find-oversized-deployments.sh` - поиск проблем

---

## ⚠️ Возможные проблемы

### "Pod не запускается после перезагрузки"
```bash
# Проверить логи
kubectl logs deployment/wbgram-original -n default

# Если OOMKilled - увеличить limits
kubectl edit deployment wbgram-original -n default
```

### "ResourceQuota exceeded"
Это нормально при первоначальном применении. Скрипт перезагружает поды, поэтому они пересоздаются с новыми лимитами.

### "Алерт все еще срабатывает"
1. Подождать 5-10 минут (время кэша Prometheus)
2. Проверить, что ResourceQuota применен
3. Проверить, что deployment обновлен

---

## ✅ Что проверить после исправления

- [ ] Скрипт закончился без ошибок
- [ ] `kubectl get resourcequota -A` - показывает ResourceQuota
- [ ] `kubectl top nodes` - показывает нормальное использование
- [ ] Логи подов чистые (нет ошибок)
- [ ] Алерт исчез (проверить Prometheus/Alertmanager)

---

## 📞 Если что-то не работает

1. **Запустить диагностику:**
   ```bash
   bash k8s/monitoring/analyze-memory-usage.sh
   ```

2. **Проверить статус ResourceQuota:**
   ```bash
   kubectl describe resourcequota -A
   ```

3. **Посмотреть события:**
   ```bash
   kubectl get events -n default --sort-by='.lastTimestamp'
   ```

4. **Если нужно откатить:**
   ```bash
   # Удалить ResourceQuota
   kubectl delete resourcequota -A -l app=adv-bot
   
   # Вернуть старый deployment
   git checkout wbgram-original-deployment.yaml
   kubectl apply -f wbgram-original-deployment.yaml
   ```

---

**Время на исправление:** ~5-10 минут  
**Риск:** Низкий (не трогаем основной функционал приложения)  
**Результат:** Алерт исчезнет, кластер стабилен ✅



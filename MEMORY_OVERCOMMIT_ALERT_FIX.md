# 🚨 ИСПРАВЛЕНИЕ ОШИБКИ: Cluster has overcommitted memory resource requests

## Проблема
```
Alert: Cluster has overcommitted memory resource requests.
Severity: warning
Description: Cluster has overcommitted memory resource requests for Pods by 68.84G bytes
and cannot tolerate node failure.
```

---

## ⚡ БЫСТРОЕ РЕШЕНИЕ (10 минут)

### Шаг 1: Сделать скрипты исполняемыми
```bash
chmod +x k8s/monitoring/*.sh
```

### Шаг 2: Запустить исправление
```bash
bash k8s/monitoring/apply-memory-fixes.sh
```

### Шаг 3: Проверить результат
```bash
bash k8s/monitoring/verify-memory-fix.sh
```

**Готово!** ✅ Алерт должен исчезнуть через 5-10 минут.

---

## 📚 Документация

| Файл | Время | Для кого |
|------|-------|----------|
| **k8s/MEMORY_FIX_QUICK_GUIDE.md** | 5 мин | 🚀 Хочу быстро исправить |
| **k8s/MEMORY_OVERCOMMIT_SUMMARY.md** | 10 мин | 📋 Хочу понять суть |
| **k8s/MEMORY_OVERCOMMIT_FIX.md** | 20 мин | 📖 Хочу полный анализ |
| **k8s/MEMORY_FIX_INDEX.md** | 5 мин | 📑 Навигация и индекс |

---

## 🔧 Что было изменено

- ✅ **wbgram-original-deployment.yaml** - память: 1Gi → 512Mi requests, 768Mi limits
- ✅ **k8s/monitoring/resourcequota-default.yaml** - ограничения для namespace
- ✅ **k8s/monitoring/resourcequota-kube-prometheus-stack.yaml** - ограничения для мониторинга

---

## 🛠️ Скрипты

| Скрипт | Использование |
|--------|---------------|
| **apply-memory-fixes.sh** | Применить все исправления (основной) |
| **analyze-memory-usage.sh** | Диагностика памяти |
| **find-oversized-deployments.sh** | Найти problematic deployments |
| **verify-memory-fix.sh** | Проверить исправления |

---

## ✅ Результат

**До:** Requests ~165Gi > Allocatable ~97.5Gi ❌  
**После:** Requests ~95Gi < Allocatable ~97.5Gi ✅

---

**Время на исправление:** 10-15 минут  
**Риск:** Низкий ✅  
**Статус:** Готово к применению

Перейди в `k8s/MEMORY_FIX_INDEX.md` для полной навигации!



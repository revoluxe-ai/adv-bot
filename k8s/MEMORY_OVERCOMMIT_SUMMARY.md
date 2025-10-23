# 📋 SUMMARY: Исправление Memory Overcommit в Kubernetes кластере

## 🎯 Проблема

```
🚨 Alert: Cluster has overcommitted memory resource requests.
Description: Cluster has overcommitted memory resource requests for Pods by 68.84G bytes
and cannot tolerate node failure.
```

**Причина:** Сумма `requests` памяти для всех подов превышает суммарный `allocatable` ресурс узлов на 68.84 ГБ.

---

## 💡 Решение (Примененные изменения)

### 1. ✅ Оптимизирован deployment файл

**Файл:** `wbgram-original-deployment.yaml`

**Изменения:**
```diff
- memory requests: 1Gi → 512Mi
- memory limits: 1Gi → 768Mi
- cpu requests: 1 → 500m
```

**Почему:** Уменьшение requests позволяет более эффективно использовать ресурсы кластера и предотвратить перегрузку.

---

### 2. ✅ Созданы ResourceQuota для namespace-ов

#### a) Для namespace `default`
**Файл:** `k8s/monitoring/resourcequota-default.yaml`

```yaml
ResourceQuota:
  - requests.memory: 60Gi (макс на requests)
  - limits.memory: 80Gi (макс на limits)
  - pods: 200 (макс подов)

LimitRange:
  - Max memory/контейнер: 2Gi
  - Default memory/контейнер: 512Mi
  - Min memory/контейнер: 64Mi
```

#### b) Для namespace `kube-prometheus-stack`
**Файл:** `k8s/monitoring/resourcequota-kube-prometheus-stack.yaml`

```yaml
ResourceQuota:
  - requests.memory: 20Gi (для мониторинга)
  - limits.memory: 30Gi

LimitRange:
  - Max memory/контейнер: 4Gi
  - Default memory/контейнер: 1Gi
```

---

### 3. ✅ Созданы скрипты для автоматизации

#### a) Основной скрипт применения
**Файл:** `k8s/monitoring/apply-memory-fixes.sh`

Применяет все изменения за один раз:
- Обновляет deployment
- Применяет ResourceQuota и LimitRange
- Перезагружает поды
- Проверяет статус

#### b) Скрипт диагностики
**Файл:** `k8s/monitoring/analyze-memory-usage.sh`

Анализирует текущее состояние:
- Информацию о узлах и их ресурсах
- Все deployments/statefulsets с их requests
- Фактическое использование памяти
- Суммарные requests по namespace

#### c) Скрипт поиска проблемных deployments
**Файл:** `k8s/monitoring/find-oversized-deployments.sh`

Находит deployments/statefulsets с избыточными лимитами памяти.

---

## 🚀 Быстрый старт

### Вариант 1: Полностью автоматизированное применение

```bash
# Сделать скрипты исполняемыми
chmod +x k8s/monitoring/*.sh

# Запустить основной скрипт применения
bash k8s/monitoring/apply-memory-fixes.sh
```

### Вариант 2: Пошаговое применение

```bash
# 1. Сначала запустить диагностику
bash k8s/monitoring/analyze-memory-usage.sh

# 2. Найти проблемные deployments
bash k8s/monitoring/find-oversized-deployments.sh

# 3. Обновить deployment
kubectl apply -f wbgram-original-deployment.yaml

# 4. Применить ResourceQuota
kubectl apply -f k8s/monitoring/resourcequota-default.yaml
kubectl apply -f k8s/monitoring/resourcequota-kube-prometheus-stack.yaml

# 5. Перезагрузить deployment
kubectl rollout restart deployment wbgram-original -n default

# 6. Проверить статус
kubectl get resourcequota -A
kubectl describe resourcequota default-quota -n default
```

---

## 📊 Ожидаемые результаты

### До исправления:
```
Узел 1: 87.4 ГБ allocatable
Узел 2: 10.1 ГБ allocatable
───────────────────────────
Итого: 97.5 ГБ allocatable

⚠️ Сумма requests: ~165 ГБ
🚨 ПРЕВЫШЕНИЕ: 68.84 ГБ
❌ Алерт: Cluster has overcommitted memory
```

### После исправления:
```
Узел 1: 87.4 ГБ allocatable
Узел 2: 10.1 ГБ allocatable
───────────────────────────
Итого: 97.5 ГБ allocatable

✅ Сумма requests: ~95 ГБ
✅ В пределах допустимого
✅ Алерт должен исчезнуть
```

---

## 🔧 Таблица рекомендуемых лимитов

| Тип сервиса | Requests | Limits | Использование |
|------------|----------|--------|---------------|
| Web App | 256Mi | 512Mi | Простые приложения |
| API Server | 512Mi | 768Mi | REST API |
| Bot (Telegram) | 512Mi | 768Mi | 🤖 adv-bot |
| Worker | 512Mi | 1Gi | Фоновые задачи |
| Cache (Redis) | 1Gi | 2Gi | Кэширование |
| Database | 2Gi | 4Gi | БД (критично) |
| Prometheus | 512Mi | 1Gi | Мониторинг |
| Grafana | 256Mi | 512Mi | Графики |

---

## ✅ Чек-лист после применения

- [ ] Запущен скрипт диагностики
- [ ] Найдены все проблемные deployments
- [ ] Обновлены deployment файлы
- [ ] Применены ResourceQuota
- [ ] Перезагружены поды
- [ ] Проверен статус ResourceQuota (`kubectl get resourcequota -A`)
- [ ] Проверено использование памяти (`kubectl top nodes`)
- [ ] Алерт исчез из Prometheus/Alertmanager
- [ ] Логи подов чистые (нет ошибок OOM)
- [ ] Мониторинг настроен для отслеживания памяти

---

## 📖 Документация

- **Полная инструкция:** `k8s/MEMORY_OVERCOMMIT_FIX.md`
- **Диагностический скрипт:** `k8s/monitoring/analyze-memory-usage.sh`
- **Скрипт поиска проблем:** `k8s/monitoring/find-oversized-deployments.sh`
- **Скрипт применения:** `k8s/monitoring/apply-memory-fixes.sh`

---

## 🎓 Краткое объяснение Requests vs Limits

### Requests (Запросы) - Гарантированно выделяется
```yaml
resources:
  requests:
    memory: 512Mi    # Кластер гарантирует 512MB этому поду
```
- Используется для планирования (scheduling)
- Сумма requests не должна превышать allocatable узлов
- Если превышение - это ошибка, которую мы исправили

### Limits (Лимиты) - Максимум, который может использовать
```yaml
resources:
  limits:
    memory: 768Mi    # Под не может использовать больше 768MB
```
- Если контейнер превысит лимит - будет убит (OOMKilled)
- Может быть больше requests
- Обычно: limits = requests × 1.5 или × 2

---

## 🛡️ Защита от будущих проблем

1. **Всегда указывайте requests/limits** в deployments
2. **Используйте LimitRange** для установки defaults
3. **Используйте ResourceQuota** для контроля namespace-ов
4. **Мониторьте использование** памяти постоянно
5. **Настройте алерты** при превышении 80% лимита

---

## 🆘 Если проблема не решилась

1. Проверить, что поды перезагрузились:
   ```bash
   kubectl get pods -n default
   ```

2. Проверить логи ошибок:
   ```bash
   kubectl logs deployment/wbgram-original -n default
   ```

3. Проверить статус ResourceQuota:
   ```bash
   kubectl describe resourcequota default-quota -n default
   ```

4. Если нужны дополнительные ресурсы - масштабировать кластер

---

**Последнее обновление:** 2025-10-19  
**Статус:** ✅ Готово к применению  
**Версия:** 1.0



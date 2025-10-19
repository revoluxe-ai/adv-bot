# 📑 ИНДЕКС: Исправление Memory Overcommit в Kubernetes кластере

## 🎯 Проблема

```
🚨 Alert: Cluster has overcommitted memory resource requests.
Severity: warning
Description: Cluster has overcommitted memory resource requests for Pods by 68.84G bytes
and cannot tolerate node failure.
```

---

## 📚 Документация (выбери что читать)

### ⚡ БЫСТРЫЙ СТАРТ (5-10 минут)
- **Файл:** `k8s/MEMORY_FIX_QUICK_GUIDE.md`
- **Для кого:** Те, кто хочет быстро исправить проблему
- **Содержит:** 3 шага для решения + быстрая проверка результата
- **Время:** ~5 минут чтения + 5 минут на применение

### 📋 КРАТКОЕ РЕЗЮМЕ (10-15 минут)
- **Файл:** `k8s/MEMORY_OVERCOMMIT_SUMMARY.md`
- **Для кого:** Те, кто хочет понять ЧТО и ПОЧЕМУ было изменено
- **Содержит:** Краткое описание проблемы + применённые решения + таблица лимитов
- **Время:** ~10 минут чтения

### 📖 ПОЛНАЯ ИНСТРУКЦИЯ (20-30 минут)
- **Файл:** `k8s/MEMORY_OVERCOMMIT_FIX.md`
- **Для кого:** Те, кто хочет полностью разобраться в проблеме
- **Содержит:** Полный анализ проблемы + подробное решение + дополнительные опции
- **Время:** ~20 минут чтения

### 📄 ЭТОТ ФАЙЛ (5 минут)
- **Файл:** `k8s/MEMORY_FIX_INDEX.md` (ты сейчас читаешь)
- **Содержит:** Навигация по всей документации и скриптам
- **Время:** ~5 минут

---

## 🛠️ Скрипты для применения

### 1️⃣ ОСНОВНОЙ СКРИПТ (все в одном)
- **Файл:** `k8s/monitoring/apply-memory-fixes.sh`
- **Что делает:** Применяет ВСЕ исправления за один раз
- **Время:** ~5 минут
- **Команда:**
  ```bash
  bash k8s/monitoring/apply-memory-fixes.sh
  ```
- **Внутри:**
  - Обновляет deployment с новыми лимитами
  - Применяет ResourceQuota
  - Перезагружает поды
  - Проверяет статус

### 2️⃣ ДИАГНОСТИЧЕСКИЙ СКРИПТ
- **Файл:** `k8s/monitoring/analyze-memory-usage.sh`
- **Что делает:** Анализирует текущее состояние памяти
- **Команда:**
  ```bash
  bash k8s/monitoring/analyze-memory-usage.sh
  ```
- **Показывает:**
  - Информацию о узлах
  - Все deployments/statefulsets
  - Использование памяти по подам
  - Суммарные requests по namespace

### 3️⃣ СКРИПТ ПРОВЕРКИ ПРОБЛЕМ
- **Файл:** `k8s/monitoring/find-oversized-deployments.sh`
- **Что делает:** Находит deployments с избыточными лимитами
- **Команда:**
  ```bash
  bash k8s/monitoring/find-oversized-deployments.sh
  ```
- **Показывает:**
  - Список deployments с проблемными лимитами
  - Размеры памяти на каждый под
  - Рекомендуемые значения

### 4️⃣ СКРИПТ ПРОВЕРКИ ИСПРАВЛЕНИЙ
- **Файл:** `k8s/monitoring/verify-memory-fix.sh`
- **Что делает:** Проверяет, что все исправления применены корректно
- **Команда:**
  ```bash
  bash k8s/monitoring/verify-memory-fix.sh
  ```
- **Проверяет:**
  - Deployment обновлен
  - ResourceQuota применен
  - Поды работают
  - Лимиты не превышены

---

## 🔧 Файлы конфигурации

### Обновленный Deployment
- **Файл:** `wbgram-original-deployment.yaml`
- **Что изменилось:**
  - Memory requests: 1Gi → 512Mi
  - Memory limits: 1Gi → 768Mi
  - CPU requests: 1 → 500m

### ResourceQuota для namespace default
- **Файл:** `k8s/monitoring/resourcequota-default.yaml`
- **Содержит:**
  - ResourceQuota (ограничение по памяти и подам)
  - LimitRange (лимиты по умолчанию для контейнеров)

### ResourceQuota для kube-prometheus-stack
- **Файл:** `k8s/monitoring/resourcequota-kube-prometheus-stack.yaml`
- **Содержит:**
  - ResourceQuota с повышенными лимитами (для мониторинга)
  - LimitRange

---

## 🚀 Рекомендуемый порядок действий

### Вариант 1: "Я хочу быстро исправить"
1. Прочитать `k8s/MEMORY_FIX_QUICK_GUIDE.md` (5 мин)
2. Запустить `bash k8s/monitoring/apply-memory-fixes.sh` (5 мин)
3. Запустить `bash k8s/monitoring/verify-memory-fix.sh` (2 мин)
4. **Готово!** ✅

### Вариант 2: "Я хочу всё понять"
1. Прочитать `k8s/MEMORY_OVERCOMMIT_SUMMARY.md` (10 мин)
2. Прочитать `k8s/MEMORY_OVERCOMMIT_FIX.md` (20 мин)
3. Запустить `bash k8s/monitoring/analyze-memory-usage.sh` (2 мин)
4. Запустить `bash k8s/monitoring/apply-memory-fixes.sh` (5 мин)
5. Запустить `bash k8s/monitoring/verify-memory-fix.sh` (2 мин)
6. **Готово!** ✅

### Вариант 3: "Я хочу пошагово"
1. Запустить `bash k8s/monitoring/analyze-memory-usage.sh` (2 мин)
2. Запустить `bash k8s/monitoring/find-oversized-deployments.sh` (2 мин)
3. Вручную применить каждый файл конфигурации (5 мин)
4. Запустить `bash k8s/monitoring/verify-memory-fix.sh` (2 мин)
5. **Готово!** ✅

---

## 📊 Что получится после исправления

### До:
```
Allocatable памяти: ~97.5 Gi
Requests памяти:   ~165 Gi   ❌ ПЕРЕГРУЗКА НА 68.84 Gi
Статус:            🚨 АЛЕРТ
```

### После:
```
Allocatable памяти: ~97.5 Gi
Requests памяти:   ~95 Gi    ✅ В ПРЕДЕЛАХ НОРМЫ
Статус:            ✅ OK
```

---

## 📞 Помощь и отладка

### Если скрипт выдал ошибку:
1. Запустить диагностику:
   ```bash
   bash k8s/monitoring/analyze-memory-usage.sh
   ```
2. Проверить логи:
   ```bash
   kubectl logs deployment/wbgram-original -n default
   ```
3. Посмотреть полную инструкцию: `k8s/MEMORY_OVERCOMMIT_FIX.md`

### Если алерт не исчез:
1. Подождать 5-10 минут (Prometheus кэширует данные)
2. Проверить ResourceQuota:
   ```bash
   kubectl describe resourcequota -A
   ```
3. Запустить проверку:
   ```bash
   bash k8s/monitoring/verify-memory-fix.sh
   ```

### Если нужно откатить изменения:
```bash
# Удалить ResourceQuota
kubectl delete resourcequota -A -l app=adv-bot

# Вернуть старый deployment
git checkout wbgram-original-deployment.yaml
kubectl apply -f wbgram-original-deployment.yaml
```

---

## ✅ Чек-лист для убедительности

- [ ] Прочитал документацию на выбор
- [ ] Запустил основной скрипт
- [ ] Запустил скрипт проверки
- [ ] Результат: ✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ или ⚠️ ПРОВЕРКИ ПРОЙДЕНЫ С ПРЕДУПРЕЖДЕНИЯМИ
- [ ] Подождал 5-10 минут
- [ ] Алерт исчез в Prometheus/Alertmanager
- [ ] Логи подов чистые

---

## 📈 Статистика и метрики

### Скорость исправления:
- Чтение документации: 5-30 минут
- Применение скриптов: 5-10 минут
- Проверка: 2-5 минут
- **Итого:** 12-45 минут

### Риск:
- **Низкий** ✅ - не трогаем основной функционал приложения
- Изменяем только лимиты памяти
- Приложение продолжит работать нормально

### Результат:
- Алерт исчезнет
- Кластер станет стабильнее
- Будет возможность отказа узла

---

## 🔗 Быстрые ссылки

### Вся документация в одном месте:
```
k8s/
├── MEMORY_FIX_INDEX.md                           ← ТЫ ЗДЕСЬ
├── MEMORY_FIX_QUICK_GUIDE.md                    ← НАЧНИ ОТСЮДА (быстро)
├── MEMORY_OVERCOMMIT_SUMMARY.md                 ← НАЧНИ ОТСЮДА (резюме)
├── MEMORY_OVERCOMMIT_FIX.md                     ← НАЧНИ ОТСЮДА (полная)
├── monitoring/
│   ├── apply-memory-fixes.sh                    ← СКРИПТ #1 (основной)
│   ├── analyze-memory-usage.sh                  ← СКРИПТ #2 (диагностика)
│   ├── find-oversized-deployments.sh            ← СКРИПТ #3 (проблемы)
│   ├── verify-memory-fix.sh                     ← СКРИПТ #4 (проверка)
│   ├── resourcequota-default.yaml               ← CONFIG #1
│   └── resourcequota-kube-prometheus-stack.yaml ← CONFIG #2
└── wbgram-original-deployment.yaml              ← DEPLOYMENT (обновлен)
```

---

## 🎓 Обучающие материалы

### Что такое Memory Requests?
- Гарантированная память, которая выделяется поду при создании
- Сумма requests не должна превышать allocatable узлов
- Это именно то, что нарушилось в нашем случае

### Что такое Memory Limits?
- Максимум памяти, который может использовать контейнер
- Если превышить - контейнер будет убит (OOMKilled)
- Может быть больше requests

### Что такое ResourceQuota?
- Ограничение на суммарное использование ресурсов в namespace
- Предотвращает создание подов, которые превысят лимит

### Что такое LimitRange?
- Установка default лимитов для контейнеров
- Автоматически применяется ко всем новым подам в namespace

---

**Дата создания:** 2025-10-19  
**Версия:** 1.0  
**Статус:** ✅ Готово к использованию  
**Автор:** Kubernetes DevOps Team



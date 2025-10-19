# 🛠️ CTR v2 Diagnostic Toolkit

Набор скриптов для диагностики и отладки проблем с CTR v2 прогнозированием.

## 📋 Быстрый Старт

### 1. Общая Диагностика (Начните Отсюда)

```bash
./ctr-status.sh
```

Покажет:
- ✅/❌ Статус подов CTR v2
- 📊 Количество обработанных кампаний за последний час
- 🔴 Последние ошибки

### 2. Если CTR Не Работает для Магазина

```bash
./debug-ctr.sh e46468f2-3d7d-43ec-9113-d590e51452ea 500
```

Заменить `e46468f2...` на нужный shop_id

Покажет логи, связанные с этим магазином из всех компонентов.

### 3. Полная Диагностика (Детально)

```bash
./ctr-final-diagnosis.sh
```

**Самая полезная команда!** Проверит:
- ✅ Item vectors в Neo4j
- ✅ Item vectors в Redis  
- ✅ Ошибки в логах
- ✅ Статистику пропущенных кампаний
- ✅ Процесс обновления vectors

### 4. Просмотр Логов

```bash
./view-logs.sh all          # все логи мониторинга
./view-logs.sh prometheus   # только prometheus
./view-logs.sh grafana      # только grafana
./view-logs.sh alertmanager # только alertmanager
```

### 5. Мониторинг в браузере

```bash
./access-monitoring-ui.sh
```

Откроет Prometheus, Grafana и AlertManager в браузере автоматически.

## 🔍 Типичные Сценарии

### Сценарий 1: CTR вообще не обновляется

```bash
$ ./ctr-status.sh
```

Если видите:
```
Обработано кампаний: 0
Предсказаний выполнено: 0
```

**Решение:**
```bash
kubectl restart deployment/predict-ctr-updater -n default
```

### Сценарий 2: CTR обновляется, но не для конкретного магазина

```bash
$ ./debug-ctr.sh <shop_id> 500
```

Смотрите, есть ли логи про этот магазин. Если нет - магазин не включен в бот.

### Сценарий 3: 20%+ кампаний пропускается

```bash
$ ./ctr-final-diagnosis.sh
```

Если видите:
```
Item nodes с fastrp в Neo4j: 0
```

**Это основная проблема!** Item vectors не загружены в Redis.

**Решение:**
```bash
./fix-ctr-vectors.sh
```

Следуйте рекомендациям из скрипта.

## 📊 Файлы в этой Папке

| Файл | Описание |
|------|---------|
| `ctr-status.sh` | Быстрая проверка статуса |
| `debug-ctr.sh` | Отладка конкретного магазина |
| `ctr-final-diagnosis.sh` | Полная диагностика всех компонентов |
| `fix-ctr-vectors.sh` | Рекомендации по исправлению |
| `access-monitoring-ui.sh` | Открыть UI мониторинга в браузере |
| `view-logs.sh` | Просмотр логов компонентов |
| `CTR_v2_ISSUE_SUMMARY.md` | Подробный отчет о проблеме |

## 🧪 Примеры Использования

### Полный цикл отладки:

```bash
# Шаг 1: Общая проверка
./ctr-status.sh

# Шаг 2: Полная диагностика
./ctr-final-diagnosis.sh

# Шаг 3: Если нужны детали для конкретного магазина
./debug-ctr.sh e46468f2-3d7d-43ec-9113-d590e51452ea 1000

# Шаг 4: Посмотреть все логи
./view-logs.sh all

# Шаг 5: Открыть UI мониторинга
./access-monitoring-ui.sh
```

### Мониторинг в реальном времени:

```bash
# Живые логи predict-ctr-updater
kubectl logs -f -n default $(kubectl get pods -n default -l app=predict-ctr-updater -o jsonpath="{.items[0].metadata.name}")

# Живые логи predict-ctr-service  
kubectl logs -f -n default $(kubectl get pods -n default -l app=predict-ctr-service -o jsonpath="{.items[0].metadata.name}")
```

## 🐛 Распространенные Проблемы

### Проблема: "Нет item_features"

**Вероятная причина:** Item vectors не в Redis

**Проверка:**
```bash
./ctr-final-diagnosis.sh | grep "item_vector"
```

**Решение:**
```bash
./fix-ctr-vectors.sh
```

### Проблема: Медленные запросы (>10s)

**Вероятная причина:** Переполнена БД или медленный запрос к ClickHouse

**Проверка:**
```bash
./ctr-status.sh | grep "Медленные"
```

**Решение:** Посмотрите полные логи:
```bash
./debug-ctr.sh <shop_id> 2000
```

### Проблема: "Pod не найден"

**Решение:** Проверьте наличие подов:
```bash
kubectl get pods -n default | grep -i "ctr\|predict"
```

## 📈 Метрики, Которые Нужно Отслеживать

| Метрика | Норма | Проблема |
|---------|-------|---------|
| Item vectors в Redis | >0 | Нужно загрузить vectors |
| Кампаний обработано/час | >50 | Слишком мало обновлений |
| Медленные запросы | <5 | Если >10 - проблема с БД |
| Процент успеха CTR | >95% | Если <90% - есть проблема |
| Pod restarts | 0 | Если >2 - крашится |

## 🔗 Полезные Ссылки

- **Prometheus:** http://localhost:9090 (требует port-forward)
- **Grafana:** http://localhost:3000 (требует port-forward)
- **AlertManager:** http://localhost:9093 (требует port-forward)

Запустите `./access-monitoring-ui.sh` для автоматического port-forward.

## 📝 Логирование

Все скрипты используют цветной вывод:

- 🟢 **Зеленый** - OK, все нормально
- 🟠 **Желтый** - Warning, требует внимания
- 🔴 **Красный** - Error, критично

## 🆘 Если Ничего Не Помогает

1. Проверьте все логи:
   ```bash
   ./view-logs.sh all | head -200
   ```

2. Посмотрите статус кластера:
   ```bash
   kubectl get nodes
   kubectl get pods -n default
   ```

3. Проверьте дисковое пространство:
   ```bash
   kubectl describe node <node-name>
   ```

4. Создайте issue с выводом:
   ```bash
   ./ctr-final-diagnosis.sh > ctr_issue.log 2>&1
   ```

---

**Последнее обновление:** 2025-10-18  
**Версия:** 1.0





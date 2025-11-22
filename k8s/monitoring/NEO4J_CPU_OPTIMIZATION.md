# 🔧 Оптимизация CPU использования Neo4j

## 📋 Проблема
Neo4j использует только **1 CPU** из доступных **4 CPU**, что может замедлять:
- Загрузку векторов из Neo4j в Redis
- Запросы на получение векторов для прогнозирования CTR
- Общую производительность системы

## 🔍 Текущая конфигурация

### Ресурсы Kubernetes:
- **CPU Limits:** 4 cores
- **CPU Requests:** 4 cores  
- **Memory Limits:** 16Gi
- **Memory Requests:** 16Gi

### Текущее использование:
- **CPU:** ~1 core (969m)
- **Memory:** 2.3GiB

### Конфигурация Neo4j (из my-neo4j-values.yaml):
```yaml
config:
  server.memory.heap.initial_size: 24g
  server.memory.heap.max_size: 24g
  server.memory.pagecache.size: 512m
```

**Проблема:** Нет настроек для параллелизма и использования нескольких CPU!

## 🛠️ Решение: Добавить настройки параллелизма

### Необходимые настройки Neo4j:

1. **dbms.threads.worker_count** - количество worker потоков
2. **cypher.forbid_exhaustive_shortestpath** - оптимизация запросов
3. **dbms.scheduler.threads** - планировщик потоков
4. **dbms.threads.pagecache_io_enabled** - параллельная работа с pagecache

### Обновленный конфиг:

```yaml
neo4j:
  config:
    # Существующие настройки
    db.checkpoint.interval.time: 15m
    db.checkpoint.interval.tx: "10000"
    db.tx_log.rotation.retention_policy: 1G size
    db.tx_log.rotation.size: 250M
    dbms.security.procedures.allowlist: gds.*,apoc.*
    dbms.security.procedures.unrestricted: gds.*,apoc.*
    server.config.strict_validation.enabled: "false"
    server.memory.heap.initial_size: 24g
    server.memory.heap.max_size: 24g
    server.memory.pagecache.size: 512m
    db.tx_log.rotation.keep_logical_logs: "true"
    
    # НОВЫЕ настройки для использования нескольких CPU
    dbms.threads.worker_count: 8  # 2x количество CPU cores
    dbms.scheduler.threads: 4     # Количество CPU cores
    dbms.threads.pagecache_io_enabled: "true"
    cypher.forbid_exhaustive_shortestpath: "true"
    
    # Оптимизация для параллельных запросов
    dbms.query_cache_size: 256m
    dbms.transaction.timeout: 60s
    
    # Оптимизация для GDS (Graph Data Science)
    gds.threads: 4  # Использовать все доступные CPU
```

## 📝 Шаги для применения

### 1. Обновить my-neo4j-values.yaml

Добавить новые настройки в секцию `config`:

```yaml
neo4j:
  config:
    # ... существующие настройки ...
    
    # Оптимизация CPU
    dbms.threads.worker_count: 8
    dbms.scheduler.threads: 4
    dbms.threads.pagecache_io_enabled: "true"
    cypher.forbid_exhaustive_shortestpath: "true"
    dbms.query_cache_size: 256m
    dbms.transaction.timeout: 60s
    gds.threads: 4
```

### 2. Применить изменения

```powershell
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'

# Обновить Helm release
helm upgrade my-neo4j neo4j/neo4j \
  -n prod-analytics \
  -f k8s\databases\neo4j\my-neo4j-values.yaml

# Или если используется другой способ деплоя
kubectl apply -f k8s\databases\neo4j\my-neo4j-values.yaml -n prod-analytics
```

### 3. Перезапустить Neo4j (если нужно)

```powershell
kubectl rollout restart statefulset/my-neo4j -n prod-analytics
```

### 4. Проверить результат

```powershell
# Проверить использование CPU
kubectl top pod my-neo4j-0 -n prod-analytics

# Проверить логи на наличие ошибок
kubectl logs my-neo4j-0 -n prod-analytics --tail=50
```

## 🎯 Ожидаемый результат

После применения настроек:
- ✅ Neo4j должен использовать **больше CPU** (2-4 cores вместо 1)
- ✅ Запросы на получение векторов должны выполняться **быстрее**
- ✅ Процесс загрузки векторов в Redis должен **ускориться**
- ✅ Прогнозирование CTR должно работать **быстрее**

## ⚠️ Важные замечания

1. **dbms.threads.worker_count** - рекомендуется устанавливать в 2x количество CPU cores
2. **gds.threads** - для Graph Data Science операций, должно быть равно количеству CPU cores
3. **Память** - убедитесь что heap size не превышает доступную память
4. **Мониторинг** - после изменений нужно мониторить использование ресурсов

## 📊 Мониторинг после изменений

```powershell
# Проверить использование CPU каждые 30 секунд
while ($true) {
    kubectl top pod my-neo4j-0 -n prod-analytics
    Start-Sleep -Seconds 30
}
```

## 🔗 Связанные проблемы

- Если векторы не загружаются в Redis → может быть связано с медленной работой Neo4j
- Если прогнозы CTR не работают → может быть связано с отсутствием векторов из-за медленной загрузки

---

**Дата создания:** 2025-11-18  
**Статус:** Требуется применение настроек






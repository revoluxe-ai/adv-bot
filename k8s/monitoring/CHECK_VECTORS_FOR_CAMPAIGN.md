# 🔍 Проверка векторов для кампании 30554463

## 📋 Проблема
Кампания `30554463` не получает прогнозы CTR. Возможная причина - отсутствие векторов в Redis или Neo4j.

## ✅ Что уже проверено

1. ✅ **update-keywords-vectors процесс работает** - логи показывают активную запись векторов в Redis
2. ✅ **predict-ctr-service работает** - Pod Running
3. ✅ **run-shop-update-worker работает** - 4 реплики Running
4. ✅ **Переменные окружения установлены** - PREDICT_CTR_HOST и PREDICT_CTR_PORT

## 🔍 Что нужно проверить

### Шаг 1: Получить данные кампании из БД

```sql
-- Получить nmids кампании
SELECT nmids 
FROM adv_setting 
WHERE adv_id = 30554463;

-- Получить ключевые слова кампании
SELECT ks.text
FROM keyword_setting ks
JOIN adv_setting a ON ks.adv_setting_id = a.id
WHERE a.adv_id = 30554463
LIMIT 10; -- для примера первые 10
```

### Шаг 2: Проверить векторы товаров в Redis

```powershell
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'

# Найти Redis pod
$redisPod = kubectl get pods -n prod-adv-bot -l app=redis -o jsonpath='{.items[0].metadata.name}'

# Проверить общее количество item_vector ключей
kubectl exec $redisPod -n prod-adv-bot -- redis-cli --raw KEYS "item_vector:*" | Measure-Object -Line

# Проверить конкретный nmid (заменить {nmid} на реальный nmid из шага 1)
kubectl exec $redisPod -n prod-adv-bot -- redis-cli GET "item_vector:{nmid}"
```

**Ожидаемый результат:** Должен вернуть JSON массив с вектором (массив чисел)

### Шаг 3: Проверить векторы товаров в Neo4j

```cypher
// Заменить [nmid1, nmid2, ...] на реальные nmids из шага 1
MATCH (item:Item)
WHERE item.nmid IN [nmid1, nmid2, ...]
RETURN item.nmid, 
       CASE 
         WHEN item.fastrp IS NOT NULL THEN 'HAS_VECTOR' 
         ELSE 'NO_VECTOR' 
       END as status,
       size(item.fastrp) as vector_size
```

**Ожидаемый результат:** Все nmids должны иметь `status = 'HAS_VECTOR'` и `vector_size > 0`

### Шаг 4: Проверить векторы ключевых слов в Redis

```powershell
# Проверить общее количество keyword_vector ключей
kubectl exec $redisPod -n prod-adv-bot -- redis-cli --raw KEYS "keyword_vector:*" | Measure-Object -Line

# Проверить конкретное ключевое слово (заменить {keyword} на реальное из шага 1)
kubectl exec $redisPod -n prod-adv-bot -- redis-cli GET "keyword_vector:{keyword}"
```

**Ожидаемый результат:** Должен вернуть JSON массив с вектором

### Шаг 5: Проверить векторы ключевых слов в Neo4j

```cypher
// Заменить ['keyword1', 'keyword2', ...] на реальные ключевые слова из шага 1
MATCH (k:KeywordPhrase)
WHERE k.text IN ['keyword1', 'keyword2', ...]
RETURN k.text,
       CASE 
         WHEN k.fastrp IS NOT NULL THEN 'HAS_VECTOR' 
         ELSE 'NO_VECTOR' 
       END as status,
       size(k.fastrp) as vector_size
LIMIT 20
```

**Ожидаемый результат:** Большинство ключевых слов должны иметь векторы

## 🛠️ Решение проблем

### Если векторов нет в Redis, но есть в Neo4j:

1. **Перезапустить процесс обновления векторов:**
   ```powershell
   kubectl rollout restart deployment/update-keywords-vectors-in-redis-from-neo4j -n prod-adv-bot
   ```

2. **Подождать 2-3 минуты** и проверить снова

3. **Проверить логи процесса:**
   ```powershell
   $pod = kubectl get pods -n prod-adv-bot -l app=update-keywords-vectors-in-redis-from-neo4j -o jsonpath='{.items[0].metadata.name}'
   kubectl logs $pod -n prod-adv-bot --tail=100
   ```

### Если векторов нет в Neo4j:

1. **Проверить процесс генерации векторов:**
   - Должен быть процесс который создает векторы в Neo4j
   - Проверить логи graph_vector_updater или аналогичного процесса

2. **Запустить генерацию векторов:**
   - Зависит от архитектуры системы
   - Может потребоваться запуск ML pipeline

### Если векторы есть, но прогнозы не работают:

1. **Проверить формат векторов:**
   - Векторы должны быть массивами чисел
   - Размерность должна соответствовать ожидаемой моделью

2. **Проверить логи predict-ctr-service:**
   ```powershell
   $pod = kubectl get pods -n prod-adv-bot -l app=predict-ctr-service -o jsonpath='{.items[0].metadata.name}'
   kubectl logs $pod -n prod-adv-bot --tail=200 | Select-String -Pattern "30554463|error|ERROR" -CaseSensitive:$false
   ```

## 📊 Критические проверки

### Минимальные требования для работы CTR v2:

1. ✅ **Item vectors в Redis** - хотя бы для одного nmid кампании
2. ✅ **Keyword vectors в Redis** - хотя бы для одного ключевого слова
3. ✅ **Процесс обновления векторов работает** - update-keywords-vectors-in-redis-from-neo4j
4. ✅ **predict-ctr-service доступен** - gRPC соединение работает

## 🎯 Следующие шаги

1. Выполнить SQL запросы для получения nmids и ключевых слов
2. Проверить векторы в Redis для полученных данных
3. Проверить векторы в Neo4j для полученных данных
4. Если векторов нет - запустить процесс обновления
5. Если векторы есть - проверить логи predict-ctr-service на ошибки

---

**Дата создания:** 2025-11-18  
**Статус:** Требуется выполнение проверок






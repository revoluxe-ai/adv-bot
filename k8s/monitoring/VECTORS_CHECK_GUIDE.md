# 🔍 Проверка векторов для прогнозирования CTR

## 📋 Проблема
Кампания `30554463` не получает прогнозы CTR. Возможная причина - отсутствие векторов в Redis или Neo4j.

## 🔄 Pipeline использования векторов

### Процесс прогнозирования CTR v2:

```
1. Получение nmids кампании
   ↓
2. Получение векторов товаров (item_vector) из Redis
   ↓
3. Если нет в Redis → получение из Neo4j (Item.fastrp)
   ↓
4. Получение ключевых слов кампании
   ↓
5. Получение векторов ключевых слов (keyword_vector) из Redis
   ↓
6. Если нет в Redis → получение из Neo4j (KeywordPhrase.fastrp)
   ↓
7. Формирование features для ML модели
   ↓
8. Прогноз CTR через predict-ctr-service
```

## 🔍 Что нужно проверить

### 1. Векторы товаров (Item Vectors)

#### В Redis:
```bash
# Подключиться к Redis pod
kubectl exec -it -n prod-adv-bot redis-pod-name -- redis-cli

# Проверить количество item_vector ключей
KEYS item_vector:* | wc -l

# Проверить конкретный nmid (нужно знать nmids кампании)
GET item_vector:{nmid}
```

#### В Neo4j:
```cypher
// Проверить количество Item с векторами
MATCH (item:Item)
WHERE item.fastrp IS NOT NULL
RETURN count(item) as items_with_vectors

// Проверить конкретные nmids (нужно знать nmids кампании)
MATCH (item:Item)
WHERE item.nmid IN [nmid1, nmid2, ...]
RETURN item.nmid, 
       CASE WHEN item.fastrp IS NOT NULL THEN 'HAS_VECTOR' ELSE 'NO_VECTOR' END as status
```

### 2. Векторы ключевых слов (Keyword Vectors)

#### В Redis:
```bash
# Проверить количество keyword_vector ключей
KEYS keyword_vector:* | wc -l

# Проверить конкретное ключевое слово
GET keyword_vector:{keyword_text}
```

#### В Neo4j:
```cypher
// Проверить количество KeywordPhrase с векторами
MATCH (k:KeywordPhrase)
WHERE k.fastrp IS NOT NULL
RETURN count(k) as keywords_with_vectors

// Проверить конкретные ключевые слова
MATCH (k:KeywordPhrase)
WHERE k.text IN ['keyword1', 'keyword2', ...]
RETURN k.text,
       CASE WHEN k.fastrp IS NOT NULL THEN 'HAS_VECTOR' ELSE 'NO_VECTOR' END as status
```

## 📊 SQL запросы для получения данных кампании

### Получить nmids кампании:
```sql
SELECT nmids 
FROM adv_setting 
WHERE adv_id = 30554463;
```

### Получить ключевые слова кампании:
```sql
SELECT ks.text
FROM keyword_setting ks
JOIN adv_setting a ON ks.adv_setting_id = a.id
WHERE a.adv_id = 30554463;
```

## 🛠️ Команды для проверки

### Проверка Redis векторов товаров:
```powershell
$env:KUBECONFIG = 'C:\Users\vkita\my_code\tasks\DevOps-GitOps-Cursor\adv-bot\k8s\new-cluster\new-cluster-config.yaml'
$redisPod = kubectl get pods -n prod-adv-bot -l app=redis -o jsonpath='{.items[0].metadata.name}'
kubectl exec $redisPod -n prod-adv-bot -- redis-cli --raw KEYS "item_vector:*" | Measure-Object -Line
```

### Проверка Redis векторов ключевых слов:
```powershell
kubectl exec $redisPod -n prod-adv-bot -- redis-cli --raw KEYS "keyword_vector:*" | Measure-Object -Line
```

### Проверка логов update-keywords-vectors:
```powershell
$vectorPod = kubectl get pods -n prod-adv-bot -l app=update-keywords-vectors-in-redis-from-neo4j -o jsonpath='{.items[0].metadata.name}'
kubectl logs $vectorPod -n prod-adv-bot --tail=100
```

## 🔧 Решение проблем

### Если векторов нет в Redis:

1. **Проверить процесс обновления векторов:**
   ```powershell
   kubectl logs -n prod-adv-bot deployment/update-keywords-vectors-in-redis-from-neo4j --tail=200
   ```

2. **Перезапустить процесс обновления векторов:**
   ```powershell
   kubectl rollout restart deployment/update-keywords-vectors-in-redis-from-neo4j -n prod-adv-bot
   ```

3. **Проверить что векторы есть в Neo4j:**
   - Если нет в Neo4j → нужно запустить процесс генерации векторов
   - Если есть в Neo4j → процесс обновления должен их загрузить в Redis

### Если векторов нет в Neo4j:

1. **Проверить процесс генерации векторов:**
   - Должен быть процесс который создает векторы в Neo4j
   - Проверить логи graph_vector_updater или аналогичного процесса

2. **Запустить генерацию векторов:**
   - Зависит от архитектуры системы
   - Может потребоваться запуск ML pipeline для генерации векторов

## 📝 Чеклист проверки

- [ ] Получить nmids кампании из БД
- [ ] Проверить наличие item_vector в Redis для всех nmids
- [ ] Проверить наличие Item.fastrp в Neo4j для всех nmids
- [ ] Получить ключевые слова кампании из БД
- [ ] Проверить наличие keyword_vector в Redis для всех ключевых слов
- [ ] Проверить наличие KeywordPhrase.fastrp в Neo4j для всех ключевых слов
- [ ] Проверить логи update-keywords-vectors процесса
- [ ] Проверить логи predict-ctr-service на ошибки отсутствия векторов

## 🎯 Критические точки

1. **predict-ctr-service требует векторы для работы:**
   - Без векторов товаров → не может создать item_features
   - Без векторов ключевых слов → не может создать keyword_features
   - Без features → не может сделать прогноз

2. **Процесс обновления векторов:**
   - `update-keywords-vectors-in-redis-from-neo4j` должен работать постоянно
   - Загружает векторы из Neo4j в Redis
   - Если процесс не работает → векторы не обновляются

3. **Источник векторов:**
   - Neo4j - основной источник (должны быть созданы заранее)
   - Redis - кэш для быстрого доступа
   - Если нет в Neo4j → нужно генерировать

---

**Дата создания:** 2025-11-18  
**Статус:** Требуется проверка векторов






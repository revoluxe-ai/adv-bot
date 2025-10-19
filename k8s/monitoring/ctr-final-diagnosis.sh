#!/bin/bash

# Финальная диагностика проблемы CTR v2
# Проверяет: nmid vectors, item features, redis, neo4j

echo -e "\033[1;32m╔════════════════════════════════════════════════════════════════════╗\033[0m"
echo -e "\033[1;32m║         ФИНАЛЬНАЯ ДИАГНОСТИКА CTR v2: NMID VECTORS ISSUE           ║\033[0m"
echo -e "\033[1;32m╚════════════════════════════════════════════════════════════════════╝\033[0m"
echo ""

# 1. Проверяем Redis на наличие item vectors
echo -e "\033[1;36m1️⃣  Проверка Redis: item_vector:* ключи\033[0m"
REDIS_POD=$(kubectl get pods -n default -l app=redis -o jsonpath="{.items[0].metadata.name}" 2>/dev/null | grep -o "redis[^-]*-[^-]*-[0-9]*")
if [ -n "$REDIS_POD" ]; then
    echo "   Redis pod: $REDIS_POD"
    COUNT=$(kubectl exec -n default "$REDIS_POD" -- redis-cli --no-auth-warning KEYS "item_vector:*" 2>/dev/null | wc -l)
    echo "   Количество item_vector ключей в Redis: $COUNT"
    if [ "$COUNT" -eq 0 ]; then
        echo -e "   \033[1;31m❌ ПРОБЛЕМА: нет item_vector ключей в Redis!\033[0m"
    else
        echo -e "   \033[1;32m✅ OK: найдено $COUNT item_vector ключей\033[0m"
    fi
else
    echo -e "   \033[1;31m❌ Redis pod не найден\033[0m"
fi

echo ""

# 2. Проверяем Neo4j на наличие Item с fastrp
echo -e "\033[1;36m2️⃣  Проверка Neo4j: Item nodes с fastrp\033[0m"
NEO4J_POD=$(kubectl get pods -n default -l app=my-neo4j -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -n "$NEO4J_POD" ]; then
    echo "   Neo4j pod: $NEO4J_POD"
    # Проверим наличие Item nodes
    COUNT=$(kubectl exec -n default "$NEO4J_POD" -c neo4j -- cypher-shell -u neo4j -p "$(kubectl get secret -n default my-neo4j-auth -o jsonpath='{.data.NEO4J_AUTH}' 2>/dev/null | base64 -d | cut -d'/' -f2)" "MATCH (i:Item) WHERE i.fastrp IS NOT NULL RETURN count(i) as cnt" 2>/dev/null | tail -1 || echo "Ошибка подключения")
    echo "   Item nodes с fastrp в Neo4j: $COUNT"
else
    echo -e "   \033[1;31m❌ Neo4j pod не найден\033[0m"
fi

echo ""

# 3. Ошибки в predict-ctr-updater
echo -e "\033[1;36m3️⃣  Ошибки в predict-ctr-updater (последние 50 строк)\033[0m"
UPDATER_POD=$(kubectl get pods -n default -l app=predict-ctr-updater -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -n "$UPDATER_POD" ]; then
    ERRORS=$(kubectl logs -n default "$UPDATER_POD" --tail=500 2>&1 | grep -i "error\|exception\|failed\|redis" | head -20)
    if [ -z "$ERRORS" ]; then
        echo -e "   \033[1;32m✅ Явных ошибок не найдено\033[0m"
    else
        echo -e "   \033[1;31m❌ Найдены ошибки:\033[0m"
        echo "$ERRORS" | head -5
    fi
else
    echo -e "   \033[1;31m❌ predict-ctr-updater pod не найден\033[0m"
fi

echo ""

# 4. Количество "Нет item_features"
echo -e "\033[1;36m4️⃣  Статистика пропущенных кампаний\033[0m"
if [ -n "$UPDATER_POD" ]; then
    NO_FEATURES=$(kubectl logs -n default "$UPDATER_POD" --tail=1000 2>&1 | grep "Нет item_features" | wc -l)
    TOTAL_CAMPAIGNS=$(kubectl logs -n default "$UPDATER_POD" --tail=1000 2>&1 | grep "Обработка кампании" | wc -l)
    
    echo "   Всего обработано кампаний: $TOTAL_CAMPAIGNS"
    echo "   Пропущено (нет item_features): $NO_FEATURES"
    if [ "$TOTAL_CAMPAIGNS" -gt 0 ]; then
        PERCENT=$((NO_FEATURES * 100 / TOTAL_CAMPAIGNS))
        echo "   Процент пропусков: $PERCENT%"
        if [ "$PERCENT" -gt 50 ]; then
            echo -e "   \033[1;31m❌ КРИТИЧНО: более 50% кампаний пропускается!\033[0m"
        fi
    fi
fi

echo ""

# 5. Проверяем update_vectors_in_redis процесс
echo -e "\033[1;36m5️⃣  Логи update_vectors_in_redis\033[0m"
WORKER_POD=$(kubectl get pods -n default -l app=adv-bot-updater -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -n "$WORKER_POD" ]; then
    VECTOR_LOGS=$(kubectl logs -n default "$WORKER_POD" --tail=500 2>&1 | grep -i "update_vectors_in_redis\|update_items_vectors\|Redis" | head -10)
    if [ -z "$VECTOR_LOGS" ]; then
        echo -e "   \033[1;31m⚠️  Нет логов про обновление vectors\033[0m"
    else
        echo "$VECTOR_LOGS"
    fi
else
    echo -e "   \033[1;33m⚠️  adv-bot-updater pod не найден (проверьте имя)\033[0m"
fi

echo ""
echo -e "\033[1;32m╔════════════════════════════════════════════════════════════════════╗\033[0m"
echo -e "\033[1;32m║                        РЕКОМЕНДАЦИИ:                               ║\033[0m"
echo -e "\033[1;32m╚════════════════════════════════════════════════════════════════════╝\033[0m"
echo ""
echo -e "\033[1;33m1. Если item_vector ключей = 0:\033[0m"
echo "   → Проверьте: `kubectl logs -n default update-keywords-vectors... --tail=200`"
echo "   → Item vectors должны загружаться в Redis из Neo4j"
echo ""
echo -e "\033[1;33m2. Если > 50% кампаний пропускается:\033[0m"
echo "   → Проблема в отсутствии item features в Redis"
echo "   → Нужно запустить force-update vectors"
echo ""
echo -e "\033[1;33m3. Проверить связь Redis ↔ Neo4j:\033[0m"
echo "   → `kubectl exec -n default <redis-pod> -- redis-cli ping`"
echo "   → Должно быть: PONG"
echo ""


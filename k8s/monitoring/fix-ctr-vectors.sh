#!/bin/bash

# Скрипт для исправления проблемы с CTR v2
# Запускает обновление item vectors из Neo4j в Redis

echo -e "\033[1;32m🔧 Исправление CTR v2: обновление item vectors\033[0m"
echo ""

# Найдем pod adv-bot-updater
UPDATER_POD=$(kubectl get pods -n default -l app=adv-bot-updater -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)

if [ -z "$UPDATER_POD" ]; then
    echo -e "\033[1;31m❌ Pod adv-bot-updater не найден!\033[0m"
    echo ""
    echo "Доступные поды:"
    kubectl get pods -n default | grep -i updater
    exit 1
fi

echo -e "✅ Найден pod: $UPDATER_POD"
echo ""

# Опция 1: Перезагрузить pod (это часто помогает при проблемах с инициализацией)
echo -e "\033[1;33m📋 Вариант 1: Перезагрузить pod (рекомендуется)\033[0m"
echo "   Команда: kubectl rollout restart deployment/adv-bot-updater -n default"
echo ""

# Опция 2: Выполнить скрипт обновления напрямую
echo -e "\033[1;33m📋 Вариант 2: Выполнить python команду в pod\033[0m"
echo "   (требует прямого доступа к коду)"
echo ""

echo -e "\033[1;33m💡 Рекомендуемые действия:\033[0m"
echo ""
echo "1️⃣  Сначала проверьте логи adv-bot-updater:"
echo "   kubectl logs -n default $UPDATER_POD --tail=200 | grep -i 'update_items_vectors\|update_vectors'"
echo ""
echo "2️⃣  Если логов про update нет - перезагрузите deployment:"
echo "   kubectl rollout restart deployment/adv-bot-updater -n default"
echo ""
echo "3️⃣  После перезагрузки (подождите 2-3 минуты):"
echo "   ./ctr-final-diagnosis.sh"
echo ""
echo "4️⃣  Если Item vectors все еще = 0 в Neo4j:"
echo "   → Проверьте процесс graph_vector_updater"
echo "   → Могут отсутствовать данные о товарах в системе"
echo ""


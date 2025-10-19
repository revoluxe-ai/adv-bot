#!/bin/bash

# Скрипт для очистки ClickHouse от старых версий данных
# Удаляет дублирующиеся версии и архивирует старые данные

echo -e "\033[1;32m🧹 Очистка ClickHouse от старых версий данных\033[0m"
echo ""

# Получаем пароль ClickHouse
CLICKHOUSE_POD="clickhouse-1739529274-shard0-0"
CLICKHOUSE_NS="default"

echo -e "\033[1;36m📊 Текущий размер таблиц:\033[0m"
echo ""

# Подключаемся без пароля (может быть пустой) или используем default
kubectl exec -n $CLICKHOUSE_NS $CLICKHOUSE_POD -- clickhouse-client \
  --query "SELECT table, formatReadableSize(sum(bytes)) as size FROM system.parts WHERE database='default_db' GROUP BY table ORDER BY sum(bytes) DESC;" \
  2>/dev/null || echo "⚠️ Не удалось подключиться - проверьте пароль"

echo ""
echo -e "\033[1;36m🗑️ Рекомендации по очистке:\033[0m"
echo ""
echo "1️⃣  Удалить старые версии данных (оставить только последние):"
echo "   Для таблицы full_adv_wb_stat:"
echo ""
echo "   ALTER TABLE default_db.full_adv_wb_stat DELETE"
echo "   WHERE version NOT IN ("
echo "     SELECT DISTINCT version FROM ("
echo "       SELECT version, ROW_NUMBER() OVER (PARTITION BY adv_id, date ORDER BY version DESC) as rn"
echo "       FROM default_db.full_adv_wb_stat"
echo "     )"
echo "     WHERE rn = 1"
echo "   );"
echo ""
echo "2️⃣  Или удалить все данные старше N дней:"
echo "   ALTER TABLE default_db.full_adv_wb_stat DELETE WHERE date < now() - interval 90 day;"
echo ""
echo "3️⃣  Оптимизировать таблицу после удаления:"
echo "   OPTIMIZE TABLE default_db.full_adv_wb_stat FINAL;"
echo ""
echo -e "\033[1;33m⚠️  ВАЖНО:\033[0m"
echo "  - Выполняйте эти операции во время низкой нагрузки"
echo "  - Они могут занять время"
echo "  - Сделайте бэкап перед удалением"
echo ""





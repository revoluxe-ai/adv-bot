# Точки входа приложения в Kubernetes

Этот документ содержит список всех точек входа приложения, которые запускаются в кластере Kubernetes.

## Основные сервисы

| Деплоймент | Команда запуска | Описание |
|------------|-----------------|----------|
| adv-bot-asq-worker | `exec arq app.arq_workers.workers.WorkerSettings` | Асинхронная очередь задач (ARQ) |
| adv-bot-updater | `exec python updater.py` | Старый модуль обновления данных|
| keywords-parsing | `exec python run_keywords_parsing.py` | Парсинг ключевых слов - устарело |
| model-updater-deployment | `exec python run_update_model.py` | Обновление модели |
| new-wb-shop-updater | `exec python new_wb_shop_update_run.py` | Новый модуль обновления магазинов Wildberries |
| predict-ctr-updater | `exec python run_update_predict_ctr.py` | Обновление предсказаний CTR |
| sender-message | `exec python run_send_info_message_to_users_process.py` | Отправка информационных сообщений пользователям |
| update-keywords-vectors-in-redis-from-neo4j | `exec python run_update_keyword_vectors_in_redis.py` | Обновление векторов ключевых слов в Redis из Neo4j |
| update-wb-adv-phrases | `exec python keyword_sending_to_neo4j.py` | Отправка ключевых слов в Neo4j |
| click-house-system-logs-table-cleaner | `exec python trunc_system_log_in_clickhouse.py` | Очистка системных логов в ClickHouse |
| sellerspub-bot | `exec python client_bot_run.py` | Клиентский бот |

## Заметки по запуску

Все точки входа запускаются через `/bin/bash -c` с предварительным запуском следующих сервисов:
```bash
service rsyslog start;
service cron start;
# Затем выполняется команда запуска
```

## Настройка окружения

Все контейнеры работают с настройкой часового пояса `Europe/Moscow` и используют конфигурационные данные из ConfigMaps и Secrets Kubernetes.

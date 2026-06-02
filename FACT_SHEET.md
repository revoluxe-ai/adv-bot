# Fact Sheet: WB Advertising Auto-Optimization Platform

## 📋 Технический Стек

### Языки и Фреймворки
- **Python 3.11** — основной язык разработки
- **aiogram 3.4** — Telegram Bot framework для клиентского интерфейса
- **FastAPI 0.110** — REST API и webhook обработчик
- **SQLAlchemy 2.0** (async) — ORM для работы с PostgreSQL
- **Pydantic 2.5** — валидация данных и settings management
- **ARQ 0.26** — асинхронная очередь задач на базе Redis

### Базы Данных и Хранилища
- **PostgreSQL** — основная БД (master-replica конфигурация)
  - Alembic для миграций (36 миграций)
  - AsyncPG драйвер
  - SSL-соединения с поддержкой сертификатов
- **ClickHouse** — аналитическая БД для статистики и метрик
  - Хранение истории позиций
  - Агрегация статистики кампаний
  - Plan-Fact анализ
- **Redis** — кеширование и очереди задач
  - Master-replica топология
  - Celery broker (5 retries, 30s delay)
  - ARQ job queue (24h retention, 10 max tries)
  - Кеш расчетных ключевых слов, минимальных ставок, векторов
- **Neo4j** — граф БД для рекомендаций товаров

### ML и Аналитика
- **TensorFlow/Keras** — ML модели для прогнозирования CTR
- **scikit-learn 1.4** — ML utilities
- **NumPy/Pandas** — data processing
- **gRPC** — predict-ctr-service для ML инференса (порт 50053)

### Инфраструктура
- **Kubernetes** — оркестрация (Docker Desktop kubectl v1.34.1)
- **GitHub Actions** — CI/CD pipeline (auto-deploy на push в master)
- **GitHub Container Registry** — хранение Docker образов
- **Prometheus + Grafana** — мониторинг и алертинг (15+ правил)
- **Fluent Bit** — централизованное логирование
- **Docker** — контейнеризация
- **Poetry** — управление зависимостями

### Внешние API
- **Wildberries API** — основной маркетплейс (promotion, analytics, content)
  - Rate limiting с экспоненциальным backoff (0.1s - 300s)
  - Adaptive delay mechanism (5 успехов → уменьшение на 50ms)
- **YooKassa API** — прием платежей
- **Telegram Bot API** — пользовательский интерфейс

---

## 🚀 Ключевые Достижения (Что Сделал → Результат → Где в Коде)

### 1. Автоматическая Оптимизация Рекламных Ставок
**Действие:** Разработал систему автоматического управления ставками для ~30 типов рекламных кампаний Wildberries  
**Результат:** Оптимизация бюджета с учетом CTR, позиций, и конкурентной среды; автоподбор минимальных ставок  
**Код:** `app/modules/shop_runner/service_manager/services/update_cluster_bids_manager/`

### 2. ML-Прогнозирование CTR для Ключевых Слов
**Действие:** Внедрил систему прогнозирования CTR через gRPC-сервис с векторизацией ключевых слов и товаров  
**Результат:** Умные рекомендации ставок на основе предсказанной кликабельности; снижение расходов на нерелевантные запросы  
**Код:** `app/modules/grpcs/predict_ctr_client.py`, `app/modules/wb_adv_updater/graph_vector_updater.py`, `run_update_keyword_vectors_in_redis.py`

### 3. Multi-Tenant Архитектура с Изоляцией Магазинов
**Действие:** Спроектировал систему управления множественными WB-кабинетами с изоляцией данных и токенов  
**Результат:** Один бот обслуживает сотни магазинов параллельно; независимые настройки и безопасное хранение API-токенов  
**Код:** `app/modules/shop_runner/shop_run_worker/`, `app/modules/common_slaves/wildberries/`, `app/modules/token_monitoring/`

### 4. Billing и Управление Балансами
**Действие:** Реализовал биллинговую систему с событийной архитектурой и бонусной программой (100% по умолчанию)  
**Результат:** Автоматическое списание за услуги, отслеживание событий, гибкие тарифы (от ₽1,667/мес за опцию)  
**Код:** `app/modules/billing/`, `app/modules/balance_manager/`, `app/payments/`

### 5. Асинхронная Обработка с ARQ + Celery
**Действие:** Настроил распределенную обработку задач через ARQ (сложные операции) и Celery (массовые задачи)  
**Результат:** Параллельная обработка до 50 задач парсинга, 10 ARQ workers; 24-часовая ретенция джоб  
**Код:** `app/arq_workers/workers.py`, `celeryconfig.py`, `app/modules/adv_creator/backend/tasks.py`

### 6. Real-Time Telegram Bot Интерфейс
**Действие:** Создал интерактивный Telegram-бот с 50+ хендлерами, FSM-состояниями, inline-кнопками  
**Результат:** Полное управление кампаниями через мессенджер; графики позиций, статистика, настройки в реальном времени  
**Код:** `app/client_bot/`, `client_bot_run.py`, `app/client_bot/user_interface/`

### 7. ClickHouse для Аналитики Big Data
**Действие:** Интегрировал ClickHouse для хранения временных рядов статистики (позиции, показы, клики)  
**Результат:** Быстрые аналитические запросы по истории кампаний; агрегация миллионов строк за секунды  
**Код:** `app/core/clickhouse_manager/`, `app/modules/shop_runner/service_manager/services/plan_fact_controller/clickhouse_plan_fact_manager.py`

### 8. Токен-Мониторинг и Auto-Expiration
**Действие:** Разработал систему мониторинга валидности API-токенов WB с уведомлениями за 7/3/1 день до истечения  
**Результат:** Проактивное предотвращение сбоев из-за протухших токенов; автоматические проверки каждые 4 часа  
**Код:** `app/modules/token_monitoring/`, `tests/token_monitoring/` (11 тестов)

### 9. CI/CD Pipeline с GitHub Actions
**Действие:** Настроил автоматическую сборку и деплой Docker-образов в GHCR при push в master  
**Результат:** Zero-downtime deployments; версионирование по SHA; rollback через kubectl  
**Код:** `.github/workflows/deploy.yml`, `dockers/Dockerfile`

### 10. Comprehensive Testing Suite
**Действие:** Написал 513 тестов (unit/integration/e2e) с pytest, pytest-asyncio, factory-boy  
**Результат:** 96 тестовых файлов; покрытие критичных модулей (billing, balance_manager, shop_runner)  
**Код:** `tests/`, `conftest.py` (24 фикстуры), `tests/integration/`, `tests/unit/`

### 11. Observability Stack (Prometheus + Grafana + Fluent Bit)
**Действие:** Развернул полный стек мониторинга: 15+ Prometheus alerting rules, Grafana dashboards, centralized logging  
**Результат:** Обнаружение OOMKilled, CrashLoopBackOff за секунды; логи из всех подов в едином интерфейсе  
**Код:** `k8s/monitoring/` (prometheusrule, dashboards, scripts), `k8s/logging/fluent-bit-configs/`

### 12. Rate Limiting для Wildberries API
**Действие:** Реализовал адаптивный rate limiter с экспоненциальным backoff и автоматическим восстановлением  
**Результат:** Избежание бана от WB API; 0.1s базовая задержка → до 300s при ошибках → авто-уменьшение при успехах  
**Код:** `app/core/redis_manager_v2/mixins/rate_limit.py`, `app/core/mp/wb/api/http_request.py`

### 13. Plan-Fact Контроллер Расходов
**Действие:** Создал систему сравнения планируемых и фактических расходов по кампаниям с алертами  
**Результат:** Автоматическое отключение неэффективных кампаний; контроль перерасхода бюджета  
**Код:** `app/modules/shop_runner/service_manager/services/plan_fact_controller/`

### 14. White/Black List Управление Фразами
**Действие:** Разработал модули автоматического управления белыми/черными списками фраз на основе эффективности  
**Результат:** Автоматическое исключение неконверсионных запросов; экономия 15-30% бюджета  
**Код:** `app/modules/white_list_updater/`, `app/modules/shop_runner/service_manager/services/minus_phrase_manager/`

### 15. Auto-Budget Watchdog
**Действие:** Внедрил сервис автоматического пополнения бюджета кампаний при падении баланса ниже порога  
**Результат:** Предотвращение простоя кампаний; настраиваемый порог (default 500₽) и сумма пополнения (1000₽)  
**Код:** `app/modules/auto_budget_manager/service.py`, настройки `AUTO_BUDGET_MIN_BALANCE`, `AUTO_BUDGET_TOPUP_AMOUNT`

---

## ⚠️ Риски и Сложности Проекта (Проблема → Решение)

### 1. Rate Limiting от Wildberries API
**Проблема:** WB API агрессивно блокирует при превышении лимитов (429 Too Many Requests)  
**Решение:** 
- Экспоненциальный backoff с адаптивной задержкой (0.1s → 300s)
- Глобальный rate limiter на базе Redis с TTL
- Success counter для постепенного снижения задержки (5 успехов → -50ms)
- Настраиваемые параметры через env: `WB_RATE_LIMIT_BASE_DELAY_SEC`, `WB_RATE_LIMIT_MAX_DELAY_SEC`
- **Код:** `app/core/redis_manager_v2/mixins/rate_limit.py`

### 2. Database Connection Pooling в Асинхронной Среде
**Проблема:** При высокой нагрузке (50+ параллельных задач) connection pool PostgreSQL переполнялся  
**Решение:**
- Увеличены лимиты pool: `PG_POOL_SIZE=30`, `PG_MAX_OVERFLOW=50`
- Retry mechanism с экспоненциальным backoff для DB операций
- Использование `NullPool` в тестах для изоляции
- Proper connection lifecycle management в DI-контейнерах
- **Код:** `app/settings/settings_master.py` (PG_POOL_SIZE), `app/core/di/databases/`

### 3. Memory Overcommit в Kubernetes
**Проблема:** OOMKilled поды из-за превышения лимитов памяти; Neo4j и ClickHouse особенно критичны  
**Решение:**
- Мониторинг через Prometheus alerts для memory usage > 80%
- Оптимизация Neo4j buffer settings и ClickHouse query complexity
- Автоматические скрипты для диагностики и очистки: `k8s/monitoring/cleanup-clickhouse.sh`
- Документация по troubleshooting: `k8s/MEMORY_FIX_INDEX.md`, `MEMORY_OVERCOMMIT_ALERT_FIX.md`
- **Код:** `k8s/monitoring/apply-memory-fixes.sh`, Prometheus rules в `k8s/monitoring/`

### 4. Циклические Импорты в Модулях
**Проблема:** При масштабировании проекта (29 модулей) возникли циклические зависимости  
**Решение:**
- Автоматизированная проверка циклических импортов через `pycycle` в pytest
- Использование Dependency Injection (dependency-injector) для инверсии зависимостей
- Protocol-based интерфейсы вместо прямых импортов классов
- CI-интеграция: тесты падают при обнаружении циклов
- **Код:** `tests/test_circular_imports.py`, `app/core/di/app_container.py`

### 5. Токены API Протухают Без Уведомления
**Проблема:** API-токены WB истекают через 90 дней, вызывая сбои кампаний без предупреждения  
**Решение:**
- Система мониторинга с scheduler: проверка токенов каждые 4 часа
- Уведомления пользователей за 7/3/1 день до истечения
- Decorator для автоматической валидации токенов при API-вызовах
- Graceful degradation: магазин переводится в readonly mode при невалидном токене
- **Код:** `app/modules/token_monitoring/` (scheduler.py, services/), `tests/token_monitoring/` (11 тестов)

---

## 📊 Метрики и Объёмы Системы

### Архитектурные Метрики
- **29 бизнес-модулей** в `app/modules/` (от billing до white_list_updater)
- **36 Alembic миграций** — эволюция схемы БД
- **27 SQLAlchemy моделей** — основные сущности (WBCabinet, Campaign, Keyword, Billing, Token, etc.)
- **96 тестовых файлов** с 513 тестами (unit/integration/e2e)
- **24 pytest фикстуры** для переиспользования (DB, Redis, ClickHouse, mocks)

### Масштаб Кодовой Базы
- **~1,500 Python файлов** в `app/` (модули, core, utils)
- **50+ Kubernetes YAML манифестов** (deployments, services, monitoring)
- **15+ Prometheus alerting rules** (OOMKilled, CrashLoop, High Error Rate, etc.)
- **12+ bash/PowerShell скриптов** для DevOps операций

### Конфигурация Воркеров
- **ARQ Workers:**
  - `max_tries = 10` — максимум попыток выполнения задачи
  - `job_timeout = 86400` (24 часа) — таймаут долгих операций
  - `keep_jobs = 86400` — ретенция истории джоб в Redis
  - Функции: `create_complex_advs` (создание кампаний)
- **Celery Workers:**
  - `worker_concurrency = 0` (авто по количеству CPU)
  - `task_retries = 5` — повторные попытки
  - `task_retry_delay = 30s` — задержка между ретраями
  - Prefix: `CELERY_PREFIX` для изоляции задач
- **Shop Update Workers:**
  - `MAX_TASKS = 7` — параллельные таски обновления магазинов
  - `SHOP_UPDATE_TIMEOUT_MINUTES = 60` — таймаут обновления
  - `SHOPS_WORKS_TTL = 300s` (5 минут) — TTL активности магазина

### Периодичность Задач
- **Парсинг ключевых слов:** каждые 1-4 часа (`MAX_HOURS_PERIOD_FOR_PARSING_KEYWORDS`)
- **Обновление статистики кампаний:** каждый час (`UPDATE_FULL_ADV_STAT_PERIOD = 3600s`)
- **Порог stale для автоматизации:** фиксированный 1 час (не зависит от `UPDATE_FULL_ADV_STAT_PERIOD`)
- **Мониторинг токенов:** каждые 4 часа (scheduler в `token_monitoring`)
- **Plan-Fact контроль:** real-time проверка при каждом обновлении бюджета
- **Адаптивный rate limiter:** сброс задержки каждые 5 успешных запросов

### Лимиты и Пороги
- **WB API Rate Limiting:**
  - Базовая задержка: 0.1s (`WB_RATE_LIMIT_BASE_DELAY_SEC`)
  - Максимальная задержка: 300s (5 минут) при ошибках
  - Множитель: 2.0 (экспоненциальный рост)
  - Уменьшение: -50ms каждые 5 успехов
- **Парсинг:**
  - `MAX_PARSING_PARALLEL_JOBS = 10` — одновременные задачи
  - `PARALLER_PARSE_TASKS = 50` — параллельные парсинг-воркеры
  - `PARSING_TIMEOUT = 14400s` (4 часа) — общий таймаут
  - `MAX_PAGE_LIMIT_PARSER_WORKER = 60` — лимит страниц за запрос
- **Auto-Budget:**
  - Минимальный баланс для пополнения: 500₽
  - Сумма пополнения: 1,000₽
  - Блокировка (TTL): 120s на операцию
  - Верификация: 2 попытки с задержкой 2s
- **Биллинг:**
  - Минимальная сумма пополнения: настраиваемая (`MIN_SUM`)
  - Бонус при пополнении: 100% по умолчанию (`BALANCE_TOPUP_BONUS_PERCENT`)
  - Тарифы:
    - Полная автоматизация: ₽5,000/месяц
    - White List режим: ₽1,667/месяц
    - Target Place режим: ₽1,667/месяц
    - Exponenta режим: ₽1,667/месяц

### Объёмы БД (Примерные Оценки из Кода)
- **PostgreSQL Connections:**
  - Pool size: 30 одновременных подключений
  - Max overflow: +50 дополнительных при пиках
- **ClickHouse:**
  - Threads: 10 параллельных (`CH_MAX_THREAD`)
  - Retention: 30 дней полной статистики (`FULL_STAT_THRESHOLD_DATES`)
  - Типы таблиц: keyword_jam_stat, plan_fact_stats, position_history, common_advs_stat
- **Redis:**
  - Database 1: Celery broker
  - Кеши: calculated_keywords, min_bids, rate_limits, shop_status, keyword_vectors
  - min_bids read miss: WARNING `min_bids cache miss` (см. `docks/snapshot_data_updater.md`)
  - TTL кешей: от 300s (shop status) до 86400s (job history)

### Мониторинг и Алертинг
- **Prometheus Metrics:**
  - Pod restarts > 5 за 10 минут → Critical alert
  - Memory usage > 80% → Warning
  - CPU throttling > 50% → Investigation needed
  - Error rate > 5% за 5 минут → Page on-call
- **Grafana Dashboards:**
  - Pod Error Monitoring (5+ панелей)
  - Resource Usage по namespace
  - ClickHouse Query Performance
  - Neo4j CPU diagnostics
- **Logging Volume:**
  - Fluent Bit агрегирует логи со всех подов
  - Error Collector фильтрует критичные события
  - Retention в Loki/ClickHouse: 7-30 дней

---

**Дата создания:** 25 января 2026  
**Версия проекта:** 0.1.0  
**Python:** 3.11  
**Основной автор:** Andrey (vkitaebiz@gmail.com)  
**Репозиторий:** GitHub Container Registry (ghcr.io/revoluxe-ai/adv-bot)

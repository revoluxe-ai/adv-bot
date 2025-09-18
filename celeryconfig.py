from app import settings

redis_master_host = settings.REDIS_MASTER_HOST

# URL брокера сообщений (например, Redis или RabbitMQ)
broker_url = f"redis://{redis_master_host}:6379/1"

# Бэкэнд для хранения результатов
result_backend = f"redis://{redis_master_host}:6379/1"

# Форматы данных и общие настройки
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "UTC"
enable_utc = True

# Включение автоматического повторного подключения брокера при запуске
broker_connection_retry_on_startup = True

# Указание, какие задачи включать
include = ["app.modules.adv_creator.backend.tasks"]

# Количество потоков (0 — автоматически)
worker_concurrency = 0

# Лимиты на число задач в одном процессе (None — без ограничений)
worker_max_tasks_per_child = None
task_reject_on_worker_lost = True
broker_transport_options = {"global_keyprefix": f"{settings.CELERY_PREFIX}"}


task_acks_late = (True,)  # Задачи подтверждаются только после их успешного выполнения
task_retries = (5,)  # Количество повторных попыток выполнения задачи
task_retry_delay = (30,)  # Задержка между повторными попытками

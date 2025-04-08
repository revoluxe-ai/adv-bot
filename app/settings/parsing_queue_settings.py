from typing import Dict, Any
from pydantic import BaseSettings, Field


class ParsingQueueSettings(BaseSettings):
    # Настройки Redis
    redis_queue_key: str = "parser:task:queue"
    redis_task_data_prefix: str = "parser:task:data:"
    redis_text_index_prefix: str = "parser:task:index:text:"
    
    # Настройки воркера
    worker_sleep_interval: float = 1.0  # Интервал между проверками очереди в секундах
    worker_concurrency: int = 5  # Количество параллельных воркеров
    worker_max_retries: int = 3  # Максимальное количество попыток обработки задачи
    worker_retry_delay: float = 5.0  # Задержка между повторными попытками в секундах
    
    # TTL для задач
    task_ttl_seconds: int = 24 * 3600  # 24 часа
    
    # Настройки ARQ
    arq_queue_name: str = "parser_queue"
    arq_default_priority: int = 0
    
    class Config:
        env_prefix = "PARSING_QUEUE_"
        case_sensitive = False


# Создаем экземпляр настроек
settings = ParsingQueueSettings()

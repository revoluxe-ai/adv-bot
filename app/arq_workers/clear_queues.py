import asyncio
import logging

from arq.connections import create_pool
from arq.constants import (
    abort_jobs_ss,
    default_queue_name,
    in_progress_key_prefix,
    job_key_prefix,
    result_key_prefix,
    retry_key_prefix,
)

from app.arq_workers.arq_redis_settings import arq_redis_settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def clear_queues():
    try:
        # Создаем пул подключений к Redis с настройками проекта
        redis = await create_pool(arq_redis_settings)

        # Получаем все ключи, которые нужно очистить
        keys_to_delete = []

        # Очищаем основную очередь
        await redis.delete(default_queue_name)
        logger.info(f"Очищена основная очередь {default_queue_name}")

        # Очищаем ключи задач
        job_keys = await redis.keys(f"{job_key_prefix}*")
        keys_to_delete.extend(job_keys)
        logger.info(f"Найдено {len(job_keys)} ключей задач")

        # Очищаем ключи выполняющихся задач
        in_progress_keys = await redis.keys(f"{in_progress_key_prefix}*")
        keys_to_delete.extend(in_progress_keys)
        logger.info(f"Найдено {len(in_progress_keys)} ключей выполняющихся задач")

        # Очищаем ключи результатов
        result_keys = await redis.keys(f"{result_key_prefix}*")
        keys_to_delete.extend(result_keys)
        logger.info(f"Найдено {len(result_keys)} ключей результатов")

        # Очищаем ключи повторных попыток
        retry_keys = await redis.keys(f"{retry_key_prefix}*")
        keys_to_delete.extend(retry_keys)
        logger.info(f"Найдено {len(retry_keys)} ключей повторных попыток")

        # Очищаем ключи отмененных задач
        await redis.delete(abort_jobs_ss)
        logger.info(f"Очищен ключ отмененных задач {abort_jobs_ss}")

        # Удаляем все найденные ключи
        if keys_to_delete:
            await redis.delete(*keys_to_delete)
            logger.info(f"Удалено {len(keys_to_delete)} ключей")

        logger.info("Все очереди ARQ успешно очищены")

    except Exception as e:
        logger.error(f"Ошибка при очистке очередей: {e}")
        raise
    finally:
        # Закрываем соединение
        if "redis" in locals():
            await redis.close()


if __name__ == "__main__":
    asyncio.run(clear_queues())

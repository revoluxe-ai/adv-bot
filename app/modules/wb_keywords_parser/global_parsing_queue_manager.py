import hashlib
import json
import logging
import time
from typing import Optional, Set

from redis.asyncio.client import Pipeline

from .parsing_task import ParsingTask
from ...core.redis_manager.base_redis_manager import BaseRedis

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class GlobalParsingQueueManager(BaseRedis):
    def __init__(self) -> None:
        self.queue_key = "parser:task:queue"
        self.task_data_prefix = "parser:task:data:"
        self.text_index_prefix = "parser:task:index:text:"

    @staticmethod
    def _get_task_id(text: str) -> str:
        """Генерирует уникальный ID задачи на основе текста"""
        return hashlib.sha1(text.encode()).hexdigest()[:12]

    async def add_or_update_task(self, text: str, nmids: Set[int]) -> str:
        """
        Добавляет новую задачу или обновляет существующую

        Args:
            text: Текст для поиска
            nmids: Множество nmids для поиска

        Returns:
            task_id: ID задачи
        """
        task_id = self._get_task_id(text)
        task_key = f"{self.task_data_prefix}{task_id}"

        logger.debug(f"Adding/updating task: text={text}, task_id={task_id}")

        # Проверяем существование задачи вне pipeline
        exists = await self.client.exists(task_key)
        logger.debug(f"Task exists: {exists}")

        if exists:
            old_data = await self.client.get(task_key)
            if old_data:
                old_task = json.loads(old_data)
                old_nmids = set(old_task.get("nmids", []))
                nmids = old_nmids.union(nmids)
                logger.debug(
                    f"Updating existing task. Old nmids: {old_nmids}, New nmids: {nmids}"
                )

        # Формируем task_data после возможного объединения
        task_data = {
            "text": text,
            "nmids": list(nmids),
        }

        # Индексный ключ — безопасно хешируем текст
        text_hash = hashlib.md5(text.encode()).hexdigest()
        index_key = f"{self.text_index_prefix}{text_hash}"

        # Проверяем, есть ли задача в очереди
        in_queue = await self.client.zscore(self.queue_key, task_id)
        logger.debug(f"Task in queue: {in_queue is not None}")
        pipe: Pipeline
        # Записываем данные и индексируем атомарно
        async with self.client.pipeline() as pipe:
            pipe.set(task_key, json.dumps(task_data))
            if not exists or in_queue is None:
                # Добавляем в очередь, если задача новая или её нет в очереди
                score = int(time.time() * 1000)  # Преобразуем в целое число
                logger.debug(f"Adding task to queue with score: {score}")
                pipe.zadd(self.queue_key, {task_id: score})
            pipe.sadd(index_key, task_id)
            await pipe.execute()

        # Проверяем, что задача добавлена в очередь
        queue_size = await self.client.zcard(self.queue_key)
        logger.debug(f"Current queue size: {queue_size}")

        return task_id

    async def get_next_task(self) -> Optional[ParsingTask]:
        """
        Получает следующую задачу из очереди по приоритету

        Returns:
            task: Объект ParsingTask или None, если очередь пуста
        """
        # Проверяем размер очереди
        queue_size = await self.client.zcard(self.queue_key)
        logger.debug(f"Current queue size: {queue_size}")

        # Сначала получаем ID задачи
        task_ids = await self.client.zrange(self.queue_key, 0, 0)
        if not task_ids:
            logger.debug("Queue is empty.")
            return None

        task_id = task_ids[0].decode()
        task_key = f"{self.task_data_prefix}{task_id}"

        logger.debug(f"Fetching task with task_id: {task_id}")

        # Получаем данные задачи
        task_data = await self.client.get(task_key)
        if not task_data:
            logger.warning(f"No task data found for task_id: {task_id}")
            # Удаляем несуществующую задачу из очереди
            await self.client.zrem(self.queue_key, task_id)
            return None

        # Удаляем задачу из очереди и её данные
        async with self.client.pipeline() as pipe:
            pipe.zrem(self.queue_key, task_id)
            pipe.delete(task_key)
            await pipe.execute()

        data = json.loads(task_data)
        logger.debug(f"Task data: {data}")

        return ParsingTask(
            keyword=data["text"],
            nmids=set(data["nmids"]),
        )

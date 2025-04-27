import hashlib
import json
from datetime import datetime
from typing import Optional, Set, List, Awaitable, Union

from app.core.redis_manager.base_redis_manager import BaseRedis
from .parsing_task import ParsingTask


class TaskQueueManager(BaseRedis):
    """
    Менеджер очереди задач парсинга.
    Обеспечивает атомарные операции добавления/обновления задач и получения следующей задачи.
    """

    def __init__(self):
        super().__init__()
        self.queue_key = "parser:task:queue"
        self.task_data_prefix = "parser:task:data:"
        self.text_index_prefix = "parser:task:index:text:"

    @property
    def redis(self):
        """Геттер для доступа к клиенту Redis"""
        return self.client

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
        timestamp = datetime.now().timestamp()

        # Атомарная операция для добавления/обновления задачи
        async with self.client.pipeline() as pipe:
            exists = await pipe.exists(f"{self.task_data_prefix}{task_id}")
            if exists:
                # Обновляем существующую задачу
                old_data = await self.client.get(f"{self.task_data_prefix}{task_id}")
                if old_data:
                    old_task = json.loads(old_data)
                    # Объединяем nmids
                    old_nmids = set(old_task["nmids"])
                    new_nmids = old_nmids.union(nmids)
                    task_data = {"text": text, "nmids": list(new_nmids)}
                else:
                    task_data = {"text": text, "nmids": list(nmids)}
            else:
                task_data = {"text": text, "nmids": list(nmids)}

            # Сохраняем данные задачи
            await pipe.set(f"{self.task_data_prefix}{task_id}", json.dumps(task_data))
            # Добавляем в очередь с приоритетом по времени добавления
            await pipe.zadd(self.queue_key, {task_id: timestamp})
            # Индексируем по тексту
            result: Union[Awaitable[int], int] = pipe.sadd(
                f"{self.text_index_prefix}{text}", task_id
            )
            if isinstance(result, Awaitable):
                await result
            await pipe.execute()

        return task_id

    async def get_next_task(self) -> Optional[ParsingTask]:
        """
        Получает следующую задачу из очереди по приоритету

        Returns:
            task: Объект ParsingTask или None, если очередь пуста
        """
        # Получаем ID задачи с наивысшим приоритетом (самая ранняя задача)
        task_id = await self.client.zrange(self.queue_key, 0, 0)
        if not task_id:
            return None

        task_id = task_id[0].decode()
        # Получаем данные задачи
        task_data = await self.client.get(f"{self.task_data_prefix}{task_id}")
        if not task_data:
            return None

        data = json.loads(task_data)
        # Создаем объект ParsingTask
        return ParsingTask(
            keyword=data["text"],
            nmids=set(data["nmids"]),  # Преобразуем список в множество
        )

    async def remove_task(self, task_id: str) -> bool:
        """
        Удаляет задачу из очереди

        Args:
            task_id: ID задачи для удаления

        Returns:
            bool: True если задача была удалена, иначе False
        """
        # Получаем данные задачи для удаления индексов
        task_data = await self.client.get(f"{self.task_data_prefix}{task_id}")
        if not task_data:
            return False

        task = json.loads(task_data)
        text = task["text"]

        async with self.client.pipeline() as pipe:
            await pipe.zrem(self.queue_key, task_id)
            await pipe.delete(f"{self.task_data_prefix}{task_id}")
            result: Union[Awaitable[int], int] = pipe.srem(
                f"{self.text_index_prefix}{text}", task_id
            )
            if isinstance(result, Awaitable):
                await result
            await pipe.execute()

        return True

    async def get_queue_size(self) -> int:
        """
        Возвращает количество задач в очереди
        """
        return await self.client.zcard(self.queue_key)

    async def get_all_tasks(self) -> List[ParsingTask]:
        """
        Возвращает все задачи из очереди
        """
        task_ids = await self.client.zrange(self.queue_key, 0, -1)
        tasks = []
        for task_id in task_ids:
            task_id = task_id.decode()
            task_data = await self.client.get(f"{self.task_data_prefix}{task_id}")
            if task_data:
                data = json.loads(task_data)
                tasks.append(
                    ParsingTask(
                        keyword=data["text"],
                        nmids=set(data["nmids"]),  # Преобразуем список в множество
                    )
                )
        return tasks

    async def get_task_by_text(self, text: str) -> Optional[ParsingTask]:
        """
        Ищет задачу по тексту

        Args:
            text: Текст для поиска

        Returns:
            task: Объект ParsingTask или None, если не найдена
        """
        task_id = self._get_task_id(text)
        task_data = await self.client.get(f"{self.task_data_prefix}{task_id}")
        if task_data:
            data = json.loads(task_data)
            return ParsingTask(
                keyword=data["text"],
                nmids=set(data["nmids"]),  # Преобразуем список в множество
            )
        return None

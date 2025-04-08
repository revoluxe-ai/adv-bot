from typing import Optional, Set, Dict
import json
import hashlib
from datetime import datetime
from app.utils.redis_manager import RedisManager

class TaskQueueManager:
    def __init__(self):
        self.redis = RedisManager()
        self.queue_key = "parser:task:queue"  # ZSET для хранения очереди
        self.task_data_prefix = "parser:task:data:"  # HASH для хранения данных задачи
        self.text_index_prefix = "parser:task:index:text:"  # SET для индексации по тексту
        
    def _get_task_id(self, text: str) -> str:
        """Генерирует уникальный ID задачи на основе текста"""
        return hashlib.sha1(text.encode()).hexdigest()[:12]
        
    async def add_or_update_task(self, text: str, nmids: Set[int], priority: int = 0) -> str:
        """
        Добавляет новую задачу или обновляет существующую
        
        Args:
            text: Текст для поиска
            nmids: Множество nmids для поиска
            priority: Приоритет задачи (чем меньше, тем выше приоритет)
            
        Returns:
            task_id: ID задачи
        """
        task_id = self._get_task_id(text)
        task_data = {
            "text": text,
            "nmids": list(nmids),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Атомарная операция для добавления/обновления задачи
        async with self.redis.pipeline() as pipe:
            # Проверяем существование задачи
            exists = await pipe.exists(f"{self.task_data_prefix}{task_id}")
            if exists:
                # Обновляем существующую задачу
                old_data = await self.redis.get(f"{self.task_data_prefix}{task_id}")
                if old_data:
                    old_task = json.loads(old_data)
                    # Объединяем nmids
                    old_nmids = set(old_task["nmids"])
                    new_nmids = old_nmids.union(nmids)
                    task_data["nmids"] = list(new_nmids)
                    task_data["created_at"] = old_task["created_at"]
            
            # Сохраняем данные задачи
            pipe.set(f"{self.task_data_prefix}{task_id}", json.dumps(task_data))
            # Добавляем в очередь с приоритетом
            pipe.zadd(self.queue_key, {task_id: priority})
            # Индексируем по тексту
            pipe.sadd(f"{self.text_index_prefix}{text}", task_id)
            await pipe.execute()
            
        return task_id
        
    async def get_next_task(self) -> Optional[Dict]:
        """
        Получает следующую задачу из очереди
        
        Returns:
            task_data: Данные задачи или None, если очередь пуста
        """
        # Получаем ID задачи с наивысшим приоритетом
        task_id = await self.redis.zrange(self.queue_key, 0, 0)
        if not task_id:
            return None
            
        task_id = task_id[0].decode()
        # Получаем данные задачи
        task_data = await self.redis.get(f"{self.task_data_prefix}{task_id}")
        if not task_data:
            return None
            
        return json.loads(task_data)
        
    async def remove_task(self, task_id: str) -> None:
        """
        Удаляет задачу из очереди
        
        Args:
            task_id: ID задачи для удаления
        """
        # Получаем данные задачи для удаления индексов
        task_data = await self.redis.get(f"{self.task_data_prefix}{task_id}")
        if task_data:
            task = json.loads(task_data)
            text = task["text"]
            
            async with self.redis.pipeline() as pipe:
                # Удаляем из очереди
                pipe.zrem(self.queue_key, task_id)
                # Удаляем данные задачи
                pipe.delete(f"{self.task_data_prefix}{task_id}")
                # Удаляем индекс по тексту
                pipe.srem(f"{self.text_index_prefix}{text}", task_id)
                await pipe.execute()
                
    async def get_task_by_text(self, text: str) -> Optional[Dict]:
        """
        Ищет задачу по тексту
        
        Args:
            text: Текст для поиска
            
        Returns:
            task_data: Данные задачи или None, если не найдена
        """
        task_id = self._get_task_id(text)
        task_data = await self.redis.get(f"{self.task_data_prefix}{task_id}")
        if task_data:
            return json.loads(task_data)
        return None 
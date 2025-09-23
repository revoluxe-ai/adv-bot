"""
Батчевый процессор для эффективной обработки больших объемов данных.

Этот модуль предоставляет функциональность для группировки задач в батчи
и их параллельной обработки с учетом ограничений API.
"""

import asyncio
import logging
from asyncio import Queue, QueueEmpty
from dataclasses import dataclass
from typing import Any, Callable, Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")  # Тип элемента в батче
R = TypeVar("R")  # Тип результата обработки


@dataclass
class BatchResult(Generic[R]):
    """Результат обработки батча."""

    success: bool
    results: List[R]
    errors: List[Exception]


class BatchProcessor(Generic[T, R]):
    """
    Процессор для батчевой обработки элементов.

    Собирает элементы в батчи фиксированного размера и обрабатывает их
    с помощью предоставленной функции-обработчика.
    """

    def __init__(
        self,
        batch_size: int,
        process_func: Callable[[List[T]], Any],
        max_queue_size: int = 1000,
        flush_timeout: Optional[float] = None,
    ):
        """
        Инициализация батч-процессора.

        Args:
            batch_size: Максимальный размер батча
            process_func: Асинхронная функция для обработки батча
            max_queue_size: Максимальный размер очереди
            flush_timeout: Таймаут для принудительной отправки неполного батча
        """
        self.batch_size = batch_size
        self.process_func = process_func
        self.flush_timeout = flush_timeout

        self._queue: Queue[Optional[T]] = Queue(maxsize=max_queue_size)
        self._current_batch: List[T] = []
        self._processing_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._flush_event = asyncio.Event()

    async def add(self, item: T) -> None:
        """
        Добавляет элемент в очередь обработки.

        Args:
            item: Элемент для обработки
        """
        await self._queue.put(item)

    async def flush(self) -> None:
        """Принудительно обрабатывает текущий батч."""
        self._flush_event.set()

    async def start(self) -> None:
        """Запускает обработку батчей."""
        if self._processing_task is not None:
            raise RuntimeError("BatchProcessor already started")

        self._processing_task = asyncio.create_task(self._process_loop())
        logger.info(f"BatchProcessor started with batch_size={self.batch_size}")

    async def stop(self) -> None:
        """Останавливает обработку и обрабатывает оставшиеся элементы."""
        logger.info("Stopping BatchProcessor...")

        # Сигнализируем об остановке
        self._stop_event.set()

        # Добавляем None в очередь для пробуждения обработчика
        await self._queue.put(None)

        # Ждем завершения обработки
        if self._processing_task:
            await self._processing_task

        # Обрабатываем оставшийся батч
        if self._current_batch:
            await self._process_batch(self._current_batch)

        logger.info("BatchProcessor stopped")

    async def _process_loop(self) -> None:
        """Основной цикл обработки батчей."""
        try:
            while not self._stop_event.is_set():
                # Создаем задачи для ожидания
                tasks = [
                    asyncio.create_task(self._collect_batch()),
                    asyncio.create_task(self._flush_event.wait()),
                ]

                if self.flush_timeout:
                    tasks.append(asyncio.create_task(asyncio.sleep(self.flush_timeout)))

                # Ждем первое событие
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )

                # Отменяем незавершенные задачи
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Обрабатываем батч если он готов
                if self._current_batch:
                    await self._process_batch(self._current_batch)
                    self._current_batch = []

                # Сбрасываем flush event
                self._flush_event.clear()

        except Exception as e:
            logger.error(f"Error in batch processing loop: {e}", exc_info=True)
            raise

    async def _collect_batch(self) -> None:
        """Собирает элементы в батч."""
        while len(self._current_batch) < self.batch_size:
            try:
                # Используем get_nowait для первых элементов в батче
                if self._current_batch:
                    item = self._queue.get_nowait()
                else:
                    # Для первого элемента ждем
                    item = await self._queue.get()

                if item is None:  # Сигнал остановки
                    return

                self._current_batch.append(item)

            except QueueEmpty:
                # Если очередь пуста и есть элементы в батче, выходим
                if self._current_batch:
                    return
                # Иначе ждем новые элементы
                item = await self._queue.get()
                if item is None:
                    return
                self._current_batch.append(item)

    async def _process_batch(self, batch: List[T]) -> BatchResult[R]:
        """
        Обрабатывает батч элементов.

        Args:
            batch: Список элементов для обработки

        Returns:
            Результат обработки батча
        """
        logger.debug(f"Processing batch of {len(batch)} items")

        try:
            results = await self.process_func(batch)
            return BatchResult(
                success=True,
                results=results if isinstance(results, list) else [results],
                errors=[],
            )
        except Exception as e:
            logger.error(f"Error processing batch: {e}", exc_info=True)
            return BatchResult(success=False, results=[], errors=[e])


class AsyncBatchCollector(Generic[T]):
    """
    Коллектор для асинхронного сбора элементов из нескольких источников.

    Используется для параллельного сбора данных из разных корутин
    и передачи их в батч-процессор.
    """

    def __init__(self, batch_processor: BatchProcessor[T, Any]):
        """
        Args:
            batch_processor: Батч-процессор для обработки собранных элементов
        """
        self.batch_processor = batch_processor
        self._tasks: List[asyncio.Task] = []

    async def collect_from_coroutine(
        self, coro: Any, extractor: Optional[Callable[[Any], List[T]]] = None
    ) -> None:
        """
        Собирает элементы из корутины.

        Args:
            coro: Корутина, возвращающая элементы
            extractor: Функция для извлечения элементов из результата корутины
        """
        try:
            result = await coro

            # Извлекаем элементы
            if extractor:
                items = extractor(result)
            elif isinstance(result, list):
                items = result
            else:
                items = [result]

            # Добавляем в батч-процессор
            for item in items:
                if item is not None:
                    await self.batch_processor.add(item)

        except Exception as e:
            logger.error(f"Error collecting from coroutine: {e}", exc_info=True)

    async def collect_all(self, coroutines: List[Any]) -> None:
        """
        Параллельно собирает данные из всех корутин.

        Args:
            coroutines: Список корутин для сбора данных
        """
        tasks = [
            asyncio.create_task(self.collect_from_coroutine(coro))
            for coro in coroutines
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

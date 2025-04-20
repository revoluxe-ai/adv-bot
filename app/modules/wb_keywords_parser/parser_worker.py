import asyncio
import logging
from asyncio import Task

from python_modules.logger import setup_logging
from app.modules.wb_keywords_parser.global_parsing_queue_manager import GlobalParsingQueueManager
from app.modules.wb_keywords_parser.wb_parser import parser
from app.modules.wb_keywords_parser.parsing_task import ParsingTask
setup_logging()

logger = logging.getLogger(__name__)


class ParserWorker:
    def __init__(self, max_parallel_tasks: int = 3):
        self.queue_manager = GlobalParsingQueueManager()
        self._max_parallel_tasks = max_parallel_tasks
        self._stop_event = asyncio.Event()
        self._tasks: set[Task] = set()

    async def run(self):
        try:
            workers = [self._run() for _ in range(self._max_parallel_tasks)]
            self._tasks = {asyncio.create_task(w) for w in workers}
            await asyncio.gather(*self._tasks)
        finally:
            for task in self._tasks:
                task.cancel()

    async def stop(self):
        """Корректно останавливает воркер"""
        self._stop_event.set()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run(self) -> None:
        """Основной цикл воркера"""
        logger.info("Starting parser worker")
        while not self._stop_event.is_set():
            try:
                # Получаем следующую задачу из очереди
                task: ParsingTask | None = await self.queue_manager.get_next_task()
                if task:
                    logger.debug(f'Processing task: {task}')
                    try:
                        await self._process_task(task)
                        logger.debug(f'Finished task: {task}')
                    except Exception as e:
                        logger.error(f"Error processing task {task}: {e}", exc_info=True)
                else:
                    # Если задач нет, ждем немного
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in worker main loop: {e}")
                await asyncio.sleep(30)  # Ждем перед повторной попыткой

    @staticmethod
    async def _process_task(task: ParsingTask):
        """Обработка отдельной задачи"""
        try:
            # Выполняем парсинг через новый метод
            await parser.add_wb_positions(
                text=task.keyword,
                need_nmids=task.nmids,
                delay=0.1,
                page_limit=1)
        except Exception as e:
            logger.error(f"Error processing task {task}: {e}", exc_info=True)

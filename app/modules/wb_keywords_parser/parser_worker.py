import asyncio
import logging

from app.modules.wb_keywords_parser.global_parsing_queue_manager import GlobalParsingQueueManager
from app.modules.wb_keywords_parser.wb_parser import parser
from app.modules.wb_keywords_parser.parsing_task import ParsingTask


logger = logging.getLogger(__name__)


class ParserWorker:
    def __init__(self, max_parallel_tasks: int = 3):
        self.queue_manager = GlobalParsingQueueManager()
        self._max_parallel_tasks = max_parallel_tasks

    async def run(self):
        await asyncio.gather(*[self._run() for _ in range(self._max_parallel_tasks)])  # Запускаем несколько воркеров

    async def _run(self) -> None:
        """Основной цикл воркера"""
        logger.info("Starting parser worker")
        while True:
            try:
                # Получаем следующую задачу из очереди
                task: ParsingTask | None = await self.queue_manager.get_next_task()
                if task:
                    text = task.keyword
                    need_nmids = task.nmids
                    await parser.add_wb_positions(text,
                                                  need_nmids,
                                                  0.1)
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
                page_limit=60)
        except Exception as e:
            logger.error(f"Error processing task {task}: {e}", exc_info=True)

# mypy: ignore-errors

import asyncio
import logging

from dotenv import load_dotenv

from app.core.di import AppContainer, DIManager
from app.modules.wb_keywords_parser.parser_worker import ParserWorker
from app.settings import settings

load_dotenv()
# Настройка логирования
logger = logging.getLogger(__name__)

max_parallel_parsing_tasks = settings.PARALLER_PARSE_TASKS


async def main():
    """Основная функция запуска парсера"""
    try:
        # Загружаем переменные окружения
        async with await DIManager.create(AppContainer):
            # Создаем и запускаем воркер
            worker = ParserWorker(max_parallel_tasks=max_parallel_parsing_tasks)
            await worker.run()

    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise e


if __name__ == "__main__":
    asyncio.run(main())

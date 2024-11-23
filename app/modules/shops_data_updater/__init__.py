from .main import async_process_run
import asyncio
import logging

logger = logging.getLogger(__name__)

def run():
    try:
        asyncio.run(async_process_run())
    except Exception as e:
        logger.error(f'Произошла ошибка: {e}')
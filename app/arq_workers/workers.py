"""ARQ worker settings and lifecycle hooks for background tasks."""

from typing import Any

import dotenv
from aiohttp import ClientSession

dotenv.load_dotenv()
import logging

from app.arq_workers.arq_redis_settings import arq_redis_settings
from app.client_bot.bot import aclose_telegram_http_session, get_bot
from app.modules.adv_creator.backend.tasks import (
    create_auto_only,
    create_complex_advs,
    create_search_only,
)
from python_modules.logger import setup_logging

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Инициализация бота при запуске воркера."""
    setup_logging()
    logger.debug("Инициализация воркера. ctx перед запуском: %s", ctx)
    ctx["bot"] = get_bot()
    client_session = ClientSession()
    ctx["client_session"] = client_session

    logger.debug("Бот успешно создан и сохранен в ctx")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Закрытие сессии бота при завершении работы воркера."""
    if "bot" in ctx:
        logger.debug("Закрытие сессии бота")
        await aclose_telegram_http_session()
        logger.debug("Сессия бота закрыта")
    client_session: ClientSession = ctx["client_session"]
    await client_session.close()


class WorkerSettings:
    """Настройки Arq."""

    functions = [
        create_auto_only,
        create_complex_advs,
        create_search_only,
    ]
    redis_settings = arq_redis_settings
    on_startup = startup
    on_shutdown = shutdown
    keep_jobs = 86400  # Храним задачи в Redis 24 часа
    max_tries = 1  # Без ретраев: ошибки обрабатываются в самих задачах
    job_timeout = 86400  # максимальное время на выполнение задачи

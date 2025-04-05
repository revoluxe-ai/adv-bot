import dotenv
from app.arq_workers.arq_redis_settings import arq_redis_settings
from app.modules.wb_keywords_parser.parser import create_arq_parsing_task, _create_arq_parsing_task
from app.settings import settings

dotenv.load_dotenv()
import logging
from python_modules.logger import setup_logging
from app.client_bot.bot import get_bot
from app.modules.adv_creator.backend.tasks import create_complex_advs

# Настраиваем логирование
setup_logging()
logger = logging.getLogger(__name__)


async def startup(ctx):
    """Инициализация бота при запуске воркера."""
    logger.debug('Инициализация воркера. ctx перед запуском: %s', ctx)
    ctx["bot"] = get_bot()
    logger.debug('Бот успешно создан и сохранен в ctx')

async def shutdown(ctx):
    """Закрытие сессии бота при завершении работы воркера."""
    if "bot" in ctx:
        logger.debug('Закрытие сессии бота')
        await ctx["bot"].session.close()
        logger.debug('Сессия бота закрыта')

class WorkerSettings:
    """Настройки Arq."""
    functions = [
        create_complex_advs,
    ]
    redis_settings = arq_redis_settings
    on_startup = startup
    on_shutdown = shutdown
    keep_jobs = 86400  # Храним задачи в Redis 24 часа
    max_tries = 10 # Максимальное число попыток
    job_timeout = 86400   #максимальное время на выполнение задачи


class ParserWorker:
    functions = [_create_arq_parsing_task]
    redis_settings = arq_redis_settings
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = settings.MAX_PARSING_PARALLEL_JOBS
    keep_jobs = 60*60*4 # Храним задачи в Redis 1 час
    max_tries = 1 # Максимальное число попыток
    job_timeout = 120 #максимальное время на выполнение задачи
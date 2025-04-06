__all__ = ['cv', 'settings']

from .settings_master import settings

cv = settings.cv

WEBHOOK_URL = settings.WEBHOOK_URL

polling_mode = settings.polling_mode

COUNT_THREAD_SQL_KW_STAT_LOAD = settings.COUNT_THREAD_SQL_KW_STAT_LOAD

MAX_THREAD_PARSER = settings.MAX_THREAD_PARSER

MAX_MINUS_KW_THREAD = settings.MAX_MINUS_KW_THREAD

WEBHOOK_PATH = settings.WEBHOOK_PATH

TELEGRAM_WEB_PORT = settings.TELEGRAM_WEB_PORT

CELERY_PREFIX = settings.CELERY_PREFIX


BIDDER_STEP = settings.BIDDER_STEP

REDIS_MASTER_HOST = settings.REDIS_MASTER_HOST


REDIS_REPLICA_HOST = settings.REDIS_REPLICA_HOST


MIN_SUM = settings.MIN_SUM


WEBHOOK_SECRET = settings.WEBHOOK_SECRET
__all__ = ['cv']

from .settings_master import settings

cv = settings.cv

WEBHOOK_URL = settings.WEBHOOK_URL

polling_mode = settings.polling_mode

COUNT_THREAD_SQL_KW_STAT_LOAD = settings.COUNT_THREAD_SQL_KW_STAT_LOAD

MAX_THREAD_PARSER = settings.MAX_THREAD_PARSER

MAX_MINUS_KW_THREAD = settings.MAX_MINUS_KW_THREAD

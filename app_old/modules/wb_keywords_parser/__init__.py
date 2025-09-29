"""
Модуль для парсинга ключевых слов на Wildberries
"""

# Экспортируем основные классы для облегчения импорта
from .parsing_found_redis_manager import ParsingFoundRedisManager
from .parsing_queue_manager import ParsingQueueManager
from .parsing_task import ParsingTask
from .wb_parser.parser import parser

__all__ = ["ParsingQueueManager", "ParsingFoundRedisManager", "ParsingTask", "parser"]

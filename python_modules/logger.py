import json
import logging
import os
import datetime
from logging.handlers import SysLogHandler


class EnhancedJSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'logger': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
            'path': record.pathname,
            'line': record.lineno
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logging():
    """Настройка логирования"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Только один обработчик - для stdout
    handler = logging.StreamHandler()
    handler.setFormatter(EnhancedJSONFormatter())

    # Удаляем все существующие обработчики
    logger.handlers.clear()

    # Добавляем только один обработчик
    logger.addHandler(handler)

    logging.info("Logging is set up!")
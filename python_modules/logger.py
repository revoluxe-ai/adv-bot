import json
import logging
import os
import datetime
import platform
from logging.handlers import SysLogHandler

class EnhancedJSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'logger': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
            'path': record.pathname,
            'line': record.lineno,
            'service': os.getenv('SERVICE_NAME', 'wb_adv_updater')
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


class SimpleStringFormatter(logging.Formatter):
    def format(self, record):
        return f"{record.levelname} - {record.name} - {record.getMessage()} ({record.pathname}:{record.lineno})"


def setup_logging():
    """Настройка логирования"""
    try:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # Удаляем все существующие обработчики
        logger.handlers.clear()

        # Проверяем операционную систему
        is_windows = platform.system() == "Windows"

        # Добавляем обработчик для вывода в stdout с нужным форматом
        stream_handler = logging.StreamHandler()
        if is_windows:
            stream_handler.setFormatter(SimpleStringFormatter())
        else:
            stream_handler.setFormatter(SimpleStringFormatter())
        logger.addHandler(stream_handler)

        # Добавляем обработчик для отправки логов в Syslog (только для Linux и MacOS)
        if not is_windows:
            syslog_address = os.getenv('SYSLOG_ADDRESS', '/dev/log')
            syslog_handler = SysLogHandler(address=syslog_address)
            syslog_handler.setFormatter(SimpleStringFormatter())
            logger.addHandler(syslog_handler)

        logging.info("Логирование настроено успешно!")
    except Exception as e:
        logging.error(f"Ошибка при настройке логирования: {str(e)}")

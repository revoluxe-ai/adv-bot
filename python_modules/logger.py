import json
import logging
import os
import datetime
from logging.handlers import SysLogHandler, RotatingFileHandler

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
        return json.dumps(log_data,  ensure_ascii=False)


def setup_logging():
    """Настройка логирования"""
    try:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # Удаляем все существующие обработчики
        logger.handlers.clear()

        # Добавляем обработчик для вывода в stdout
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(EnhancedJSONFormatter())
        logger.addHandler(stream_handler)

        # Чтение параметров из окружения для файла логов и его размера
        log_file = os.getenv('LOG_FILE_PATH', 'app_logs.json')
        max_log_size = int(os.getenv('MAX_LOG_SIZE', 1024 * 1024 * 10))  # 10MB
        backup_count = int(os.getenv('BACKUP_COUNT', 3))

        # Добавляем обработчик для записи в файл с ротацией
        file_handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count)
        file_handler.setFormatter(EnhancedJSONFormatter())
        logger.addHandler(file_handler)

        # Добавляем обработчик для отправки логов в Syslog
        syslog_address = os.getenv('SYSLOG_ADDRESS', '/dev/log')
        syslog_handler = SysLogHandler(address=syslog_address)
        syslog_handler.setFormatter(EnhancedJSONFormatter())
        logger.addHandler(syslog_handler)

        logging.info("Логирование настроено успешно!")
    except Exception as e:
        logging.error(f"Ошибка при настройке логирования: {str(e)}")

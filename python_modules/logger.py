import json
import logging
import logging.handlers
import textwrap
import platform
import os
import datetime

system_name = platform.system()
logging_setup_done = False

class EnhancedJSONFormatter(logging.Formatter):
    """Форматтер для JSON логов с сохранением цветного вывода в консоль"""
    def __init__(self, color_output=False, **kwargs):
        super().__init__()
        self.color_output = color_output
        self.extra_fields = kwargs
        self.colors = {
            'DEBUG': '\x1b[34m',
            'INFO': '\x1b[37m',
            'WARNING': '\x1b[38;21m',
            'ERROR': '\x1b[31m',
            'CRITICAL': '\x1b[31m',
            'RESET': '\x1b[0m'
        }

    def format(self, record):
        # Базовая структура лога
        log_data = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'logger': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
            'path': record.pathname,
            'line': record.lineno,
            'service': os.getenv('SERVICE_NAME', 'updater')
        }

        # Добавляем информацию об исключении
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Для консоли возвращаем цветной вывод
        if self.color_output:
            color = self.colors.get(record.levelname, '')
            reset = self.colors['RESET']
            formatted = (f"{color}{log_data['logger']} - {log_data['timestamp']} - "
                       f"{log_data['path']}:{log_data['line']} - {record.levelname} - "
                       f"{log_data['message']}{reset}")
            return textwrap.fill(formatted, width=100)

        return json.dumps(log_data)

class CustomJournalHandler(logging.handlers.SysLogHandler):
    """Обработчик для системного журнала с поддержкой JSON"""
    priority_map = {
        logging.DEBUG: 7,
        logging.INFO: 6,
        logging.WARNING: 4,
        logging.ERROR: 3,
        logging.CRITICAL: 2
    }

    def emit(self, record):
        try:
            priority = self.priority_map.get(record.levelno, 6)
            record.priority = priority
            super().emit(record)
        except Exception:
            self.handleError(record)

def setup_logging():
    """Сохраняем оригинальную сигнатуру, но добавляем новую функциональность"""
    import warnings
    warnings.filterwarnings("error", category=RuntimeWarning)
    global logging_setup_done

    if logging_setup_done:
        return

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Консольный вывод с цветами
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(EnhancedJSONFormatter(color_output=True))
    logger.addHandler(console_handler)

    # JSON файловый вывод
    file_handler = logging.handlers.RotatingFileHandler(
        'app.log',
        maxBytes=10_000_000,
        backupCount=5
    )
    file_handler.setFormatter(EnhancedJSONFormatter())
    logger.addHandler(file_handler)

    # TCP handler для отправки в системы сбора логов
    if os.getenv('LOG_HOST') and os.getenv('LOG_PORT'):
        tcp_handler = logging.handlers.SocketHandler(
            os.getenv('LOG_HOST'),
            int(os.getenv('LOG_PORT'))
        )
        tcp_handler.setFormatter(EnhancedJSONFormatter())
        logger.addHandler(tcp_handler)

    if system_name == 'Linux':
        try:
            from systemd.journal import JournalHandler
            journal_handler = JournalHandler(SYSLOG_IDENTIFIER='updater')
            journal_handler.setFormatter(EnhancedJSONFormatter())
            logger.addHandler(journal_handler)
        except ImportError:
            pass

    logging_setup_done = True
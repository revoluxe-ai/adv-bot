import json
import logging
import logging.handlers
import os
from typing import Optional
import datetime


class EnhancedJSONFormatter(logging.Formatter):
    """Форматтер, который преобразует логи в структурированный JSON"""

    def __init__(self, **kwargs):
        super().__init__()
        self.extra_fields = kwargs

    def format(self, record):
        log_data = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'logger': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
            'path': record.pathname,
            'line_number': record.lineno,
            'function': record.funcName,
            'process': record.process,
            'thread': record.thread,
            'service': os.getenv('SERVICE_NAME', 'wbgram'),
            'environment': os.getenv('ENVIRONMENT', 'development')
        }

        # Добавляем extra поля, если они есть
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Добавляем информацию об исключении, если оно есть
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class LoggerFactory:
    """Фабрика для создания логгеров с разными обработчиками"""

    @staticmethod
    def setup_logger(
            name: str,
            log_level: str = 'INFO',
            console_output: bool = True,
            file_output: Optional[str] = None,
            tcp_handler: Optional[dict] = None,
            udp_handler: Optional[dict] = None
    ) -> logging.Logger:
        """
        Настройка логгера с различными обработчиками

        Args:
            name: Имя логгера
            log_level: Уровень логирования
            console_output: Включить вывод в консоль
            file_output: Путь к файлу для файлового логирования
            tcp_handler: Словарь с настройками TCP хендлера (host, port)
            udp_handler: Словарь с настройками UDP хендлера (host, port)
        """
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, log_level.upper()))

        # Создаем форматтер
        json_formatter = EnhancedJSONFormatter()

        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(json_formatter)
            logger.addHandler(console_handler)

        if file_output:
            # Ротируемый файловый хендлер
            file_handler = logging.handlers.RotatingFileHandler(
                file_output,
                maxBytes=10_000_000,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(json_formatter)
            logger.addHandler(file_handler)

        if tcp_handler:
            socket_handler = logging.handlers.SocketHandler(
                tcp_handler['host'],
                tcp_handler['port']
            )
            socket_handler.setFormatter(json_formatter)
            logger.addHandler(socket_handler)

        if udp_handler:
            datagram_handler = logging.handlers.DatagramHandler(
                udp_handler['host'],
                udp_handler['port']
            )
            datagram_handler.setFormatter(json_formatter)
            logger.addHandler(datagram_handler)

        return logger

setup_logging = LoggerFactory.setup_logger
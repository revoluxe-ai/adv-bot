

class TooManyRequestsInParserError(Exception):
    """Базовое исключение для ошибок rate-limiting при парсинге WB."""
    pass


class WBConnectionRateLimitError(TooManyRequestsInParserError):
    """
    SSL/Connection ошибка от WB, которая обычно означает мягкий rate-limiting.
    
    WB разрывает SSL соединение вместо явного возврата HTTP 429.
    Это более мягкая форма ограничения, обрабатывается с меньшими паузами.
    """
    pass

"""Исключения для WB API модуля."""


class WBApiError(Exception):
    """Базовое исключение для WB API."""

    pass


class WBApiHttpError(WBApiError):
    """HTTP ошибка WB API."""

    def __init__(
            self, message: str, status_code: int | None = None, response_text: str | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class WBApiForbiddenError(WBApiHttpError):
    """403 Forbidden ошибка (обычно проблемы с токеном)."""

    def __init__(self, message: str = "Доступ запрещен", response_text: str | None = None):
        super().__init__(message, 403, response_text)


class WBApiTooManyRequestsError(WBApiHttpError):
    """429 Too Many Requests ошибка (rate limit)."""

    def __init__(
            self, message: str = "Превышен лимит запросов", response_text: str | None = None
    ):
        super().__init__(message, 429, response_text)


class WBApiValidationError(WBApiError):
    """Ошибка валидации данных."""

    pass


class WBApiAdapterError(WBApiError):
    """Ошибка адаптера."""

    pass


class WBApiVersionError(WBApiError):
    """Ошибка версионирования API."""

    pass

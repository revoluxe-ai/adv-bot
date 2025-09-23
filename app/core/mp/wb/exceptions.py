"""Исключения для WB API модуля."""

from app.modules.common_slaves.wildberries.models import WBUserCabinet


class WBApiError(Exception):
    """Базовое исключение для WB API."""

    pass


class ApiForbiddenError(Exception):
    def __init__(self, text, wb_user_cabinet: WBUserCabinet | None = None):
        self.text = text
        self.wb_user_cabinet = wb_user_cabinet
        m = "API доступ запрещен"
        super().__init__(f"{m} text: {self.text}")


class WBApiHttpError(WBApiError):
    """HTTP ошибка WB API."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class WBApiForbiddenError(WBApiHttpError):
    """403 Forbidden ошибка (обычно проблемы с токеном)."""

    def __init__(
        self, message: str = "Доступ запрещен", response_text: str | None = None
    ):
        super().__init__(message, 403, response_text)


class TooManyRequestsError(WBApiHttpError):
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


class ArgumentsError(WBApiError):
    """Ошибка аргументов при вызове API."""

    def __init__(self, message: str = "Ошибка аргументов", *args, **kwargs):
        super().__init__(message, *args)


class ApiUnexpectedError(WBApiError):
    """Неожиданная ошибка API (непредусмотренный статус или ответ)."""

    def __init__(self, message: str = "Неожиданный ответ API", *args, **kwargs):
        super().__init__(message, *args)


class ApiTimeoutError(WBApiError):
    """Ошибка таймаута при обращении к API."""

    def __init__(self, message: str = "Таймаут при обращении к API", *args, **kwargs):
        super().__init__(message, *args)

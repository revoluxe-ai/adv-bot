"""
Заглушка для старого модуля wb_api.exceptions.

Этот файл создан для совместимости со старым кодом.
Рекомендуется мигрировать на новый модуль app.core.mp.wb.exceptions.
"""

# Импортируем исключения из нового модуля
from app.core.mp.wb.exceptions import (
    WBApiError,
    WBApiHttpError,
    WBApiForbiddenError as ApiForbiddenError,  # Алиас для совместимости
    WBApiTooManyRequestsError,
    WBApiValidationError,
    WBApiAdapterError,
    WBApiVersionError,
)


class MaxAttemptsError(Exception):
    pass


class UnknownApiRequestError(Exception):
    pass


class ApiErrorWithCode(Exception):
    def __init__(self, code: str | int, message: str, rejection: str) -> None:
        self.code = code
        self.message = message
        self.rejection = rejection
        m = "Типовая ошибка Api Wildberries"
        super().__init__(
            f"{m} code: {self.code}, message: {self.message}, rejection: {self.rejection}"
        )


class TokenExpiredError(Exception):
    def __init__(self, text):
        self.text = text
        m = "Срок действия токена истек"
        super().__init__(f"{m} text: {self.text}")


class TokensFromDifferentShopsError(BaseException):
    def __init__(self):
        m = "Токены принадлежат разным магазинам"
        super().__init__(f"{m}")


# class ApiForbiddenError(Exception):
#     def __init__(self, text, wb_user_cabinet: WBUserCabinet | None = None):
#         self.text = text
#         self.wb_user_cabinet = wb_user_cabinet
#         m = "API доступ запрещен"
#         super().__init__(f"{m} text: {self.text}")


class TooManyRequests(Exception):
    pass


class NotValidDataError(Exception):
    pass


class CardNotFoundInWB(Exception):
    pass


class NotItemsInAdvSetting(Exception):
    pass


class NotMatchWBApiError(Exception):
    pass


class MinAdvBidWBApiError(Exception):
    def __init__(self, new_min_bid: int):
        self.new_min_bid = new_min_bid
        m = "Минимальная ставка изменилась"
        super().__init__(f"{m} new_min_bid: {self.new_min_bid}")

    new_min_bid: int


class BadRequestError(WBApiHttpError):
    """Ошибка плохого запроса (для совместимости)."""

    def __init__(self, message="Bad request", response_text=None):
        super().__init__(message, 400, response_text)


# Для обратной совместимости
__all__ = [
    "WBApiError",
    "WBApiHttpError",
    "ApiForbiddenError",  # Старое имя
    "WBApiTooManyRequestsError",
    "WBApiValidationError",
    "WBApiAdapterError",
    "WBApiVersionError",
    "MinAdvBidWBApiError",  # Для совместимости
    "BadRequestError",  # Для совместимости
]

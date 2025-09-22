from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    pass  # Remove the import of 'new' module since it's not available


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
        super().__init__(f"{m} code: {self.code}, message: {self.message}, rejection: {self.rejection}")


class NotValidTokenError(Exception):
    pass


class TokenExpiredError(Exception):
    def __init__(self, text: Any) -> None:
        self.text = text
        m = "Срок действия токена истек"
        super().__init__(f"{m} text: {self.text}")


class TokensFromDifferentShopsError(BaseException):
    def __init__(self) -> None:
        m = "Токены принадлежат разным магазинам"
        super().__init__(f"{m}")


class ApiForbiddenError(Exception):
    def __init__(self, text: Any, wb_user_cabinet: Any = None) -> None:
        self.text = text
        self.wb_user_cabinet = wb_user_cabinet
        m = "API доступ запрещен"
        super().__init__(f"{m} text: {self.text}")


class TooManyRequests(Exception):
    pass


class BadRequestError(Exception):
    error_message: str


class NotValidDataError(Exception):
    pass


class CardNotFoundInWB(Exception):
    pass


class NotItemsInAdvSetting(Exception):
    pass


class NotMatchWBApiError(Exception):
    pass


class MinAdvBidWBApiError(Exception):
    new_min_bid: int

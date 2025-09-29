from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class UnknownApiRequestError(BaseException):
    pass


class ApiErrorWithCode(BaseException):
    def __init__(self, code, message, rejection):
        self.code = code
        self.message = message
        self.rejection = rejection
        m = "Типовая ошибка Api Wildberries"
        super().__init__(
            f"{m} code: {self.code}, message: {self.message}, rejection: {self.rejection}"
        )


class NotValidTokenError(BaseException):
    pass


class TokenExpiredError(Exception):
    def __init__(self, text):
        self.text = text
        m = "Срок действия токена истек"
        super().__init__(f"{m} text: {self.text}")


class TokensFromDifferentShopsError(BaseException):
    def __init__(self):
        m = "Токены принадлежат разным магазинам"
        super().__init__(f"{m}")


class TooManyRequests(Exception):
    pass


class BadRequestError(Exception):
    pass


class NotValidDataError(Exception):
    pass


class CardNotFoundInWB(Exception):
    pass


class NotItemsInAdvSetting(Exception):
    pass


class WBCabinetNotFoundError(Exception):
    def __init__(self, identifier: int | str):
        self.identifier = identifier
        self.is_shop_id = isinstance(identifier, str)

        id_type = "shop_id" if self.is_shop_id else "cabinet_id"
        message = f"Кабинет не найден (по {id_type}: {self.identifier})"
        super().__init__(message)

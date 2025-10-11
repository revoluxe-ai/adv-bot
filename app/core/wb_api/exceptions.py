from app.modules.common_slaves.wildberries.models import WBUserCabinet


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
    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__(f"Token expired: {self.text}")


class TokensFromDifferentShopsError(BaseException):
    def __init__(self, m: str) -> None:
        super().__init__(f"{m}")


class ApiForbiddenError(Exception):
    def __init__(self, text: str, wb_user_cabinet: WBUserCabinet | None = None):
        self.text = text
        self.wb_user_cabinet = wb_user_cabinet
        m = "API доступ запрещён"
        super().__init__(f"{m} text: {self.text}")


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
    def __init__(self, new_min_bid: int) -> None:
        self.new_min_bid = new_min_bid
        m = "Минимальная ставка изменена"
        super().__init__(f"{m} new_min_bid: {self.new_min_bid}")

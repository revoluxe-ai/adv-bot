class TokenExpiredError(Exception):
    def __init__(self, text: str) -> None:
        self.text = text
        m = "Срок действия токена истек"
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

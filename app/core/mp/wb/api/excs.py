from typing import Any

from app.modules.common_slaves.wildberries.models import WBUserCabinet


class WBApiError(Exception):
    pass


class StandardError(WBApiError):
    def __init__(self,
                 title: str,
                 detail: str,
                 status: int,
                 ) -> None:
        self.title = title
        self.message = detail
        self.status = status
        super().__init__(self.message)

    def __str__(self) -> str:
        return f'{self.title}: {self.message}'

    def __repr__(self) -> str:
        return f'{self.title}: {self.message}'


class UnexpectedRequestError(WBApiError):
    pass


class BadRequestError(WBApiError):
    pass


class ApiForbiddenError(Exception):
    def __init__(
        self, text: str, wb_user_cabinet: WBUserCabinet | None = None
    ):
        self.text = text
        self.wb_user_cabinet = wb_user_cabinet
        m = "API доступ запрещён"
        super().__init__(f"{m} text: {self.text}")


class TooManyRequests(WBApiError):
    def __init__(self, next_pause: int | None, *args: Any):
        self.next_pause = next_pause
        super().__init__(*args)


class MaxAttemptsError(WBApiError):
    pass


class UnknownApiRequestError(WBApiError):
    pass


class UnknownWBApiStatus(WBApiError):
    pass


class HttpTimeOutError(WBApiError):
    pass
from typing import Any

from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum
from app.modules.common_slaves.wildberries.models import WBUserCabinet


class WBApiError(Exception):
    pass


class StandardError(WBApiError):
    def __init__(
        self,
        title: str,
        detail: str,
        status: int,
    ) -> None:
        self.title = title
        self.message = detail
        self.status = status
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.title}: {self.message}"

    def __repr__(self) -> str:
        return f"{self.title}: {self.message}"


class UnexpectedRequestError(WBApiError):
    pass


class BadRequestError(WBApiError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ApiForbiddenError(WBApiError):
    def __init__(
        self,
        text: str,
        wb_user_cabinet: WBUserCabinet | None = None,
        not_valid_token_hash: str | None = None,
        section: SectionsEnum | None = None,
    ):
        self.__not_valid_token_hash = not_valid_token_hash
        self.__section = section
        self.text = text
        self.wb_user_cabinet = wb_user_cabinet
        m = "API доступ запрещён"
        super().__init__(f"{m} text: {self.text}")

    @property
    def not_valid_token_hash(self) -> str | None:
        return self.__not_valid_token_hash

    @property
    def section(self) -> SectionsEnum | None:
        return self.__section


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


class PoolTimeoutError(HttpTimeOutError):
    """Исчерпан пул HTTP-соединений (httpcore.PoolTimeout) до получения response."""

    def __init__(
        self,
        message: str = "Превышено время ожидания слота пула HTTP-соединений",
        *,
        original_exc: BaseException | None = None,
    ) -> None:
        self.original_exc = original_exc
        self.exc_type = (
            type(original_exc).__name__ if original_exc is not None else "PoolTimeout"
        )
        super().__init__(message)

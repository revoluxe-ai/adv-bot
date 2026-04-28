from __future__ import annotations


class UnisenderGoError(Exception):
    """Unisender Go Web API returned an error or the response was invalid."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        api_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.api_code = api_code
        self.response_body = response_body

"""
Заглушка для старого модуля legacy-wb_api_clients.exceptions.

Этот файл создан для совместимости со старым кодом.
Рекомендуется мигрировать на новый модуль app.core.mp.wb.exceptions.
"""



class TokenExpiredError(Exception):
    def __init__(self, text):
        self.text = text
        m = "Срок действия токена истек"
        super().__init__(f"{m} text: {self.text}")


class TooManyRequests(Exception):
    pass


class NotValidDataError(Exception):
    pass


class CardNotFoundInWB(Exception):
    pass


class BadRequestError(Exception):
    """Ошибка плохого запроса (для совместимости)."""

    def __init__(self, message="Bad request", response_text=None):
        super().__init__(message, 400, response_text)


class NotValidTokenError(Exception):
    """Исключение для недействительного/tокена невалидного токена (совместимость)."""

    pass


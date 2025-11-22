from typing import Any


def parse_too_many_requests_error(raw_response: Any) -> int | None:
    """
    Возвращает рекомендуемую паузу (в секундах) после ошибки 429 Too Many Requests.

    Ищет заголовок 'x-ratelimit-retry'. Если его нет — возвращает дефолт.
    """
    default_retry = 5

    try:
        # Открываем доступ к headers
        headers = getattr(raw_response, "headers", None)
        if not headers:
            return default_retry

        # Ищем ключ без учёта регистра
        for key, value in headers.items():
            if key.lower() == "x-ratelimit-retry":
                try:
                    return int(value)
                except ValueError:
                    return default_retry

        return default_retry

    except Exception:
        return default_retry
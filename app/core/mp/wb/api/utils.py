import time
from typing import Any

_MAX_429_PAUSE_SEC = 120
_UNIX_RESET_THRESHOLD = 1_000_000_000


def parse_too_many_requests_error(raw_response: Any) -> int | None:
    """
    Возвращает рекомендуемую паузу (в секундах) после ошибки 429 Too Many Requests.

    Учитывает ``x-ratelimit-retry`` и ``x-ratelimit-reset``:
    если ``reset`` больше порога — считаем его Unix-временем окончания окна;
    иначе — секундами ожидания/длительностью окна (как в ответах s2s-api-auth-adv).
    Итог: ``max(retry, вычисленный_reset)``, с ограничением сверху.
    """
    default_retry = 5

    try:
        headers = getattr(raw_response, "headers", None)
        if not headers:
            return default_retry

        h = {str(k).lower(): str(v) for k, v in headers.items()}
        retry_s = default_retry
        if "x-ratelimit-retry" in h:
            try:
                retry_s = max(int(h["x-ratelimit-retry"]), 1)
            except ValueError:
                pass

        reset_raw = h.get("x-ratelimit-reset")
        if reset_raw is None:
            return min(retry_s, _MAX_429_PAUSE_SEC)

        try:
            reset_val = int(reset_raw)
        except ValueError:
            return min(retry_s, _MAX_429_PAUSE_SEC)

        now = int(time.time())
        if reset_val > _UNIX_RESET_THRESHOLD:
            pause = max(retry_s, reset_val - now, 1)
        else:
            pause = max(retry_s, reset_val, 1)

        return min(pause, _MAX_429_PAUSE_SEC)

    except Exception:
        return default_retry

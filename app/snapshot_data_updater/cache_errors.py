"""Исключения кеша snapshot/Redis без тяжёлых зависимостей пакета.

Импортируйте отсюда из shop-runner и ``tasks_manager``, чтобы не загружать
``snapshot_data_updater.__init__`` (collector, assembler, …).
"""


class RequiredDataMissError(RuntimeError):
    """Нет обязательных данных в кеше — нужен прогрев snapshot updater."""

    def __init__(
        self,
        message: str,
        *,
        shop_id: str = "",
        adv_id: int = 0,
        resource: str = "",
    ) -> None:
        super().__init__(message)
        self.shop_id = shop_id
        self.adv_id = adv_id
        self.resource = resource


class KeywordsCacheMissError(RequiredDataMissError):
    """Нет keywords в Redis (``calculated_keywords:{adv_id}``)."""

    def __init__(self, message: str, *, shop_id: str = "", adv_id: int = 0) -> None:
        super().__init__(
            message,
            shop_id=shop_id,
            adv_id=adv_id,
            resource="calculated_keywords",
        )


class CacheStaleError(RuntimeError):
    """Данные в кеше старше допустимого возраста или нет метки времени."""

    def __init__(
        self,
        message: str,
        *,
        context: str,
        age_sec: float | None = None,
        max_age_sec: float | None = None,
    ) -> None:
        super().__init__(message)
        self.context = context
        self.age_sec = age_sec
        self.max_age_sec = max_age_sec

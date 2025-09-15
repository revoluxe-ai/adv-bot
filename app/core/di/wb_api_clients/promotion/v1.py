from dependency_injector import containers, providers

from app.core.mp.wb.generated.promotion.v1.client.client import (
    Client as PromotionV1Client,
)


class PromotionV1Container(containers.DeclarativeContainer):
    """Контейнер для клиентов Promotion API v1."""

    settings = providers.Dependency()

    client = providers.Singleton(
        PromotionV1Client,
        base_url=settings.provided.infrastructure.wb.api_url,
        timeout=settings.provided.infrastructure.wb.timeout,
    )

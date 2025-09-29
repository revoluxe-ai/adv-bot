"
class WBApiClientsContainer(containers.DeclarativeContainer):
    """Главный контейнер клиентов WB API."""

    wiring_config = containers.WiringConfiguration(packages=["app"])
    settings = providers.Dependency()

    # Promotion API v1
    promotion_v1 = providers.Container(
        PromotionV1Container,
        settings=settings,
    )
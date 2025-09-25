from dependency_injector import containers, providers

from app.core.di.api_section_container import ApiSectionContainer


class RootContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Пример: контейнеры для разных разделов
    promotion = providers.Container(
        ApiSectionContainer,
        config=config.promotion,
    )

    # orders = providers.Container(ApiSectionContainer, config=config.orders)
    # ... добавлять другие разделы по аналогии

    # Методы для инициализации/закрытия всех сессий
    def init_resources(self):
        self.promotion().init_resources()
        # self.orders().init_resources()
        # ...

    async def shutdown_resources(self):
        await self.promotion().shutdown_resources()
        # await self.orders().shutdown_resources()
        # ...

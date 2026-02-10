from dependency_injector import containers, providers

from app.core.mp.wb.api.adapter.content_products_client import ContentProductCardsAdapter
from app.core.mp.wb.api.auth_client_handler import AuthClientHandler
from app.core.mp.wb.api.domain_managers import ProductsManager
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager


class ProductsContainer(containers.DeclarativeContainer):
    _content_base_url = providers.Object("https://content-api.wildberries.ru")
    _auth_client_handler = providers.Dependency(instance_of=AuthClientHandler)
    _request_limit_manager = providers.Singleton(RequestLimitManager)

    _product_cards_adapter = providers.Singleton(
        ContentProductCardsAdapter,
        base_url=_content_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    products_domain_manager = providers.Singleton(
        ProductsManager,
        product_cards_adapter=_product_cards_adapter,
    )

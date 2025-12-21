from dependency_injector import containers, providers

from app.core.mp.wb.api.adapter.analitika_i_dannye_client import (
    poiskovye_zaprosy_po_vashim_tovaram,
)
from app.core.mp.wb.api.adapter.analitika_i_dannye_client import voronka_prodazh
from app.core.mp.wb.api.adapter.analitika_i_dannye_client import AnalyticAndDataClient
from app.core.mp.wb.api.auth_client_handler import AuthClientHandler
from app.core.mp.wb.api.domain_managers import AnalyticsManager
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager


class AnalyticAndDataContainer(containers.DeclarativeContainer):
    _base_url = providers.Object("https://seller-analytics-api.wildberries.ru")
    _auth_client_handler = providers.Dependency(instance_of=AuthClientHandler)
    _request_limit_manager = providers.Singleton(RequestLimitManager)

    _search_keywords_adapter = providers.Singleton(
        poiskovye_zaprosy_po_vashim_tovaram.Adapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _sales_funnel_adapter = providers.Singleton(
        voronka_prodazh.Adapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _analytics_and_data_client = providers.Singleton(
        AnalyticAndDataClient,
        search_keywords_adapter=_search_keywords_adapter,
        sales_funnel_adapter=_sales_funnel_adapter,
    )
    analytics_domain_manager = providers.Singleton(
        AnalyticsManager,
        wb_api_client=_analytics_and_data_client,
    )

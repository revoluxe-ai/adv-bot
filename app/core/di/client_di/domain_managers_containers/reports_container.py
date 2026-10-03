"""DI-контейнер ReportsManager (statistics-api)."""

from dependency_injector import containers, providers

from app.core.mp.wb.api.adapter.reports_client import SupplierOrdersSalesAdapter
from app.core.mp.wb.api.auth_client_handler import AuthClientHandler
from app.core.mp.wb.api.domain_managers.reports import ReportsManager
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager


class ReportsContainer(containers.DeclarativeContainer):
    """Контейнер адаптера/менеджера supplier orders/sales."""

    _statistics_base_url = providers.Object("https://statistics-api.wildberries.ru")
    _auth_client_handler = providers.Dependency(instance_of=AuthClientHandler)
    _request_limit_manager = providers.Singleton(RequestLimitManager)

    _supplier_orders_sales_adapter = providers.Singleton(
        SupplierOrdersSalesAdapter,
        base_url=_statistics_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    reports_domain_manager = providers.Singleton(
        ReportsManager,
        supplier_orders_sales_adapter=_supplier_orders_sales_adapter,
    )

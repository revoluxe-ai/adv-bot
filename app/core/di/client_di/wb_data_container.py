from dependency_injector import containers, providers
from dependency_injector.providers import Provider, Container

from app.core.di.client_di.domain_managers_containers.analitycs_container import (
    AnalyticAndDataContainer,
)
from app.core.mp.wb.api.auth_client_handler import AuthClientHandler

from app.core.mp.wb.api.domain_managers import AnalyticsManager
from app.core.mp.wb.api.managers import WBDataManager


class WBDataContainer(containers.DeclarativeContainer):
    _auth_client_handler = providers.Dependency(instance_of=AuthClientHandler)
    _analytics_and_data_container: Container[AnalyticAndDataContainer] = providers.Container(
        AnalyticAndDataContainer,
        _auth_client_handler=_auth_client_handler,
    )

    _analytics_domain_manager: Provider[AnalyticsManager] = _analytics_and_data_container.analytics_domain_manager # pyright: ignore


    wb_data_manager = providers.Singleton(
        WBDataManager,
        analytics_manager=_analytics_domain_manager,
    )

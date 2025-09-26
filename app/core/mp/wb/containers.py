from __future__ import annotations

import httpx
from dependency_injector import containers, providers

from app.core.mp.wb.adapter_factory import WbApiAdapterFactory
from app.core.mp.wb.client_factory import ClientFactory
from app.core.mp.wb.rate_limit.storage import RateLimitStorage
from app.core.mp.wb.tokens.token_manager import TokenManager
from app.core.mp.wb.tokens.token_manager_factory import TokenManagerFactory
from app.core.mp.wb.base_wb_api import BaseWBApi
from app.modules.shop_runner.service_manager.services.update_cpm.wb_api_managers import WBApiDataGetter, WBApiCpmUpdater
from app.modules.shop_runner.service_manager.services.update_cpm.update_cpm_manager import UpdateCPMManager


class WBApiContainer(containers.DeclarativeContainer):
    """DI container for Wildberries API integration components."""

    config = providers.Configuration()

    # Http clients (singletons per section)
    promotion_http_client = providers.Singleton(
        httpx.AsyncClient,
        base_url=config.promotion.base_url,
        # Other default settings for httpx.AsyncClient if needed
        # For example, timeouts, verify_ssl, follow_redirects, headers
        timeout=30.0,
        verify=True,
        follow_redirects=True,
        headers={'User-Agent': 'MyAwesomeApp/1.0'},
    )

    # Grouping all http clients by section name for ClientFactory
    http_clients = providers.Dict(
        promotion=promotion_http_client,
    )

    # RateLimitStorage (singleton)
    rate_limit_storage = providers.Singleton(RateLimitStorage)

    # TokenManagerFactory (singleton)
    token_manager_factory = providers.Singleton(
        TokenManagerFactory
    )

    # TokenManager (factory/scoped per shop_id - managed by TokenManagerFactory)
    token_manager = providers.Factory(
        TokenManager,
        shop_id=providers.Dependency(str),
        # TokenManagerFactory handles caching, so this is just a provider for creation
    )

    # ClientFactory (singleton)
    client_factory = providers.Singleton(
        ClientFactory,
        token_manager_factory=token_manager_factory,
        async_http_clients=http_clients,
    )

    # WbApiAdapterFactory (singleton with cache)
    wb_api_adapter_factory = providers.Singleton(
        WbApiAdapterFactory,
        client_factory=client_factory,
    )

    # BaseWBApi (factory/scoped per shop_id)
    base_wb_api = providers.Factory(
        BaseWBApi,
        shop_id=providers.Dependency(str),
        adapter_factory=wb_api_adapter_factory,
        rate_limit_storage=rate_limit_storage,
    )

    # WBApiDataGetter (factory/scoped per shop_id)
    wb_api_data_getter = providers.Factory(
        WBApiDataGetter,
        shop_id=providers.Dependency(str),
        adapter_factory=wb_api_adapter_factory, # BaseWBApi will resolve this, so we provide it here
        rate_limit_storage=rate_limit_storage,
    )

    # WBApiCpmUpdater (factory/scoped per shop_id)
    wb_api_cpm_updater = providers.Factory(
        WBApiCpmUpdater,
        shop_id=providers.Dependency(str),
        adapter_factory=wb_api_adapter_factory, # BaseWBApi will resolve this, so we provide it here
        rate_limit_storage=rate_limit_storage,
    )

    # UpdateCPMManager (factory/scoped per shop_id)
    update_cpm_manager = providers.Factory(
        UpdateCPMManager,
        shop_id=providers.Dependency(str),
        wb_data_getter=wb_api_data_getter,
        wb_cpm_updater=wb_api_cpm_updater,
    )

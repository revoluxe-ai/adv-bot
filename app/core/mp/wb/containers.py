# app/core/mp/wb/containers.py
from __future__ import annotations

import httpx
from dependency_injector import containers, providers

from .adapters.promotion_v1_adapter import PromotionV1Adapter
from .base_wb_api_manager import BaseWBApiManager


class WBApiContainer(containers.DeclarativeContainer):
    """Dependency injection container for WB API components."""

    config = providers.Configuration()

    # Singleton http clients per section (to be wired in application)
    http_clients = providers.Dict()

    rate_limit_storage = providers.Singleton(object)  # replace with RateLimitStorage

    token_manager_factory = providers.Singleton(object)  # replace with TokenManagerFactory

    adapter_factory = providers.Singleton(object)  # replace with WbApiAdapterFactory


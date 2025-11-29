from dependency_injector import containers, providers

from app.core.mp.wb.api.adapter.promotion_client import (
    MinusPhrasesAdapter,
    NormqueryStatsAdapter,
    PromotionClient,
)
from app.core.mp.wb.api.auth_client_handler import AuthClientHandler
from app.core.mp.wb.api.domain_managers import PromotionManager
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager


class PromotionContainer(containers.DeclarativeContainer):
    _base_url = providers.Object("https://advert-api.wildberries.ru")
    _auth_client_handler = providers.Dependency(instance_of=AuthClientHandler)
    _request_limit_manager = providers.Singleton(RequestLimitManager)

    _minus_phrases_adapter = providers.Singleton(
        MinusPhrasesAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _normquery_stats_adapter = providers.Singleton(
        NormqueryStatsAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _promotion_client = providers.Singleton(
        PromotionClient,
        minus_phrases_adapter=_minus_phrases_adapter,
        normquery_stats_adapter=_normquery_stats_adapter,
    )

    promotion_domain_manager = providers.Singleton(
        PromotionManager,
        promotion_client=_promotion_client,
    )

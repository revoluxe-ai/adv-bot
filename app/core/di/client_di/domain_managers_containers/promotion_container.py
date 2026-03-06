from dependency_injector import containers, providers

from app.core.mp.wb.api.adapter.promotion_client import (
    CabinetAdvertsListAdapter,
    CampaignsManagementAdapter,
    CampaignsInfoV2Adapter,
    FullstatsAdapter,
    MinusPhrasesAdapter,
    NormqueryStatsAdapter,
    NormqueryBidsAdapter,
    MinBidsAdapter,
    PromotionClient,
    FinanceAdapter,
    CommonBidsAdapter,
    ProductCardsAdapter,
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

    _normquery_bids_adapter = providers.Singleton(
        NormqueryBidsAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _min_bids_adapter = providers.Singleton(
        MinBidsAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _finance_adapter = providers.Singleton(
        FinanceAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _campaigns_management_adapter = providers.Singleton(
        CampaignsManagementAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _campaigns_info_v2_adapter = providers.Singleton(
        CampaignsInfoV2Adapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _cabinet_adverts_list_adapter = providers.Singleton(
        CabinetAdvertsListAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _common_bids_adapter = providers.Singleton(
        CommonBidsAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _product_cards_adapter = providers.Singleton(
        ProductCardsAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _fullstats_adapter = providers.Singleton(
        FullstatsAdapter,
        base_url=_base_url,
        auth_client_handler=_auth_client_handler,
        request_limit_manager=_request_limit_manager,
    )

    _promotion_client = providers.Singleton(
        PromotionClient,
        minus_phrases_adapter=_minus_phrases_adapter,
        normquery_stats_adapter=_normquery_stats_adapter,
        normquery_bids_adapter=_normquery_bids_adapter,
        min_bids_adapter=_min_bids_adapter,
        finance_adapter=_finance_adapter,
        campaigns_management_adapter=_campaigns_management_adapter,
        campaigns_info_v2_adapter=_campaigns_info_v2_adapter,
        cabinet_adverts_list_adapter=_cabinet_adverts_list_adapter,
        common_bids_adapter=_common_bids_adapter,
        product_cards_adapter=_product_cards_adapter,
        fullstats_adapter=_fullstats_adapter,
    )

    promotion_domain_manager = providers.Singleton(
        PromotionManager,
        promotion_client=_promotion_client,
    )

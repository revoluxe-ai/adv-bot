from dependency_injector import containers, providers
from .click_house_manager import ClickHouseKeywordStampManager
from app.core.mp.wb.api.wb_manager_hub import WBManagerHub
from .keyword_stamp_manager import KeywordStampManager


class KeywordStampManagerContainer(containers.DeclarativeContainer):

    _wb_api_manager_hub = providers.Dependency(instance_of=WBManagerHub)

    _click_house_manager = providers.Singleton(ClickHouseKeywordStampManager)

    keyword_stamp_manager = providers.Singleton(KeywordStampManager,
                                                wb_api_manager_hub=_wb_api_manager_hub,
                                                click_house_manager=_click_house_manager
                                                )

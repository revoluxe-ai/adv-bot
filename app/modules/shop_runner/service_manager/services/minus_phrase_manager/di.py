from dependency_injector import containers, providers
from app.core.mp.wb.api.wb_manager_hub import WBManagerHub
from .minus_phrase_manager import MinusPhraseManager


class MinusPhraseManagerContainer(containers.DeclarativeContainer):

    _wb_api_manager_hub = providers.Dependency(instance_of=WBManagerHub)

    minus_phrase_manager = providers.Singleton(
        MinusPhraseManager,
        wb_api_manager_hub=_wb_api_manager_hub,
    )

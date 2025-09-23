"""Фабрика для создания WB API клиентов через DI."""

from typing import Type, TypeVar

from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess

from .base_wb_api import BaseWBApi
from .containers import WBApiContainer
from .mixins import CPMUpdateMixin

T = TypeVar("T", bound=BaseWBApi)


def create_wb_api_client(client_class: Type[T], access: WBCabinetAccess) -> T:
    """
    Создать WB API клиент указанного типа через DI контейнер.

    Args:
        client_class: Класс клиента (например, WBApi)
        access: Объект доступа к WB API

    Returns:
        Экземпляр клиента с инжектированными зависимостями

    Example:
        wb_api = create_wb_api_client(WBApi, access)
    """
    container = WBApiContainer()

    # Создаем клиент через фабрику DI контейнера
    base_api = container.wb_api_factory(wb_access=access)

    # Если нужен специализированный клиент, создаем его
    if client_class != BaseWBApi:
        # Создаем экземпляр специализированного класса
        specialized_client = client_class.__new__(client_class)

        # Копируем все атрибуты из базового API
        for attr_name in dir(base_api):
            if not attr_name.startswith("_") or attr_name in [
                "_adapters_cache",
                "_domain_versions",
            ]:
                setattr(specialized_client, attr_name, getattr(base_api, attr_name))

        return specialized_client

    return base_api


def create_cpm_client(access: WBCabinetAccess) -> "CPMUpdateMixin":
    """
    Создать клиент для работы с CPM ставками.

    Args:
        access: Объект доступа к WB API

    Returns:
        Клиент с CPMUpdateMixin функциональностью
    """

    # Создаем класс с миксином динамически
    class CPMClient(CPMUpdateMixin, BaseWBApi):
        pass

    return create_wb_api_client(CPMClient, access)

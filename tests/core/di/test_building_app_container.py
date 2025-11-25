import pytest
from dependency_injector import providers

from app.core.di.app_container import AppContainer


@pytest.mark.asyncio
async def test_building_app_container(app_container: AppContainer):
    app_container.check_dependencies()



def test_all_services_can_be_built(app_container: AppContainer):
    # Предполагаем, что внешние штуки уже замоканы во fixture `container`
    failed = []

    for provider in app_container.traverse(types=[providers.Factory, providers.Singleton]):
        name = getattr(provider, "__repr__", lambda: str(provider))()

        try:
            # Важно: некоторые singletons могут иметь побочки (логгер, метрики и т.д.).
            # Если не хочешь их трогать — можно добавить фильтр по имени/модулю.
            provider()
        except Exception as exc:  # noqa: BLE001
            failed.append((name, exc))

    assert not failed, f"Некоторые провайдеры не строятся: {failed}"
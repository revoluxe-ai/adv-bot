"""Под-контейнер DI для модуля predict_ctr_update_manager.

Отделяет тонкие менеджеры (PredictCTRRedisManager / PredictCTRUpdateManager) от корневого контейнера.
Корневой контейнер (AppContainer) пробрасывает общий redis_client_wrapper как зависимость.

Преимущества:
- Локализация зависимостей модуля
- Возможность расширить модуль (добавить новые менеджеры) без изменения root контейнера
- Тесты могут подменять PredictCTRManagerContainer целиком или отдельные провайдеры
"""

from __future__ import annotations

from dependency_injector import containers, providers

from app.core.redis_manager_v2.redis_client import RedisClient
from .redis_manager import PredictCTRRedisManager


class PredictCTRManagerContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.modules.shop_runner.service_manager.services.predict_ctr_update_manager.predict_ctr_update_manager",  # функции/корутины модуля predict_ctr_update_manager
            "app.modules.wb_adv_updater.get_text_to_predict_ctr_dict",  # функция get для получения словаря предсказаний CTR
        ]
    )

    # Зависимость: обёрнутый RedisClient из корневого контейнера
    redis_client_wrapper = providers.Dependency(instance_of=RedisClient)

    # Тонкие менеджеры
    redis_manager = providers.Singleton(
        PredictCTRRedisManager,
        redis_client=redis_client_wrapper,
    )


__all__ = ["PredictCTRManagerContainer"]

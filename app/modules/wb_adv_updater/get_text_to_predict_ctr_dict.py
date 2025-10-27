import typing
from dependency_injector.wiring import inject, Provide
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.predict_ctr_update_manager.di import (
    PredictCTRManagerContainer,
)

if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.predict_ctr_update_manager.redis_manager import (
        PredictCTRRedisManager,
    )


@inject
async def get(
    adv_setting: AdvSetting,
    texts: list[str],
    predict_ctr_redis_manager: "PredictCTRRedisManager" = Provide[
        PredictCTRManagerContainer.redis_manager
    ],
) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    # TODO: Не понятно как Мин CTR Определяется по РК, кажется где-то ошибк - баг
    for text in texts:
        result_for_text = await predict_ctr_redis_manager.get_predict_ctr(  # type: ignore[attr-defined]
            adv_setting, text
        )
        result[text] = result_for_text
    return result

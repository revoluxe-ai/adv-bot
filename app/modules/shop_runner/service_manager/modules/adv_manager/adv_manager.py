
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.data_classes import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword


async def get_complex_adv(
    adv: AdvSetting, keywords: list[CalculatedKeyword]
) -> ComplexAdv:
    return ComplexAdv(adv, keywords)

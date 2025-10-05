from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.data_classes import ComplexAdv


async def get_complex_adv(
    adv: AdvSetting, keywords: list[CalculatedKeyword]
) -> ComplexAdv:
    return ComplexAdv(adv, keywords)

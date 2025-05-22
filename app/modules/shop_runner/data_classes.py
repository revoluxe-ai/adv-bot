from dataclasses import dataclass

from app.client_bot.user_interface.states import AdvSetting
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)


@dataclass
class ComplexAdv:
    adv: AdvSetting
    keywords: list[CalculatedKeyword]

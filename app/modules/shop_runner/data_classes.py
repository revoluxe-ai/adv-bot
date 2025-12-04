from dataclasses import dataclass

from app.client_bot.user_interface.states import AdvSetting
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword


@dataclass
class ComplexAdv:
    adv: AdvSetting
    keywords: list[CalculatedKeyword]

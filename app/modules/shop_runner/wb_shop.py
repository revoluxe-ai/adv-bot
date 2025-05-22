import asyncio
import logging
from typing import (
    TypeVar,
)

from .modules.wb_api import WBApi

logger = logging.getLogger(__name__)
from .service_manager import CoroutinesManager

T = TypeVar("T")


class WBShop:

    def __init__(self, wb_api: WBApi):
        self._wb_api = wb_api

    async def run(self) -> None:
        wb_api = self._wb_api
        coroutines_manager = CoroutinesManager(wb_api)
        await asyncio.gather(
            coroutines_manager.parsing_keywords_run(),
            coroutines_manager.update_advs_data_from_wb_to_pg(),
            coroutines_manager.update_cards_data_from_wb_to_pf(),
            coroutines_manager.update_cpm_bid(),
            coroutines_manager.update_common_sale_stat(),
            coroutines_manager.update_full_adv_stat(),
            coroutines_manager.adv_settings_auto_update(),
            coroutines_manager.update_top_key_in_advs(),
        )

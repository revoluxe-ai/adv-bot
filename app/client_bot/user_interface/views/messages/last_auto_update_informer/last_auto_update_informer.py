import datetime

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager import (
    LastSetDownTargetPlace,
    LastSetUpTargetPlace,
    LastUpdateFirstPhrase,
    last_auto_update_phrases_to_white_list,
)


class LastAutoUpdateSettingInformer:
    def __init__(self, adv: AdvSetting):
        self._delete_from_white_list = (
            last_auto_update_phrases_to_white_list.LastAutoDeleteFromWhiteList(adv)
        )
        self._add_to_white_list = (
            last_auto_update_phrases_to_white_list.LastAutoAddPhraseToWhiteList(adv)
        )
        self._up_target_place = LastSetUpTargetPlace(adv)
        self._down_target_place = LastSetDownTargetPlace(adv)
        self._update_top_key = LastUpdateFirstPhrase(adv)

        self.delete_from_white_list_str: str | None = None
        self.add_to_white_list_str: str | None = None
        self.up_target_place_str: str | None = None
        self.down_target_place_str: str | None = None
        self.update_top_key_str: str | None = None

    async def update_data(self) -> None:
        self.delete_from_white_list_str = self.to_str_timestamp(
            await self._delete_from_white_list.get()
        )
        self.add_to_white_list_str = self.to_str_timestamp(await self._add_to_white_list.get())
        self.up_target_place_str = self.to_str_timestamp(await self._up_target_place.get())
        self.down_target_place_str = self.to_str_timestamp(await self._down_target_place.get())
        self.update_top_key_str = self.to_str_timestamp(await self._update_top_key.get())

    @staticmethod
    def to_str_timestamp(timestamp: datetime.datetime | None) -> str:
        fmt = "%H:%M:%S %d-%m-%Y"
        return timestamp.strftime(fmt) if timestamp else "Нет данных"

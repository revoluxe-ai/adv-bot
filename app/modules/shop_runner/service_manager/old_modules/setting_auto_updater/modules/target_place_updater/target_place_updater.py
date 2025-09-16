from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.target_place_updater.redis_cache import (
    LastSetUpTargetPlace,
    LastSetDownTargetPlace,
)
from app.utils.db.session_maker import get_async_session_maker as sm


class TargetPlaceUpdater:

    def __init__(self, adv: AdvSetting):
        self._adv: AdvSetting = adv

        self._target_place = adv.max_place

    async def _refresh_adv(self):
        async with sm() as session:
            await session.refresh(self._adv, attribute_names=[AdvSetting.max_place])

    async def set_up(self) -> tuple[bool, bool]:
        pass_time = 15 * 60
        last_set_up_target_place = LastSetUpTargetPlace(self._adv)
        if not await last_set_up_target_place.check_pass_time(pass_time):
            return False, False
        adv = self._adv
        target_place = self._target_place
        new_target_place = target_place - 1
        if new_target_place < 1:
            new_target_place = 1
        if new_target_place < 1:
            new_target_place = 1
        elif new_target_place > 30:
            new_target_place = 30
        if new_target_place != target_place:
            async with sm() as session:
                stmt = (
                    update(AdvSetting)
                    .where(AdvSetting.id == adv.id)
                    .values({"max_place": new_target_place})
                )
                await session.execute(stmt)
                await session.commit()
                await last_set_up_target_place.set()
                return True, False
        return False, True

    async def set_down(self) -> tuple[bool, bool]:
        pass_time = 15 * 60
        last_set_down_target_place = LastSetDownTargetPlace(self._adv)
        if not await last_set_down_target_place.check_pass_time(pass_time):
            return False, False
        adv = self._adv
        target_place = self._target_place
        new_target_place = target_place + 1
        if new_target_place > 100_000:
            new_target_place = 100_000
        if new_target_place != target_place:
            async with sm() as session:
                stmt = (
                    update(AdvSetting)
                    .where(AdvSetting.id == adv.id)
                    .values({"max_place": new_target_place})
                )
                await session.execute(stmt)
                await session.commit()
                await last_set_down_target_place.set()
                return True, False
        else:
            return False, True

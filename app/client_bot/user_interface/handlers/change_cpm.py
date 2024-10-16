import aiogram
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

import app
from app.client_bot.user_interface import states
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm


router = Router()



@router.callback_query(callbacks.ChangeCPM.filter())
async def change_cpm(callback: aiogram.types.CallbackQuery,
                     callback_data: callbacks.ChangeCPM,
                     bot: aiogram.Bot,
                     state: FSMContext):
    await callback.answer()
    adv_setting_original_id = callback_data.adv_setting_original_id
    await state.update_data(last_adv_setting_original_id=adv_setting_original_id)
    await state.set_state(states.ChangeCPM.waiting_for_cpm)
    await bot.send_message(callback.from_user.id, 'Введите новое значение CPM')



@router.message(StateFilter(states.ChangeCPM.waiting_for_cpm))
async def change_cpm(message: aiogram.types.Message,
                        state: FSMContext):
        data = await state.get_data()
        adv_setting_original_id: int = int(data['last_adv_setting_original_id'])
        cpm = message.text
        if not cpm.isdigit():
            await message.answer('CPM должен быть числом')
            return
        cpm = int(cpm)
        if cpm > 1500:
            await message.answer('Внимание! Системное ограничение: нельзя задать ставку больше 1500. Если нужно снять ограничение, обратитесь к администратору')
            return

        await state.set_state(None)
        async with sm() as session:
            stmt = select(AdvSetting)\
                .join(AdvSetting.wb_cabinet)\
                .options(joinedload(AdvSetting.wb_cabinet))\
                .where(AdvSetting.id == adv_setting_original_id)
            adv_setting: AdvSetting = (await session.execute(stmt)).scalar()
            shop_id = adv_setting.wb_cabinet.shop_id
            access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
            wb_api = WBApi(access)
            await wb_api.advert.update_cpm(adv_setting.adv_id, cpm)
            await message.answer('CPM Авто на {}'.format(cpm))
            if adv_id := adv_setting.search_adv_id:
                await wb_api.advert.update_cpm(adv_id, cpm)
                await message.answer('CPM Поиск на {}'.format(cpm))

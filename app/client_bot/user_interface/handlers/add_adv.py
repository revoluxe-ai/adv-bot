import logging

import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import or_
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries import super_cabinet_manager as scm
from app.modules.common_slaves.wildberries.models import WBCard
from app.utils.db.session_maker import get_async_session_maker

from ... import manager
from .. import states
from ..views import callbacks, messages

sm = get_async_session_maker()

router = Router()


logger = logging.getLogger(__name__)


@router.callback_query(callbacks.Adv.filter(F.action == 'new'))
async def process_adv_new(callback: types.CallbackQuery, callback_data: callbacks.Adv,
                          bot: aiogram.Bot,
                          state: FSMContext):
    await bot.answer_callback_query(callback.id)
    await state.set_state(states.CreateNewAdvCompany.waiting_for_name)
    await messages.GetNameOfNewAdvCompany(bot, callback.message.chat.id)()
    return


@router.message(state=states.CreateNewAdvCompany.waiting_for_name)
async def process_adv_new_name(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if len(text) > 120:
        await state.clear()
        await state.set_state(states.CreateNewAdvCompany.waiting_for_name)
        await messages.TooLongNameOfNewAdvCompany(message.bot, message.chat.id)()
        return

    await state.update_data(adv_company_name=text)
    await state.set_state(states.CreateNewAdvCompany.waiting_for_nmids)
    await messages.GetNmidOfNewAdvCompany(message.bot, message.chat.id)()
    return


@router.message(state=states.CreateNewAdvCompany.waiting_for_nmids)
async def process_adv_new_nmids(message: types.Message, state: FSMContext):
    text = message.text.strip()
    text = text.replace(' ', '')
    text = text.replace(',', ' ')
    text = text.replace(';', ' ')
    text = text.replace('.', ' ')

    items = text.split()
    items = list(set(items))
    items = [int(item) for item in items if item.isdigit()]
    not_founded_items = set()
    founded_nmids = set()
    async with sm() as session:
       for item in items:
           stmt = select(WBCard)\
           .where(or_(WBCard.nmid == item,
                      WBCard.offer_id == item))
           result = await session.execute(stmt)
           card = result.scalars().first()
           if not card:
               not_founded_items.add(item)
           else:
                founded_nmids.add(card.nmid)
    if not_founded_items:
        await state.set_state(states.CreateNewAdvCompany.waiting_for_nmids)
        not_founded_items = [str(item) for item in not_founded_items]
        await messages.NotFoundNmidOfNewAdvCompany(message.bot, message.chat.id, not_founded_items)()
        return
    else:
        data = await state.get_data()
        adv_company_name = data['adv_company_name']
        await state.clear()
        access = scm.get_access_for_wb_user_cabinet()
        await manager.create_new_adv_company(adv_company_name, founded_nmids, access)



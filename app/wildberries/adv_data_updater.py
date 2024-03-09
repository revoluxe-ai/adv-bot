from .api import WBApi
from .models import AdvSetting
import asyncio
from sqlalchemy import select
from . import models
from session_maker import get_async_session_maker
import json
import logging
import typing
from app.db.associations import WBUserCabinet


sm = get_async_session_maker()

logger = logging.getLogger(__name__)

_coroutine_queue = asyncio.Queue()


async def consumer():
    logger.info('Consumer started')
    active_tasks = []
    while True:
        logger.info('Consumer waiting for task')
        if _coroutine_queue.empty() and active_tasks:
            logger.info('Consumer waiting for task')
            done, _ = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
            # Удалять задачи из списка active_tasks здесь не нужно, так как мы используем колбэки для их удаления
        else:
            coroutine: asyncio.Future = await _coroutine_queue.get()
            task =  asyncio.create_task(coroutine)
            task.add_done_callback(lambda t, lst=active_tasks: lst.remove(t))
            active_tasks.append(task)


class ShopDataUpdater:
    def __init__(self, wb_api: WBApi, wb_user_cabinet: WBUserCabinet):
        self.__wb_api = wb_api
        self.__wb_cabinet = wb_user_cabinet.wb_cabinet



    async def update_all_data(self):
        await self.__update_advs()


    async def __update_advs(self):
        wb_api  = self.__wb_api
        advert_api = wb_api.advert
        adv_ids = await advert_api.get_advertIds(advert_api.live_company_status, advert_api.auto_adv_types)
        async with sm() as session:
            stmt = select(models.AdvSetting).where(models.AdvSetting.adv_id.in_(adv_ids))
            result = (await session.execute(stmt)).unique()
            existing_advs: list[models.AdvSetting] = result.scalars().all()
            existind_advs_ids = {adv.adv_id for adv in existing_advs}
            not_existing_adv_ids = set(adv_ids) - set(existind_advs_ids)
            if not_existing_adv_ids:
                await self.__update_advs_in_db(not_existing_adv_ids)
            task = asyncio.create_task(self.__update_advs_in_db( existind_advs_ids))
            await _coroutine_queue.put(task)


    async def __update_advs_in_db(self, adv_ids:set[int]):
        wb_api = self.__wb_api
        advs = await wb_api.advert.get_advs(list(adv_ids))
        nmids_collection = set()
        async with sm() as session:
            for adv in advs:
                stmt = select(models.AdvSetting).where(models.AdvSetting.adv_id == adv.advertId)
                result = await session.execute(stmt)
                existing_adv = result.scalars().first()
                if existing_adv:
                    existing_adv.active_status = adv.status_native
                    existing_adv.name = adv.name
                    existing_adv.nmids = adv.nmids
                    nmids = existing_adv.nmids
                    if nmids:
                        for nmid in nmids:
                            nmids_collection.add(nmid)
                else:
                    adv_in_db = models.AdvSetting()
                    adv_in_db.adv_id = adv.advertId
                    adv_in_db.name = adv.name
                    adv_in_db.wb_cabinet = self.__wb_cabinet
                    adv_in_db.nmids = adv.nmids
                    adv_in_db.active_status = adv.status_native
                    await session.merge(adv_in_db)
                    nmids = adv.nmids
                    await session.commit()
                    if nmids:
                        for nmid in nmids:
                            nmids_collection.add(nmid)

        task = asyncio.create_task(self.__update_cards(nmids_collection))
        await _coroutine_queue.put(task)


    async def __update_cards(self, nmids:set[int]):
        cards = await self.__wb_api.advert.get_cards_by_text(nmids)
        async with sm() as session:
            for card in cards:
                stmt = select(models.WBCard).where(models.WBCard.nmid == card.nmid)
                result = await session.execute(stmt)
                existing_card = result.scalars().first()
                if existing_card:
                    # Если карточка уже существует, обновляем ее
                    existing_card.json = json.dumps(card.data)
                else:
                    # Если карточка новая, добавляем ее в список для последующего добавления в базу
                    db_card = models.WBCard()
                    db_card.offer_id = card.offer_id
                    db_card.name = card.name
                    db_card.wb_category_name = card.wb_category_name
                    db_card.json = json.dumps(card.data)
                    db_card.wb_cabinet = self.__wb_cabinet
                    db_card.nmid = card.nmid
                    session.add(db_card)
                    stmt = select(models.WBCategory) \
                        .where(models.WBCategory.wb_category_name == card.wb_category_name)
                    result = await session.execute(stmt)
                    category = result.scalars().first()
                    if not category:
                        category = models.WBCategory()
                        category.wb_category_name = card.wb_category_name
                        category.wb_cabinet = self.__wb_cabinet
                        session.add(category)
                    db_card.wb_category = category
                    await session.commit()



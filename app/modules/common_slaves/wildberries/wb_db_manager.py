import json

from sqlalchemy import select

from app import my_types
from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker()


async def update_advs_in_db(advs, wb_cabinet: WBCabinet):
    async with _sm() as session:
        for adv in advs:
            stmt = select(my_types.AdvSetting).where(my_types.AdvSetting.adv_id == adv.advertId)
            result = await session.execute(stmt)
            existing_adv = result.scalars().first()
            if existing_adv:
                existing_adv.active_status = adv.status_native
                existing_adv.name = adv.name
                existing_adv.type = adv.type
                nmids = adv.nmids
                if nmids:
                    existing_adv.nmids = adv.nmids
            else:
                stmt = select(WBCabinet)\
                .where(WBCabinet.id == wb_cabinet.id)
                wb_cabinet: WBCabinet = (await session.execute(stmt)).scalar()
                adv_in_db = my_types.AdvSetting()
                adv_in_db.adv_id = adv.advertId
                adv_in_db.name = adv.name
                adv_in_db.wb_cabinet = wb_cabinet
                adv_in_db.nmids = adv.nmids
                adv_in_db.active_status = adv.status_native
                adv_in_db.type = adv.type
                session.add(adv_in_db)
                adv_in_db.wb_cabinet = wb_cabinet
        await session.commit()


async def update_cards_in_db(cards: list[CardFromWB], wb_cabinet: WBCabinet):
    async with _sm() as session:
        for card in cards:
            stmt = select(my_types.WBCard).where(my_types.WBCard.nmid == card.nmid)
            result = await session.execute(stmt)
            existing_card = result.scalars().first()
            if existing_card:
                # Если карточка уже существует, обновляем ее
                existing_card.json = json.dumps(card.data)
            else:
                # Если карточка новая, добавляем ее в список для последующего добавления в базу
                db_card = my_types.WBCard()
                db_card.offer_id = card.offer_id
                db_card.name = card.name
                db_card.wb_category_name = card.wb_category_name
                db_card.json = json.dumps(card.data)
                db_card.wb_cabinet = wb_cabinet
                db_card.nmid = card.nmid
                session.add(db_card)
                stmt = select(my_types.WBCategory) \
                    .where(my_types.WBCategory.wb_category_name == card.wb_category_name)
                result = await session.execute(stmt)
                category = result.scalars().first()
                if not category:
                    category = my_types.WBCategory()
                    category.wb_category_name = card.wb_category_name
                    category.wb_cabinet = wb_cabinet
                    session.add(category)
                db_card.wb_category = category
                await session.commit()
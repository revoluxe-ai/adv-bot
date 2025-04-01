import json
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import my_types
from app.core.wb_api.data_classes.adv import Adv
from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker


async def update_advs_in_db(advs: list[Adv], wb_cabinet_id: int, session: AsyncSession):
    # Преобразуем в список словарей
    adv_data = [
        {
            "adv_id": adv.advertId,
            "name": adv.name,
            "wb_cabinet_id": wb_cabinet_id,
            "nmids": adv.nmids,
            "active_status": adv.status_native,
            "type": adv.type,
            "cpm": adv.cpm
        }
        for adv in advs
    ]

    # Выполняем UPSERT
    stmt = insert(my_types.AdvSetting).values(adv_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["adv_id"],  # Указываем, по какому полю искать дубликаты
        set_={
            "name": stmt.excluded.name,
            "wb_cabinet_id": stmt.excluded.wb_cabinet_id,
            "nmids": stmt.excluded.nmids,
            "active_status": stmt.excluded.active_status,
            "type": stmt.excluded.type,
            "cpm": stmt.excluded.cpm,
        }
    )

    await session.execute(stmt)
    await session.commit()


async def update_cards_in_db(cards: list[CardFromWB], wb_cabinet: WBCabinet, session: AsyncSession):
    # Получаем все nmid из списка карточек
    nmids = [card.nmid for card in cards]

    # Делаем один запрос для получения всех карточек
    stmt = select(my_types.WBCard).where(my_types.WBCard.nmid.in_(nmids))
    result = await session.execute(stmt)
    existing_cards = result.scalars().all()

    # Создаём словарь для быстрого поиска
    cards_by_nmid = {card.nmid: card for card in existing_cards}

    # Теперь можем итерироваться по исходным карточкам
    for card in cards:
        existing_card = cards_by_nmid.get(card.nmid)
        if existing_card:
            # Если карточка уже существует, обновляем ее
            existing_card.json = json.dumps(card.data)
            existing_card.name = card.name
        else:
            # Если карточка новая, добавляем ее в список для последующего добавления в базу
            db_card = my_types.WBCard()
            db_card.nmid = card.nmid
            db_card.name = card.name
            db_card.json = json.dumps(card.data)
            session.add(db_card)  # Используем add вместо merge
            # Проверяем существование категории и добавляем ее, если необходимо
            stmt = select(my_types.WBCategory).where(my_types.WBCategory.wb_category_name == card.wb_category_name)
            result = await session.execute(stmt)
            category = result.scalars().first()
            if not category:
                category = my_types.WBCategory(
                    wb_category_name=card.wb_category_name,
                    wb_cabinet=wb_cabinet
                )
                session.add(category)

            db_card.wb_category = category
        await session.commit()
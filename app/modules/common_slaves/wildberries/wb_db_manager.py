import json

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.wb_api.data_classes.adv import Adv
from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.models import (
    WBCabinet,
    AdvSetting,
    WBCard,
    WBCategory,
)
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker


async def update_advs_in_db(
    advs: list[Adv], wb_cabinet_id: int, session: AsyncSession
) -> None:
    part = 10
    # Разбиваем список advs на части по 10 элементов
    for i in range(0, len(advs), part):
        advs_part = advs[i : i + part]
        await _update_advs_in_db(advs_part, wb_cabinet_id, session)


async def _update_advs_in_db(
    advs: list[Adv], wb_cabinet_id: int, session: AsyncSession
) -> None:
    # Преобразуем в список словарей
    adv_data = [
        {
            "adv_id": adv.advertId,
            "name": adv.name,
            "wb_cabinet_id": wb_cabinet_id,
            "nmids": adv.nmids,
            "active_status": adv.status_native,
            "type": adv.type,
            "cpm": adv.cpm,
        }
        for adv in advs
    ]

    # Выполняем UPSERT
    stmt = insert(AdvSetting).values(adv_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["adv_id"],  # Указываем, по какому полю искать дубликаты
        set_={
            "name": stmt.excluded.name,
            "wb_cabinet_id": stmt.excluded.wb_cabinet_id,
            "nmids": stmt.excluded.nmids,
            "active_status": stmt.excluded.active_status,
            "type": stmt.excluded.type,
            "cpm": stmt.excluded.cpm,
        },
    )

    await session.execute(stmt)
    await session.commit()





async def update_cards_in_db(
    cards: list[CardFromWB], wb_cabinet: WBCabinet, session: AsyncSession
) -> None:
    if not cards:
        return

    # Подготовим список данных
    card_values = []
    category_names = {card.wb_category_name for card in cards}

    # Получаем или создаём категории
    stmt = select(WBCategory).where(WBCategory.wb_category_name.in_(category_names))
    result = await session.execute(stmt)
    existing_categories = {cat.wb_category_name: cat for cat in result.scalars().all()}

    # Добавляем недостающие категории
    for name in category_names - existing_categories.keys():
        new_cat = WBCategory(wb_category_name=name, wb_cabinet=wb_cabinet)
        session.add(new_cat)
        existing_categories[name] = new_cat

    await session.flush()  # чтобы получить id категорий

    # Готовим данные для upsert
    for card in cards:
        wb_category_id = existing_categories[card.wb_category_name].id
        card_values.append(
            {
                "nmid": card.nmid,
                "name": card.name,
                "json": json.dumps(card.data),
                "wb_category_id": wb_category_id,
            }
        )

    # Выполняем bulk upsert
    stmt = insert(WBCard).values(card_values)
    update_dict = {
        "name": stmt.excluded.name,
        "json": stmt.excluded.json,
        "wb_category_id": stmt.excluded.wb_category_id,
    }
    stmt = stmt.on_conflict_do_update(index_elements=["nmid"], set_=update_dict)

    await session.execute(stmt)
    await session.commit()

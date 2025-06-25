import json
from typing import Sequence

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

    part = 3

    for i in range(0, len(cards), part):
        cards_part = cards[i : i + part]
        await _update_cards_in_db(cards_part, wb_cabinet, session)


async def _update_cards_in_db(
    cards: Sequence[CardFromWB], wb_cabinet: WBCabinet, session: AsyncSession
) -> None:

    if not cards:
        return

    pass_nmids = set()
    clear_cards = []
    for card in cards:
        nmid = card.nmid
        if nmid not in pass_nmids:
            clear_cards.append(card)
            pass_nmids.add(card)

    cards = clear_cards
    # Получаем уникальные имена категорий
    category_names = {card.wb_category_name for card in cards}

    # Получаем уже существующие категории
    stmt = select(WBCategory).where(WBCategory.wb_category_name.in_(category_names))
    result = await session.execute(stmt)
    existing_categories = {
        category.wb_category_name: category for category in result.scalars().all()
    }

    # Добавляем недостающие категории
    for name in category_names - existing_categories.keys():
        new_category = WBCategory(wb_category_name=name, wb_cabinet=wb_cabinet)
        session.add(new_category)
        existing_categories[name] = new_category

    await session.flush()  # Чтобы получить id новых категорий

    # Подготавливаем данные для UPSERT
    card_values = [
        {
            "nmid": card.nmid,
            "name": card.name,
            "json": json.dumps(card.data),
            "wb_category_id": existing_categories[card.wb_category_name].id,
        }
        for card in cards
    ]

    # Выполняем UPSERT (insert ... on conflict do update)
    stmt_for_insert_cards = insert(WBCard).values(card_values)
    stmt_on_conflict = stmt_for_insert_cards.on_conflict_do_update(
        index_elements=["nmid"],
        set_={
            "name": stmt_for_insert_cards.excluded.name,
            "json": stmt_for_insert_cards.excluded.json,
            "wb_category_id": stmt_for_insert_cards.excluded.wb_category_id,
        },
    )

    try:
        await session.execute(stmt_on_conflict)
        await session.commit()
    except Exception:
        raise

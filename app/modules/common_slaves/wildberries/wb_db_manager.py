import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.client_bot.user_interface.services.auto_management_mode import (
    apply_new_campaign_free_defaults,
)
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBCard,
    WBCategory,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.shared.domains.wb.utils.wb_campaign_meta import (
    apply_wb_campaign_meta_from_legacy_adv_data,
)
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker


async def update_advs_in_db(advs: list[AuctionAdv], wb_cabinet_id: int) -> None:
    part = 10
    # Разбиваем список advs на части по 10 элементов
    for i in range(0, len(advs), part):
        advs_part = advs[i : i + part]
        await _update_advs_in_db(advs_part, wb_cabinet_id)


async def _update_advs_in_db(advs: list[AuctionAdv], wb_cabinet_id: int) -> None:
    """TODO Была ошибка, когда пытаемся добавить две одинаковых РК. Вообще, такого быть не должно
    но есть, если юзеры не правильно прописывают в названии артикул Аукциона
    """
    stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet_id)
    async with _sm(read_only=False) as session:
        result = await session.execute(stmt)
        wb_cabinet: WBCabinet = result.scalar_one()


    advs_to_process: list[AuctionAdv] = []
    seen_adv_ids: set[int] = set()
    for adv in advs:
        if adv.advertId not in seen_adv_ids:
            advs_to_process.append(adv)
            seen_adv_ids.add(adv.advertId)

    async with _sm(read_only=False) as session:
        # Получаем существующие записи по adv_id
        adv_ids = [adv.advertId for adv in advs_to_process]
        existing_stmt = select(AdvSetting).where(AdvSetting.adv_id.in_(adv_ids))
        existing_result = await session.execute(existing_stmt)
        existing_adv_settings = {adv.adv_id: adv for adv in existing_result.scalars().all()}

        # Обрабатываем каждую кампанию
        for adv in advs_to_process:
            if adv.advertId in existing_adv_settings:
                # Обновляем существующую запись через ORM
                adv_setting = existing_adv_settings[adv.advertId]
                # Комплексная РК (запись с _search_adv_id) хранит имя по шаблону «Артикул Название карточки» — не перезаписываем из WB
                if adv_setting._search_adv_id is None: # pyright: ignore #noqa
                    adv_setting.name = adv.name
                adv_setting.wb_cabinet_id = wb_cabinet_id
                adv_setting.nmids = adv.nmids
                adv_setting.active_status = adv.status_native
                adv_setting.type = adv.type
                adv_setting.cpm = adv.cpm
                apply_wb_campaign_meta_from_legacy_adv_data(
                    adv_setting, adv.data
                )
            else:
                # Создаем новую запись через ORM
                adv_setting = AdvSetting(
                    adv_id=adv.advertId,
                    name=adv.name,
                    wb_cabinet_id=wb_cabinet_id,
                    nmids=adv.nmids,
                    active_status=adv.status_native,
                    type=adv.type,
                    cpm=adv.cpm,
                )
                # Применяем дефолты через ORM
                # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
                apply_new_campaign_free_defaults(adv_setting, wb_cabinet)
                apply_wb_campaign_meta_from_legacy_adv_data(
                    adv_setting, adv.data
                )
                session.add(adv_setting)

        await session.commit()


async def update_cards_in_db(cards: list[CardFromWB], wb_cabinet: WBCabinet) -> None:
    if not cards:
        return

    part = 3

    for i in range(0, len(cards), part):
        cards_part = cards[i : i + part]
        await _update_cards_in_db(cards_part, wb_cabinet)


async def _update_cards_in_db(
    cards: Sequence[CardFromWB], wb_cabinet: WBCabinet
) -> None:
    if not cards:
        return

    # Удаляем дубликаты по nmid
    pass_nmids: set[int] = set()
    clear_cards: list[CardFromWB] = []
    for card in cards:
        if card.nmid not in pass_nmids:
            clear_cards.append(card)
            pass_nmids.add(card.nmid)
    cards = clear_cards

    # Получаем уникальные имена категорий
    category_names: set[str] = {card.wb_category_name for card in cards}

    async with _sm(read_only=False) as session:
        # Получаем уже существующие категории
        stmt = select(WBCategory).where(WBCategory.wb_category_name.in_(category_names))
        result = await session.execute(stmt)
        existing_categories: dict[str, WBCategory] = {
            category.wb_category_name: category for category in result.scalars().all()
        }

        # Добавляем недостающие категории
        for name in category_names - existing_categories.keys():
            new_category = WBCategory(wb_category_name=name, wb_cabinet=wb_cabinet)
            session.add(new_category)
            existing_categories[name] = new_category

        # Flush — получаем ID для новых категорий
        await session.flush()

        # Подготавливаем данные для UPSERT
        card_values: list[dict[str, Any]] = [
            {
                "nmid": card.nmid,
                "offer_id": card.offer_id,
                "name": card.name,
                "json": json.dumps(card.data),
                "wb_category_id": existing_categories[card.wb_category_name].id,
            }
            for card in cards
        ]

        # Выполняем UPSERT
        stmt_for_insert_cards = insert(WBCard).values(card_values) # pyright: ignore
        stmt_on_conflict = stmt_for_insert_cards.on_conflict_do_update(
            index_elements=["nmid"],
            set_={
                "offer_id": stmt_for_insert_cards.excluded.offer_id,
                "name": stmt_for_insert_cards.excluded.name,
                "json": stmt_for_insert_cards.excluded.json,
                "wb_category_id": stmt_for_insert_cards.excluded.wb_category_id,
            },
        )

        await session.execute(stmt_on_conflict)
        await session.commit()

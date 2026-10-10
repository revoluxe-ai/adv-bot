"""Постраничный список кампаний кабинета. Ключ строки — advert_id."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.models import AdvSetting

PAGE_SIZE = 8


@dataclass(frozen=True, slots=True)
class CampaignListItem:
    """Строка списка. ``name`` — подпись, не идентичность."""

    advert_id: int
    name: str


@dataclass(frozen=True, slots=True)
class CampaignPage:
    """Одна страница offset-пагинации."""

    items: tuple[CampaignListItem, ...]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        if self.total <= 0:
            return 1
        return (self.total + self.page_size - 1) // self.page_size


async def load_campaign_page(
    session: AsyncSession,
    *,
    wb_cabinet_id: int,
    page: int,
) -> CampaignPage:
    """
    Кампании кабинета с непустым advert_id, порядок по advert_id.

    В выборку попадает только текущая страница.
    """
    safe_page = page if page >= 1 else 1
    where = (
        AdvSetting.wb_cabinet_id == wb_cabinet_id,
        AdvSetting.adv_id.is_not(None),
        AdvSetting.adv_id > 0,
    )
    count_stmt = select(func.count()).select_from(AdvSetting).where(*where)
    total = int((await session.execute(count_stmt)).scalar_one())
    offset = (safe_page - 1) * PAGE_SIZE
    stmt = (
        select(AdvSetting.adv_id, AdvSetting.name)
        .where(*where)
        .order_by(AdvSetting.adv_id)
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    result = await session.execute(stmt)
    items: list[CampaignListItem] = []
    for advert_id, name in result.all():
        if advert_id is None:
            continue
        items.append(CampaignListItem(advert_id=int(advert_id), name=str(name)))
    return CampaignPage(
        items=tuple(items),
        page=safe_page,
        page_size=PAGE_SIZE,
        total=total,
    )


async def load_campaign_label(
    session: AsyncSession,
    *,
    wb_cabinet_id: int,
    advert_id: int,
) -> str | None:
    """Подпись кампании, если advert_id принадлежит кабинету. Иначе None."""
    stmt = select(AdvSetting.name).where(
        AdvSetting.wb_cabinet_id == wb_cabinet_id,
        AdvSetting.adv_id == advert_id,
    )
    result = await session.execute(stmt)
    name = result.scalar_one_or_none()
    if name is None:
        return None
    return str(name)

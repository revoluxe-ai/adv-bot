"""Read-only PG inventory scope: AdvSetting/WBCabinet join по shop_id."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from app.modules.ai_package_v1.scope.queries import (
    select_search_advs_by_adv_ids,
    select_shop_inventory_advs,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker


def _resolve_main_nmid(nmids: Sequence[int]) -> int | None:
    """Первый nmid после сортировки (как ``ComplexAdv.main_nmid``), либо ``None``."""
    if not nmids:
        return None
    return sorted(nmids)[0]


def _build_scope_rows(
    shop_id: str,
    auto_advs: Sequence[AdvSetting],
    search_by_adv_id: dict[int, AdvSetting],
) -> list[ExportScopeAdv]:
    rows: list[ExportScopeAdv] = []
    for adv in auto_advs:
        adv_id_value = cast(object, adv.adv_id)
        if not isinstance(adv_id_value, int):
            continue
        search_id = adv.search_adv_id
        if search_id is not None and search_id not in search_by_adv_id:
            search_id = None
        rows.append(
            ExportScopeAdv(
                shop_id=shop_id,
                auto_adv_id=adv_id_value,
                search_adv_id=search_id,
                main_nmid=_resolve_main_nmid(list(adv.nmids)),
                name=adv.name,
                active_status=adv.active_status,
                bot_active=bool(adv.bot_active),
            )
        )
    return rows


class PgExportShopScopeReader:
    """
    Named seam §1.2: PG inventory для export без shop-runner orchestrator.

    Открывает ``get_async_session_maker(read_only=True)``; только static select/join.
    Пустой inventory → ``[]`` (не shop-runner ``NotFoundActiveAdvCompany``).
    """

    async def load_scope(self, shop_id: str) -> list[ExportScopeAdv]:
        """
        Загрузить scope-кампании магазина из PG (inventory grain).

        Args:
            shop_id: Authoritative ключ ``WBCabinet.shop_id``.

        Returns:
            Список ``ExportScopeAdv``; может быть пустым.
        """
        async with get_async_session_maker(read_only=True) as session:
            return await self.load_scope_with_session(session, shop_id)

    async def load_scope_with_session(
        self,
        session: AsyncSession,
        shop_id: str,
    ) -> list[ExportScopeAdv]:
        """
        Тот же scope с session, открытой parent-callable (unit/integration seam).

        Args:
            session: Read-only AsyncSession.
            shop_id: ``WBCabinet.shop_id``.

        Returns:
            Список scope DTO.
        """
        stmt = select_shop_inventory_advs(shop_id)
        result = await session.execute(stmt)
        auto_advs: Sequence[AdvSetting] = result.scalars().all()
        if not auto_advs:
            return []

        search_ids: set[int] = {
            adv.search_adv_id for adv in auto_advs if adv.search_adv_id is not None
        }
        search_by_adv_id: dict[int, AdvSetting] = {}
        if search_ids:
            search_stmt = select_search_advs_by_adv_ids(search_ids)
            search_result = await session.execute(search_stmt)
            search_rows: Sequence[AdvSetting] = search_result.scalars().all()
            search_by_adv_id = {row.adv_id: row for row in search_rows}

        return _build_scope_rows(shop_id, auto_advs, search_by_adv_id)

"""PG read-only KeywordSetting projection at (adv_setting_id, query_text) grain."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_package_v1.keyword_performance.readers.pg_session_adapter import (
    default_pg_session_factory,
)
from app.modules.ai_package_v1.scope.pg_adv_setting_inventory_reader import (
    SessionMakerProtocol,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.common_slaves.wildberries.models.models import KeywordSetting


@dataclass(frozen=True, slots=True)
class KeywordQueryPolicySnapshot:
    """Per-keyword PG policy; не наследует campaign max_cpm как applied bid."""

    adv_setting_id: int
    query_text: str
    target_place: int | None
    strategy_mode: str | None
    hard_status: int | None


def _enum_text(value: object) -> str | None:
    if value is None:
        return None
    inner = getattr(value, "value", value)
    return str(inner) if inner is not None else None


class PgKeywordQueryPolicyReader:
    """Load KeywordSetting rows for shop-scoped adv_setting ids."""

    def __init__(
        self,
        session_maker: SessionMakerProtocol | None = None,
    ) -> None:
        self._session_maker = session_maker or default_pg_session_factory

    async def load_query_policies(
        self, shop_id: str, adv_setting_ids: frozenset[int]
    ) -> dict[tuple[int, str], KeywordQueryPolicySnapshot]:
        """Return keyword policies keyed by (adv_setting_id, query_text as stored)."""
        if not adv_setting_ids:
            return {}
        session_factory = self._session_maker(read_only=True)
        async with session_factory() as session:
            return await self._load_with_session(session, shop_id, adv_setting_ids)

    async def _load_with_session(
        self,
        session: AsyncSession,
        shop_id: str,
        adv_setting_ids: frozenset[int],
    ) -> dict[tuple[int, str], KeywordQueryPolicySnapshot]:
        stmt = (
            select(KeywordSetting)
            .join(AdvSetting, KeywordSetting.adv_setting_id == AdvSetting.id)
            .join(WBCabinet, AdvSetting.wb_cabinet_id == WBCabinet.id)
            .where(
                WBCabinet.shop_id == shop_id,
                KeywordSetting.adv_setting_id.in_(adv_setting_ids),
            )
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        policies: dict[tuple[int, str], KeywordQueryPolicySnapshot] = {}
        for ks in rows:
            key = (ks.adv_setting_id, ks.text)
            policies[key] = KeywordQueryPolicySnapshot(
                adv_setting_id=ks.adv_setting_id,
                query_text=ks.text,
                target_place=ks.target_place,
                strategy_mode=_enum_text(ks.strategy_mode),
                hard_status=ks.hard_status,
            )
        return policies

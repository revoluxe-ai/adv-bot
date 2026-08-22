"""Выборка и сидирование ключей Postgres для интеграционных тестов V3 target_place."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from tests.factories.adv_factory import AdvSettingFactory, KeywordSettingFactory


@dataclass(frozen=True, slots=True)
class V3KeywordSample:
    """Ключ из БД для прогона target_place / bid profile."""

    keyword_text: str
    adv_setting_id: int
    adv_id: int | None
    nmid: int | None
    strategy_mode: KeywordStrategyMode


async def load_v3_keyword_samples(
    session: AsyncSession,
    *,
    limit: int = 30,
) -> list[V3KeywordSample]:
    """Ключи V3-кампаний с индивидуальными целями (не OFF).

    Args:
        session: Async SQLAlchemy session (тестовая или dev БД).
        limit: Максимум строк.

    Returns:
        Список образцов; может быть пустым в пустой test DB.
    """
    stmt = (
        select(
            KeywordSetting.text,
            KeywordSetting.adv_setting_id,
            KeywordSetting.strategy_mode,
            AdvSetting.adv_id,
            AdvSetting.nmids,
        )
        .join(AdvSetting, AdvSetting.id == KeywordSetting.adv_setting_id)
        .where(AdvSetting.bot_active.is_(True))
        .where(AdvSetting.individual_keywords_target_place_mode.is_(True))
        .where(KeywordSetting.strategy_mode != KeywordStrategyMode.OFF)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    samples: list[V3KeywordSample] = []
    for text, adv_setting_id, strategy_mode, adv_id, nmids in rows:
        nmid: int | None = None
        if nmids and len(nmids) > 0:
            nmid = int(nmids[0])
        samples.append(
            V3KeywordSample(
                keyword_text=str(text),
                adv_setting_id=int(adv_setting_id),
                adv_id=int(adv_id) if adv_id is not None else None,
                nmid=nmid,
                strategy_mode=strategy_mode,
            )
        )
    return samples


async def ensure_v3_keyword_samples(
    session: AsyncSession,
    *,
    limit: int = 30,
) -> list[V3KeywordSample]:
    """Образцы из БД; при отсутствии V3-данных создаёт минимальную кампанию в test DB."""
    existing = await load_v3_keyword_samples(session, limit=limit)
    if existing:
        return existing
    return await _seed_v3_keyword_samples(session)


async def _seed_v3_keyword_samples(session: AsyncSession) -> list[V3KeywordSample]:
    """Одна V3-РК с тремя ключами (MIN / OPT / MAX) для интеграционного прогона."""
    wb_cabinet = WBCabinet(
        shop_id=f"v3_tp_{uuid.uuid4().hex}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    session.add(wb_cabinet)
    await session.flush()

    nmid = 880_000 + (uuid.uuid4().int % 50_000)
    adv = cast(
        AdvSetting,
        AdvSettingFactory.build(
            wb_cabinet=wb_cabinet,
            name="V3 target place integration",
            bot_active=True,
            active_status="started",
            adv_id=890_000 + (uuid.uuid4().int % 10_000),
        ),
    )
    adv.nmids = [nmid]
    adv.individual_keywords_target_place_mode = True
    session.add(adv)
    await session.flush()

    keywords: list[tuple[str, KeywordStrategyMode]] = [
        ("v3_ladder_min_kw", KeywordStrategyMode.MIN_CPA),
        ("v3_ladder_opt_kw", KeywordStrategyMode.OPTIMUM),
        ("v3_ladder_max_kw", KeywordStrategyMode.MAX_CONVERSION),
    ]
    samples: list[V3KeywordSample] = []
    for text, mode in keywords:
        ks = cast(
            KeywordSetting,
            KeywordSettingFactory.build(
                adv_setting_id=adv.id,
                text=text,
                hard_status=2,
                strategy_mode=mode,
            ),
        )
        session.add(ks)
        samples.append(
            V3KeywordSample(
                keyword_text=text,
                adv_setting_id=int(adv.id),
                adv_id=int(adv.adv_id) if adv.adv_id is not None else None,
                nmid=nmid,
                strategy_mode=mode,
            )
        )
    await session.commit()
    return samples

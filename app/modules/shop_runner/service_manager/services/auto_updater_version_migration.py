"""Runtime migration of deprecated AutoUpdater V1 to V2."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

V1_AUTO_UPDATER_VERSION = 1
V2_AUTO_UPDATER_VERSION = 2


async def migrate_v1_auto_updaters_to_v2(advs: Sequence[ComplexAdv]) -> int:
    """Force ``automatic_version`` 1→2 in DB and in-memory for loaded campaigns."""
    v1_ids = [
        adv.original_adv_setting_id
        for adv in advs
        if adv.auto_updater_version == V1_AUTO_UPDATER_VERSION
    ]
    if not v1_ids:
        return 0

    shop_id = advs[0].shop_id if advs else "unknown"
    async with sm() as session:
        stmt = (
            update(AdvSetting)
            .where(AdvSetting.id.in_(v1_ids))
            .where(AdvSetting.automatic_version == V1_AUTO_UPDATER_VERSION)
            .values(automatic_version=V2_AUTO_UPDATER_VERSION)
        )
        result = await session.execute(stmt)
        await session.commit()
        migrated_count = int(getattr(result, "rowcount", len(v1_ids)))

    for adv in advs:
        if adv.auto_updater_version == V1_AUTO_UPDATER_VERSION:
            # TODO(strategy-transition): Вынести переключение стратегий в общий хелпер!
            adv.adv_setting.automatic_version = V2_AUTO_UPDATER_VERSION

    logger.debug(
        "AutoUpdater V1→V2 migration: shop_id=%s migrated=%s adv_setting_ids=%s",
        shop_id,
        migrated_count,
        v1_ids,
    )
    return migrated_count

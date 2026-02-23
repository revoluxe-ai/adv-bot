"""One-time script: set individual_keywords_target_place_mode=True for all AdvSettings
in cabinets that have the new tariff (TariffMode.AUTO).
Idempotent: only updates rows where the flag is not already True."""

from __future__ import annotations

import argparse
import asyncio
import logging

try:
    from set_path import add_project_root_to_path
except ImportError:
    from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

import dotenv

dotenv.load_dotenv()

from sqlalchemy import or_, select, update

from app.modules.billing.pricer.pricer import Pricer, TariffMode
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.session_maker import get_async_session_maker

LOG = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set individual_keywords_target_place_mode=True for all campaigns in cabinets with new (AUTO) tariff."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count and log; do not commit.",
    )
    return parser.parse_args()


async def _run(dry_run: bool) -> None:
    cabinets_processed = 0
    cabinets_with_new_tariff = 0
    adv_settings_updated = 0

    async with get_async_session_maker(read_only=False) as session:
        stmt = select(WBCabinet.id, WBCabinet.shop_id)
        result = await session.execute(stmt)
        cabinets = result.all()

        pricer = Pricer()
        for cabinet_id, shop_id in cabinets:
            cabinets_processed += 1
            details = await pricer.get_tariff_details(session, shop_id)
            if details.mode != TariffMode.AUTO:
                continue
            cabinets_with_new_tariff += 1

            update_stmt = (
                update(AdvSetting)
                .where(
                    AdvSetting.wb_cabinet_id == cabinet_id,
                    or_(
                        AdvSetting.individual_keywords_target_place_mode.is_(None),
                        AdvSetting.individual_keywords_target_place_mode.is_(False),
                    ),
                )
                .values(individual_keywords_target_place_mode=True)
            )
            r = await session.execute(update_stmt)
            count = getattr(r, "rowcount", 0)
            adv_settings_updated += count
            if count > 0:
                LOG.info(
                    "Cabinet id=%s shop_id=%s: would update %d AdvSetting(s)",
                    cabinet_id,
                    shop_id,
                    count,
                )

        if not dry_run and adv_settings_updated > 0:
            await session.commit()

    LOG.info(
        "Processed %d cabinet(s), %d with new tariff, %d AdvSetting(s) %s (dry_run=%s)",
        cabinets_processed,
        cabinets_with_new_tariff,
        adv_settings_updated,
        "updated" if not dry_run else "would be updated",
        dry_run,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    asyncio.run(_run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

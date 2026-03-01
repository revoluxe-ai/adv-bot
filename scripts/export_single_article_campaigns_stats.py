"""
Выгрузка статистики РК по одному артикулу в Excel.

Находит все активные РК захардкоженного магазина (SHOP_ID), содержащие только
указанный артикул (NMID), запрашивает статистику за TARGET_DATE и сохраняет
в xlsx: adv_id, shop_id, название, показы, клики, корзины, заказы.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    from set_path import add_project_root_to_path
except ImportError:
    from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

import dotenv
import pandas as pd
from aiohttp import ClientSession
from redis.asyncio import Redis

dotenv.load_dotenv()

from app.configs.app_config import AppConfig
from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.super_cabinet_manager import (
    get_access_for_wb_cabinet,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import (
    DayStats,
    FullAdvStat,
)
from app.modules.shop_runner.modules.wb_api import WBApi

logger = logging.getLogger(__name__)

# --- Захардкоженные параметры ---
SHOP_ID: str = "..."  # подставить реальный shop_id
NMID: int = ... # артикул WB
TARGET_DATE: date = date.today()  # день, за который нужна статистика


def _nm_ids_from_settings(item: Any) -> set[int]:
    """Артикулы из nm_settings и additional_properties кампании (как в candidates_service)."""
    out: set[int] = set()
    for ns in getattr(item, "nm_settings", []) or []:
        nid = getattr(ns, "nm_id", None)
        if nid is not None:
            out.add(int(nid))
        elif getattr(ns, "additional_properties", None):
            for key in ("nm_id", "nmId"):
                val = ns.additional_properties.get(key)
                if val is not None:
                    out.add(int(val))
                    break
    extra = getattr(item, "additional_properties", None) or {}
    for key in ("nm_id", "nmId", "nm_ids", "nmIds"):
        val = extra.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            for v in val:
                if v is not None:
                    try:
                        out.add(int(v))
                    except (TypeError, ValueError):
                        pass
        else:
            try:
                out.add(int(val))
            except (TypeError, ValueError):
                pass
    return out


def filter_campaigns_only_nmid(
    auction: list[Any], auto: list[Any], nmid: int
) -> list[Any]:
    """Оставляет только кампании, у которых ровно один артикул — nmid."""
    combined = list(auction) + list(auto)
    return [item for item in combined if _nm_ids_from_settings(item) == {nmid}]


def _campaign_name(item: Any) -> str:
    """Имя кампании из item (модель может не иметь поля name)."""
    name = getattr(item, "name", None)
    if name is not None:
        return str(name)
    return str(getattr(item, "additional_properties", {}).get("name", "") or "")


def _day_for_date(stat: FullAdvStat, target: date) -> DayStats | None:
    """Возвращает DayStats за target из stat.days, или первый день при одной дате."""
    if not stat.days:
        return None
    if len(stat.days) == 1:
        return stat.days[0]
    for d in stat.days:
        day_date = d.date.date() if isinstance(d.date, datetime) else d.date
        if day_date == target:
            return d
    return None


async def _async_main() -> None:
    app_config = AppConfig.create()
    redis_config = app_config.infrastructure.redis
    redis_client_raw: Redis = Redis(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        decode_responses=True,
    )
    await redis_client_raw.ping()
    redis_client_wrapper = RedisClient(redis_client=redis_client_raw)
    httpx_client_handler = HttpxClientHandler()
    await httpx_client_handler.init()

    wb_manager_hub_factory = WBManagerHubFactory(
        httpx_client_handler=httpx_client_handler,
        redis_client_wrapper=redis_client_wrapper,
    )

    try:
        try:
            access = await get_access_for_wb_cabinet(SHOP_ID)
        except Exception as e:
            logger.exception("Нет доступа к кабинету %s: %s", SHOP_ID, e)
            return

        rows: list[dict[str, Any]] = []

        async with ClientSession() as session:
            wb_api = WBApi(access, session)
            hub = wb_manager_hub_factory.get_wb_manager_hub(SHOP_ID)
            promotion_manager = hub.wb_modifier._promotion_manager

            try:
                candidates = await promotion_manager.get_connect_existing_candidates(
                    NMID
                )
            except Exception as e:
                logger.exception("Ошибка получения списка кампаний: %s", e)
                return

            filtered = filter_campaigns_only_nmid(
                candidates.auction_candidates,
                candidates.auto_candidates,
                NMID,
            )
            if not filtered:
                logger.info(
                    "Нет активных РК с единственным артикулом %s для shop_id=%s",
                    NMID,
                    SHOP_ID,
                )
            else:
                adv_ids = [item.id for item in filtered]
                adv_id_to_name = {item.id: _campaign_name(item) for item in filtered}

                try:
                    stats: list[FullAdvStat] = await wb_api.get_adv_full_state(
                        adv_ids, [TARGET_DATE]
                    )
                except Exception as e:
                    logger.exception("Ошибка запроса статистики: %s", e)
                    return

                for stat in stats or []:
                    day_stat = _day_for_date(stat, TARGET_DATE)
                    name = adv_id_to_name.get(stat.advertId, "")
                    if day_stat is not None:
                        rows.append(
                            {
                                "adv_id": stat.advertId,
                                "shop_id": SHOP_ID,
                                "name": name,
                                "views": day_stat.views,
                                "clicks": day_stat.clicks,
                                "atbs": day_stat.atbs,
                                "orders": day_stat.orders,
                            }
                        )
                    else:
                        rows.append(
                            {
                                "adv_id": stat.advertId,
                                "shop_id": SHOP_ID,
                                "name": name,
                                "views": 0,
                                "clicks": 0,
                                "atbs": 0,
                                "orders": 0,
                            }
                        )

        df = pd.DataFrame(
            rows,
            columns=[
                "adv_id",
                "shop_id",
                "name",
                "views",
                "clicks",
                "atbs",
                "orders",
            ],
        )
        out_name = f"report_{NMID}_{TARGET_DATE.isoformat()}.xlsx"
        out_path = Path(__file__).parent / out_name
        df.to_excel(out_path, index=False)
        logger.info("Выгружено строк: %s, файл: %s", len(rows), out_path)
    finally:
        await httpx_client_handler.shutdown()
        await redis_client_raw.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()

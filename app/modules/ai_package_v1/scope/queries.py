"""Статические SQLAlchemy select для PG inventory scope (shop_id authoritative)."""

from __future__ import annotations

from sqlalchemy import Select, select

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet


def select_shop_inventory_advs(shop_id: str) -> Select[tuple[AdvSetting]]:
    """
    Inventory scope для ``shop_id``: join AdvSetting → WBCabinet.

    Evidence (task §1.1):
    - ``WBCabinet.shop_id == shop_id``
    - ``AdvSetting.active_status != 'done'``
    - **без** ``AdvSetting.bot_active.is_(True)`` (в отличие от
      ``snapshot_data_updater.providers.postgres_provider`` warmup filter)
    - Форма запроса согласована с
      ``WBShopDataManager.__get_advs(..., only_bot_active=False)`` без вызова
      ``WBShopDataManager``.
    """
    return (
        select(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .where(
            WBCabinet.shop_id == shop_id,
            AdvSetting.active_status != "done",
        )
    )


def select_search_advs_by_adv_ids(search_adv_ids: set[int]) -> Select[tuple[AdvSetting]]:
    """Второй hop: search AdvSetting по ``adv_id`` (как ``__get_adv_id_to_search_adv_map``)."""
    return select(AdvSetting).where(AdvSetting.adv_id.in_(search_adv_ids))

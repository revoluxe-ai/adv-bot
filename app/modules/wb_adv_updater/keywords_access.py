"""Точки входа для keywords: Redis (shop-runner) vs пересчёт из БД (UI, warmup).

Shop-runner и фоновые корутины — только ``fetch_calculated_keywords_from_redis`` (miss → ошибка).
Telegram UI и ручной просмотр — ``fetch_keywords_from_database`` (CH/PG через
``get_good_bad_phrases``), без чтения Redis-кеша.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
        ComplexAdv,
    )
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
        CalculatedKeyword,
    )


async def fetch_keywords_from_database(
    complex_adv: ComplexAdv,
) -> list[CalculatedKeyword]:
    """Пересчёт keywords из ClickHouse/Postgres; обновляет Redis hash как побочный эффект.

    Использовать в bot UI и там, где нужны актуальные данные «сейчас», а не снимок кеша.
  """
    from app.modules.wb_adv_updater.phrases_processor import get_good_bad_phrases

    return await get_good_bad_phrases(complex_adv)

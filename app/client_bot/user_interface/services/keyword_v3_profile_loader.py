"""Загрузка профиля ставок CH для карточки ключа V3 в Telegram."""

from __future__ import annotations

import logging
from typing import cast

from sqlalchemy import select

from app.client_bot.user_interface.views.keyword_v3_profile_ui import KeywordV3ProfileData
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.di.wb_manager_hub import WBManagerHubFactory
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    load_v3_bid_profiles,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    profile_points_from_bid_positions,
    resolve_keyword_bid_profile,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


async def _build_complex_adv(adv_setting: AdvSetting) -> ComplexAdv:
    """Собрать ``ComplexAdv`` для одной кампании (как в ``get_keywords_for_keyboard``)."""
    search_adv = None
    search_adv_id = adv_setting.search_adv_id
    if search_adv_id:
        stmt = select(AdvSetting).where(AdvSetting.adv_id == search_adv_id)
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            search_adv = result.scalar_one_or_none()
    return ComplexAdv(
        adv_setting=adv_setting,
        search_adv=search_adv,
        shop_id=adv_setting.wb_cabinet.shop_id,
    )


async def load_keyword_v3_profile_data(
    adv_setting: AdvSetting,
    calculated_keyword: CalculatedKeyword,
) -> KeywordV3ProfileData | None:
    """Профиль лестницы для одного ключа: CH bid curve + ``build_mode_candidates``.

    Returns:
        Данные для UI или ``None``, если WB/CH контекст недоступен.
    """
    complex_adv = await _build_complex_adv(adv_setting)
    shop_id = adv_setting.wb_cabinet.shop_id
    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            factory = cast(
                WBManagerHubFactory,
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory(),  # pyright: ignore
            )
            hub = factory.get_wb_manager_hub(shop_id)
            wb_shop_data_manager = WBShopDataManager(
                wb_cabinet=adv_setting.wb_cabinet,
                tasks_manager=TasksManager(max_workers=1),
                wb_api_data_manager=hub.wb_data_manager,
                wb_manager=hub.wb_manager,
            )
            _dto, raw_profiles = await load_v3_bid_profiles(
                complex_adv,
                wb_shop_data_manager=wb_shop_data_manager,
            )
    except Exception:
        logger.exception(
            "v3 keyword profile load failed adv_id=%s keyword=%s",
            adv_setting.adv_id,
            calculated_keyword.text,
        )
        return None

    bids = resolve_keyword_bid_profile(raw_profiles, calculated_keyword.text)
    if not bids:
        return None

    profile_points = profile_points_from_bid_positions(bids)
    candidates = build_mode_candidates(
        profile=profile_points,
        keyword_text=calculated_keyword.text,
        conv_views_to_orders=calculated_keyword.conv_views_to_orders,
    )

    predictor = build_predict_keywords_target_place()
    target_by_mode: dict[KeywordStrategyMode, int | None] = {}
    for mode in (
        KeywordStrategyMode.MIN_CPA,
        KeywordStrategyMode.OPTIMUM,
        KeywordStrategyMode.MAX_CONVERSION,
    ):
        try:
            target_by_mode[mode] = predictor.get_target_position_for_strategy_mode(
                bids, mode
            )
        except NotImplementedError:
            target_by_mode[mode] = None

    return KeywordV3ProfileData(
        current_mode=calculated_keyword.strategy_mode,
        candidates=candidates,
        raw_bid_positions=bids,
        target_positions_by_mode=target_by_mode,
    )

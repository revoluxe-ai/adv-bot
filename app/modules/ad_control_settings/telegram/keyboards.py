"""Inline-клавиатуры Advertising Control."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.user_interface.views.callbacks import Shop, Action
from app.modules.ad_control_settings.domain.enums import AdControlFeatureId
from app.modules.ad_control_settings.domain.registry import FEATURE_REGISTRY
from app.modules.ad_control_settings.telegram.callbacks import (
    AdcCamp,
    AdcCampPage,
    AdcFeat,
    AdcPrev,
    AdcShop,
)
from app.modules.ad_control_settings.telegram.inventory import (
    CampaignListItem,
    PAGE_SIZE,
)
from app.modules.ad_control_settings.ui.labels import CODE_BY_FEATURE, feature_label


def shop_keyboard(cabinet_id: int) -> InlineKeyboardMarkup:
    """Обзор магазина: список кампаний и возврат в меню магазина."""
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Кампании",
            callback_data=AdcCampPage(cab=cabinet_id, pg=1).pack(),
        )
    )
    _ = builder.row(
        InlineKeyboardButton(
            text="Обновить",
            callback_data=AdcShop(cab=cabinet_id).pack(),
        )
    )
    _ = builder.row(
        InlineKeyboardButton(
            text="В магазин",
            callback_data=Shop(
                action=Action.select,
                wb_user_cabinet_original_id=cabinet_id,
            ).pack(),
        )
    )
    return builder.as_markup()


def campaign_list_keyboard(
    *,
    cabinet_id: int,
    page: int,
    pages: int,
    items: tuple[CampaignListItem, ...],
) -> InlineKeyboardMarkup:
    """Кнопки advert_id и листание страниц."""
    builder = InlineKeyboardBuilder()
    for item in items[:PAGE_SIZE]:
        _ = builder.row(
            InlineKeyboardButton(
                text=f"adv {item.advert_id}",
                callback_data=AdcCamp(
                    cab=cabinet_id,
                    aid=item.advert_id,
                    pg=page,
                ).pack(),
            )
        )
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="◀",
                callback_data=AdcCampPage(cab=cabinet_id, pg=page - 1).pack(),
            )
        )
    if page < pages:
        nav.append(
            InlineKeyboardButton(
                text="▶",
                callback_data=AdcCampPage(cab=cabinet_id, pg=page + 1).pack(),
            )
        )
    if nav:
        _ = builder.row(*nav)
    _ = builder.row(
        InlineKeyboardButton(
            text="К обзору",
            callback_data=AdcShop(cab=cabinet_id).pack(),
        )
    )
    return builder.as_markup()


def campaign_detail_keyboard(
    *,
    cabinet_id: int,
    advert_id: int,
    page: int,
) -> InlineKeyboardMarkup:
    """Пять feature и возврат к списку."""
    builder = InlineKeyboardBuilder()
    for feature_id in FEATURE_REGISTRY:
        code = CODE_BY_FEATURE[feature_id]
        _ = builder.row(
            InlineKeyboardButton(
                text=feature_label(feature_id),
                callback_data=AdcFeat(
                    cab=cabinet_id,
                    aid=advert_id,
                    f=code,
                    pg=page,
                ).pack(),
            )
        )
    _ = builder.row(
        InlineKeyboardButton(
            text="К списку",
            callback_data=AdcCampPage(cab=cabinet_id, pg=page).pack(),
        )
    )
    return builder.as_markup()


def feature_keyboard(
    *,
    cabinet_id: int,
    advert_id: int,
    feature_id: AdControlFeatureId,
    page: int,
) -> InlineKeyboardMarkup:
    """Три preview и возврат к кампании. Кнопки Apply нет."""
    code = CODE_BY_FEATURE[feature_id]
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Просмотр: отключить",
            callback_data=AdcPrev(
                cab=cabinet_id,
                aid=advert_id,
                f=code,
                op="dis",
                pg=page,
            ).pack(),
        )
    )
    _ = builder.row(
        InlineKeyboardButton(
            text="Просмотр: наследование",
            callback_data=AdcPrev(
                cab=cabinet_id,
                aid=advert_id,
                f=code,
                op="clr",
                pg=page,
            ).pack(),
        )
    )
    _ = builder.row(
        InlineKeyboardButton(
            text="Просмотр: OVERRIDE с shop",
            callback_data=AdcPrev(
                cab=cabinet_id,
                aid=advert_id,
                f=code,
                op="ovr",
                pg=page,
            ).pack(),
        )
    )
    _ = builder.row(
        InlineKeyboardButton(
            text="К кампании",
            callback_data=AdcCamp(
                cab=cabinet_id,
                aid=advert_id,
                pg=page,
            ).pack(),
        )
    )
    return builder.as_markup()


def preview_keyboard(
    *,
    cabinet_id: int,
    advert_id: int,
    feature_code: str,
    page: int,
) -> InlineKeyboardMarkup:
    """После preview — только назад к feature."""
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Назад к feature",
            callback_data=AdcFeat(
                cab=cabinet_id,
                aid=advert_id,
                f=feature_code,
                pg=page,
            ).pack(),
        )
    )
    return builder.as_markup()

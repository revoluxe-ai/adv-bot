"""
Хендлеры Advertising Control.

Читают configured slots и показывают dry-run. Репозиторий на запись не вызывается.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.persistence.repository import (
    AdControlSettingsRepository,
)
from app.modules.ad_control_settings.telegram.access import load_owned_cabinet
from app.modules.ad_control_settings.telegram.callbacks import (
    AdcCamp,
    AdcCampPage,
    AdcFeat,
    AdcPrev,
    AdcShop,
)
from app.modules.ad_control_settings.telegram.context import build_settings_context
from app.modules.ad_control_settings.telegram.inventory import (
    load_campaign_label,
    load_campaign_page,
)
from app.modules.ad_control_settings.telegram.keyboards import (
    campaign_detail_keyboard,
    campaign_list_keyboard,
    feature_keyboard,
    preview_keyboard,
    shop_keyboard,
)
from app.modules.ad_control_settings.telegram.snapshots import load_dry_run_snapshots
from app.modules.ad_control_settings.ui.dry_run_preview import (
    preview_clear_to_inherit,
    preview_disable,
    preview_override_from_shop_payload,
)
from app.modules.ad_control_settings.ui.format import (
    format_campaign_detail,
    format_campaign_list,
    format_dry_run,
    format_feature_detail,
    format_shop_screen,
)
from app.modules.ad_control_settings.ui.labels import feature_from_code
from app.modules.ad_control_settings.ui.view_models import (
    FeatureControlLine,
    describe_campaign_features,
    describe_shop_features,
    summarize_campaign_modes,
)
from app.utils.db.session_maker import get_async_session_maker as sm

router = Router(name="ad_control_telegram")


async def _show(
    callback: CallbackQuery,
    text: str,
    markup: InlineKeyboardMarkup,
) -> None:
    message = callback.message
    if not isinstance(message, Message):
        _ = await callback.answer("Сообщение недоступно", show_alert=True)
        return
    _ = await message.edit_text(text, reply_markup=markup)
    _ = await callback.answer()


@router.callback_query(AdcShop.filter())
async def open_shop(callback: CallbackQuery, callback_data: AdcShop) -> None:
    """Обзор configured-настроек магазина."""
    user = callback.from_user
    async with sm(read_only=True) as session:
        cabinet = await load_owned_cabinet(
            session,
            wb_user_cabinet_id=callback_data.cab,
            telegram_user_id=user.id,
        )
        if cabinet is None:
            _ = await callback.answer("Нет доступа к магазину", show_alert=True)
            return
        shop_id = cabinet.wb_cabinet.shop_id
        if not shop_id:
            await _show(
                callback,
                "Рекламный контроль\nshop_id кабинета не задан. Экран закрыт.",
                shop_keyboard(callback_data.cab),
            )
            return
        repository = AdControlSettingsRepository(session)
        slots = await repository.load_shop_slots(shop_id)
    lines = describe_shop_features(slots)
    await _show(
        callback,
        format_shop_screen(shop_id=shop_id, lines=lines),
        shop_keyboard(callback_data.cab),
    )


@router.callback_query(AdcCampPage.filter())
async def open_campaign_page(
    callback: CallbackQuery,
    callback_data: AdcCampPage,
) -> None:
    """Страница кампаний кабинета."""
    user = callback.from_user
    async with sm(read_only=True) as session:
        cabinet = await load_owned_cabinet(
            session,
            wb_user_cabinet_id=callback_data.cab,
            telegram_user_id=user.id,
        )
        if cabinet is None:
            _ = await callback.answer("Нет доступа к магазину", show_alert=True)
            return
        shop_id = cabinet.wb_cabinet.shop_id or ""
        page = await load_campaign_page(
            session,
            wb_cabinet_id=cabinet.wb_cabinet.id,
            page=callback_data.pg,
        )
        mode_by_advert: dict[int, str] = {}
        if shop_id:
            repository = AdControlSettingsRepository(session)
            for item in page.items:
                slots = await repository.load_campaign_slots(
                    CampaignRef(shop_id=shop_id, advert_id=item.advert_id)
                )
                mode_by_advert[item.advert_id] = summarize_campaign_modes(slots)
    rows = tuple(
        (
            item.advert_id,
            item.name,
            mode_by_advert.get(item.advert_id, ""),
        )
        for item in page.items
    )
    await _show(
        callback,
        format_campaign_list(
            shop_id=shop_id or "—",
            page=page.page,
            pages=page.pages,
            rows=rows,
        ),
        campaign_list_keyboard(
            cabinet_id=callback_data.cab,
            page=page.page,
            pages=page.pages,
            items=page.items,
        ),
    )


@router.callback_query(AdcCamp.filter())
async def open_campaign(callback: CallbackQuery, callback_data: AdcCamp) -> None:
    """Карточка кампании по advert_id."""
    loaded = await _load_campaign_view(callback, callback_data.cab, callback_data.aid)
    if loaded is None:
        return
    shop_id, name, lines = loaded
    await _show(
        callback,
        format_campaign_detail(
            shop_id=shop_id,
            advert_id=callback_data.aid,
            name=name,
            lines=lines,
        ),
        campaign_detail_keyboard(
            cabinet_id=callback_data.cab,
            advert_id=callback_data.aid,
            page=1,
        ),
    )


@router.callback_query(AdcFeat.filter())
async def open_feature(callback: CallbackQuery, callback_data: AdcFeat) -> None:
    """Одна feature. Неизвестный код — fail closed."""
    feature_id = feature_from_code(callback_data.f)
    if feature_id is None:
        _ = await callback.answer("UNKNOWN_FEATURE", show_alert=True)
        return
    loaded = await _load_campaign_view(callback, callback_data.cab, callback_data.aid)
    if loaded is None:
        return
    _shop_id, _name, lines = loaded
    line = next(item for item in lines if item.feature_id == feature_id)
    await _show(
        callback,
        format_feature_detail(line, advert_id=callback_data.aid),
        feature_keyboard(
            cabinet_id=callback_data.cab,
            advert_id=callback_data.aid,
            feature_id=feature_id,
        ),
    )


@router.callback_query(AdcPrev.filter(F.op.in_({"dis", "clr", "ovr"})))
async def open_preview(callback: CallbackQuery, callback_data: AdcPrev) -> None:
    """Dry-run disable / clear / override. Запись не выполняется."""
    feature_id = feature_from_code(callback_data.f)
    if feature_id is None:
        _ = await callback.answer("UNKNOWN_FEATURE", show_alert=True)
        return
    user = callback.from_user
    async with sm(read_only=True) as session:
        cabinet = await load_owned_cabinet(
            session,
            wb_user_cabinet_id=callback_data.cab,
            telegram_user_id=user.id,
        )
        if cabinet is None:
            _ = await callback.answer("Нет доступа к магазину", show_alert=True)
            return
        shop_id = cabinet.wb_cabinet.shop_id
        if not shop_id:
            _ = await callback.answer("shop_id не задан", show_alert=True)
            return
        label = await load_campaign_label(
            session,
            wb_cabinet_id=cabinet.wb_cabinet.id,
            advert_id=callback_data.aid,
        )
        if label is None:
            _ = await callback.answer("Кампания не найдена", show_alert=True)
            return
        repository = AdControlSettingsRepository(session)
        campaign = CampaignRef(shop_id=shop_id, advert_id=callback_data.aid)
        shop_slots = await repository.load_shop_slots(shop_id)
        shop_snapshots, campaign_snapshots = await load_dry_run_snapshots(
            repository,
            campaign,
        )
    snap = campaign_snapshots.get((shop_id, callback_data.aid, feature_id))
    expected_revision = None if snap is None else snap.revision
    if callback_data.op == "clr":
        preview = preview_clear_to_inherit(
            shop_id=shop_id,
            advert_id=callback_data.aid,
            feature_id=feature_id,
            expected_revision=expected_revision,
            shop_snapshots=shop_snapshots,
            campaign_snapshots=campaign_snapshots,
        )
    elif callback_data.op == "dis":
        preview = preview_disable(
            shop_id=shop_id,
            advert_id=callback_data.aid,
            feature_id=feature_id,
            expected_revision=expected_revision,
            shop_snapshots=shop_snapshots,
            campaign_snapshots=campaign_snapshots,
        )
    else:
        shop_slot = shop_slots.get(feature_id)
        preview = preview_override_from_shop_payload(
            shop_id=shop_id,
            advert_id=callback_data.aid,
            feature_id=feature_id,
            expected_revision=expected_revision,
            shop_payload=None if shop_slot is None else shop_slot.payload,
            shop_snapshots=shop_snapshots,
            campaign_snapshots=campaign_snapshots,
        )
    await _show(
        callback,
        format_dry_run(preview),
        preview_keyboard(
            cabinet_id=callback_data.cab,
            advert_id=callback_data.aid,
            feature_code=callback_data.f,
        ),
    )


@router.callback_query(AdcPrev.filter())
async def reject_unknown_preview(
    callback: CallbackQuery,
    callback_data: AdcPrev,
) -> None:
    """Неизвестная операция preview не собирает ChangeSet."""
    _ = callback_data
    _ = await callback.answer("UNSUPPORTED_OPERATION", show_alert=True)


async def _load_campaign_view(
    callback: CallbackQuery,
    cabinet_id: int,
    advert_id: int,
) -> tuple[str, str, tuple[FeatureControlLine, ...]] | None:
    user = callback.from_user
    async with sm(read_only=True) as session:
        cabinet = await load_owned_cabinet(
            session,
            wb_user_cabinet_id=cabinet_id,
            telegram_user_id=user.id,
        )
        if cabinet is None:
            _ = await callback.answer("Нет доступа к магазину", show_alert=True)
            return None
        shop_id = cabinet.wb_cabinet.shop_id
        if not shop_id:
            _ = await callback.answer("shop_id не задан", show_alert=True)
            return None
        label = await load_campaign_label(
            session,
            wb_cabinet_id=cabinet.wb_cabinet.id,
            advert_id=advert_id,
        )
        if label is None:
            _ = await callback.answer("Кампания не найдена", show_alert=True)
            return None
        repository = AdControlSettingsRepository(session)
        shop_slots = await repository.load_shop_slots(shop_id)
        campaign_slots = await repository.load_campaign_slots(
            CampaignRef(shop_id=shop_id, advert_id=advert_id)
        )
    context = build_settings_context(
        shop_id=shop_id,
        advert_id=advert_id,
        shop_features=shop_slots,
        campaign_features=campaign_slots,
    )
    return shop_id, label, describe_campaign_features(context)


"""Клавиатура главного меню настроек кампании."""

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.ui_access import UiAccessMode
from app.client_bot.user_interface.views import callbacks
from .v3_rollout_aggressiveness_ui import v3_rollout_aggressiveness_main_button
from .v3_calibration_step_ui import v3_calibration_step_main_button
from .v3_tick_report_button import v3_tick_report_main_button
from app.client_bot.user_interface.views.callbacks import (
    IncrementalStatsToggle,
    OrdersSourceToggle,
    SalesPredictMethodToggle,
    ChangeAutoAddOnlyRelevantPhraseStatus,
    ManageRelevantAndNonRelevantPhrases,
    ChangeCommonBidInSearchAdvStatus,
    SetCommonBidManual,
    IndividualKeywordsTargetPlaceToggle,
    RebindAdvCampaignIds,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.enums import (
    OrdersSourceForAutoMode,
)
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import (
    BidderCoroutineType,
)

from app.modules.white_list_mode_settings.telegram.main_callback import (
    WhiteListModeMenu,
)
from app.client_bot.user_interface.handlers.bidder_coroutine_type_toggle.callbacks import (
    BidderCoroutineTypeToggle,
)
from app.client_bot.user_interface.handlers.time_settings.callbacks import TS
from app.modules.shop_runner.service_manager.old_modules.auto_updater_target_place.telegram.callbacks import (
    AutoUpdateTargetPlaceSetting as AutoUpdateTargetPlaceSettingCallBack,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldMenu,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    card_ab_hold_status_label,
    is_card_ab_hold_ui_visible,
)
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker


def get_relevant_phrase_management_keyboard(adv_setting: AdvSetting):
    """Собрать клавиатуру подменю управления релевантными и нерелевантными фразами."""
    builder = InlineKeyboardBuilder()

    if adv_setting.auto_add_only_relevant_phrase:
        toggle_text = "Выключить добавление только релевантных фраз"
        toggle_new_status = False
        middle_text = "Добавить РЕЛЕВАНТНЫЕ фразы"
        middle_callback = callbacks.AddRelevantPhrases(
            adv_setting_id=adv_setting.id
        ).pack()
        templates_text = "Шаблоны релевантных фраз"
        templates_callback = callbacks.AddRelevantPhraseTemplates(
            adv_setting_id=adv_setting.id
        ).pack()
    else:
        toggle_text = "Включить добавление только релевантных фраз"
        toggle_new_status = True
        middle_text = "Добавить НЕРЕЛЕВАНТНЫЕ фразы"
        middle_callback = callbacks.AddBlackPhrasesTemplates(
            adv_setting_id=adv_setting.id
        ).pack()
        templates_text = "Шаблоны нерелевантных фраз"
        templates_callback = callbacks.AddBlackPhrasesTemplates(
            adv_setting_id=adv_setting.id
        ).pack()

    builder.row(
        InlineKeyboardButton(
            text=toggle_text,
            callback_data=ChangeAutoAddOnlyRelevantPhraseStatus(
                adv_id=adv_setting.adv_id,
                wb_user_cabinet_original_id=0,
                new_status=toggle_new_status,
            ).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=middle_text,
            callback_data=middle_callback,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=templates_text,
            callback_data=templates_callback,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Назад в меню",
            callback_data=callbacks.Adv(adv_original_id=adv_setting.id).pack(),
        )
    )
    return builder.as_markup()


def get_adv_setting_keyboard(
    wb_user_cabinet: WBUserCabinet,
    adv_setting: AdvSetting,
    in_favorites: bool,
    ui_access: UiAccessMode = UiAccessMode.PAID,
):
    """Собрать inline-клавиатуру главного меню настроек кампании."""
    builder = InlineKeyboardBuilder()
    is_paid_access = ui_access == UiAccessMode.PAID

    auto_button_text = (
        "🟢 Автоуправление включено"
        if adv_setting.bot_active
        else "🔴 Автоуправление выключено / подключить"
    )
    _ = builder.row(
        InlineKeyboardButton(
            text=auto_button_text,
            callback_data=callbacks.AutoManagementLanding(
                action="open",
                adv_setting_original_id=adv_setting.id,
                wb_user_cabinet_original_id=wb_user_cabinet.id,
            ).pack(),
        )
    )

    minus_phrases_enabled = bool(
        getattr(adv_setting, "auto_update_minus_phrases", False)
    )
    minus_phrases_button_text = (
        "🟢 Обновление минус-фраз: включено"
        if minus_phrases_enabled
        else "🔴 Обновление минус-фраз: выключено"
    )
    _ = builder.row(
        InlineKeyboardButton(
            text=minus_phrases_button_text,
            callback_data=callbacks.MinusPhrasesSetting(
                action="open",
                adv_setting_original_id=adv_setting.id,
                wb_user_cabinet_original_id=wb_user_cabinet.id,
            ).pack(),
        )
    )

    """План продаж"""
    from .buttoms import sales_plan_button
    _ = builder.row(
        sales_plan_button.get(adv_setting)
    )



    _ = builder.row(
        InlineKeyboardButton(
            text="➡ Контроль ключевых слов по кампании",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="by_adv"
            ).pack(),
        )
    )

    button = InlineKeyboardButton(
        text="Анализ Динамики Ранжирования",
        callback_data=callbacks.RaiseCardAnalyze(
            adv_setting_original_id=adv_setting.id,
            action="menu",
        ).pack(),
    )
    _ = builder.row(button)

    """Рекомендательные системы (настройка)"""
    from .buttoms import rec_system_button
    if is_paid_access:
        rec_bottom = rec_system_button.get(adv_setting, wb_user_cabinet)
        _ = builder.row(rec_bottom)

    # TODO: Из free удалить все не не релевантных фраз, это только автомат
    # TODO: сделать для free отдельное описание Рел не рел Фраз

    relevant_button = InlineKeyboardButton(
        text="Управление релевантными и нерелевантными фразами",
        callback_data=ManageRelevantAndNonRelevantPhrases(
            adv_setting_original_id=adv_setting.id  # type:ignore
        ).pack(),
    )
    _ = builder.row(relevant_button)

    indiv_place_mode = bool(adv_setting.individual_keywords_target_place_mode)
    if indiv_place_mode:
        indiv_place_text = "Выключить индивид. места запросов"
    else:
        indiv_place_text = "$ Включить индивид. места запросов (платно, см. тарифы)"
    indiv_place_callback = IndividualKeywordsTargetPlaceToggle(
        adv_id=adv_setting.adv_id, new_status=not indiv_place_mode
    ).pack()
    if is_paid_access:
        _ = builder.row(
            InlineKeyboardButton(
                text=indiv_place_text,
                callback_data=indiv_place_callback,
            )
        )
    white_list_button = InlineKeyboardButton(
        text="Режимы Управления Белым Списком",
        callback_data=WhiteListModeMenu(adv_id=adv_setting.adv_id).pack(),
    )
    _ = builder.row(white_list_button)
    incremental_stats_text = (
        "Включить инкрементальную статистику ПП"
        if not adv_setting.use_incremental_stats
        else "Выключить инкрементальную статистику ПП"
    )
    incremental_stats_callback = IncrementalStatsToggle(
        adv_setting_original_id=adv_setting.id,
        new_status=not bool(adv_setting.use_incremental_stats),
    ).pack()
    _ = builder.row(
        InlineKeyboardButton(
            text=incremental_stats_text,
            callback_data=incremental_stats_callback,
        )
    )

    common_bid_active = bool(
        adv_setting.updater_common_bid_in_search_adv_active_status
    )
    common_bid_text = (
        "Выключить управление общей ставкой в Аукционе"
        if common_bid_active
        else "Включить управление общей ставкой в Аукционе"
    )
    common_bid_callback = ChangeCommonBidInSearchAdvStatus(
        adv_id=adv_setting.adv_id, new_status=not common_bid_active
    ).pack()
    if is_paid_access:
        _ = builder.row(
            InlineKeyboardButton(text=common_bid_text, callback_data=common_bid_callback)
        )



    activity_callback = callbacks.ManageCampaignActivity(
        action="menu", adv_setting_original_id=adv_setting.id
    ).pack()
    _ = builder.row(
        InlineKeyboardButton(
            text="Управление активностью РК",
            callback_data=activity_callback,
        )
    )
    # Ограничения по времени настраиваются для любой РК; применяются только при
    # включённом «Контроле активности кампании» (см. AutoAdvActiveControlService).
    _ = builder.row(
        InlineKeyboardButton(
            text="⏰ Ограничения показов по времени",
            callback_data=TS(a="open", adv=adv_setting.id).pack(),
        )
    )
    if is_paid_access:
        _ = builder.row(
            InlineKeyboardButton(
                text="Стратегия РК",
                callback_data=callbacks.StrategyMenu(
                    action="open",
                    adv_setting_original_id=adv_setting.id,
                ).pack(),
            )
        )

    button = InlineKeyboardButton(
        text="Управление ставкой",
        callback_data=callbacks.CPMSettingMenu(
            action="to_cpm_setting_page", adv_original_id=adv_setting.id
        ).pack(),
    )
    _ = builder.row(button)
    if is_paid_access:
        _ = builder.row(
            InlineKeyboardButton(
                text="Управление ставкой в полках",
                callback_data=callbacks.AutoShelfBidControlMenu(
                    action="open",
                    adv_setting_original_id=adv_setting.id,
                ).pack(),
            )
        )

    if is_paid_access:
        _ = builder.row(
            InlineKeyboardButton(
                text="Перепривязать кампании WB",
                callback_data=RebindAdvCampaignIds(
                    action="menu",
                    adv_setting_original_id=adv_setting.id,
                    wb_user_cabinet_original_id=wb_user_cabinet.id,
                ).pack(),
            )
        )

    watchdog_enabled = getattr(adv_setting, "auto_budget_watchdog_enabled", False)
    watchdog_button = InlineKeyboardButton(
        text=(
            "Выключить контроль активности кампании"
            if watchdog_enabled
            else "Включить контроль активности кампании"
        ),
        callback_data=callbacks.AutoBudgetWatchdogToggle(
            adv_setting_original_id=adv_setting.id,
            new_status=not watchdog_enabled,
        ).pack(),
    )
    if is_paid_access:
        _ = builder.row(watchdog_button)

    # Кнопка для применения дефолтных настроек
    if adv_setting.bot_active and is_paid_access:
        button = InlineKeyboardButton(
            text="Применить дефолтные настройки",
            callback_data=callbacks.ApplyCampaignDefaults(
                adv_setting_original_id=adv_setting.id,
                wb_user_cabinet_original_id=wb_user_cabinet.id,
            ).pack(),
        )
        _ = builder.row(button)

    if adv_setting.bidder_coroutine_type == BidderCoroutineType.OLD_UPDATE_CPM_BIDDER:
        bidder_text = "Переключить на кластерный биддер"
        new_bidder_type = BidderCoroutineType.UPDATE_CLUSTER_BIDS
    else:
        bidder_text = "Переключить на стандартный биддер (CPM)"
        new_bidder_type = BidderCoroutineType.OLD_UPDATE_CPM_BIDDER

    if is_paid_access:
        bidder_callback = BidderCoroutineTypeToggle(
            new_type=new_bidder_type.value,
            adv_setting_original_id=adv_setting.id,
        ).pack()
        bidder_button = InlineKeyboardButton(
            text=bidder_text, callback_data=bidder_callback
        )
        _ = builder.row(bidder_button)

    if adv_setting.auto_update_target_place:
        text = "$ Выключить автоуправление целевой позицией"
        new_status = False
    else:
        text = "Включить автоуправление целевой позицией (платно, см. тарифы)"
        new_status = True

    callback = AutoUpdateTargetPlaceSettingCallBack(
        new_status=new_status, adv_setting_original_id=adv_setting.id
    ).pack()
    if is_paid_access:
        button = InlineKeyboardButton(text=text, callback_data=callback)
        _ = builder.row(button)

    # Добавляем кнопку переключения источника заказов для автоуправления
    if adv_setting.orders_source_for_auto_mode == OrdersSourceForAutoMode.ADV_SUM:
        text = "Переключить на общую статистику заказов"
        new_source = (
            OrdersSourceForAutoMode.COMMON_STATISTIC.value
        )  # Use .value for string
    else:
        text = "Переключить на заказы только из рекламы"
        new_source = OrdersSourceForAutoMode.ADV_SUM.value  # Use .value for string

    callback = OrdersSourceToggle(
        new_source=new_source, adv_setting_original_id=adv_setting.id  # type:ignore
    ).pack()
    if is_paid_access:
        button = InlineKeyboardButton(text=text, callback_data=callback)
        _ = builder.row(button)

    # Кнопка переключения метода прогноза продаж (сразу под источником заказов)
    if adv_setting.sales_predict_method == FactMethods.DIRECT_SALES:
        text = "Переключить на прогноз продаж по корзинам"
        new_method = FactMethods.BY_CARTS
    else:
        text = "Переключить на прямой прогноз продаж"
        new_method = FactMethods.DIRECT_SALES

    callback = SalesPredictMethodToggle(
        new_method=new_method, adv_setting_original_id=adv_setting.id
    ).pack()
    if is_paid_access:
        button = InlineKeyboardButton(text=text, callback_data=callback)
        _ = builder.row(button)

    # V3-only runtime (D3): no version-toggle UI; v3 controls when bot_active.
    if adv_setting.bot_active and is_paid_access:
        _ = builder.row(v3_tick_report_main_button(adv_setting))
        _ = builder.row(v3_calibration_step_main_button(adv_setting))
        _ = builder.row(v3_rollout_aggressiveness_main_button(adv_setting))

    if is_card_ab_hold_ui_visible(adv_setting):
        _ = builder.row(
            InlineKeyboardButton(
                text=card_ab_hold_status_label(adv_setting),
                callback_data=CardAbHoldMenu(
                    adv_setting_original_id=adv_setting.id
                ).pack(),
            )
        )

    button = InlineKeyboardButton(
        text="Шаблоны не релевантных фраз",
        callback_data=callbacks.AddBlackPhrasesTemplates(
            adv_setting_id=adv_setting.id
        ).pack(),
    )
    _ = builder.row(button)

    _ = builder.row(
        InlineKeyboardButton(
            text="Шаблоны релевантных фраз",
            callback_data=callbacks.AddRelevantPhraseTemplates(
                adv_setting_id=adv_setting.id
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="Добавить фразы в продвижение (Белый список)",
            callback_data=callbacks.AddWhitePhrases(
                adv_setting_id=adv_setting.id
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="Добавить в фикс.фразы (всегда вкл)",
            callback_data=callbacks.AddFixedPhrases(
                adv_setting_id=adv_setting.id
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="Добавить РЕЛЕВАНТНЫЕ фразы",
            callback_data=callbacks.AddRelevantPhrases(
                adv_setting_id=adv_setting.id
            ).pack(),
        )
    )

    button = InlineKeyboardButton(
        text="Выгрузить ключи в csv-файл",
        callback_data=callbacks.DownloadCSV(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )

    _ = builder.row(button)

    button = InlineKeyboardButton(
        text="История позиций ключевых слов",
        callback_data=callbacks.KeywordPositionHistory(
            adv_original_id=adv_setting.id
        ).pack(),
    )
    _ = builder.row(button)


    button = InlineKeyboardButton(
        text="Изменить ставку в Авто",
        callback_data=callbacks.ChangeAutoBid(
            action="open", adv_original_id=adv_setting.id
        ).pack(),
    )
    _ = builder.row(button)

    if adv_setting.search_adv_id:
        set_common_bid_callback = SetCommonBidManual(
            adv_setting_original_id=adv_setting.id,
            wb_user_cabinet_original_id=wb_user_cabinet.id,
        ).pack()
        _ = builder.row(
            InlineKeyboardButton(
                text="Поставить общую ставку для Поисковой РК",
                callback_data=set_common_bid_callback,
            )
        )

    button = InlineKeyboardButton(
        text="Сбросить белый список",
        callback_data=callbacks.ResetWhiteList(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )
    _ = builder.row(button)

    button = InlineKeyboardButton(
        text="Сбросить все нерелевантные фразы",
        callback_data=callbacks.ResetNonRelevantPhrases(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )
    _ = builder.row(button)

    wb_user_cabinet_original_id = wb_user_cabinet.id
    _ = builder.row(
        InlineKeyboardButton(
            text="Вернуться к списку кампаний",
            callback_data=callbacks.ChoiceAdvPaginator(
                wb_user_cabinet_original_id=wb_user_cabinet_original_id, page=1
            ).pack(),
        )
    )

    return builder.as_markup()

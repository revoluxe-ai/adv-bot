
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import (
    IncrementalStatsToggle,
    TurnBot,
    OrdersSourceToggle,
    PredictCTRModeToggle,
    SalesPredictMethodToggle,
    AutoUpdaterVersionToggle,
    ChangeAutoAddOnlyRelevantPhraseStatus,
    ChangeCommonBidInSearchAdvStatus,
    IndividualKeywordsTargetPlaceToggle,
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
    PredictCTRMode,
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
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater.telegram.callbacks import (
    AutoUpdateWhiteListSetting,
)
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker


def get_adv_setting_keyboard(
    wb_user_cabinet: WBUserCabinet,
    adv_setting: AdvSetting,
    in_favorites: bool,
):
    builder = InlineKeyboardBuilder()

    """План продаж"""
    from .buttoms import sales_plan_button
    _ = builder.row(sales_plan_button.get(adv_setting))

    button = InlineKeyboardButton(
        text="Анализ Изменения Ранжирования",
        callback_data=callbacks.RaiseCardAnalyze(
            adv_setting_original_id=adv_setting.id,
            action="menu",
        ).pack(),
    )
    _ = builder.row(button)

    button = InlineKeyboardButton(
        text="Задать/Изменить максимальную стоимость клика",
        callback_data=callbacks.ChangeMaxCPC(
            action="to_max_cpc_change_page", adv_original_id=adv_setting.id
        ).pack(),
    )

    _ = builder.row(button)


    _ = builder.row(
        InlineKeyboardButton(
            text="➡ Контроль ключевых слов по кампании",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="by_adv"
            ).pack(),
        )
    )

    """Рекомендательные системы (настройка)"""
    from .buttoms import rec_system_button
    rec_bottom = rec_system_button.get(adv_setting, wb_user_cabinet)
    _ = builder.row(rec_bottom)

    indiv_place_mode = bool(adv_setting.individual_keywords_target_place_mode)
    if indiv_place_mode:
        indiv_place_text = "Выключить индивид. места запросов"
    else:
        indiv_place_text = "$ Включить индивид. места запросов (платно, см. тарифы)"
    indiv_place_callback = IndividualKeywordsTargetPlaceToggle(
        adv_id=adv_setting.adv_id, new_status=not indiv_place_mode
    ).pack()
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
    _ = builder.row(watchdog_button)

    # Кнопка для применения дефолтных настроек
    if adv_setting.bot_active:
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

    bidder_callback = BidderCoroutineTypeToggle(
        new_type=new_bidder_type.value,
        adv_setting_original_id=adv_setting.id,
    ).pack()
    bidder_button = InlineKeyboardButton(
        text=bidder_text, callback_data=bidder_callback
    )
    _ = builder.row(bidder_button)

    if adv_setting.bot_active:
        _ = builder.row(
            InlineKeyboardButton(
                text="$ Выключить автоматическое управление",
                callback_data=TurnBot(
                    action="off",
                    adv_original_id=adv_setting.id,
                    wb_user_cabinet_original_id=wb_user_cabinet.id,
                ).pack(),
            )
        )

    else:
        _ = builder.row(
            InlineKeyboardButton(
                text="Включить автоматическое управление (платно, см. тарифы)",
                callback_data=TurnBot(
                    action="on",
                    adv_original_id=adv_setting.id,
                    wb_user_cabinet_original_id=wb_user_cabinet.id,
                ).pack(),
            )
        )

    if adv_setting.auto_update_white_list:
        text = "$ Выключить автообновление белого списка"
        new_status = False
    else:
        text = "Включить автообновление белого списка (платно, см. тарифы)"
        new_status = True

    callback = AutoUpdateWhiteListSetting(
        new_status=new_status, adv_setting_original_id=adv_setting.id
    ).pack()
    button = InlineKeyboardButton(text=text, callback_data=callback)
    _ = builder.row(button)

    if adv_setting.auto_update_target_place:
        text = "$ Выключить автоуправление целевой позицией"
        new_status = False
    else:
        text = "Включить автоуправление целевой позицией (платно, см. тарифы)"
        new_status = True

    callback = AutoUpdateTargetPlaceSettingCallBack(
        new_status=new_status, adv_setting_original_id=adv_setting.id
    ).pack()
    button = InlineKeyboardButton(text=text, callback_data=callback)
    _ = builder.row(button)

    if adv_setting.automatic_version == 2:
        # Кнопка для auto_add_only_relevant_phrase
        if adv_setting.auto_add_only_relevant_phrase:
            relevant_text = "Выключить добавление только релевантных фраз"
            relevant_new_status = False
        else:
            relevant_text = "Включить добавление только релевантных фраз"
            relevant_new_status = True

        relevant_callback = ChangeAutoAddOnlyRelevantPhraseStatus(
            adv_id=adv_setting.adv_id,
            wb_user_cabinet_original_id=wb_user_cabinet.id,
            new_status=relevant_new_status,
        ).pack()
        relevant_button = InlineKeyboardButton(
            text=relevant_text, callback_data=relevant_callback
        )
        _ = builder.row(relevant_button)


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
    button = InlineKeyboardButton(text=text, callback_data=callback)
    _ = builder.row(button)

    # Кнопка переключения версии АвтоАпдейтера
    if adv_setting.automatic_version == 1:
        text = "Переключить на АвтоАпдейтер V2"
        new_version = 2
    else:
        text = "Переключить на АвтоАпдейтер V1"
        new_version = 1

    callback = AutoUpdaterVersionToggle(
        new_version=new_version, adv_setting_original_id=adv_setting.id
    ).pack()
    button = InlineKeyboardButton(text=text, callback_data=callback)
    _ = builder.row(button)


    button = InlineKeyboardButton(
        text="Шаблоны не релевантных фраз",
        callback_data=callbacks.AddBlackPhrasesTemplates(
            adv_setting_id=adv_setting.id
        ).pack(),
    )
    _ = builder.row(button)

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


    if adv_setting.reset_place is not None and adv_setting.reset_place:
        button = InlineKeyboardButton(
            text="Выключить сброс позиций",
            callback_data=callbacks.ResetPlace(
                action="off", adv_setting_original_id=adv_setting.id
            ).pack(),
        )
    else:
        button = InlineKeyboardButton(
            text="Включить сброс позиций",
            callback_data=callbacks.ResetPlace(
                action="on", adv_setting_original_id=adv_setting.id
            ).pack(),
        )

    _ = builder.row(button)


    button = InlineKeyboardButton(
        text="Загрузить статистику из WB",
        callback_data=callbacks.WBUpdate(
            action="update_keyword_stat", adv_setting_original_id=adv_setting.id
        ).pack(),
    )
    _ = builder.row(button)

    button = InlineKeyboardButton(
        text="Обновить минус-слова",
        callback_data=callbacks.WBUpdate(
            action="update_minus_keywords", adv_setting_original_id=adv_setting.id
        ).pack(),
    )

    _ = builder.row(button)

    button = InlineKeyboardButton(
        text="Сбросить белый список",
        callback_data=callbacks.ResetWhiteList(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )
    _ = builder.row(button)

    if not in_favorites:
        button = InlineKeyboardButton(
            text="Добавить в избранное",
            callback_data=callbacks.AddToFavorites(
                adv_setting_original_id=adv_setting.id
            ).pack(),
        )
    else:
        button = InlineKeyboardButton(
            text="Удалить из избранного",
            callback_data=callbacks.RemoveFromFavorites(
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

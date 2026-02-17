import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot import const
from app.client_bot.const import AUTO_MODE, BLACK_LIST, TURN_OFF, WHITE_LIST
from app.client_bot.user_interface.utils import (
    format_target_place_display,
    get_effective_keyword_target_place,
)
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import (
    Action,
    CommonBudgetModeToggle,
    IncrementalStatsToggle,
    TurnBot,
    OrdersSourceToggle,
    PredictCTRModeToggle,
    SalesPredictMethodToggle,
    AutoUpdaterVersionToggle,
    ChangeAutoAddOnlyRelevantPhraseStatus,
    ChangeRecSystemModeStatus,
    ChangeCommonBidInSearchAdvStatus,
    IndividualKeywordsTargetPlaceToggle,
)
from app.modules.admin_user_balance.callbacks import AdminUserBalance
from app.modules.cabinet_bonus_manager.callbacks import AdminBonus
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import (
    BidderCoroutineType,
    PredictCTRMode,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.predict_ctr_exponent_settings import (
    ChangeExponentSettinginAdvSettingCallback,
)
from app.modules.hide_zero_views_toggle import ChangeHideZeroViewsStatus
from app.modules.sales_plan_settings.telegram.main_callback import (
    SalesPlanSettingsMenu as SalesPlanSettingsMenuCallback,
)
from app.modules.white_list_mode_settings.telegram.main_callback import (
    WhiteListModeMenu,
)
from app.client_bot.user_interface.handlers.bidder_coroutine_type_toggle.callbacks import (
    BidderCoroutineTypeToggle,
)
from app.modules.shop_runner.service_manager.old_modules.auto_updater_target_place.telegram.callbacks import (
    AutoUpdateTargetPlaceSetting as AutoUpdateTargetPlaceSettingCallBack,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater.telegram.callbacks import (
    AutoUpdateWhiteListSetting,
    RelevantKeywordStatusSetting,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from app.utils.db.session_maker import get_async_session_maker
from app.shared.domains.wb.enums import (
    AdvType,
)

sm = get_async_session_maker


def get_adv_setting_keyboard(
    wb_user_cabinet: WBUserCabinet,
    adv_setting: AdvSetting,
    in_favorites: bool,
):
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Контроль ключевых слов по кампании",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="by_adv"
            ).pack(),
        )
    )

    button = InlineKeyboardButton(
        text="План продаж",
        callback_data=SalesPlanSettingsMenuCallback(adv_id=adv_setting.adv_id).pack(),
    )

    _ = builder.row(button)

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
                adv_setting_original_id=adv_setting.id
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

    # Новая кнопка для режима раскрутки РС (полок)
    if adv_setting.rec_system_mode:
        rec_text = "Выключить режим раскрутки РС (полок)"
        rec_new_status = False
    else:
        rec_text = "Включить режим раскрутки РС (полок)"
        rec_new_status = True

    rec_callback = ChangeRecSystemModeStatus(
        adv_id=adv_setting.adv_id,
        wb_user_cabinet_original_id=wb_user_cabinet.id,
        new_status=rec_new_status,
    ).pack()
    rec_button = InlineKeyboardButton(text=rec_text, callback_data=rec_callback)
    _ = builder.row(rec_button)

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

    # Добавляем кнопку переключения режима прогноза CTR
    if adv_setting.predict_ctr_mode == PredictCTRMode.V1:
        text = "Переключить на режим прогноза CTR v2 (по артикулам)"
        new_mode = PredictCTRMode.V2
    else:
        text = "Переключить на режим прогноза CTR v1 (по ID кампании)"
        new_mode = PredictCTRMode.V1

    callback = PredictCTRModeToggle(
        new_mode=new_mode, adv_setting_original_id=adv_setting.id
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
        text="Управление ставкой",
        callback_data=callbacks.CPMSettingMenu(
            action="to_cpm_setting_page", adv_original_id=adv_setting.id
        ).pack(),
    )
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
        text="Задать/Изменить максимальную стоимость клика",
        callback_data=callbacks.ChangeMaxCPC(
            action="to_max_cpc_change_page", adv_original_id=adv_setting.id
        ).pack(),
    )

    _ = builder.row(button)

    button = InlineKeyboardButton(
        text="Изменить мин. кол-во просмотров для ИИ-прогноза CTR",
        callback_data=callbacks.ChangeMinViewsForPredictCTR(
            adv_setting_original_id=adv_setting.id
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

    if adv_setting.clusters_mode is not None and not adv_setting.clusters_mode:
        button = InlineKeyboardButton(
            text="Включить поддержку кластеров",
            callback_data=callbacks.TurnClusters(
                action="on", adv_original_id=adv_setting.id
            ).pack(),
        )
    else:
        button = InlineKeyboardButton(
            text="Отключить поддержку кластеров",
            callback_data=callbacks.TurnClusters(
                action="off", adv_original_id=adv_setting.id
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


def get_campaign_activity_menu_keyboard(adv_setting: AdvSetting) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    use_common = getattr(adv_setting, "use_common_budget", False)
    if use_common:
        _ = builder.row(
            InlineKeyboardButton(
                text="Настроить общий бюджет",
                callback_data=callbacks.ManageCampaignActivity(
                    action="open",
                    adv_setting_original_id=adv_setting.id,
                    campaign_type=None,
                ).pack(),
            )
        )
    else:
        _ = builder.row(
            InlineKeyboardButton(
                text="Настроить Аукцион",
                callback_data=callbacks.ManageCampaignActivity(
                    action="open",
                    adv_setting_original_id=adv_setting.id,
                    campaign_type=AdvType.SEARCH,
                ).pack(),
            )
        )
        _ = builder.row(
            InlineKeyboardButton(
                text="Настроить Авто",
                callback_data=callbacks.ManageCampaignActivity(
                    action="open",
                    adv_setting_original_id=adv_setting.id,
                    campaign_type=AdvType.AUTO,
                ).pack(),
            )
        )

    if getattr(adv_setting, "auto_budget_watchdog_enabled", False):
        use_common_budget = getattr(adv_setting, "use_common_budget", False)
        common_budget_text = (
            "Включить раздельный бюджет на каждую РК"
            if use_common_budget
            else "Включить общий бюджет на две РК"
        )
        common_budget_callback = CommonBudgetModeToggle(
            adv_setting_original_id=adv_setting.id,
            new_status=not use_common_budget,
        ).pack()
        _ = builder.row(
            InlineKeyboardButton(
                text=common_budget_text,
                callback_data=common_budget_callback,
            )
        )

    _ = builder.row(
        InlineKeyboardButton(
            text="Вернуться к настройкам кампании",
            callback_data=callbacks.Adv(adv_original_id=adv_setting.id).pack(),
        )
    )

    return builder.as_markup()


def get_campaign_activity_target_keyboard(
    adv_setting: AdvSetting,
    campaign_type: AdvType | None,
    current_limit: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    _ = builder.row(
        InlineKeyboardButton(
            text="Изменить лимит",
            callback_data=callbacks.ManageCampaignActivity(
                action="change",
                adv_setting_original_id=adv_setting.id,
                campaign_type=campaign_type,
            ).pack(),
        )
    )

    if current_limit > 0:
        _ = builder.row(
            InlineKeyboardButton(
                text="Выключить",
                callback_data=callbacks.ManageCampaignActivity(
                    action="turn_off",
                    adv_setting_original_id=adv_setting.id,
                    campaign_type=campaign_type,
                ).pack(),
            )
        )

    _ = builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=callbacks.ManageCampaignActivity(
                action="menu",
                adv_setting_original_id=adv_setting.id,
            ).pack(),
        )
    )

    return builder.as_markup()


def get_advs_keyboard_with_paginator(
    wb_user_cabinet_original_id: int,
    adv_settings: list[AdvSetting],
    page: int,
    on_page: int,
    keyword_filter: list[str] | None,
):
    adv_setting_without_auctions = [
        adv for adv in adv_settings if adv.auction_adv_id is not None
    ]

    active_part_advs = list(
        filter(
            lambda adv_local: adv_local.bot_active is True, adv_setting_without_auctions
        )
    )
    not_active_part_advs = list(
        filter(
            lambda adv_locale: adv_locale.bot_active is not True,
            adv_setting_without_auctions,
        )
    )
    adv_settings = active_part_advs + not_active_part_advs

    assert page > 0
    keyboard_buttons: list[list[InlineKeyboardButton]] = []
    start_index = (page - 1) * on_page
    end_index = start_index + on_page
    for adv in adv_settings[start_index:end_index]:
        check_last_24_hours = adv.check_last_24_hours  # type: ignore[attr-defined]
        check_text = "✅" if check_last_24_hours else "❓"
        button_text = (
            f"{'(' + str(adv.worst_promo_position) + ')' if adv.worst_promo_position else ''}{check_text} {adv.name} (Бот включен)"
            if adv.bot_active
            else f"{adv.name} (Бот отключен)"
        )
        button_text += f"({adv.adv_id})"
        button_text += f" Статус: {adv.active_status}"
        callback_data = callbacks.Adv(
            action="select",
            adv_original_id=adv.id,
            wb_user_cabinet_original_id=wb_user_cabinet_original_id,
        ).pack()
        keyboard_buttons.append(
            [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
        )

    # Добавляем кнопки навигации
    if page > 1:
        prev_page = page - 1
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=callbacks.ChoiceAdvPaginator(
                        wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                        page=prev_page,
                    ).pack(),
                )
            ]
        )

    if len(adv_settings) > end_index:
        next_page = page + 1
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=callbacks.ChoiceAdvPaginator(
                        wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                        page=next_page,
                    ).pack(),
                )
            ]
        )

    if keyword_filter:
        button = [
            InlineKeyboardButton(
                text="Сбросить фильтр",
                callback_data=callbacks.ChoiceAdvPaginator(
                    wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                    page=page,
                    reset_filter=True,
                ).pack(),
            )
        ]

        keyboard_buttons.append(button)

    button = InlineKeyboardButton(
        text="Вернуться к меню магазина",
        callback_data=callbacks.Shop(
            action=Action.select,
            wb_user_cabinet_original_id=wb_user_cabinet_original_id,
        ).pack(),
    )

    keyboard_buttons.append([button])  # type: ignore[list-item]
    button = InlineKeyboardButton(
        text="Полностью обновить мета-данные от WB",
        callback_data=callbacks.UpdateCompanyFromWB(
            wb_user_cabinet_original_id=wb_user_cabinet_original_id
        ).pack(),
    )

    keyboard_buttons.append([button])  # type: ignore[list-item]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard


def get_keywords_setting_keyboard(
    keywords: list[CalculatedKeyword],
    adv_setting: AdvSetting,
    wb_user_cabinet_original_id: int,
    page: int,
    return_from_filter_bottom: bool,
    on_page: int,
    hide_keywords_is_not_relevant: bool,
    sort_mode: str = "default",
    image_mode: str = "graphic",
):
    from . import keyword_statuses_util as k_util
    def sorting_keywords(
        kws_: list[CalculatedKeyword], sort_mode_: str
    ) -> list[CalculatedKeyword]:
        if sort_mode_ in ["by_adv", "only_out_index"]:

            kws_.sort(
                key=lambda x: x.rating_by_orders, reverse=True
            )

            return kws_

        elif sort_mode_ == "white_list":

            def sort_func(kw_: CalculatedKeyword) -> float:
                return kw_.rating_by_orders

            return sorted(kws_, key=sort_func, reverse=True)

        elif sort_mode_ == "sort_by_ctr_desc":
            return sorted(kws_, key=lambda x: x.ctr or 0, reverse=True)  # type: ignore[arg-type]
        else:
            raise ValueError(f"Unknown sort_mode: {sort_mode_}")

    start_index = (page - 1) * on_page
    end_index = start_index + on_page

    keywords = sorting_keywords(keywords, sort_mode)

    bottoms: list[list[InlineKeyboardButton]] = []
    for keyword in keywords[start_index:end_index]:
        clicks = keyword.clicks
        views = keyword.views
        ctr = keyword.ctr
        turn_on = "✅" if keyword.status == KeywordStatus.GOOD else "❌"
        text = "🌟" if keyword.best_keyword_status else ""
        if keyword.relevant:
            text += "🟢"
        if adv_setting.rec_system_mode and keyword.above_rec_conversion is not None:
            text += "П-" if keyword.above_rec_conversion else ""
        text += f"""{clicks}/{views}/{round(ctr * 100, 2)}%"""
        add_to_cart = keyword.add_to_cart
        orders = keyword.orders
        total_orders = keyword.total_orders
        total_orders = f"({add_to_cart}-{orders}-{total_orders})"
        text += total_orders
        text += "|"
        if keyword.position:
            text += f"{int(keyword.position + 0.5)}"
        elif keyword.position == 0:
            text += ">"
        else:
            text += "?"  # TODO: Проверить логику: кажется позиция не может быть None

        if adv_setting.individual_keywords_target_place_mode:
            if target_place := keyword.target_place:
                text += f'->{target_place}'
            else:
                text += f'->Н>'

        cpm = int(keyword.cpm + 0.5) # плата за показы
        text += f"({cpm})"
        text += f"{turn_on}{k_util.get_hard_status(keyword)}{k_util.get_dynamic_status(keyword)} {keyword.text}"
        pay_for_order = str((round(keyword.pay_for_order_by_current_cpm, 2))) \
                                if keyword.pay_for_order_by_current_cpm != float('inf') else 'Б'
        text += f"({round(keyword.rating_by_orders * 1000, 2)})({pay_for_order})"

        keyword_setting_original_id = keyword.keyword_setting_original_id
        assert keyword_setting_original_id

        inline_keyboard = [
            InlineKeyboardButton(
                text=text,
                callback_data=callbacks.SettingKeyword(
                    keyword_setting_original_id=keyword_setting_original_id,
                ).pack(),
            )
        ]
        bottoms.append(inline_keyboard)

    if return_from_filter_bottom or image_mode == "image":
        bottom = [
            InlineKeyboardButton(
                text="Сбросить фильтр",
                callback_data=callbacks.SettingKeywords(
                    adv_original_id=adv_setting.id,
                    type="by_adv",
                    page=page,
                    reset_filter=True,
                ).pack(),
            )
        ]
        bottoms.append(bottom)

    if page > 1:
        prev_page = page - 1
        bottoms.append(
            [
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=callbacks.SettingKeywords(
                        adv_original_id=adv_setting.id, type=sort_mode, page=prev_page
                    ).pack(),
                )
            ]
        )

    if len(keywords) > end_index:
        next_page = page + 1
        bottoms.append(
            [
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=callbacks.SettingKeywords(
                        adv_original_id=adv_setting.id, type=sort_mode, page=next_page
                    ).pack(),
                )
            ]
        )
    bottom = [
        InlineKeyboardButton(
            text="Показать фразы для продвижения (белый список)",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="white_list", page=page
            ).pack(),
        )
    ]
    bottoms.append(bottom)

    bottom = [
        InlineKeyboardButton(
            text="Показать фразы-кандидаты на включение в БС",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id,
                type="phrase_for_adding_to_white_list",
                page=page,
            ).pack(),
        )
    ]
    bottoms.append(bottom)

    bottom = [
        InlineKeyboardButton(
            text="Показать активные ключи",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="active_keywords", page=page
            ).pack(),
        )
    ]
    bottoms.append(bottom)

    bottom = [
        InlineKeyboardButton(
            text="Показать ключи вне индекса",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="only_out_index", page=page
            ).pack(),
        )
    ]

    bottoms.append(bottom)

    if not hide_keywords_is_not_relevant:
        bottom = [
            InlineKeyboardButton(
                text="Скрыть не релевантные фразы",
                callback_data=callbacks.SettingKeywords(
                    adv_original_id=adv_setting.id,
                    type="hide_keywords_is_not_relevant",
                    page=page,
                ).pack(),
            )
        ]
    else:
        bottom = [
            InlineKeyboardButton(
                text="Показывать не релевантные фразы",
                callback_data=callbacks.SettingKeywords(
                    adv_original_id=adv_setting.id,
                    type="show_keywords_is_not_relevant",
                    page=page,
                ).pack(),
            )
        ]

    bottoms.append(bottom)

    bottom = [
        InlineKeyboardButton(
            text="Показать отключенные фразы",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="show_keywords_is_hard", page=page
            ).pack(),
        )
    ]

    bottoms.append(bottom)

    bottom = [
        InlineKeyboardButton(
            text="Сортировать по ФАКТ CTR по Уб.",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id,
                type="sort_by_ctr_desc",
                page=page,
            ).pack(),
        )
    ]
    bottoms.append(bottom)

    adv_id = adv_setting.adv_id
    assert adv_id
    button = [
        InlineKeyboardButton(
            text="Изменить экспоненту прог. ctr",
            callback_data=ChangeExponentSettinginAdvSettingCallback(
                adv_id=adv_id, wb_user_cabinet_original_id=wb_user_cabinet_original_id
            ).pack(),
        )
    ]

    bottoms.append(button)

    button = [
        InlineKeyboardButton(
            text="Фильтр по прогнозируемым показам",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="filter_by_query", page=page
            ).pack(),
        )
    ]

    bottoms.append(button)

    button = [
        InlineKeyboardButton(
            text="Сбросить добавочные клики",
            callback_data=callbacks.ResetAddedClicks(
                adv_setting_original_id=adv_setting.id
            ).pack(),
        )
    ]

    bottoms.append(button)

    from app.modules.manual_phrase_positions_update.backend.frontend.telegram.buttons import (
        UpdatePositionsForActivePhrase,
    )

    button = [
        InlineKeyboardButton(
            text="Перепроверить позиции ключей из БС",
            callback_data=UpdatePositionsForActivePhrase(
                adv_setting_original_id=adv_setting.id,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                target="white_list",
            ).pack(),
        )
    ]

    bottoms.append(button)

    from app.modules.manual_phrase_positions_update.backend.frontend.telegram.buttons import (
        UpdatePositionsForActivePhrase,
    )

    button = [
        InlineKeyboardButton(
            text="Перепроверить позиции активный ключей",
            callback_data=UpdatePositionsForActivePhrase(
                adv_setting_original_id=adv_setting.id,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                target="active_phrases",
            ).pack(),
        )
    ]

    bottoms.append(button)

    # Кнопка для переключения скрытия ключей без рекламных просмотров
    if adv_setting.hide_zero_views_keywords:
        hide_views_text = "Показать ключи без рекламных просмотров"
        hide_views_new_status = False
    else:
        hide_views_text = "Скрыть ключи без рекламных просмотров"
        hide_views_new_status = True

    button = [
        InlineKeyboardButton(
            text=hide_views_text,
            callback_data=ChangeHideZeroViewsStatus(
                adv_id=adv_id,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id,
                new_status=hide_views_new_status,
            ).pack(),
        )
    ]

    bottoms.append(button)

    bottoms.append(
        [
            InlineKeyboardButton(
                text="К настройкам АРК",
                callback_data=callbacks.Adv(adv_original_id=adv_setting.id).pack(),
            )
        ]
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=bottoms)
    return keyboard


def get_keyword_setting_keyboard(
    keyword: KeywordSetting,
    adv_setting: AdvSetting,
    page: int,
) -> InlineKeyboardMarkup:
    adv_setting_original_id = adv_setting.id
    keyword_setting_original_id = keyword.id
    assert keyword_setting_original_id
    assert adv_setting_original_id
    buttons: list[list[InlineKeyboardButton]] = []
    reason: str | None
    if hasattr(keyword, "reason"):
        reason = keyword.reason  # type: ignore[attr-defined]
    else:
        reason = None

    if keyword.hard_status in [BLACK_LIST, WHITE_LIST, TURN_OFF]:
        button = [
            InlineKeyboardButton(
                text="В авто",
                callback_data=callbacks.ChangeKeywordHardStatus(
                    new_hard_status=AUTO_MODE,
                    keyword_setting_original_id=keyword_setting_original_id,
                ).pack(),
            )
        ]
        buttons.append(button)

    if keyword.hard_status in [BLACK_LIST, TURN_OFF, AUTO_MODE]:
        button = [
            InlineKeyboardButton(
                text="В белый список",
                callback_data=callbacks.ChangeKeywordHardStatus(
                    new_hard_status=WHITE_LIST,
                    keyword_setting_original_id=keyword_setting_original_id,
                ).pack(),
            )
        ]
        buttons.append(button)

    if keyword.relevant:
        text = "Удалить из релевантных фраз"
        new_relevant_status = False
    else:
        text = "Добавить в релевантные фразы"
        new_relevant_status = True

    callback = RelevantKeywordStatusSetting(
        new_relevant_status=new_relevant_status,
        keyword_setting_original_id=keyword_setting_original_id,
    )

    buttons_row = [
        InlineKeyboardButton(
            text=text,
            callback_data=callback.pack(),
        )
    ]
    buttons.append(buttons_row)

    if (
        keyword.hard_status in [AUTO_MODE, WHITE_LIST]
        or reason == KeywordStatus.VIEWS_IS_NOT_ENOUGH
    ):
        bottom = [
            InlineKeyboardButton(
                text="Отключить (релевантная фраза)",
                callback_data=callbacks.ChangeKeywordHardStatus(
                    new_hard_status=TURN_OFF,
                    keyword_setting_original_id=keyword_setting_original_id,
                ).pack(),
            )
        ]
        buttons.append(bottom)

    if keyword.hard_status in [AUTO_MODE, WHITE_LIST, TURN_OFF]:
        button = [
            InlineKeyboardButton(
                text="В список не релевантных фраз",
                callback_data=callbacks.ChangeKeywordHardStatus(
                    new_hard_status=BLACK_LIST,
                    keyword_setting_original_id=keyword_setting_original_id,
                ).pack(),
            )
        ]
        buttons.append(button)

    value, source = get_effective_keyword_target_place(keyword, adv_setting)
    target_place_value, source_text = format_target_place_display(value, source)
    buttons.append(
        [
            InlineKeyboardButton(
                text=f"Целевая позиция: {target_place_value} ({source_text}) — Изменить",
                callback_data=callbacks.ChangeKeywordTargetPlace(
                    keyword_setting_original_id=keyword_setting_original_id,
                ).pack(),
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="Вернуться к списку ключевых слов",
                callback_data=callbacks.SettingKeywords(
                    adv_original_id=adv_setting_original_id,
                    page=page,
                ).pack(),
            )
        ]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return keyboard


def get_subscribe_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(text="Подписаться", url="https://t.me/auto_wb_master")
    )
    return builder.as_markup()


def get_shop_menu_keyboard(
    wb_user_cabinet: WBUserCabinet, wb_cabinet_original_id: int, is_active_adv: bool
):
    wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
    expiration_time: datetime.datetime = wb_cabinet.expiration_time
    now = datetime.datetime.now()
    balance = wb_cabinet.balance or 0
    bonus = wb_cabinet.bonus or 0
    builder = InlineKeyboardBuilder()

    if any([expiration_time > now, balance > 0, bonus > 0]):
        _ = builder.row(
            InlineKeyboardButton(
                text="Автоматические рекламные кампании",
                callback_data=callbacks.ChoiceAdvPaginator(
                    wb_user_cabinet_original_id=wb_user_cabinet.id, page=1
                ).pack(),
            )
        )

    _ = builder.row(
        InlineKeyboardButton(
            text="Пополнить баланс (Yookassa)",
            callback_data=callbacks.AddBalance(
                wb_cabinet_original_id=wb_cabinet_original_id
            ).pack(),
        )
    )

    if is_active_adv:
        _ = builder.row(
            InlineKeyboardButton(
                text="Отключить все кампании",
                callback_data=callbacks.TurnBot(
                    action="off_all", wb_user_cabinet_original_id=wb_user_cabinet.id
                ).pack(),
            )
        )
    _ = builder.row(
        InlineKeyboardButton(
            text="Вернуться к списку магазинов", callback_data=callbacks.ShowShopsList().pack()
        )
    )
    return builder.as_markup()


def get_payment_keyboard(wb_cabinet_original_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Пополнить баланс (Yookassa)",
            callback_data=callbacks.AddBalance(
                wb_cabinet_original_id=wb_cabinet_original_id
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="К списку магазинов", callback_data=callbacks.ShowShopsList().pack()
        )
    )

    return builder.as_markup()


def get_setting_max_cpc_keyboard(adv: AdvSetting) -> InlineKeyboardMarkup:
    adv_original_id = adv.id
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=callbacks.Adv(adv_original_id=adv_original_id).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="Отключить максимальную стоимость клика",
            callback_data=callbacks.ChangeMaxCPC(
                action="turn_off_max_cpc", adv_original_id=adv_original_id
            ).pack(),
        )
    )
    return builder.as_markup()


def get_setting_min_views_for_predict_ctr_keyboard(
    adv: AdvSetting,
) -> InlineKeyboardMarkup:
    adv_original_id = adv.id
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=callbacks.Adv(adv_original_id=adv_original_id).pack(),
        )
    )
    return builder.as_markup()


def get_return_to_adv_setting_keyboard(adv_original_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Назад в настройки кампании",
            callback_data=callbacks.Adv(adv_original_id=adv_original_id).pack(),
        )
    )
    return builder.as_markup()


def get_call_me_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Получить консультацию и тест-драйв бота", url=f"{const.SUPPORT_LINK}"
        )
    )
    return builder.as_markup()


def get_call_me_keyboard0() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Связаться с разработчиком бота для консультации",
            url=const.SUPPORT_LINK,
        )
    )
    return builder.as_markup()


def get_call_me_keyboard1() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(text="Заказать демо-доступ к боту", url=const.SUPPORT_LINK)
    )
    return builder.as_markup()


def get_ozon_keyword_setting_keyboard(
    keyword_setting_id: int, page: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(
            text="Назад к списку ключевых слов",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=keyword_setting_id, page=page
            ).pack(),
        )
    )
    return builder.as_markup()


def get_payment_keyboard_for_shops(
    wb_user_cabinets: list[WBUserCabinet],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for wb_user_cabinet in wb_user_cabinets[:20]:
        wb_cabinet = wb_user_cabinet.wb_cabinet
        balance = wb_cabinet.balance or 0
        bonus = wb_cabinet.bonus or 0
        total_money = balance + bonus

        button = InlineKeyboardButton(
            text="Пополнить "
            + wb_user_cabinet.name
            + f" Текущий общий баланс({total_money})",
            callback_data=callbacks.AddBalance(
                wb_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )
        _ = builder.row(button)
    return builder.as_markup()




def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру администратора: пополнение кабинетов (shop_id) или пользователей (telegram_id).
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Пополнение кабинетов",
                    callback_data=AdminBonus(action="menu").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Пополнение пользователей",
                    callback_data=AdminUserBalance(action="menu").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=callbacks.Start().pack(),
                )
            ],
        ]
    )
    return keyboard

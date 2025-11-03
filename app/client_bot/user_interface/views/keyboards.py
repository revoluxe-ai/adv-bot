import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot import const
from app.client_bot.const import AUTO_MODE, BLACK_LIST, TURN_OFF, WHITE_LIST
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import (
    Action,
    TurnBot,
    OrdersSourceToggle,
    PredictCTRModeToggle,
    SalesPredictMethodToggle,
)
from app.modules.cabinet_bonus_manager.callbacks import AdminBonus
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
    KeywordStatus,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBCabinet,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import PredictCTRMode
from app.modules.predict_ctr_exponent_settings import (
    ChangeExponentSettinginAdvSettingCallback,
)
from app.modules.sales_plan_settings.telegram.main_callback import (
    SalesPlanSettingsMenu as SalesPlanSettingsMenuCallback,
)
from app.modules.shop_runner.auction_boost_mode_settings.telegram.callbacks import (
    SettingAuctionBoostMode,
)
from app.modules.shop_runner.service_manager.old_modules.auto_updater_target_place.telegram.callbacks import (
    AutoUpdateTargetPlaceSetting as AutoUpdateTargetPlaceSettingCallBack,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater.telegram.callbacks import (
    AutoUpdateWhiteListSetting,
    RelevantKeywordStatusSetting,
)
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker


def get_adv_setting_keyboard(
    chat_id, wb_user_cabinet: WBUserCabinet, adv_setting: AdvSetting, in_favorites: bool
):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Контроль ключевых слов по кампании",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="by_adv"
            ).pack(),
        )
    )

    if adv_setting.bot_active:
        builder.row(
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
        builder.row(
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
    builder.row(button)

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
    builder.row(button)

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
        new_source=new_source, adv_setting_original_id=adv_setting.id
    ).pack()
    button = InlineKeyboardButton(text=text, callback_data=callback)
    builder.row(button)

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
    builder.row(button)

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
    builder.row(button)

    button = InlineKeyboardButton(
        text="План продаж",
        callback_data=SalesPlanSettingsMenuCallback(adv_id=adv_setting.adv_id).pack(),
    )

    builder.row(button)

    button = InlineKeyboardButton(
        text="Управление ставкой",
        callback_data=callbacks.CPMSettingMenu(
            action="to_cpm_setting_page", adv_original_id=adv_setting.id
        ).pack(),
    )
    builder.row(button)

    botton = InlineKeyboardButton(
        text="Шаблоны не релевантных фраз",
        callback_data=callbacks.AddBlackPhrasesTemplates(
            adv_setting_id=adv_setting.id
        ).pack(),
    )
    builder.row(botton)

    builder.row(
        InlineKeyboardButton(
            text="Добавить фразы в продвижение (Белый список)",
            callback_data=callbacks.AddWhitePhrases(
                adv_setting_id=adv_setting.id
            ).pack(),
        )
    )

    builder.row(
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

    builder.row(button)

    button = InlineKeyboardButton(
        text="История позиций ключевых слов",
        callback_data=callbacks.KeywordPositionHistory(
            adv_original_id=adv_setting.id
        ).pack(),
    )
    builder.row(button)

    if adv_setting.hard_min_ctr:
        builder.row(
            InlineKeyboardButton(
                text="Изменить минимальный CTR",
                callback_data=callbacks.ChangeMinCTR(
                    action="change_min_ctr", adv_original_id=adv_setting.id
                ).pack(),
            )
        )

    else:
        builder.row(
            InlineKeyboardButton(
                text="Режим управления CTR",
                callback_data=callbacks.ChangeMinCTR(
                    action="change_min_ctr", adv_original_id=adv_setting.id
                ).pack(),
            )
        )

    button = InlineKeyboardButton(
        text="Задать/Изменить максимальную стоимость клика",
        callback_data=callbacks.ChangeMaxCPC(
            action="to_max_cpc_change_page", adv_original_id=adv_setting.id
        ).pack(),
    )

    builder.row(button)

    button = InlineKeyboardButton(
        text="Изменить мин. кол-во просмотров для ИИ-прогноза CTR",
        callback_data=callbacks.ChangeMinViewsForPredictCTR(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )

    builder.row(button)

    if adv_setting.reset_place:
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

    builder.row(button)

    if not adv_setting.clusters_mode:
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
    builder.row(button)

    button = InlineKeyboardButton(
        text="Загрузить статистику из WB",
        callback_data=callbacks.WBUpdate(
            action="update_keyword_stat", adv_setting_original_id=adv_setting.id
        ).pack(),
    )
    builder.row(button)

    button = InlineKeyboardButton(
        text="Обновить минус-слова",
        callback_data=callbacks.WBUpdate(
            action="update_minus_keywords", adv_setting_original_id=adv_setting.id
        ).pack(),
    )

    builder.row(button)

    button = InlineKeyboardButton(
        text="Сбросить белый список",
        callback_data=callbacks.ResetWhiteList(
            adv_setting_original_id=adv_setting.id
        ).pack(),
    )
    builder.row(button)

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

    builder.row(button)

    wb_user_cabinet_original_id = wb_user_cabinet.id
    builder.row(
        InlineKeyboardButton(
            text="Вернуться к списку кампаний",
            callback_data=callbacks.ChoiceAdvPaginator(
                wb_user_cabinet_original_id=wb_user_cabinet_original_id, page=1
            ).pack(),
        )
    )

    return builder.as_markup()


def get_advs_keyboard_with_paginator(
    wb_user_cabinet_original_id: int,
    adv_settings: list[AdvSetting],
    page: int,
    on_page: int,
    keyword_filter,
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
    keyboard_buttons = []
    start_index = (page - 1) * on_page
    end_index = start_index + on_page
    for adv in adv_settings[start_index:end_index]:
        check_last_24_hours = adv.check_last_24_hours
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
    adv_choice_last_page,
    wb_user_cabinet_original_id: int,
    page,
    return_from_filter_bottom: bool,
    on_page,
    min_ctr,
    hide_keywords_is_not_relevant,
    sort_mode="default",
    image_mode="graphic",
):
    def sorting_keywords(keywords, sort_mode):
        if sort_mode in ["by_adv", "only_out_index"]:
            keywords_with_rating = [
                kw for kw in keywords if kw.rating_by_predict_ctr > 0
            ]
            keywords_with_rating.sort(
                key=lambda x: x.rating_by_predict_ctr, reverse=True
            )
            keywords_without_rating = [
                kw for kw in keywords if kw.rating_by_predict_ctr == 0
            ]
            keywords_without_rating.sort(key=lambda x: x.predict_ctr, reverse=True)
            keywords = keywords_with_rating + keywords_without_rating
            return keywords

        elif sort_mode == "white_list":

            def sort_func(keyword: CalculatedKeyword):
                return keyword.baes_ctr

            return sorted(keywords, key=sort_func, reverse=True)

        elif sort_mode == "sort_by_ctr_desc":
            return sorted(keywords, key=lambda x: x.ctr, reverse=True)
        else:
            raise ValueError(f"Unknown sort_mode: {sort_mode}")

    start_index = (page - 1) * on_page
    end_index = start_index + on_page

    keywords = sorting_keywords(keywords, sort_mode)

    if adv_setting.hide_small_query_keywords:
        keywords = [
            keyword
            for keyword in keywords
            if isinstance(keyword.query, int)
            and keyword.query >= adv_setting.hide_small_query_keywords
        ]

    bottoms = []
    for keyword in keywords[start_index:end_index]:
        clicks = keyword.clicks
        views = keyword.views
        ctr = keyword.ctr
        if keyword.reason == "max_position":
            message_status = "БС-" if keyword.hard_status == 2 else ""
            message_status += "ЦП"
        elif keyword.reason == KeywordStatus.VIEWS_IS_NOT_ENOUGH:
            message_status = "БС-" if keyword.hard_status == 2 else ""
            message_status += "МП"
        elif keyword.hard_status == BLACK_LIST:
            message_status = "НРФ"
        elif keyword.reason == "max_cpc":
            message_status = "МС"
        elif keyword.hard_status == TURN_OFF:
            message_status = "О"
        elif keyword.hard_status == WHITE_LIST:
            message_status = "БС"
        elif keyword.hard_status == AUTO_MODE:
            message_status = "А"
        else:
            raise ValueError(f"Unknown hard_status: {keyword.hard_status}")

        turn_on = "✅" if keyword.status == KeywordStatus.GOOD else "❌"
        cluster_name = keyword.cluster_name
        text = "🌟" if keyword.best_keyword_status else ""
        if keyword.relevant:
            text += "🟢"
        text += f"""{clicks}/{views}/{round(ctr * 100, 2)}%"""
        text += "|"
        if keyword.position and keyword.position != -1:
            text += f"{keyword.position}"
        elif keyword.position == 0:
            text += ">>>"
        elif keyword.position == -1:
            text += ">i"
        else:
            text += "?"  # TODO: Проверить логику: кажется позиция не может быть None
        text += f"{turn_on}({message_status}) {keyword.text}"

        text += f"({keyword.query})"

        text += f"({round(keyword.predict_ctr * 100, 2)}%)"

        text += f"""{"(" + str(keyword.added_clicks) + ")" if keyword.added_clicks else ""}"""
        text += f"""{"❗" if not cluster_name else ""}"""
        inline_keyboard = [
            InlineKeyboardButton(
                text=text,
                callback_data=callbacks.SettingKeyword(
                    keyword_setting_original_id=keyword.keyword_setting_original_id,
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

    botton = [
        InlineKeyboardButton(
            text="Фильтр по прогнозируемым показам",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_setting.id, type="filter_by_query", page=page
            ).pack(),
        )
    ]

    bottoms.append(botton)

    botton = [
        InlineKeyboardButton(
            text="Сбросить добавочные клики",
            callback_data=callbacks.ResetAddedClicks(
                adv_setting_original_id=adv_setting.id
            ).pack(),
        )
    ]

    bottoms.append(botton)

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
    chat_id: int,
    keyword: KeywordSetting,
    calculated_keyword: CalculatedKeyword,
    adv_setting: AdvSetting,
    page,
) -> InlineKeyboardMarkup:
    adv_setting_original_id = adv_setting.id
    keyword_setting_original_id = keyword.id
    assert keyword_setting_original_id
    assert adv_setting_original_id
    buttons = []
    if hasattr(keyword, "reason"):
        reason = keyword.reason
    else:
        reason = None

    if (
        calculated_keyword.hard_status == 1
        and calculated_keyword.status == KeywordStatus.BAD
        and calculated_keyword.reason != "max_position"
    ):
        button = [
            InlineKeyboardButton(
                text="Тестировать дальше",
                callback_data=callbacks.ChangeKeywordHardStatus(
                    new_hard_status=-1,
                    keyword_setting_original_id=keyword_setting_original_id,
                ).pack(),
            )
        ]

        buttons.append(button)

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

    button = [
        InlineKeyboardButton(
            text="Проверить позицию",
            callback_data=callbacks.CheckPosition(
                keyword_setting_original_id=keyword_setting_original_id,
                adv_original_id=adv_setting_original_id,
            ).pack(),
        )
    ]

    buttons.append(button)

    button = [
        InlineKeyboardButton(
            text="Изменить ставку",
            callback_data=callbacks.ChangeCPM(
                adv_setting_original_id=adv_setting_original_id
            ).pack(),
        )
    ]

    buttons.append(button)
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


def get_subscribe_keyboard():
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(text="Подписаться", url="https://t.me/auto_wb_master")
    builder.row(button)
    return builder.as_markup()


def get_ref_program_keyboard():
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(
        text="Создать новую реф.ссылку",
        callback_data=callbacks.RefProgram(action="new").pack(),
    )
    builder.row(button)
    button = InlineKeyboardButton(
        text="Существующие ссылки и их имена",
        callback_data=callbacks.RefProgram(action="select").pack(),
    )
    builder.row(button)
    return builder.as_markup()


def get_return_for_your_ref_links():
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(
        text="Назад", callback_data=callbacks.RefProgram(action="return").pack()
    )

    builder.row(button)
    return builder.as_markup()


def get_shop_menu_keyboard(
    wb_user_cabinet: WBUserCabinet, wb_cabinet_original_id: int, is_active_adv: True  # type: ignore[valid-type]
):
    wb_cabinet: WBCabinet = wb_user_cabinet.wb_cabinet
    expiration_time: datetime.datetime = wb_cabinet.expiration_time
    now = datetime.datetime.now()
    if not (balance := wb_cabinet.balance):
        balance = 0
    if not (bonus := wb_cabinet.bonus):
        bonus = 0
    builder = InlineKeyboardBuilder()

    if any([expiration_time > now, balance > 0, bonus > 0]):
        button = InlineKeyboardButton(
            text="Автоматические рекламные кампании",
            callback_data=callbacks.ChoiceAdvPaginator(
                wb_user_cabinet_original_id=wb_user_cabinet.id, page=1
            ).pack(),
        )
        builder.row(button)

    button = InlineKeyboardButton(
        text="Пополнить баланс",
        callback_data=callbacks.AddBalance(
            wb_cabinet_original_id=wb_cabinet_original_id
        ).pack(),
    )

    builder.row(button)

    if is_active_adv:
        button = InlineKeyboardButton(
            text="Отключить все кампании",
            callback_data=callbacks.TurnBot(
                action="off_all", wb_user_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )
        builder.row(button)
    button = InlineKeyboardButton(
        text="Вернуться к списку магазинов", callback_data=callbacks.Start().pack()
    )
    builder.row(button)
    return builder.as_markup()


def get_payment_keyboard(wb_cabinet_original_id):
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(
        text="Пополнить баланс",
        callback_data=callbacks.AddBalance(
            wb_cabinet_original_id=wb_cabinet_original_id
        ).pack(),
    )
    builder.row(button)

    button = InlineKeyboardButton(
        text="К списку магазинов", callback_data=callbacks.Start().pack()
    )

    builder.row(button)

    return builder.as_markup()


def get_setting_min_ctr_keyboard(adv: AdvSetting):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Назад", callback_data=callbacks.Adv(adv_original_id=adv.id).pack()
        )
    )
    if adv.new_auto_min_ctr_mode:
        button = InlineKeyboardButton(
            text="Выключить управление CTR по белому списку",
            callback_data=callbacks.ChangeAutoMinCTR(
                action="turn_off_auto_min_ctr", adv_setting_original_id=adv.id
            ).pack(),
        )
    else:
        button = InlineKeyboardButton(
            text="Включить управление CTR по белому списку",
            callback_data=callbacks.ChangeAutoMinCTR(
                action="turn_on_auto_min_ctr", adv_setting_original_id=adv.id
            ).pack(),
        )

    builder.row(button)

    return builder.as_markup()


def get_setting_max_cpc_keyboard(adv: AdvSetting):
    adv_original_id = adv.id
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=callbacks.Adv(adv_original_id=adv_original_id).pack(),
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Отключить максимальную стоимость клика",
            callback_data=callbacks.ChangeMaxCPC(
                action="turn_off_max_cpc", adv_original_id=adv_original_id
            ).pack(),
        )
    )
    return builder.as_markup()


def get_setting_min_views_for_predict_ctr_keyboard(adv: AdvSetting):
    adv_original_id = adv.id
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=callbacks.Adv(adv_original_id=adv_original_id).pack(),
        )
    )
    return builder.as_markup()


def get_return_to_adv_setting_keyboard(adv_original_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Назад в настройки кампании",
            callback_data=callbacks.Adv(adv_original_id=adv_original_id).pack(),
        )
    )
    return builder.as_markup()


def get_call_me_keyboard():
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(
        text="Получить консультацию и тест-драйв бота", url=f"{const.SUPPORT_LINK}"
    )
    builder.row(button)
    return builder.as_markup()


def get_call_me_keyboard0():
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(
        text="Связаться с разработчиком бота для консультации", url=const.SUPPORT_LINK
    )
    builder.row(button)
    return builder.as_markup()


def get_call_me_keyboard1():
    builder = InlineKeyboardBuilder()
    button = InlineKeyboardButton(
        text="Заказать демо-доступ к боту", url=const.SUPPORT_LINK
    )
    builder.row(button)
    return builder.as_markup()


def get_ozon_keyword_setting_keyboard(keyword_setting_id: int, page: int = 1):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Назад к списку ключевых слов",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=keyword_setting_id, page=page
            ).pack(),
        )
    )
    return builder.as_markup()


def get_payment_keyboard_for_shops(wb_user_cabinets: list[WBUserCabinet]):
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
        builder.row(button)
    return builder.as_markup()


def get_advs_list(advs: list[AdvSetting]):
    builder = InlineKeyboardBuilder()
    for adv in advs:
        name = (
            "(" + str(adv.worst_promo_position) + ")"
            if adv.worst_promo_position
            else ""
        )
        name += adv.name
        button = InlineKeyboardButton(
            text=name, callback_data=callbacks.Adv(adv_original_id=adv.id).pack()
        )
        builder.row(button)
    return builder.as_markup()


def get_admin_keyboard():
    """
    Создает клавиатуру администратора с доступными административными функциями
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Управление бонусами",
                    callback_data=AdminBonus(action="menu").pack(),
                )
            ]
        ]
    )
    return keyboard

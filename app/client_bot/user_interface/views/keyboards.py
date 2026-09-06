import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.client_bot import const
from app.client_bot.admin_access import is_bot_admin
from app.client_bot.const import ALWAYS_ON, AUTO_MODE, BLACK_LIST, TURN_OFF, WHITE_LIST
from app.client_bot.user_interface.utils import (
    format_target_place_display,
    get_effective_keyword_target_place,
)
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import (
    Action,
    AutoCommonBudgetToggle,
    CommonBudgetModeToggle,
)
from app.modules.admin_user_balance.callbacks import AdminUserBalance
from app.modules.cabinet_bonus_manager.callbacks import AdminBonus, AdminPanel
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.hide_zero_views_toggle import ChangeHideZeroViewsStatus

from app.client_bot.user_interface.views.keyword_strategy_ui import (
    keyword_strategy_letter,
)
from app.client_bot.user_interface.views.keyword_v3_profile_ui import (
    keyword_v3_decision_trace_button_label,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater.auto_white_list_updater.telegram.callbacks import (
    RelevantKeywordStatusSetting,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state import (
    format_keyword_list_target_place_suffix,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from app.utils.db.session_maker import get_async_session_maker
from app.shared.domains.wb.enums import (
    AdvType,
)

sm = get_async_session_maker


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
        auto_common_flag = bool(getattr(adv_setting, "auto_common_budget", False))
        auto_common_text = (
            "Включить авторасчёт общего бюджета"
            if not auto_common_flag
            else "Выключить авторасчёт общего бюджета"
        )
        auto_common_callback = AutoCommonBudgetToggle(
            adv_setting_original_id=adv_setting.id,
            new_status=not auto_common_flag,
        ).pack()
        _ = builder.row(
            InlineKeyboardButton(
                text=auto_common_text,
                callback_data=auto_common_callback,
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


def get_strategy_menu_keyboard(adv_setting: AdvSetting) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # None means auto-enabled (same as True); only False is manual
    auto_update_strategy = getattr(adv_setting, "auto_update_strategy", True) is not False
    strategy = adv_setting.strategy or Strategy.MIN_CPO

    _ = builder.row(
        InlineKeyboardButton(
            text=(
                "Выключить авто-выбор стратегии"
                if auto_update_strategy
                else "Включить авто-выбор стратегии"
            ),
            callback_data=callbacks.StrategyMenu(
                action="toggle_auto",
                adv_setting_original_id=adv_setting.id,
            ).pack(),
        )
    )

    if not auto_update_strategy:
        min_cpo_active = "✅ " if strategy == Strategy.MIN_CPO else ""
        max_conv_active = "✅ " if strategy == Strategy.MAX_CONV else ""
        _ = builder.row(
            InlineKeyboardButton(
                text=f"{min_cpo_active}MIN_CPO (минимальная себестоимость заказа)",
                callback_data=callbacks.StrategyMenu(
                    action="set_strategy",
                    adv_setting_original_id=adv_setting.id,
                    strategy=Strategy.MIN_CPO.value,
                ).pack(),
            )
        )
        _ = builder.row(
            InlineKeyboardButton(
                text=f"{max_conv_active}MAX_CONV (максимум конверсии)",
                callback_data=callbacks.StrategyMenu(
                    action="set_strategy",
                    adv_setting_original_id=adv_setting.id,
                    strategy=Strategy.MAX_CONV.value,
                ).pack(),
            )
        )

    _ = builder.row(
        InlineKeyboardButton(
            text="Вернуться к настройкам кампании",
            callback_data=callbacks.Adv(adv_original_id=adv_setting.id).pack(),
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
        # DEPRECATED residual read: AdvSetting.worst_promo_position (populate-path off).
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


def sorting_keywords_for_v3(
    keywords: list[CalculatedKeyword],
) -> list[CalculatedKeyword]:
    """V3: сортировка по возрастанию ``pay_for_order`` (``None`` — в конец списка)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.sort_utils import (
        sort_keywords_by_pay_for_order,
    )

    return sort_keywords_by_pay_for_order(keywords)


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
    """Клавиатура списка ключей на странице кампании."""
    from . import keyword_statuses_util as k_util

    def sorting_keywords(
        kws_: list[CalculatedKeyword], sort_mode_: str
    ) -> list[CalculatedKeyword]:
        if sort_mode_ in ["by_adv", "only_out_index"]:

            kws_.sort(
                key=lambda x: x.rating or 0, reverse=True
            )

            return kws_

        elif sort_mode_ == "white_list":

            def sort_func(kw_: CalculatedKeyword) -> float:
                return kw_.rating or 0

            return sorted(kws_, key=sort_func, reverse=True)

        elif sort_mode_ == "sort_by_ctr_desc":
            return sorted(kws_, key=lambda x: x.ctr or 0, reverse=True)  # type: ignore[arg-type]
        else:
            raise ValueError(f"Unknown sort_mode: {sort_mode_}")

    start_index = (page - 1) * on_page
    end_index = start_index + on_page

    if not adv_setting.bot_active:
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
            text += format_keyword_list_target_place_suffix(keyword.target_place)
        cpm: float | None = keyword.cpm
        if cpm is not None:
            cpm_text = str(int(cpm + 0.5))
        else:
            cpm_text = "?"
        text += f"({cpm_text})"
        status_block = (
            f"{turn_on}{k_util.get_hard_status(keyword)}{k_util.get_dynamic_status(keyword)}"
        )
        if adv_setting.bot_active:
            mode_letter = keyword_strategy_letter(keyword)
            text += f"{status_block}[{mode_letter}] {keyword.text}"
        else:
            text += f"{status_block} {keyword.text}"
        conv_views_to_orders = str(round(keyword.conv_views_to_orders * 1000, 2))
        pay_for_order = (
            str(round(keyword.pay_for_order, 2))
            if keyword.pay_for_order is not None
            else "НЗ"
        )
        text += f"({conv_views_to_orders})({round(keyword.orders_per_1000_rub, 2)})({pay_for_order})"

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

    adv_id = adv_setting.adv_id
    assert adv_id

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
                text="Статистика по дням",
                callback_data=callbacks.KeywordsDailyStats(
                    adv_original_id=adv_setting.id,
                    page=1,
                    keywords_page=page,
                    sort_mode=sort_mode,
                ).pack(),
            )
        ]
    )

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


def get_keywords_daily_stats_keyboard(
    adv_original_id: int,
    page: int,
    total_pages: int,
    keywords_page: int,
    sort_mode: str,
) -> InlineKeyboardMarkup:
    """Клавиатура экрана дневной статистики ключей."""
    builder = InlineKeyboardBuilder()
    current_page = min(max(page, 1), max(total_pages, 1))
    nav_buttons: list[InlineKeyboardButton] = []

    if total_pages > 1 and current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=callbacks.KeywordsDailyStats(
                    adv_original_id=adv_original_id,
                    page=current_page - 1,
                    keywords_page=keywords_page,
                    sort_mode=sort_mode,
                ).pack(),
            )
        )
    if total_pages > 1 and current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=callbacks.KeywordsDailyStats(
                    adv_original_id=adv_original_id,
                    page=current_page + 1,
                    keywords_page=keywords_page,
                    sort_mode=sort_mode,
                ).pack(),
            )
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(
            text="К списку ключевых слов",
            callback_data=callbacks.SettingKeywords(
                adv_original_id=adv_original_id,
                type=sort_mode,
                page=keywords_page,
            ).pack(),
        )
    )
    return builder.as_markup()


def get_keyword_daily_history_keyboard(
    keyword_setting_original_id: int,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Клавиатура для постраничной истории одного ключа."""
    builder = InlineKeyboardBuilder()
    current_page = min(max(page, 1), max(total_pages, 1))
    nav_buttons: list[InlineKeyboardButton] = []

    if total_pages > 1 and current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=callbacks.KeywordDailyHistory(
                    keyword_setting_original_id=keyword_setting_original_id,
                    page=current_page - 1,
                ).pack(),
            )
        )
    if total_pages > 1 and current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=callbacks.KeywordDailyHistory(
                    keyword_setting_original_id=keyword_setting_original_id,
                    page=current_page + 1,
                ).pack(),
            )
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(
            text="К настройкам ключа",
            callback_data=callbacks.SettingKeyword(
                keyword_setting_original_id=keyword_setting_original_id,
            ).pack(),
        )
    )
    return builder.as_markup()


def get_keyword_setting_keyboard(
    keyword: KeywordSetting,
    adv_setting: AdvSetting,
    page: int,
    *,
    telegram_user_id: int | None = None,
    keyword_display_status: KeywordStatus | None = None,
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

    if keyword.hard_status != ALWAYS_ON:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Добавить в фикс.фразы (всегда вкл)",
                    callback_data=callbacks.ChangeKeywordHardStatus(
                        new_hard_status=ALWAYS_ON,
                        keyword_setting_original_id=keyword_setting_original_id,
                    ).pack(),
                )
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Убрать из фикс.фраз",
                    callback_data=callbacks.ChangeKeywordHardStatus(
                        new_hard_status=AUTO_MODE,
                        keyword_setting_original_id=keyword_setting_original_id,
                    ).pack(),
                )
            ]
        )

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

    if (
        adv_setting.bot_active
        and telegram_user_id is not None
        and is_bot_admin(telegram_user_id)
        and keyword_display_status is not None
    ):
        buttons.append(
            [
                InlineKeyboardButton(
                    text=keyword_v3_decision_trace_button_label(
                        keyword_display_status
                    ),
                    callback_data=callbacks.KeywordV3DecisionTraceOpen(
                        keyword_setting_original_id=keyword_setting_original_id,
                        page=page,
                    ).pack(),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="📅 История по дням",
                callback_data=callbacks.KeywordDailyHistory(
                    keyword_setting_original_id=keyword_setting_original_id,
                    page=1,
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
    """Build the support-channel subscription keyboard."""
    builder = InlineKeyboardBuilder()
    _ = builder.row(
        InlineKeyboardButton(text="Подписаться", url=const.SUPPORT_CHANNEL_URL)
    )
    _ = builder.row(
        InlineKeyboardButton(
            text="Проверить подписку",
            callback_data=callbacks.CheckSubscribe().pack(),
        )
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
                text="Полностью отключить бот от управления всех РК",
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
                    text="✅ Открыть гейт по Telegram ID",
                    callback_data=AdminPanel(action="grant_gate").pack(),
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

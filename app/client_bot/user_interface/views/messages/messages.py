# mypy: ignore-errors
# TODO: Глушу ошибки, их тут дофига, но надо разобраться потом
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dependency_injector.wiring import inject, Provide
from sqlalchemy import select

from app.client_bot import const
from app.client_bot.const import DEFAULT_BIDDER_STEP
from app.client_bot.user_interface import states
from app.client_bot.user_interface.message_templates.templates import (
    Text,
    TextWithImage,
    TextWithKeyboard,
    TextWithKeyboardPagination,
)
from app.client_bot.user_interface.utils import (
    format_target_place_display,
    get_effective_keyword_target_place,
    format_required_wb_token_scopes,
)
from app.client_bot.user_interface.views import callbacks, keyboards
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    KeywordSetting,
    WBBalancePayment,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

from app.modules.relevant_phrase_manager import RelevantPhraseManager
from app.client_bot.user_interface.services.keyword_v3_profile_loader import (
    load_keyword_v3_profile_data,
    profile_load_failure,
)
from app.client_bot.user_interface.views.keyword_v3_profile_ui import (
    format_keyword_v3_last_tick_executor_line,
    format_keyword_v3_profile_block,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report import (
    V3KeywordChangesRedisCache,
    V3KeywordChangesSnapshot,
)
from app.client_bot.user_interface.views.above_target_min_bid_ui import (
    format_ms_rule_line,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.automatic_version_ui import (
    normalize_automatic_version_ui,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus

from app.shared.domains.wb.enums import (
    AdvType,
)
from app.utils import redis_manager
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm

from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_value_manager import (
    RedisCommonBidValueManager,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_MAX_TEMPLATE_PREVIEW_TEXT_LEN = 1400
_TEMPLATE_EXPORT_HINT = (
    'Чтобы получить весь список, нажмите кнопку "Выгрузить фразы"'
)


def _render_phrase_templates_preview(
    *,
    title: str,
    phrases: list[str],
    update_hint: str,
) -> tuple[str, bool]:
    full_lines = [title, *phrases, "", update_hint]
    full_text = "\n".join(full_lines)
    if len(full_text) <= _MAX_TEMPLATE_PREVIEW_TEXT_LEN:
        return full_text, False

    hint_block = f"\n\n{_TEMPLATE_EXPORT_HINT}"
    max_body_len = _MAX_TEMPLATE_PREVIEW_TEXT_LEN - len(hint_block) - 1
    if max_body_len < 1:
        max_body_len = 1
    body_preview = full_text[:max_body_len].rstrip()
    return f"{body_preview}\n{hint_block}", True


def _campaign_type_display(campaign_type: AdvType | None) -> str:
    if campaign_type is None:
        return "Общий бюджет"
    if campaign_type == AdvType.SEARCH:
        return "Аукцион"
    if campaign_type == AdvType.AUTO:
        return "Авто"
    raise ValueError("Неверный тип кампании")


# def reverse_date(date_str: str) -> str:
#     parts = date_str.split("-")
#     if len(parts) == 3:
#         return "-".join(reversed(parts))
#     else:
#         raise ValueError("Неправильный формат даты. Ожидается 'дата-месяц-год'.")


class ChangeShopDefaultMaxCPMMessage(Text):
    def __init__(self, bot: Bot, chat_id: int, current_max_cpm: int):
        super().__init__(bot, chat_id)
        self._current_max_cpm = current_max_cpm

    @property
    def text(self) -> str:
        return f"Введите новое дефолтное значение максимальной ставки (CPM). Текущее значение: {self._current_max_cpm}."


class ShopNameGet(Text):
    def __init__(self, bot: Bot, chat_id: int):
        super().__init__(bot, chat_id)

    @property
    def text(self) -> str:
        return "Введите название магазина (кабинета):"


class ShopAddedSuccess(Text):
    def __init__(self, bot: Bot, chat_id: int, cabinet_name: str) -> None:
        super().__init__(bot, chat_id)
        self.__cabinet_name = cabinet_name

    @property
    def text(self) -> str:
        return (
            f"Магазин {self.__cabinet_name} успешно добавлен, идет обновление данных..."
        )


class GetApiForrbidenError(Text):
    @property
    def text(self) -> str:
        return (
        "Ключ API введен не верно или недостаточно прав для работы с рекламой."
        " Пожалуйста, создайте новый API-ключ и с нужными правами и пришлите его снова:"
    )


class GetCardsApiError(Text):
    @property
    def text(self) -> str:
        return  (
        "Ошибка настройки прав: нет доступа в контенту."
        " Пожалуйста, создайте новый API-ключ с требуемыми правами и попробуйте снова."
    )


class AdvCompanyChoicing(TextWithKeyboardPagination):
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        wb_user_cabinet_original_id: int,
        adv_settings: list[AdvSetting],
        state: FSMContext,
        page: int = 1,
    ) -> None:
        self._state = state
        super().__init__(bot, chat_id)
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._adv_settings = adv_settings
        self._page = page  # Устанавливаем страницу из параметра
        self._keywords_filter: list[str] = []  # Инициализируем фильтр ключевых слов

    @staticmethod
    async def _get_wb_cabinet(wb_cabinet_original_id: int) -> WBCabinet | None:
        async with sm() as session:
            stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet_original_id)
            result = await session.execute(stmt)
            wb_cabinet = result.scalar()
            return wb_cabinet

    async def __call__(self) -> None:
        await self._state.set_state(
            states.AdvCompanyCatalog.waiting_for_keywords_for_filter
        )
        # Сортируем кампании на активные и неактивные
        active_advs: list[AdvSetting] = []
        inactive_advs: list[AdvSetting] = []
        for adv in self._adv_settings:
            if adv.active_status and adv.bot_active:
                active_advs.append(adv)
            else:
                inactive_advs.append(adv)
        adv_settings: list[AdvSetting] = active_advs + inactive_advs
        adv_settings_filtred: list[AdvSetting] = await self._filter_advs(adv_settings)
        self._adv_settings = adv_settings_filtred
        stmt = select(WBCabinet.id).where(
            WBCabinet.wb_user_cabinets.any(
                WBUserCabinet.id == int(self._wb_user_cabinet_original_id)
            )
        )
        async with sm() as session:
            result = await session.execute(stmt)
            wb_cabinet_original_id = result.scalar()
        await self._state.update_data(
            last_wb_cabinet_original_id=wb_cabinet_original_id,
            last_wb_user_cabinet_original_id=self._wb_user_cabinet_original_id,
            last_wb_user_cabinet_page=self._page,
        )
        # DEPRECATED: set_worst_promo_position удалён; populate-path не восстанавливать
        # без отдельного product scope. AdvSetting.worst_promo_position — legacy residual.
        # self._adv_settings = await data_manager.set_worst_promo_position(self._adv_settings)

        for adv in self._adv_settings:
            adv.check_last_24_hours = await redis_manager.check_last_24_hours(adv.id)

        return await super().__call__()

    async def _filter_advs(self, adv_settings: list[AdvSetting]) -> list[AdvSetting]:
        state_data = await self._state.get_data()
        keywords_filter: list[str] = state_data.get("filter_advs", [])
        self._keywords_filter = keywords_filter
        if keywords_filter:
            clear_advs: list[AdvSetting] = []
            for adv in adv_settings:
                if (
                    not adv.bot_active
                    and adv.active_status == adv.ActiveStatuses.DONE.value
                ):
                    continue
                name = adv.name
                nmids: list[int] = list(adv.nmids)
                nmids_str = " ".join([str(nmid) for nmid in nmids])
                name = name + " " + nmids_str
                name = name.lower()
                name += str(adv.adv_id)
                for keyword_filter in keywords_filter:
                    keyword_filter = keyword_filter.strip().lower()
                    if keyword_filter in name:
                        clear_advs.append(adv)
            adv_settings = clear_advs
        return adv_settings

    @property
    def text(self) -> str:
        return (
            "Выберите рекламную кампанию для настройки или проверки. \n"
            "✅ - кампания проверялась в течение последних 24 часов\n"
            "❓ - кампания не проверялась в течение последних 24 часов\n"
            "\n📊 Активные кампании отображаются первыми\n"
            "🔄 Неактивные кампании отображаются после активных"
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_advs_keyboard_with_paginator(
            self._wb_user_cabinet_original_id,
            self._adv_settings,
            self._page,
            self.on_page,
            self._keywords_filter,
        )

    @property
    def on_page(self) -> int:
        return 20


class ShopUpdateInfo(Text):
    @property
    def text(self) -> str:
        return "Обновление данных для магазина, немного подождите..."



class CampaignActivityMenu(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, adv_setting: AdvSetting):
        super().__init__(bot, chat_id)
        self._adv_setting = adv_setting

    @property
    def text(self) -> str:
        watchdog_status = (
            "включен"
            if getattr(self._adv_setting, "auto_budget_watchdog_enabled", False)
            else "выключен"
        )
        use_common = getattr(self._adv_setting, "use_common_budget", False)
        if use_common:
            common_limit = self._adv_setting.common_budget_daily_limit or 0
            limits_block = (
                f"• Общий бюджет на обе РК: {common_limit} руб/сутки\n"
            )
        else:
            auto_limit = self._adv_setting.auto_budget_daily_limit or 0
            search_limit = self._adv_setting.search_auto_budget_daily_limit or 0
            limits_block = (
                f"• Аукцион: {search_limit} руб/сутки {'(выключено)' if search_limit <= 0 else ''}\n"
                f"• Авто: {auto_limit} руб/сутки {'(выключено)' if auto_limit <= 0 else ''}\n"
            )
        return (
            f"Управление активностью РК «{self._adv_setting.name}»\n"
            f"{limits_block}"
            f"• Контроль запуска кампаний и пополнения бюджета: {watchdog_status}\n"
            "Выберите, какую активность хотите скорректировать:"
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_campaign_activity_menu_keyboard(self._adv_setting)


class CampaignActivityTargetMenu(TextWithKeyboard):
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        adv_setting: AdvSetting,
        campaign_type: AdvType | None,
        current_limit: int,
    ):
        super().__init__(bot, chat_id)
        self._adv_setting = adv_setting
        self._campaign_type = campaign_type
        self._current_limit = current_limit

    @property
    def text(self) -> str:
        limit_str = f"{self._current_limit} руб/сутки" if self._current_limit > 0 else "выключено"
        return (
            f"Настройка лимита для {_campaign_type_display(self._campaign_type)} "
            f"РК «{self._adv_setting.name}»\n"
            f"Текущий лимит: {limit_str}\n"
            "Выберите действие:"
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_campaign_activity_target_keyboard(
            self._adv_setting, self._campaign_type, self._current_limit
        )


class CampaignActivityChangeLimit(Text):
    def __init__(self, bot: Bot, chat_id: int, campaign_type: AdvType | None):
        super().__init__(bot, chat_id)
        self._campaign_type = campaign_type

    @property
    def text(self) -> str:
        return (
            f"Введите новый лимит для {_campaign_type_display(self._campaign_type)} "
            "в рублях (целое положительное число):"
        )


class StrategyMenuMessage(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, adv_setting: AdvSetting):
        super().__init__(bot, chat_id)
        self._adv_setting = adv_setting

    @property
    def text(self) -> str:
        # None means auto-enabled (same as True); only False is manual
        auto_update_strategy = (
            getattr(self._adv_setting, "auto_update_strategy", True) is not False
        )
        current_strategy = self._adv_setting.strategy or Strategy.MIN_CPO
        mode_label = "Автоматический" if auto_update_strategy else "Ручной"
        if current_strategy == Strategy.MIN_CPO:
            strategy_label = "MIN_CPO (мин себестоимость заказа)"
        else:
            strategy_label = "MAX_CONV (максимум конверсии)"

        return (
            f"Стратегия кампании «{self._adv_setting.name}»\n"
            f"Текущий режим: {mode_label}\n"
            f"Текущая стратегия: {strategy_label}\n\n"
            "Как это работает:\n"
            "• MIN_CPO — приоритет минимальной себестоимости заказа.\n"
            "• MAX_CONV — приоритет максимальной конверсии/объема заказов.\n"
            "• В авто-режиме бот сам переключает стратегию по факту выполнения плана,\n"
            "  целевой себестоимости и состоянию кампании.\n"
            "• В ручном режиме стратегия фиксируется вручную и не переключается автоматически.\n\n"
            "Рекомендуется держать авто-режим включенным и переходить в ручной только для\n"
            "временных гипотез/тестов."
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_strategy_menu_keyboard(self._adv_setting)


class CabinetNameExists(Text):
    @property
    def text(self) -> str:
        return "Кабинет с таким именем уже существует, введите другое имя для кабинета:"

class CabinetExistsForUser(Text):
    @property
    def text(self) -> str:
        return "Этот кабинет уже был добавлен вам ранее. Сейчас я предоставлю вам его..."


class NotValideToken(Text):
    @property
    def text(self) -> str:
        return  "Вы ввели что-то не то. Попробуйте снова:"


class ApiForrbidenError(Text):
    def __init__(self, bot: Bot, chat_id: int, wb_user_cabinet: WBUserCabinet):
        super().__init__(bot, chat_id)
        self.__wb_user_cabinet = wb_user_cabinet

    @property
    def text(self) -> str:
        return (
        "Ошибка настройки прав: нет доступа в рекламе. Пожалуйста, "
        "создайте новый API-ключ с требуемыми правами и добавьте кабинет снова. "
        "Все ваши настройки будут сохранены"
    )


class AddNewTokenGet(TextWithImage):
    def __init__(self, bot: Bot, chat_id: int, cabinet_name: str):
        self.__cabinet_name = cabinet_name
        super().__init__(bot, chat_id)

        self._image = "app/client_bot/images/static/api_setting.png"

    @property
    def text(self) -> str:
        return (
            f"""Пришлите новый ПЕРСОНАЛЬНЫЙ Api ключ дла магазина (кабинета) {self.__cabinet_name}.\n"""
            """Создайте токен в кабинете WB.\n"""
            """Для безопасного первого входа можно использовать токен только для чтения.\n"""
            """С токеном только для чтения бот покажет аналитику, магазины и кампании, но не будет менять рекламу.\n"""
            """Для ручного управления ставками нужен токен с возможностью изменений в кабинете.\n"""
            f"{format_required_wb_token_scopes()}\n"
        )

    @property
    def image(self) -> str:
        return self._image

    @image.setter
    def image(self, value: str) -> None:
        self._image = value


# TODO: Навести порядок с БД мастер-репликами


class GetMinCtr(Text):
    def __init__(self, bot: Bot, chat_id: int, adv: AdvSetting):
        self.__adv = adv
        super().__init__(bot, chat_id)

    @property
    def text(self) -> str:
        return (
            f"Введите новое значение минимального CTR для кампании {self.__adv.name}:"
        )


class CabinetExistsInSystem(Text):
    @property
    def text(self) -> str:
        return "Этот кабинет уже существует в системе, мы его добавим вам..."


class WrongMinCTR(Text):
    @property
    def text(self) -> str:
        return  "Минимальный CTR должен быть числом от 0 до 100. Попробуйте снова:"


class MinCTRChanged(Text):
    @property
    def text(self) -> str:
        return "Минимальный CTR успешно изменен!"


class CabinetNameTooLong(Text):
    @property
    def text(self) -> str:
        return "Название кабинета слишком длинное. Попробуйте снова(не более 50 символов):"

class KeywordSettingMessage(TextWithKeyboard):
    parse_mode = ParseMode.MARKDOWN

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        keyword_setting_id: int,
        last_page: int = 1,
        *,
        telegram_user_id: int | None = None,
    ):
        super().__init__(bot, chat_id)
        self._keyword_original_id = keyword_setting_id
        self._page = last_page
        self._chat_id = chat_id
        self._telegram_user_id = telegram_user_id
        self._v3_profile_block: str | None = None
        self._v3_keyword_changes: V3KeywordChangesSnapshot | None = None


    @staticmethod
    async def _get_calculated_keyword(
        adv_id: int, text: str
    ) -> CalculatedKeyword | None:
        redis_manager_ = RedisCalculatedKeywordsCacheManager()
        keyword = await redis_manager_.get_calculated_keyword(adv_id, text)
        return keyword

    @staticmethod
    async def _get_keyword_text_and_adv_id(keyword_original_id: int,) -> tuple[KeywordSetting, AdvSetting]:
        # TODO: Поймали ошибку в рантайме
        stmt = select(KeywordSetting, AdvSetting)\
        .join(KeywordSetting.adv_setting)\
        .where(KeywordSetting.id == keyword_original_id)
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            result_row = result.first()
        if not result_row:
            raise ValueError('Не найдены данные о ключе')
        keyword: KeywordSetting = result_row[0]
        adv: AdvSetting = result_row[1]
        return keyword, adv


    @inject
    async def __call__(
        self,
    ) -> None:
        keyword_setting, adv_setting = await self._get_keyword_text_and_adv_id(self._keyword_original_id)
        self._keyword_setting = keyword_setting
        keywords_redis_cache_manager = RedisCalculatedKeywordsCacheManager()
        keyword: CalculatedKeyword = await keywords_redis_cache_manager.get_calculated_keyword(adv_setting.adv_id,
                                                                                               keyword_setting.text)

        calculated_keyword = keyword
        self._calculated_keyword = calculated_keyword
        self._adv_setting = adv_setting
        self.position = calculated_keyword.position
        self.last_full_update = calculated_keyword.timestamp

        self.clicks = keyword.clicks
        self.views = keyword.views
        self.fact_ctr = keyword.ctr

        self.spend = keyword.spend

        if normalize_automatic_version_ui(adv_setting.automatic_version) == 3:
            try:
                profile_data = await load_keyword_v3_profile_data(
                    adv_setting, calculated_keyword
                )
            except Exception:
                logger.exception(
                    "v3 keyword profile: unexpected load error adv_id=%s keyword=%s",
                    adv_setting.adv_id,
                    calculated_keyword.text,
                )
                profile_data = profile_load_failure(
                    calculated_keyword,
                    reason="ошибка загрузки профиля",
                )
            self._v3_profile_block = format_keyword_v3_profile_block(profile_data)
            self._v3_keyword_changes = await V3KeywordChangesRedisCache(adv_setting).get()

        return await super().__call__()

    @property
    def calculated_keyword(self) -> CalculatedKeyword:
        return self._calculated_keyword

    @staticmethod
    def get_str_rus_hard_status(int_hard_status: int) -> str:
        if int_hard_status == 0:
            return "Список не релевантных фраз"
        elif int_hard_status == 1:
            return "Авто"
        elif int_hard_status == 2:
            return "Белый список"
        elif int_hard_status == 3:
            return "Отключен"
        elif int_hard_status == 4:
            return "Фикс.фразы (всегда вкл)"
        raise ValueError(f"Неизвестный хард-статус ключа: {int_hard_status}")

    def _display_status_from_db_and_cache(self) -> KeywordStatus:
        """Текущий статус для отображения: из БД (keyword_setting) для 0/3/4, иначе из кеша."""
        hard = self._keyword_setting.hard_status
        if hard == 4:
            return KeywordStatus.GOOD
        if hard == 3:
            return KeywordStatus.BAD
        if hard == 0:
            return KeywordStatus.BAD
        return self._calculated_keyword.status

    @property
    def text(self) -> str:
        keyword_text = self._keyword_setting.text
        keyword_text = re.sub(r"([_*[\]()~>`#+\-=|{}.!])", r"\\\1", keyword_text)  # type: ignore
        nmids = list(self._adv_setting.nmids)
        nmids = [str(nmid) for nmid in nmids]
        nmids_str = ", ".join(nmids)
        value, source = get_effective_keyword_target_place(
            self._keyword_setting, self._adv_setting
        )
        target_place_value, target_place_source = format_target_place_display(
            value, source
        )
        hard_status_for_display = self._keyword_setting.hard_status
        display_status = self._display_status_from_db_and_cache()
        text = (
            f"📦 *Артикул:* {nmids_str}\n"
            f"⚙️ *Хард-статус:* {self.get_str_rus_hard_status(hard_status_for_display)}\n"
            f"🔄 *Текущий статус ключа:* {display_status}\n\n"
            f"🔑 *Ключевое слово и настройки:*\n{keyword_text}\n"
            f"📊 *Показы:* {self.views}\n"
            f"🖱 *Клики:* {self.clicks}\n"
            f"📈 *Фактический CTR:* {self.fact_ctr * 100:.2f}%\n"
            f"💰 *Расход:* {self.spend:.2f} ₽\n"
        )

        text += f'Заказов на 1000 показов: {round(self._calculated_keyword.conv_views_to_orders * 1000, 2)}\n'
        text += f"Заказов на 1000₽: {round(self._calculated_keyword.orders_per_1000_rub, 2)}\n"
        pay_for_order = self._calculated_keyword.pay_for_order
        if pay_for_order is not None:
            pay_for_order_str = f"{pay_for_order:.2f}"
        else:
            pay_for_order_str = 'Не определен (нет заказов)'
        text += f'Себес. заказа: {pay_for_order_str}\n'
        text += (
            format_ms_rule_line(
                self._calculated_keyword.above_target_min_bid,
                card_target_place=value,
                card_target_source=source,
            )
            + "\n"
        )

        if self._adv_setting.rec_system_mode and self._calculated_keyword.above_rec_conversion is not None:
            rec_str = "да" if self._calculated_keyword.above_rec_conversion else "нет"
            text += f"Выше конв. рек.: {rec_str}\n"

        if normalize_automatic_version_ui(self._adv_setting.automatic_version) == 3:
            executor_line = format_keyword_v3_last_tick_executor_line(
                keyword_setting_id=self._keyword_original_id,
                keyword_changes=self._v3_keyword_changes,
            )
            if executor_line:
                text += executor_line
            if self._v3_profile_block:
                text += self._v3_profile_block

        pos = self.position
        if pos > 0:
            text += f"📈 *Позиция:* {round(pos)}\n"
        else:
            text += "📈 *Позиция:* Нет на сайте\n"
        text +=  f"🎯 *Целевая позиция:* {target_place_value} ({target_place_source})\n"

        def _cpm_line(label: str, cpm: int | float | None, dt: datetime | None) -> str:
            if cpm is not None:
                val = round(cpm)
                date_str = dt.strftime("%d-%m-%Y %H:%M") if dt else ""
                return f"{label}: {val}" + (f" ({date_str})" if date_str else "") + "\n"
            return f"{label}: —\n"

        kw = self._calculated_keyword
        text += _cpm_line(
            "Установленная ставка CPM",
            kw.cpm_set_bid,
            kw.cpm_set_bid_date,
        )
        text += _cpm_line("CPM из API", kw.cpm_from_api, None)
        text += _cpm_line("Расчетная CPM", kw.cpm_from_bid_log, kw.cpm_from_bid_log_date)
        text += _cpm_line("CPM из исходной статистики", kw.cpm_from_stats, kw.cpm_from_stats_date)
        return text

    @property
    def keyboard(self):
        return keyboards.get_keyword_setting_keyboard(
            self._keyword_setting,
            self._adv_setting,
            self._page,
            telegram_user_id=self._telegram_user_id,
            keyword_display_status=self._display_status_from_db_and_cache(),
        )


class KeywordTargetPlacePrompt(Text):
    """Prompt for changing a keyword target place manually."""

    def __init__(self, bot: Bot, chat_id: int, current_value: str, adv_default: str):
        super().__init__(bot, chat_id)
        self._current_value = current_value
        self._adv_default = adv_default

    @property
    def text(self) -> str:
        return (
            f"Текущая целевая позиция: {self._current_value}.\n"
            "Целевая позиция — место, которое вы хотите удерживать по ключу.\n"
            f"Введите новое целое число (0 — использовать позицию кампании {self._adv_default})."
        )


class KeywordTargetPlaceUpdated(Text):
    """Confirmation after a manual keyword target place change."""

    def __init__(self, bot: Bot, chat_id: int, new_value: str):
        super().__init__(bot, chat_id)
        self._new_value = new_value

    @property
    def text(self) -> str:
        return f"Целевая позиция обновлена: {self._new_value}."


class GetNameOfNewAdvCompany(Text):
    @property
    def text(self) -> str:
        return "Введите название новой рекламной кампании, максимум 128 символов:"


class TooLongNameOfNewAdvCompany(Text):
    @property
    def text(self)-> str:
        return "Название кампании слишком длинное. Попробуйте снова, должно быть не более 128 символов:"


class GetNmidOfNewAdvCompany(Text):
    @property
    def text(self)-> str:
        return ("Какие товары добавить в кампанию? Вы можете указать несколько товаров"
        "В качестве разделителя можете использовать пробел, запятую, точку с запятой или точку."
        "Указать можно артикулы WB или ваши артикулы. По возможности не создавайте РК более, "
        "чем на один товар:")


class NotFoundNmidOfNewAdvCompany(Text):
    def __init__(self, bot: Bot, chat_id: int, not_found_items: list[str]):
        self.__not_found_items = not_found_items
        super().__init__(bot, chat_id)

    @property
    def text(self) -> str:
        return f"Товары с идентификаторами {', '.join(self.__not_found_items)} не найдены. Попробуйте снова:"


class LongTimeOperation(Text):
    @property
    def text(self)-> str:
        return "Операция может занять некоторые время, пожалуйста, подождите..."


class NeedSubscribe(TextWithKeyboard):
    @property
    def text(self) -> str:
        return (
            "Для использования функций вы должны быть подписаны на канал службы поддержки.\n\n"
            "Подпишитесь на канал, затем нажмите «Проверить подписку». "
            "После проверки бот откроет доступ к функциям."
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_subscribe_keyboard()


class OrderSubscribe(Text):
    @property
    def text(self) -> str:
        return (f"Не работает оплата?\n"
                f"Напишите сразу {const.SUPPORT_LINK} — пришлю рабочую ссылку, оплатите без проблем")



class ExpiredSubscription(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, wb_cabinet_original_id: int):
        self._wb_cabinet_original_id = wb_cabinet_original_id
        super().__init__(bot, chat_id)

    async def __call__(self) -> None:
        async with sm() as session:
            stmt = select(WBCabinet).where(WBCabinet.id == self._wb_cabinet_original_id)
            result = await session.execute(stmt)
            self._wb_cabinet = result.scalar()
        return await super().__call__()

    @property
    def text(self) -> str:
        return """
            Не достаточно средств для продолжения работы бота. Пополните баланс.
            """

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        # Проверка на None для self._wb_cabinet перед доступом к .id
        cabinet_id = (
            self._wb_cabinet_original_id
        )  # Если wb_cabinet_original_id гарантированно int
        return keyboards.get_payment_keyboard(
            wb_cabinet_original_id=cabinet_id,
        )

class SettingMinViewsForPredictCTR(TextWithKeyboard):
    async def __call__(self, adv_original_id: int):
        async with sm() as session:
            result = await session.execute(
                select(AdvSetting).where(AdvSetting.id == adv_original_id)
            )
            adv: AdvSetting  = result.scalar()
        self._adv: AdvSetting = adv
        return await super().__call__()

    @property
    def text(self):
        return (
            f"Введите минимальное количество показов для прогноза CTR роботом для кампании {self._adv.name}.\n"
            f"Текущее значение: {self._adv.min_views_for_ml_predict}.\n"
        )

    @property
    def keyboard(self):
        return keyboards.get_setting_min_views_for_predict_ctr_keyboard(self._adv)


class IncorrectMinViewsForPredictCTR(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, adv: AdvSetting):
        super().__init__(bot, chat_id)
        self._adv = adv

    @property
    def text(self) -> str:
        return "Минимальное количество показов должно быть целым числом от 0 и больше. Попробуйте снова:"

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_setting_min_views_for_predict_ctr_keyboard(self._adv)


class NotKeywordHistoryPositions(Text):
    @property
    def text(self) -> str:
        return "Не удалось получить историю позиций ключевых слов для этой кампании"

class NotEnoughMoneyForParsing(TextWithKeyboard):
    def __init__(self, bot: Bot, chat_id: int, wb_cabinet_original_id: int):
        super().__init__(bot, chat_id)
        self._wb_cabinet_original_id = wb_cabinet_original_id

    @property
    def text(self) -> str:
        return """Не достаточный баланс для парсинга ключевых слов. Пополните баланс и попробуйте снова"""

    @property
    def keyboard(self):
        return keyboards.get_payment_keyboard(self._wb_cabinet_original_id)


# class CallMe1(TextWithKeyboard):
#     text = """
# Вдогонку к предыдущему сообщению:
# Если я не прочитал ваше сообщение, то значит очередь до вас еще не дошла - я специально не просматриваю и не отвечаю, чтобы никого случайно не пропустить.
# Чтобы полноценно рассказать про использование бота для максимально эффективного продвижения на WB и ответить на ваши вопросы нужно в среднем 40-50 минут, поэтому обещанные 10 консультаций я смогу провести только в течении 2-3 дней.
# Прошу набраться терпения - оно того стоит!
# Если успели написать до момента отправки этого сообщения - то вы точно успели и не переживайте: дойду и до вас!
# Если не успели: осталась буквально пара мест, так что скорее напишите мне,чтобы занять место и получить тест-драйв бота!
#
# """
#     @property
#     def keyboard(self) -> InlineKeyboardMarkup:
#         return keyboards.get_call_me_keyboard()


class WaitingForWhitePhrases(TextWithKeyboard):
    async def __call__(self, adv_setting_id: int):
        self.adv_setting_id: int = adv_setting_id
        await super().__call__()

    @property
    def text(self):
        return """
Отправьте мне список фраз (через перенос) которые вы хотите добавить в белый список (фразы для продвижения).
Например:

платье женское
платье вечернее
платье летнее

Я автоматически добавлю эти ключи в белый список. Учитывается точное соответствие.

    """

    @property
    def keyboard(self):
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)


class WhitePhrasesAdded(TextWithKeyboard):
    async def __call__(self, adv_setting_id: int):
        self.adv_setting_id: int = adv_setting_id
        await super().__call__()

    @property
    def text(self) -> str:
        return "Фразы добавлены в белый список, можете ввести еще фразы или вернуться в настройки РК"

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)


class WaitingForFixedPhrases(TextWithKeyboard):
    async def __call__(self, adv_setting_id: int):
        self.adv_setting_id: int = adv_setting_id
        await super().__call__()

    @property
    def text(self):
        return """
Отправьте список фраз (через перенос строки), которые нужно добавить в фикс.фразы (всегда вкл).
Например:

платье женское
платье вечернее

Фразы будут всегда включены и не зависят от белого списка. Учитывается точное соответствие.
"""

    @property
    def keyboard(self):
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)


class FixedPhrasesAdded(TextWithKeyboard):
    async def __call__(self, adv_setting_id: int):
        self.adv_setting_id: int = adv_setting_id
        await super().__call__()

    @property
    def text(self) -> str:
        return "Фразы добавлены в фикс.фразы (всегда вкл). Можете ввести ещё или вернуться в настройки РК"

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)


class CPMSetting(TextWithKeyboard):
    """Bidder settings screen for manual CPM and target place tools."""

    @inject
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        redis_client: RedisClient = Provide["redis_client_wrapper"],
    ) -> None:
        super().__init__(bot, chat_id)
        self._redis_common_bid_value_manager = RedisCommonBidValueManager(redis_client)
        self._last_saved_bids: dict[int, int] = {}

    async def __call__(self, adv_setting_id: int) -> None:
        async with sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
            result = await session.execute(stmt)
            adv_setting = result.scalars().first()
        if adv_setting is None:
            raise RuntimeError(f"AdvSetting с id {adv_setting_id} не найден")
        self.adv_setting = adv_setting
        search_adv_id = adv_setting.search_adv_id
        nmids = adv_setting.nmids or []
        self._last_saved_bids = {}
        if search_adv_id is not None and nmids:
            self._last_saved_bids = await self._redis_common_bid_value_manager.get_bids(
                search_adv_id, nmids
            )
        await super().__call__()

    @property
    def text(self) -> str:
        mode = "Ручной" if not self.adv_setting.bidder_active else "Автоматический"
        text = (
            f"Режим управления ставкой: {mode}\n\n"
            "Целевая позиция — место, которое вы хотите удерживать по ключу.\n"
            "Max CPM — верхний предел ставки. Бот не должен ставить выше этого значения.\n"
            "Это Бесплатный инструмент.\n\n"
        )
        if self.adv_setting.bidder_active:
            max_place = (
                str(self.adv_setting.max_place)
                if self.adv_setting.max_place is not None
                else "Не задано"
            )
            max_cpm = (
                str(self.adv_setting.max_cpm)
                if self.adv_setting.max_cpm is not None
                else "Не задана"
            )
            text += (
                f"Целевое место место: {max_place}\n"
                f"Максимальная ставка: {max_cpm}\n"
            )
            text += self._format_last_saved_bids()
        return text

    def _format_last_saved_bids(self) -> str:
        header = "Последняя ставка (по артикулам):"
        if not self._last_saved_bids:
            return f"{header} Нет данных\n"
        lines = [header]
        for nmid in sorted(self._last_saved_bids):
            lines.append(f"{nmid}: {self._last_saved_bids[nmid]}")
        return "\n".join(lines) + "\n"

    @property
    def keyboard(self):
        builder = InlineKeyboardBuilder()

        if self.adv_setting.bidder_active:
            bottom = InlineKeyboardButton(
                text="Выключить автоматическое управление ставкой",
                callback_data=callbacks.CPMSettingMenu(
                    action="off_auto_cpm", adv_original_id=self.adv_setting.id
                ).pack(),
            )
        else:
            bottom = InlineKeyboardButton(
                text="Включить автоматическое управление CPM",
                callback_data=callbacks.CPMSettingMenu(
                    action="set_auto_cpm", adv_original_id=self.adv_setting.id
                ).pack(),
            )

        builder.row(bottom)

        button_text = (
            "Выключить управление ставкой для Авто"
            if self.adv_setting.bidder_for_auto
            else "Включить управление ставкой для Авто"
        )
        callback_action = (
            "off_bidder_for_auto"
            if self.adv_setting.bidder_for_auto
            else "on_bidder_for_auto"
        )

        bottom = InlineKeyboardButton(
            text=button_text,
            callback_data=callbacks.CPMSettingMenu(
                action=callback_action, adv_original_id=self.adv_setting.id
            ).pack(),
        )

        builder.row(bottom)


        bottom = InlineKeyboardButton(
            text="Изменить Максимальную ставку",
            callback_data=callbacks.CPMSettingMenu(
                action="set_manual_cpm", adv_original_id=self.adv_setting.id
            ).pack(),
        )

        _ = builder.row(bottom)

        step = self.adv_setting.bidder_step
        step = step if step else DEFAULT_BIDDER_STEP
        bottom = InlineKeyboardButton(
            text=f"Изменить Максимальный шаг ставки ({step})",
            callback_data=callbacks.CPMSettingMenu(
                action="change_cpm_step", adv_original_id=self.adv_setting.id
            ).pack(),
        )

        builder.row(bottom)

        if not self.adv_setting.auto_update_target_place:
            bottom = InlineKeyboardButton(
                text="Изменить целевую позицию",
                callback_data=callbacks.CPMSettingMenu(
                    action="set_max_position", adv_original_id=self.adv_setting.id
                ).pack(),
            )
            builder.row(bottom)

            bottom = InlineKeyboardButton(
                text="Скачать шаблон целевых позиций",
                callback_data=callbacks.CPMSettingMenu(
                    action="download_target_places_template",
                    adv_original_id=self.adv_setting.id,
                ).pack(),
            )
            builder.row(bottom)

            bottom = InlineKeyboardButton(
                text="Загрузить целевые позиции из файла",
                callback_data=callbacks.CPMSettingMenu(
                    action="upload_target_places_template",
                    adv_original_id=self.adv_setting.id,
                ).pack(),
            )
            builder.row(bottom)

        bottom = InlineKeyboardButton(
            text="К настройкам АРК",
            callback_data=callbacks.Adv(adv_original_id=self.adv_setting.id).pack(),
        )
        builder.row(bottom)

        return builder.as_markup()


class AutoCPMSettingGetMinPosition(Text):
    """Prompt asking for the desired target place for the bidder."""

    async def __call__(self, adv_setting_id: int):
        async with sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.id == adv_setting_id)
            result = await session.execute(stmt)
            adv_setting = result.scalars().first()
        self.adv_setting = adv_setting
        await super().__call__()

    @property
    def text(self):
        return (
            "Введите целевую позицию, которую вы хотите занимать\n"
            "целевая позиция — место, которое вы хотите удерживать по ключу.\n"
            "Это Бесплатный инструмент."
        )


class AutoCPMSettingGetMaxCPM(Text):
    """Prompt asking for the manual upper CPM limit."""

    @property
    def text(self) -> str:
        return (
            "Укажите Max CPM.\n"
            "Max CPM — верхний предел ставки. Бот не должен ставить выше этого значения.\n"
            "Это Бесплатный инструмент."
        )


class ManualCPMSetting(Text):
    """Prompt asking for a manual Max CPM value."""

    @property
    def text(self) -> str:
        return (
            "Укажите Max CPM (целое число от 100).\n"
            "Max CPM — верхний предел ставки. Бот не должен ставить выше этого значения.\n"
            "Это Бесплатный инструмент. "
        )


class WaitingForBlackPhrases(TextWithKeyboard):
    async def __call__(self, adv_setting_id: int):
        self.adv_setting_id: int = adv_setting_id
        async with sm() as session:
            adv: AdvSetting | None = await session.get(
                AdvSetting, self.adv_setting_id
            )  # Изменено
        if adv is None:
            raise ValueError(
                f"AdvSetting с id {self.adv_setting_id} не найден."
            )  # Изменено
        rel_manager = RelevantPhraseManager(adv)

        black_phrases: list[str] | None = await rel_manager.get_relevant_template_data()
        self.black_phrases = black_phrases
        return await super().__call__()

    @property
    def text(self) -> str:
        if self.black_phrases:
            text, _ = _render_phrase_templates_preview(
                title="Текущий черный список:",
                phrases=self.black_phrases,
                update_hint=(
                    "Чтобы обновить фразы, отправьте список еще раз. "
                    "Список будет обновлен."
                ),
            )
            return text
        else:
            return (
                "Укажите через перенос строки шаблоны для черного списка (исключение из продвижения).\n\n"
                "Строка без кавычек — regex в синтаксисе RE2 (подмножество Python: без обратных ссылок и lookaround; поиск без учета регистра). "
                "Строка в кавычках \"...\" или '...' (кавычка с начала или с конца) — точное совпадение "
                "фразы без учета регистра.\n\n"
                "Пример:\n"
                "платье.*летн\n"
                "дешев|подделк\n"
                '"женское летнее"\n\n'
                "Кнопка «Протестировать» — проверить список фраз по уже сохраненным правилам."
            )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="Протестировать",
                callback_data=callbacks.TestBlackPhrasesTemplates(
                    adv_setting_id=self.adv_setting_id
                ).pack(),
            )
        )

        if self.black_phrases:
            builder.row(
                InlineKeyboardButton(
                    text="Сбросить черный список",
                    callback_data=callbacks.ResetBlackPhrases(
                        adv_setting_id=self.adv_setting_id
                    ).pack(),
                )
            )
            builder.row(
                InlineKeyboardButton(
                    text="Выгрузить фразы",
                    callback_data=callbacks.ExportBlackPhrases(
                        adv_setting_id=self.adv_setting_id
                    ).pack(),
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="Вернуться в настройки РК",
                callback_data=callbacks.Adv(adv_original_id=self.adv_setting_id).pack(),
            )
        )
        return builder.as_markup()


class WaitingForRelevantPhraseTemplates(TextWithKeyboard):
    """Экран редактирования шаблонов релевантных фраз (зеркало WaitingForBlackPhrases)."""

    async def __call__(self, adv_setting_id: int) -> None:
        self.adv_setting_id: int = adv_setting_id
        async with sm() as session:
            adv: AdvSetting | None = await session.get(
                AdvSetting, self.adv_setting_id
            )
        if adv is None:
            raise ValueError(
                f"AdvSetting с id {self.adv_setting_id} не найден."
            )
        rel_manager = RelevantPhraseManager(adv)
        self.relevant_phrases: list[str] | None = (
            await rel_manager.get_relevant_phrases_template_data()
        )
        return await super().__call__()

    @property
    def text(self) -> str:
        if self.relevant_phrases:
            text, _ = _render_phrase_templates_preview(
                title="Текущие шаблоны релевантных фраз:",
                phrases=self.relevant_phrases,
                update_hint=(
                    "Чтобы обновить, отправьте список ещё раз — "
                    "он будет заменён."
                ),
            )
            return text
        return (
            "Укажите через перенос строки шаблоны для автоматической пометки "
            "фраз как релевантных.\n\n"
            "Строка без кавычек — regex в синтаксисе RE2 (подмножество Python: "
            "без обратных ссылок и lookaround; поиск без учета регистра). "
            "Строка в кавычках \"...\" или '...' — точное совпадение фразы "
            "без учета регистра.\n\n"
            "Пример:\n"
            "платье.*женск\n"
            "летн|вечерн\n"
            '"сарафан летний"\n\n'
            "Кнопка «Протестировать» — проверить фразы по уже сохранённым правилам.\n\n"
            "При включённом режиме «только релевантные фразы» эти шаблоны задают "
            "релевантность новых ключей; шаблоны чёрного списка в этом режиме не "
            "применяются."
        )

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="Протестировать",
                callback_data=callbacks.TestRelevantPhraseTemplates(
                    adv_setting_id=self.adv_setting_id
                ).pack(),
            )
        )
        if self.relevant_phrases:
            builder.row(
                InlineKeyboardButton(
                    text="Сбросить шаблоны релевантных фраз",
                    callback_data=callbacks.ResetRelevantPhraseTemplates(
                        adv_setting_id=self.adv_setting_id
                    ).pack(),
                )
            )
            builder.row(
                InlineKeyboardButton(
                    text="Выгрузить фразы",
                    callback_data=callbacks.ExportRelevantPhraseTemplates(
                        adv_setting_id=self.adv_setting_id
                    ).pack(),
                )
            )
        builder.row(
            InlineKeyboardButton(
                text="Вернуться в настройки РК",
                callback_data=callbacks.Adv(adv_original_id=self.adv_setting_id).pack(),
            )
        )
        return builder.as_markup()


class FilterByQuery(Text):

    @property
    def text(self) -> str:
        return """ Введите минимальное число прогнозируемых показов для показа (0 - без фильтрации):"""


class KeywordStatUpdated(Text):
    @property
    def text(self) -> str:
        return """Статистика из WB успешно загружена, подгружаю страницу"""


class MinusKeywordsUpdated(Text):
    @property
    def text(self) -> str:
        return "Минус-слова успешно обновлены, подгружаю страницу"


class WhiteListReset(Text):
    @property
    def text(self) -> str:
        return "Белый список успешно сброшен"


class RelevantPhrasesAdded(TextWithKeyboard):
    def __init__(
        self, bot: Bot, user_telegram_id: int, adv_setting_id: int
    ):  # Изменено
        self.adv_setting_id = adv_setting_id
        super().__init__(bot, user_telegram_id)

    @property
    def text(self) -> str:
        return "Фразы успешно добавлены в бот (авто) список"

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.get_return_to_adv_setting_keyboard(self.adv_setting_id)


class WaitingForRelevantPhrases(Text):
    @property
    def text(self) -> str:
        return "Введите фразы, которые вы хотите добавить в кампанию в качестве релевантных фраз:"


class RelevantPhraseManagementMenuMessage(TextWithKeyboard):
    parse_mode = ParseMode.HTML

    def __init__(self, bot: Bot, chat_id: int, adv: AdvSetting):
        super().__init__(bot, chat_id)
        self._adv = adv

    @property
    def text(self) -> str:
        only_relevant = bool(getattr(self._adv, "auto_add_only_relevant_phrase", False))
        text = (
           """
           Внимание, пожалуйста, прочитайте, как именно работает управление релевантными и нерелевантными фразами.

Есть два режима управления фразами.

<b>Обычный режим</b> используется по умолчанию. В этом режиме бот может автоматически добавлять новые фразы, кроме тех, которые заранее помечены как нерелевантные.

<b>Нерелевантные фразы</b> — это фразы, которые явно не относятся к товару или могут ввести покупателя в заблуждение. Лучше добавлять сюда только те фразы, которые на 100% не подходят товару или даже противоречат ему. Например, пользователь может перейти по такой фразе, случайно купить товар, а потом понять, что это не то, что он искал.

Не стоит добавлять в нерелевантные все фразы, которые просто кажутся сомнительными. Часто фраза выглядит нерелевантной, но на практике даёт корзины и заказы. С такими фразами бот обычно разберётся сам по статистике, если у вас выставлена нормальная максимальная себестоимость заказа.

В обычном режиме используются кнопки управления нерелевантными фразами и шаблонами нерелевантных фраз.

<b>Режим «только релевантные фразы»</b> работает строже. В этом режиме бот может автоматически добавлять только те фразы, которые уже помечены как релевантные.

Если включить этот режим, но не настроить релевантные фразы или шаблоны релевантных фраз, автоматическое добавление новых фраз может фактически остановиться.

В режиме «только релевантные фразы» используются кнопки управления релевантными фразами и шаблонами релевантных фраз.

Переключение режима меняет набор кнопок ниже.

Белый список и ручное добавление фраз в белый список для этой задачи не рекомендуются. Лучше использовать релевантные/нерелевантные фразы и шаблоны.


           """
        )

        text += '🚨'
        if only_relevant:
            text += "Сейчас включен режим «только релевантные фразы»."
        else:
            text += "Сейчас включен обычный режим с нерелевантными фразами."
        return text

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.keyboard import (
            get_relevant_phrase_management_keyboard,
        )

        return get_relevant_phrase_management_keyboard(self._adv)


async def process_cabinet_balance_topup(
    user_id: int, cabinet_id: int, amount: float
) -> WBBalancePayment:
    """Обработка запроса на пополнение баланса кабинета"""
    async with sm() as session:
        # Получаем пользователя для описания платежа
        user = await session.get(User, user_id)
        if not user:
            raise ValueError("Пользователь не найден")

        # Создаем запись о платеже
        payment = WBBalancePayment(
            wb_cabinet_id=cabinet_id,
            amount=amount,
            description=f"Пополнение баланса пользователем {user.username or user.user_telegram_id}",
            transaction_date_time=datetime.now(),
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment


async def confirm_cabinet_balance_topup(
    payment_id: int, cabinet_id: int
) -> tuple[WBBalancePayment, WBCabinet]:
    """Подтверждение платежа и обновление баланса кабинета"""
    async with sm() as session:
        # Получаем платеж
        payment: WBBalancePayment | None = await session.get(
            WBBalancePayment, payment_id
        )
        if not payment or payment.wb_cabinet_id != cabinet_id:
            raise ValueError("Платеж не найден или не соответствует кабинету")

        # Получаем кабинет
        cabinet: WBCabinet | None = await session.get(WBCabinet, cabinet_id)
        if not cabinet:
            raise ValueError("Кабинет не найден")

        # Обновляем баланс кабинета
        cabinet.balance += payment.amount

        await session.commit()
        await session.refresh(payment)
        await session.refresh(cabinet)
        return payment, cabinet

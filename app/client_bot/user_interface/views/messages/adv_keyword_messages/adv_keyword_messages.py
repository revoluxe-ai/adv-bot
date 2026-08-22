import logging
import typing
from datetime import datetime

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from dependency_injector.wiring import Provide, inject
from sqlalchemy import select
from app.utils.db.session_maker import get_async_session_maker as sm
from app.client_bot.message_manager import LastMessage
from app.client_bot.user_interface.message_templates import (
    TextWithKeyboardAndImage,
)
from app.client_bot.user_interface.views import keyboards
from app.client_bot.user_interface.views.messages.strategy_display import (
    format_adv_strategy,
)
from app.client_bot.user_interface.services.keyword_v3_ui_sort import (
    enrich_keywords_v3_list_profiles,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.sort_utils import (
    sort_keywords_by_pay_for_order,
)
from app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager import (
    CommonStatDataManager,
)
from app.client_bot.user_interface.views.messages.positions_graphic_messanges.positions_graphic_messanges import (
    KeywordGraphicPart_1,
)
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_value_manager import (
    RedisCommonBidValueManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.utils.graphic_positions_creator import get_keyword_history_graphic

if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
        FactData,
    )



# TODO: Починить сохранение файла перед отправкой в ТГ

logger = logging.getLogger(__name__)


# TODO: Во все списки ключей нужно передавать полные списки ключей, в уже внутри фильтровать т.к. они нужны для расчета АвтоМаксимальной ставки


class AdvKeywordsSetting(TextWithKeyboardAndImage):
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        keywords: list[CalculatedKeyword],
        adv_setting: AdvSetting,
        wb_user_cabinet_original_id: int,
        adv_choice_last_page,
        image: str,
        page: int,
        image_mode: str = "graphic",
        cpm_date_map: dict[str, tuple[float | None, datetime | None]] | None = None,
    ) -> None:
        super().__init__(bot, chat_id)
        self._keywords = keywords
        self._adv_setting = adv_setting
        self._page = page
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._adv_choice_last_page = adv_choice_last_page
        self._image = image
        self._filter: bool = False
        self._on_page = 24
        self.image_mode = image_mode
        self._last_saved_bids: dict[int, int] = {}
        self._cpm_date_map = cpm_date_map
        self.min_orders_per_1000_rub: float | None = None

    @inject
    async def __call__(
        self,
        state: FSMContext,
        sort_mode: str = "by_adv",
        redis_client: RedisClient = Provide["redis_client_wrapper"],
    ) -> tuple[LastMessage, str]:
        self.sort_mode = sort_mode
        self._state = state
        data = await state.get_data()
        self._status_auction = await self._get_status_auction(
            self._adv_setting.search_adv_id
        )
        redis_manager = RedisCommonBidValueManager(redis_client)
        search_adv_id = self._adv_setting.search_adv_id
        nmids = self._adv_setting.nmids or []
        self._last_saved_bids = {}
        if search_adv_id is not None and nmids:
            self._last_saved_bids = await redis_manager.get_bids(search_adv_id, nmids)

        keywords_filter: list[str] = data.get("keywords_filter")
        clear_keywords = []
        if keywords_filter:
            self._filter = True
            for keyword in self._keywords:
                for keyword_filter in keywords_filter:
                    if '"' in keyword_filter or "'" in keyword_filter:
                        # Проверка на полное совпадение, если в фразе есть кавычки
                        keyword_filter = keyword_filter.replace('"', "").replace(
                            "'", ""
                        )
                        if keyword_filter == keyword.text:
                            if keyword not in clear_keywords:
                                clear_keywords.append(keyword)
                    else:
                        # Стандартная проверка на вхождение
                        if keyword_filter in keyword.text:
                            if keyword not in clear_keywords:
                                clear_keywords.append(keyword)

            self._keywords = clear_keywords

        hide_keywords_is_not_relevant = data.get("hide_keywords_is_not_relevant")
        self.hide_keywords_is_not_relevant = hide_keywords_is_not_relevant

        if hide_keywords_is_not_relevant:
            clear_keywords = []
            for keyword in self._keywords:
                if keyword.hard_status == 0:
                    continue
                clear_keywords.append(keyword)
            self._keywords = clear_keywords
        logger.debug("Начинаю отправку сообщения")

        filter_by_query = self._adv_setting.hide_small_query_keywords
        if filter_by_query:
            clear_keywords = []
            for keyword in self._keywords:
                if keyword.total_views > filter_by_query:
                    clear_keywords.append(keyword)
            self._keywords = clear_keywords

        hide_zero_views = self._adv_setting.hide_zero_views_keywords
        if hide_zero_views:
            clear_keywords = []
            for keyword in self._keywords:
                if keyword.views != 0:
                    clear_keywords.append(keyword)
            self._keywords = clear_keywords

        if self._adv_setting.bot_active:
            self._keywords = sort_keywords_by_pay_for_order(self._keywords)
            self._keywords = await enrich_keywords_v3_list_profiles(
                self._adv_setting, self._keywords
            )

        plan_fact_provider = PlanFactProvider(self._adv_setting)
        stat_data = await plan_fact_provider.get_stat_data(self._keywords)
        fact_data = await plan_fact_provider.get_fact_data(
            stat_data
        )

        self._fact_data: FactData = fact_data

        # Устанавливаем полученные данные
        self.min_orders_per_1000_rub: float | None = stat_data.min_orders_per_1000_rub
        self.auto_cpm = stat_data.auto_cpm
        self.auction_cpm = stat_data.auction_cpm
        self.total_spend = stat_data.total_spend
        self.addition_spend_in_adv = stat_data.addition_spend_in_adv
        self._all_orders_for_last_days = stat_data.all_orders_for_last_days
        self._mean_orders_for_days = stat_data.mean_orders_for_last_days
        self._mean_price_for_order = stat_data.mean_price_for_order
        self._spend_for_inner_adv_for_3_days = stat_data.spend_for_inner_advs
        self.hard_min_ctr = stat_data.hard_min_ctr
        self.full_adv_stat_for_last_days_for_auto_adv = (
            stat_data.full_adv_stat_for_last_days_for_auto_adv
        )
        self.full_adv_stat_for_last_days_for_auction = (
            stat_data.full_adv_stat_for_last_days_for_auction
        )
        self.common_stat = stat_data.common_stat
        self.cost_per_order_from_additional_last_week = (
            stat_data.cost_per_order_from_additional_last_week
        )
        if self._all_orders_for_last_days is not None:
            self._sum_spend = self._spend_for_inner_adv_for_3_days
        if self.image_mode == "graphic":
            graphic = await self._graphic_injection()
            if not graphic:
                graphic = (
                    "app/core/telegram/static_images/not_keywords_position_graphic.jpg"
                )
            self._image = graphic

        common_days_stat_manager = CommonStatDataManager()

        self._common_stat_by_days = await common_days_stat_manager.get_days_static_text(
            self._adv_setting, 2
        )

        self._only_relevant_phrase_status: str = self._get_add_only_relevant_phrase_status()

        from app.modules.wb_adv_updater.min_ctr_manager.min_ctr_manager import (
            MinCtrManager,
        )
        min_ctr_manager = MinCtrManager(self._adv_setting)

        self._mean_auto_ctr = await min_ctr_manager.get_mean_ctr_auto_adv()

        result = await super().__call__()
        return result

    # TODO: Почистить stash и ветки
    # TODO: Сделать управление ставкой по кластерам
    @property
    def text(self) -> str:
        total_page = len(self._keywords) // self._on_page
        # TODO: Текст стал слишком большим, на спех сократил. Нужно перед изменением
        #  сообщений сделать тесты, проверяющие длину текста и его корректность
        text = (
            str(self._adv_setting.name) + "\n"
            f"{self._only_relevant_phrase_status}"
            f"Авто: {self._adv_setting.active_status}\n"
            f"Аук.: {self._status_auction}\n"
            f"Стратегия: {format_adv_strategy(self._adv_setting.strategy)}\n"
            f"""Бот {"Включен" if self._adv_setting.bot_active else "Выключен"}\n"""
            "ID Авто: " + str(self._adv_setting.adv_id) + "\n"
            f"ID Аук.: {self._adv_setting.search_adv_id}\n"
            "Cтат. за 2 дня:\n"
        )

        min_orders_per_1000_rub: float | None = self.min_orders_per_1000_rub

        if min_orders_per_1000_rub is None:
            t = 'Не достаточно данных для оценки заказов!!!\n'
        else:
            t = f"Мин. зак. на 1000₽: {min_orders_per_1000_rub:.2f}\n"

        text += t
        page_block = f"Стр.:{self._page}/{total_page + 1}\n"
        text += page_block
        text += (
            f"Общий расход: {self.total_spend:.2f}\n"
            f"Расход аукцион: {self.full_adv_stat_for_last_days_for_auction.spend:.2f}\n"
            f"Общий расход в Авто: {self.full_adv_stat_for_last_days_for_auto_adv.spend:.2f}\n"
            f"Расход на рек.(авто): {self.addition_spend_in_adv:.2f} р.\n"
        )
        if self.cost_per_order_from_additional_last_week is not None:
            text += (
                f"Себес. зак. из доп. пок. (7 д.): {self.cost_per_order_from_additional_last_week:.2f} р.\n"
            )
        text += (
            f"Заказы: {self._all_orders_for_last_days}\n"
            f"  -Авто: {self.full_adv_stat_for_last_days_for_auto_adv.orders}\n"
            f"  -Аукцион: {self.full_adv_stat_for_last_days_for_auction.orders}\n"
        )

        # Показываем источник данных для заказов
        if (
            self._adv_setting.orders_source_for_auto_mode
            == OrdersSourceForAutoMode.ADV_SUM
        ):
            text += "📊 Ист. зак.: ТОЛЬКО рек.\n"
            text += f"Сумм. заказы из рек.: {self.full_adv_stat_for_last_days_for_auto_adv.orders + self.full_adv_stat_for_last_days_for_auction.orders}\n"
        else:
            text += "📊 Ист. зак.: Общая стат. (вкл. органику)\n"
            text += f"""Зак. из Орг.: {
            self._all_orders_for_last_days
            - self.full_adv_stat_for_last_days_for_auction.orders
            - self.full_adv_stat_for_last_days_for_auto_adv.orders
            if self._all_orders_for_last_days
            else 0
            }\n"""

        # Получаем целевые значения из настроек
        plan_for_sales_for_day = self._adv_setting.plan_for_sales_for_day
        plan_for_sales_for_day_str = (
            str(round(plan_for_sales_for_day))
            if plan_for_sales_for_day
            else "Не задано"
        )

        target_price_for_order = self._adv_setting.target_price_for_order
        target_price_for_order_str = (
            str(round(target_price_for_order))
            if target_price_for_order
            else "Не задано"
        )

        max_price_for_order = self._adv_setting.max_price_for_order
        max_price_for_order_str = (
            str(round(max_price_for_order)) if max_price_for_order else "Не задано"
        )

        fact_method_ru = self._fact_data.method_ru
        pay_for_order: float | None = self._fact_data.pay_for_order
        if pay_for_order is None:
            pay_for_order_str = 'Нет данных по продажам'
        else:
            pay_for_order_str = f'{pay_for_order:.2f} р.'
        text += (
            f"\n Факт-продажи({fact_method_ru}):\n"
            f"Прог. зак. в день: {self._fact_data.predict_orders:.2f} (цель: {plan_for_sales_for_day_str})\n"
            f"Себес.: {pay_for_order_str}"
            f" (цель: {target_price_for_order_str}, макс: {max_price_for_order_str})\n"
        )

        text += self._common_stat_by_days

        text += "\n"

        text += (
            f"\nCPM Авто: {int(self.auto_cpm/100) if self.auto_cpm else 'Не получена'} р. "
        )
        text += f"""(Биддер для Авто: {" Включен" if self._adv_setting.bidder_for_auto else " Выключен"})\n"""
        if self._adv_setting.bidder_coroutine_type == BidderCoroutineType.OLD_UPDATE_CPM_BIDDER:
            text += f"Ставка из Аукциона: {self.auction_cpm}\n"
        text += f"Цел. поз.: {self._adv_setting.max_place}\n"
        text += self._format_last_saved_bids()
        return text

    @property
    def image(self) -> str:
        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    async def _graphic_injection(self):
        bot = self.bot
        user_telegram_id = self.chat_id
        adv_original_id = self._adv_setting.id
        result = await get_keyword_history_graphic(adv_original_id)
        if not result:
            graphic = None
            legend = None
        else:
            graphic, legend = result
        if legend:
            await KeywordGraphicPart_1(
                bot, user_telegram_id, graphic, adv_original_id
            )()
            return legend
        return graphic

    @property
    def keyboard(self):
        return keyboards.get_keywords_setting_keyboard(
            self._keywords,
            self._adv_setting,
            self._wb_user_cabinet_original_id,
            self._page,
            self._filter,
            self._on_page,
            self.hide_keywords_is_not_relevant,
            sort_mode=self.sort_mode,
            image_mode=self.image_mode,
        )

    def _format_last_saved_bids(self) -> str:
        header = "Последняя ставка (по артикулам):"
        if not self._last_saved_bids:
            return f"{header} Нет данных\n"
        lines = [header]
        for nmid in sorted(self._last_saved_bids):
            lines.append(f"{nmid}: {self._last_saved_bids[nmid]}")
        return "\n".join(lines) + "\n"

    @staticmethod
    async def _get_status_auction(search_adv_id: int) -> str:
        if not search_adv_id:
            return "не подключен"
        stmt = select(AdvSetting.active_status).where(
            AdvSetting.adv_id == search_adv_id
        )
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            status: str | None = result.scalar_one_or_none()
            if not status:
                status = "Не найдена"
            return status

    def _get_add_only_relevant_phrase_status(self) -> str:
        adv: AdvSetting = self._adv_setting
        only_relevant_phrase_status  = adv.auto_add_only_relevant_phrase
        if only_relevant_phrase_status:
            return "⚠️ Вкл. добавление только релевантных фраз\n"
        return ""

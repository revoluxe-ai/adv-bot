import logging

from aiogram import Bot
from aiogram.fsm.context import FSMContext

from app.client_bot.user_interface.message_templates import (
    TextWithKeyboardAndImage,
    LastMessage,
)
from app.client_bot.user_interface.views import keyboards
from app.client_bot.user_interface.views.messages import KeywordGraphicPart_1
from app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager import (
    CommonStatDataManager,
)
from app.modules.common_advs_stat import CommonAdvsStatDataManager, CommonAdvsStatData
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from app.utils.graphic_positions_creator import get_keyword_history_graphic

logger = logging.getLogger(__name__)


class AdvKeywordsSetting(TextWithKeyboardAndImage):
    def __init__(
        self,
        bot: Bot,
        chat_id,
        keywords: list[CalculatedKeyword],
        adv_setting: AdvSetting,
        wb_user_cabinet_original_id,
        adv_choice_last_page,
        image: str,
        page,
        image_mode="graphic",
    ):
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

    async def __call__(
        self, state: FSMContext, sort_mode="by_adv"
    ) -> (LastMessage, str):
        self.sort_mode = sort_mode
        self._state = state
        data = await state.get_data()
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
                if (
                    not isinstance(keyword.query, str)
                    and keyword.query >= filter_by_query
                ):
                    clear_keywords.append(keyword)
            self._keywords = clear_keywords

        # Получаем данные через CommonAdvsStatDataManager
        common_stat_data_manager = CommonAdvsStatDataManager()
        stat_data: CommonAdvsStatData = await common_stat_data_manager.get_data(
            self._adv_setting, self._keywords, 2
        )

        # Устанавливаем полученные данные
        self.min_ctr = stat_data.min_ctr
        self.auto_cpm = stat_data.auto_cpm
        self.auction_cpm = stat_data.auction_cpm
        self.total_spend = stat_data.total_spend
        self.addition_spend_in_adv = stat_data.addition_spend_in_adv
        self._all_orders_for_last_days = stat_data.all_orders_for_last_days
        self._mean_orders_for_days = stat_data.mean_orders_for_last_days
        self._mean_price_for_order = stat_data.mean_price_for_order
        self._spend_for_inner_adv_for_3_days = stat_data.spend_for_inner_advs
        self.full_adv_stat_for_last_days_for_auto_adv = (
            stat_data.full_adv_stat_for_last_days_for_auto_adv
        )
        self.full_adv_stat_for_last_days_for_auction = (
            stat_data.full_adv_stat_for_last_days_for_auction
        )
        self.common_stat = stat_data.common_stat
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

        auto_update_manager = AdvSettingAutoUpdater(self._adv_setting, 2)

        fact_data = auto_update_manager.get_fact_data(stat_data)

        self._fact_data = fact_data

        await super().__call__()
        return

    @property
    def text(self) -> str:
        total_page = len(self._keywords) // self._on_page
        text = (
            "Название кампании: " + str(self._adv_setting.name) + "\n"
            f"Статус: {self._adv_setting.active_status}\n"
            f"""Бот {'Включен' if self._adv_setting.bot_active else 'Выключен'}\n"""
            "ID кампании: " + str(self._adv_setting.adv_id) + "\n"
            f"ID Аукциона: {self._adv_setting.search_adv_id}\n"
            f"Общая статистика за 2 дня:\n"
            f"Минимальный CRT для кампании: {self.min_ctr * 100:.2f}%\n"
            f"Страница: {self._page}/{total_page + 1}\n"
            f"Экспонента прог.CTR: {self._adv_setting.exponent_predict_ctr}\n"
            f"Общий расход на рекламу: {self.total_spend:.2f}\n"
            f"Расход на доп.трафик в Авто: {self.addition_spend_in_adv:.2f} р.\n"
            f"Общее число заказов: {self._all_orders_for_last_days}\n"
            f"Заказов из Авто: {self.full_adv_stat_for_last_days_for_auto_adv.orders}\n"
            f"Заказов из Аукцион: {self.full_adv_stat_for_last_days_for_auction.orders}\n"
            f"""Заказов из Органики: {self._all_orders_for_last_days
                                                                  - self.full_adv_stat_for_last_days_for_auction.orders
                                                                  - self.full_adv_stat_for_last_days_for_auto_adv.orders
                                        if self._all_orders_for_last_days else 0}"""
        )

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

        order_cost = (
            self._spend_for_inner_adv_for_3_days / self._all_orders_for_last_days
            if self._all_orders_for_last_days
            else self._spend_for_inner_adv_for_3_days
        )

        text += (
            f"\nВ среднем в день (срез за 2 дня):\n"
            f"Прогноз средних заказов в день: {self._fact_data.predict_orders:.2f} (цель: {plan_for_sales_for_day_str})\n"
            f"Себестоимость: {round(self._fact_data.pay_for_order, 2)} р."
            f" (цель: {target_price_for_order_str}, макс: {max_price_for_order_str})"
        )

        text += self._common_stat_by_days

        text += "\n"

        text += f"\nСтавка из Авто: {self.auto_cpm} р. "
        text += f"""(Биддер для Авто: {' Включен' if self._adv_setting.bidder_for_auto else ' Выключен'})\n"""
        text += f"Ставка из Аукциона: {self.auction_cpm}\n"
        text += f"Целевая позиция: {self._adv_setting.max_place}\n"
        text += f"Максимальная ставка: {self._adv_setting.max_cpm}\n"
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
        result = await get_keyword_history_graphic(adv_original_id, self._keywords)
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
            self._adv_choice_last_page,
            self._wb_user_cabinet_original_id,
            self._page,
            self._filter,
            self._on_page,
            self.min_ctr,
            self.hide_keywords_is_not_relevant,
            sort_mode=self.sort_mode,
            image_mode=self.image_mode,
        )

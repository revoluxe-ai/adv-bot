import logging

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from app.client_bot.message_manager import LastMessage
from app.client_bot.user_interface.message_templates import (
    TextWithKeyboardAndImage,
)

from app.utils.db.session_maker import get_async_session_maker as sm

from app.client_bot.user_interface.views import keyboards
from app.client_bot.user_interface.views.messages.adv_keyword_messages.backend.common_stat_data_manager import (
    CommonStatDataManager,
)
from app.client_bot.user_interface.views.messages.positions_graphic_messanges.positions_graphic_messanges import (
    KeywordGraphicPart_1,
)

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from app.utils.graphic_positions_creator import get_keyword_history_graphic
from dependency_injector.wiring import inject, Provide


from app.modules.shop_runner.modules.max_auto_bid_manager.auto_max_bid_manager import AutoMaxBidManager
from app.modules.shop_runner.modules.max_auto_bid_manager.di import AutoMaxCpmContainer


logger = logging.getLogger(__name__)


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

    @inject
    async def __call__(
            self,
            state: FSMContext,
            sort_mode: str = "by_adv",
            auto_max_bid_manager: "AutoMaxBidManager" = Provide[AutoMaxCpmContainer.auto_max_cpm_bid_manager],
    ) -> tuple[LastMessage, str]:
        self.sort_mode = sort_mode
        self._state = state
        data = await state.get_data()
        self._status_auction = await self._get_status_auction(self._adv_setting.search_adv_id)

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
        auto_update_manager = AdvSettingAutoUpdater(self._adv_setting)

        fact_data, stat_data = await auto_update_manager.get_fact_data_and_stat(self._keywords)

        self._fact_data = fact_data

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

        # Получаем данные по Автомаксимальной ставке из Redis (через DI)
        self._auto_max_cpm_mode: bool = bool(
            getattr(self._adv_setting, "auto_max_cpm_mode", False)
        )
        self._auto_max_cpm_value: int | None = None
        if self._auto_max_cpm_mode:
            user_max_cpm = self._adv_setting.max_cpm
            self._auto_max_cpm_value = await auto_max_bid_manager.get_max_cpm(
                self._adv_setting, self._keywords, user_max_cpm
            )

        result = await super().__call__()
        return result

    @property
    def text(self) -> str:
        total_page = len(self._keywords) // self._on_page
        # TODO: Текст стал слишком большим, на спех сократил. Нужно перед изменением
        #  сообщений сделать тесты, проверяющие длину текста и его корректность
        text = (
                str(self._adv_setting.name) + "\n"
            f"Авто: {self._adv_setting.active_status}\n"
            f"Аукцион: {self._status_auction}\n"
            f"""Бот {"Включен" if self._adv_setting.bot_active else "Выключен"}\n"""
            "ID Авто: " + str(self._adv_setting.adv_id) + "\n"
            f"ID Аукциона: {self._adv_setting.search_adv_id}\n"
            f"Cтат. за 2 дня:\n"
            f"Мин. CRT: {self.min_ctr * 100:.2f}%\n"
            f"Стр.: {self._page}/{total_page + 1}\n"
            f"Экс. прог.CTR: {self._adv_setting.exponent_predict_ctr}\n"
            f"Общий расход: {self.total_spend:.2f}\n"
            f"Расход аукцион: {self.full_adv_stat_for_last_days_for_auction.spend:.2f}\n"
            f"Общий расход в Авто: {self.full_adv_stat_for_last_days_for_auto_adv.spend:.2f}\n"
            f"Расход на доп.трафик в Авто: {self.addition_spend_in_adv:.2f} р.\n"
            f"Общие заказы: {self._all_orders_for_last_days}\n"
            f"  -Авто: {self.full_adv_stat_for_last_days_for_auto_adv.orders}\n"
            f"  -Аукцион: {self.full_adv_stat_for_last_days_for_auction.orders}\n"
)

        # Показываем источник данных для заказов
        if (
                self._adv_setting.orders_source_for_auto_mode
                == OrdersSourceForAutoMode.ADV_SUM
        ):
            text += "📊 Источник заказов: ТОЛЬКО рекламные заказы\n"
            text += f"Суммарные заказы из рекламы: {self.full_adv_stat_for_last_days_for_auto_adv.orders + self.full_adv_stat_for_last_days_for_auction.orders}\n"
        else:
            text += "📊 Источник заказов: Общая статистика (включая органику)\n"
            text += f"""Заказов из Органики: {
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

        text += (
            f"\nВ среднем в день (срез за 2 дня):\n"
            f"Прогноз средних заказов в день: {self._fact_data.predict_orders:.2f} (цель: {plan_for_sales_for_day_str})\n"
            f"Себестоимость: {round(self._fact_data.pay_for_order, 2)} р."
            f" (цель: {target_price_for_order_str}, макс: {max_price_for_order_str})"
        )

        text += self._common_stat_by_days

        text += "\n"

        text += f"\nСтавка из Авто: {self.auto_cpm} р. "
        text += f"""(Биддер для Авто: {" Включен" if self._adv_setting.bidder_for_auto else " Выключен"})\n"""
        text += f"Ставка из Аукциона: {self.auction_cpm}\n"
        text += f"Целевая позиция: {self._adv_setting.max_place}\n"
        text += f"Максимальная ставка: {self._adv_setting.max_cpm}\n"

        if not self._auto_max_cpm_mode:
            text += "Авто-Максимальная ставка: не активна\n"
        else:
            value_str = (
                str(self._auto_max_cpm_value)
                if self._auto_max_cpm_value is not None
                else "нет данных"
            )
            text += f"Авто-Максимальная ставка: {value_str}\n"
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

    @staticmethod
    async def _get_status_auction(search_adv_id: int) -> str:
        if not search_adv_id:
            return 'не подключен'
        stmt = select(AdvSetting.active_status).where(AdvSetting.adv_id == search_adv_id)
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            status: str | None = result.scalar_one_or_none()
            if not status:
                status = 'Не найдена'
            return status

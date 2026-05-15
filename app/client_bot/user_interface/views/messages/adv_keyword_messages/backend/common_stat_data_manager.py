import datetime

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager
from app.modules.shop_runner.service_manager.services.traffic_clicks_manager import (
    compute_organic_clicks,
    compute_shelf_clicks,
)
from app.modules.shop_runner.wb_statistic_manager.backend.types.common_card_stat import (
    CommonCardStat,
)
from app.shared.domains.wb.utils.rec_system_shelf_mode import (
    is_rec_system_shelf_mode_operational,
    should_show_clicks_warning,
    warning_suffix,
)


class CommonStatDataManager:
    async def get_days_static_text(
        self, adv_setting: AdvSetting, last_days: int
    ) -> str:
        concatenate_stat = await self.get_concatinated_stats(adv_setting, last_days)
        nmid = adv_setting.nmids[0]
        common_card_stat = await common_stat_manager.get_stats_by_days(nmid, last_days)

        # Получаем показы авто-РК и показы по ключевым словам по дням
        auto_adv_id = adv_setting.adv_id
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=last_days)

        auto_adv_stats = await full_wb_adv_stat.get_daily_stats_by_last_days(
            [auto_adv_id], start_date, end_date
        )
        auto_views_by_day: dict[datetime.date, int] = {
            stat.date: stat.views for stat in auto_adv_stats
        }
        auto_clicks_by_day: dict[datetime.date, int] = {
            stat.date: stat.clicks for stat in auto_adv_stats
        }

        keywords_views_by_day = await full_wb_adv_stat.get_keywords_views_by_days(
            [auto_adv_id], start_date, end_date
        )
        keywords_clicks_by_day = await full_wb_adv_stat.get_keywords_clicks_by_days(
            [auto_adv_id], start_date, end_date
        )
        # Safety: ClickHouse/stat helpers must return dicts; if something returns None, don't crash UI.
        keywords_views_by_day = keywords_views_by_day or {}
        keywords_clicks_by_day = keywords_clicks_by_day or {}

        text_stat = "\n\nСтатистика по дням:\n"
        text_stat += await self._get_days_static_text(
            adv_setting,
            concatenate_stat,
            common_card_stat,
            auto_views_by_day,
            keywords_views_by_day,
            auto_clicks_by_day,
            keywords_clicks_by_day,
        )
        return text_stat

    async def get_concatinated_stats(
        self, adv_setting: AdvSetting, last_days: int
    ) -> list[SmallFullAdvStatPerDay]:
        """
        Получает статистику по РК и объединяет их в один список
        :param adv_setting: Настройки РК
        :param last_days: Количество дней для получения статистики
        :return: Список статистики
        """
        auto_adv_id = adv_setting.adv_id
        auction_adv_id = adv_setting.search_adv_id

        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=last_days)

        auto_adv_stat = await full_wb_adv_stat.get_daily_stats_by_last_days(
            [auto_adv_id], start_date, end_date
        )

        auction_adv_stat = await full_wb_adv_stat.get_daily_stats_by_last_days(
            [auction_adv_id], start_date, end_date  # type: ignore[list-item]
        )

        concatenated_result = full_wb_adv_stat.concatenate_stats(
            auto_adv_stat, auction_adv_stat
        )

        concatenated_result.sort(key=lambda x: x.date)
        return concatenated_result

    async def _get_days_static_text(
        self,
        adv: AdvSetting,
        concatenated_adv_stat_result: list[SmallFullAdvStatPerDay],
        common_card_stats: list[CommonCardStat],
        auto_views_by_day: dict[datetime.date, int],
        keywords_views_by_day: dict[datetime.date, int],
        auto_clicks_by_day: dict[datetime.date, int],
        keywords_clicks_by_day: dict[datetime.date, int],
    ) -> str:
        """
        Получает текст статистики по дням
        Args:
            concatenated_adv_stat_result: Объединенный результат статистики
            auto_views_by_day: Показы авто-РК по дням
            keywords_views_by_day: Показы по ключевым словам по дням

        Returns:
            str: Текст статистики по дням
        """

        date_to_common_stat: dict[datetime.date, CommonCardStat] = {
            cs.date: cs for cs in common_card_stats
        }

        text = ""
        today_date = datetime.datetime.now().date()
        shelves_operational = await is_rec_system_shelf_mode_operational(adv)
        for stat in concatenated_adv_stat_result:
            date = stat.date
            date_str = date.strftime("%d.%m.%Y")
            common_stat: CommonCardStat | None = date_to_common_stat.get(date)
            if not common_stat:
                continue
            orders = common_stat.orders
            add_to_cart = common_stat.add_to_cart
            organic_cart = max(0, add_to_cart - stat.added_to_cart)
            organic_orders = max(0, orders - stat.orders)

            mean_pay_for_order = stat.spend / (orders if orders else 1)

            if date == today_date:
                now = datetime.datetime.now()
                hours_passed = now.hour + now.minute / 60 + now.second / 3600
                fraction_of_day = hours_passed / 24
                mean_orders_for_fraction_day = int(round(orders / fraction_of_day, 0))
            else:
                mean_orders_for_fraction_day = None

            count_orders = orders
            text_row = f"{date_str}: Корз.:{add_to_cart}({organic_cart}) Зак.:{count_orders}"
            if mean_orders_for_fraction_day:
                text_row += f"({mean_orders_for_fraction_day})"
            text_row += f"({organic_orders})шт."
            text_row += f"Себеc: {mean_pay_for_order:.2f}р."

            # Дополнительные показы автокампании (за вычетом показов по ключевым запросам)
            auto_views = auto_views_by_day.get(date, 0)
            keywords_views = keywords_views_by_day.get(date, 0)
            extra_views = auto_views - keywords_views
            if extra_views > 0:
                text_row += f" Доп.пок.: {extra_views}"
            if date == today_date:
                auto_clicks = auto_clicks_by_day.get(date, 0)
                auto_keyword_clicks = keywords_clicks_by_day.get(date, 0)
                shelf_clicks = compute_shelf_clicks(auto_clicks, auto_keyword_clicks)
                # В organic исключаем клики всех РК комплекса за день (auto + search).
                organic_clicks = compute_organic_clicks(
                    common_stat.open_card,
                    stat.clicks,
                )
                text_row += (
                    f" Кл(рек.кл/орг/пол): {stat.clicks}/{organic_clicks}/{shelf_clicks}"
                )
                warn = should_show_clicks_warning(
                    shelves_operational=shelves_operational,
                    adv_clicks=stat.clicks,
                    organic_clicks=organic_clicks,
                    shelf_clicks=shelf_clicks,
                )
                text_row += warning_suffix(warn)

            text_row += "\n"
            text += text_row

        target_sales = adv.plan_for_sales_for_day
        target_price = adv.target_price_for_order
        max_price_for_order = adv.max_price_for_order

        text += (
            f"План: продажи: {target_sales if target_sales else ' Не задано'}"
            f" Цель: {str(target_price) + 'р.' if target_sales else ' Не задано'}"
            f" Макс: {str(max_price_for_order) + 'р.' if max_price_for_order else ' Не задано'}\n"
        )

        return text

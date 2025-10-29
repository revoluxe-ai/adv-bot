import datetime

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager
from app.modules.shop_runner.wb_statistic_manager.backend.types.common_card_stat import (
    CommonCardStat,
)


class CommonStatDataManager:
    async def get_days_static_text(
        self, adv_setting: AdvSetting, last_days: int
    ) -> str:
        concatenate_stat = await self.get_concatinated_stats(adv_setting, last_days)
        nmid = adv_setting.nmids[0]
        common_card_stat = await common_stat_manager.get_stats_by_days(nmid, last_days)
        text_stat = "\n\nСтатистика по дням:\n"
        text_stat += await self._get_days_static_text(
            adv_setting, concatenate_stat, common_card_stat
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
            [auction_adv_id], start_date, end_date # type: ignore[list-item]
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
    ) -> str:
        """
        Получает текст статистики по дням
        Args:
            concatenated_adv_stat_result: Объединенный результат статистики

        Returns:
            str: Текст статистики по дням
        """

        date_to_common_stat: dict[datetime.date, CommonCardStat] = {
            cs.date: cs for cs in common_card_stats
        }

        text = ""
        today_date = datetime.datetime.now().date()
        for stat in concatenated_adv_stat_result:
            date = stat.date
            date_str = date.strftime("%d.%m.%Y")
            common_stat: CommonCardStat | None = date_to_common_stat.get(date)
            if not common_stat:
                continue
            orders = common_stat.orders

            mean_pay_for_order = stat.spend / (orders if orders else 1)

            if date == today_date:
                now = datetime.datetime.now()
                hours_passed = now.hour + now.minute / 60 + now.second / 3600
                fraction_of_day = hours_passed / 24
                mean_orders_for_fraction_day = int(round(orders / fraction_of_day, 0))
            else:
                mean_orders_for_fraction_day = None

            count_orders = orders
            text_row = f"{date_str}: Заказы: {count_orders}"
            if mean_orders_for_fraction_day:
                text_row += f"({mean_orders_for_fraction_day})"
            text_row += "шт."
            text_row += f"Себеc: {mean_pay_for_order:.2f}р."
            text_row += "\n"
            text += text_row

        target_sales = adv.plan_for_sales_for_day
        target_price = adv.target_price_for_order
        max_price_for_order = adv.max_price_for_order

        text += (
            f"План: продажи: {target_sales if target_sales else ' Не задано'},"
            f" цель: {str(target_price) + 'р.' if target_sales else ' Не задано'},"
            f" макс: {str(max_price_for_order) + 'р.' if max_price_for_order else ' Не задано'}"
        )

        return text

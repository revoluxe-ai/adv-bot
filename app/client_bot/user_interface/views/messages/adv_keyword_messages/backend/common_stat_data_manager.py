import datetime

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat


class CommonStatDataManager:

    async def get_days_static_text(
        self, adv_setting: AdvSetting, last_days: int
    ) -> str:
        concatenate_stat = await self.get_concatinated_stats(adv_setting, last_days)

        text_stat = f"\n\nСводная статистика по дням:\n"
        text_stat += await self._get_days_static_text(concatenate_stat)
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
            [auction_adv_id], start_date, end_date
        )

        concatenated_result = full_wb_adv_stat.concatenate_stats(
            auto_adv_stat, auction_adv_stat
        )

        concatenated_result.sort(key=lambda x: x.date)
        return concatenated_result

    async def _get_days_static_text(
        self, concatenated_result: list[SmallFullAdvStatPerDay]
    ) -> str:
        """
        Получает текст статистики по дням
        Args:
            concatenated_result: Объединенный результат статистики

        Returns:
            str: Текст статистики по дням
        """

        text = ""
        today_date = datetime.datetime.now().date()
        for stat in concatenated_result:
            date = stat.date.strftime("%d.%m.%Y")
            mean_pay_for_order = stat.spend / stat.orders if stat.orders else 1

            if stat.date == today_date:
                now = datetime.datetime.now()
                hours_passed = now.hour + now.minute / 60 + now.second / 3600
                fraction_of_day = hours_passed / 24
                mean_orders_for_fraction_day = stat.orders / fraction_of_day
            else:
                mean_orders_for_fraction_day = None

            count_orders = stat.orders
            text_row = f"{date}: {mean_pay_for_order:.2f} р. ({count_orders})"
            if mean_orders_for_fraction_day:
                text_row += f" ({round(mean_orders_for_fraction_day, 1)})"
            text_row += "\n"
            text += text_row
        return text

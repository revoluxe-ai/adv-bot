import json
from datetime import datetime, timedelta

from app.core.wb_api.http_request import try_except_decorator, requests
from .wb_statistic_obj import CommonStat
from ...protocols import WBAPIProtocol

PREFIX = "https://seller-analytics-api"


class CommonStatMinix(WBAPIProtocol):

    HOST = "wildberries.ru"

    @try_except_decorator(1, 60)
    async def _get_cards_stats_by_days(self, nmIDs: list[int], pass_days: int):
        """
        Получить статистику по карточкам товаров за указанный промежуток времени.

        :param nmIDs: Список идентификаторов товаров (nmID).
        :param pass_days: Количество дней, за которые нужна статистика.
        :return: Статистика по товарам.
        """

        assert len(nmIDs) <= 20  # Ограничение по количеству товаров

        # Определим дату начала и окончания для периода
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=pass_days)

        data_for_req = {
            "nmIDs": nmIDs,
            "period": {
                "begin": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "timezone": "Europe/Moscow",
            "aggregationLevel": "day",
        }

        url = f"{PREFIX}.{self.HOST}/api/v2/nm-report/detail/history"

        response = await requests(
            self.session,
            "POST",
            url=url,
            json_data=data_for_req,
            headers=self.headers.standart,
        )

        response = json.loads(response)
        stats = []
        for data in response["data"]:
            for history in data["history"]:
                date = datetime.strptime(history["dt"], "%Y-%m-%d")
                stat = CommonStat(
                    nmid=data["nmID"],
                    date=date,
                    open_card=history["openCardCount"],
                    add_to_cart=history["addToCartCount"],
                    orders=history["ordersCount"],
                    orders_sum=history["ordersSumRub"],
                    buy_outs=history["buyoutsCount"],
                )
                stats.append(stat)
        return stats

    async def get_cards_stats_by_days(
        self, nmIDs: list[int], pass_days: int
    ) -> list[CommonStat]:
        """
        Разбивает запрос на несколько частей, если nmIDs больше 20, и вызывает _get_cards_stats_by_days.

        :param nmIDs: Список идентификаторов товаров (nmID).
        :param pass_days: Количество дней, за которые нужно получить статистику.
        :return: Статистика по товарам.
        """

        part = 20  # Максимальное количество товаров в одном запросе
        results = []

        # Разделение nmIDs на части по 20 товаров
        for i in range(0, len(nmIDs), part):
            part_nmids = nmIDs[i : i + part]
            result: list[CommonStat] = await self._get_cards_stats_by_days(
                part_nmids, pass_days
            )
            results.extend(result)

        return results

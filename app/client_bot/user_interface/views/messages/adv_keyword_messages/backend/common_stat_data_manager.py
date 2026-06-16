"""Сборка текста дневной статистики для страницы ключей."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.rebind_wb_adv_ids_history import (
    get_rebound_wb_adv_ids,
)
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
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker as sm
from app.shared.domains.wb.utils.rec_system_shelf_mode import (
    is_rec_system_shelf_mode_operational,
    should_show_clicks_warning,
    warning_suffix,
)


@dataclass(frozen=True)
class DaysStatTextOptions:
    """Настройки рендера строки дневной статистики."""

    show_forecast: bool = True
    show_clicks_warning: bool = True
    show_organic_pct: bool = False


class CommonStatDataManager:
    """Собирает текст дневной статистики из ClickHouse для bot UI."""

    async def get_days_static_text(
        self,
        adv_setting: AdvSetting,
        last_days: int,
        options: DaysStatTextOptions | None = None,
    ) -> str:
        """Получает текст по последним `last_days` дням.

        Args:
            adv_setting: Настройки объявления.
            last_days: Количество дней в хвосте периода.
            options: Флаги рендера дневной строки.

        Returns:
            Строка со статистикой по дням.
        """
        options = options or DaysStatTextOptions()
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=last_days)
        return await self.get_days_static_text_for_range(
            adv_setting,
            start_date,
            end_date,
            options=options,
        )

    async def get_days_static_text_for_range(
        self,
        adv_setting: AdvSetting,
        start_date: date,
        end_date: date,
        options: DaysStatTextOptions | None = None,
    ) -> str:
        """Получает текст статистики по явному диапазону дат.

        Args:
            adv_setting: Настройки объявления.
            start_date: Начало диапазона включительно.
            end_date: Конец диапазона включительно.
            options: Флаги рендера дневной строки.

        Returns:
            Текст блока «Статистика по дням».
        """
        options = options or DaysStatTextOptions()
        (
            concatenate_stat,
            common_card_stat,
            auto_views_by_day,
            keywords_views_by_day,
            auto_clicks_by_day,
            keywords_clicks_by_day,
            cluster_keyword_clicks_by_day,
        ) = await self._load_daily_stat_data(adv_setting, start_date, end_date)
        text_stat = "\n\nСтатистика по дням:\n"
        text_stat += await self._get_days_static_text(
            adv_setting,
            concatenate_stat,
            common_card_stat,
            auto_views_by_day,
            keywords_views_by_day,
            auto_clicks_by_day,
            keywords_clicks_by_day,
            cluster_keyword_clicks_by_day,
            options=options,
        )
        return text_stat

    async def get_concatinated_stats(
        self, adv_setting: AdvSetting, last_days: int
    ) -> list[SmallFullAdvStatPerDay]:
        """
        Получает статистику по РК и объединяет их в один список.

        Args:
            adv_setting: Настройки РК.
            last_days: Количество дней для получения статистики.

        Returns:
            Список статистики по дням.
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=last_days)
        return await self.get_concatinated_stats_for_range(
            adv_setting,
            start_date,
            end_date,
        )

    async def get_concatinated_stats_for_range(
        self, adv_setting: AdvSetting, start_date: date, end_date: date
    ) -> list[SmallFullAdvStatPerDay]:
        """Получает объединенную статистику по РК за диапазон дат."""
        auto_adv_ids, auction_adv_ids = await self._collect_adv_ids_for_stats(
            adv_setting
        )
        if not auto_adv_ids:
            return []

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())

        auto_adv_stat = await full_wb_adv_stat.get_daily_stats_by_last_days(
            auto_adv_ids, start_dt, end_dt
        )
        if not auction_adv_ids:
            auction_adv_stat: list[SmallFullAdvStatPerDay] = []
        else:
            auction_adv_stat = await full_wb_adv_stat.get_daily_stats_by_last_days(
                auction_adv_ids, start_dt, end_dt
            )

        concatenated_result = full_wb_adv_stat.concatenate_stats(
            auto_adv_stat, auction_adv_stat
        )
        concatenated_result.sort(key=lambda x: x.date)
        return concatenated_result

    async def _collect_adv_ids_for_stats(
        self, adv_setting: AdvSetting
    ) -> tuple[list[int], list[int]]:
        """adv_id текущей РК и её перепривязок — только они участвуют в метриках экрана."""
        auto_ids: set[int] = set()
        auction_ids: set[int] = set()

        if adv_setting.adv_id is not None:
            auto_ids.add(adv_setting.adv_id)
        if adv_setting.search_adv_id is not None:
            auction_ids.add(adv_setting.search_adv_id)

        rebound_auto, rebound_auction = await get_rebound_wb_adv_ids(adv_setting.id)
        auto_ids.update(rebound_auto)
        auction_ids.update(rebound_auction)
        auto_ids -= auction_ids

        return sorted(auto_ids), sorted(auction_ids)

    async def _collect_historical_adv_ids(
        self, adv_setting: AdvSetting
    ) -> tuple[list[int], list[int]]:
        """Расширенный набор adv_id для границы пагинации (siblings, кластеры CH).

        Не использовать для суммирования spend/views: соседние кампании того же
        артикула дадут завышенные метрики на экране одной РК.
        """
        auto_ids_list, auction_ids_list = await self._collect_adv_ids_for_stats(
            adv_setting
        )
        auto_ids = set(auto_ids_list)
        auction_ids = set(auction_ids_list)

        nmid = adv_setting.nmids[0] if adv_setting.nmids else None
        if nmid is not None:
            pg_auto, pg_auction = await self._get_pg_sibling_adv_ids(
                adv_setting.wb_cabinet_id, nmid
            )
            auto_ids.update(pg_auto)
            auction_ids.update(pg_auction)
            auto_ids.update(await self._get_cluster_adv_ids_for_nmid(nmid))

        auto_ids -= auction_ids
        return sorted(auto_ids), sorted(auction_ids)

    async def _get_pg_sibling_adv_ids(
        self, wb_cabinet_id: int, nmid: int
    ) -> tuple[set[int], set[int]]:
        """Все adv_id / search_adv_id из AdvSetting того же кабинета и артикула."""
        auto_ids: set[int] = set()
        auction_ids: set[int] = set()
        async with sm(read_only=True) as session:
            stmt = select(AdvSetting.adv_id, AdvSetting._search_adv_id).where(  # noqa: SLF001
                AdvSetting.wb_cabinet_id == wb_cabinet_id,
                AdvSetting.nmids == [nmid],
            )
            result = await session.execute(stmt)
            for adv_id, search_adv_id in result.all():
                if adv_id is not None:
                    auto_ids.add(adv_id)
                if search_adv_id is not None:
                    auction_ids.add(search_adv_id)
        return auto_ids, auction_ids

    async def _get_cluster_adv_ids_for_nmid(self, nmid: int) -> set[int]:
        """adv_id из clusters_adv_stats — подхватывает старые авто-РК после rebind."""
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result = await client.query(
                    """
                    SELECT DISTINCT adv_id
                    FROM default_db.clusters_adv_stats
                    WHERE nmid = %(nmid)s
                    """,
                    parameters={"nmid": nmid},
                )
        if not result or not result.result_rows:
            return set()
        return {int(row[0]) for row in result.result_rows}

    async def get_earliest_stat_date(self, adv_setting: AdvSetting) -> date | None:
        """Возвращает нижнюю границу пагинации дневной статистики.

        Берётся более поздняя из минимальных дат воронки (wb_common_stat) и рекламы
        (full_adv_wb_stat). Пересечение по дням (INNER JOIN) не используется: при
        разрыве в воронке оно сдвигает границу вперёд и скрывает дни, где реклама
        уже есть. adv_id для рекламы — расширенный набор (rebind, siblings, кластеры).
        """
        if adv_setting.adv_id is None:
            return None

        nmid = adv_setting.nmids[0] if adv_setting.nmids else None
        auto_adv_ids, auction_adv_ids = await self._collect_historical_adv_ids(
            adv_setting
        )
        all_adv_ids = sorted(set(auto_adv_ids) | set(auction_adv_ids))
        if not all_adv_ids:
            return None

        candidate_dates: list[date] = []
        if nmid is not None:
            common_date = await self._get_min_date(
                """
                SELECT MIN(toDate(date))
                FROM wb_common_stat
                WHERE nmid = %(nmid)s
                """,
                {"nmid": nmid},
            )
            if common_date is not None:
                candidate_dates.append(common_date)

        adv_date = await self._get_min_date(
            """
            SELECT MIN(date)
            FROM (
                SELECT date
                FROM (
                    SELECT adv_id, date
                    FROM default_db.full_adv_wb_stat
                    WHERE adv_id IN %(adv_ids)s
                    GROUP BY adv_id, date
                )
                GROUP BY date
            )
            """,
            {"adv_ids": all_adv_ids},
        )
        if adv_date is not None:
            candidate_dates.append(adv_date)

        if not candidate_dates:
            return None
        return max(candidate_dates)

    async def get_total_pages(
        self, adv_setting: AdvSetting, page_size: int = 14
    ) -> int:
        """Подсчитывает количество страниц дневной статистики."""
        earliest_date = await self.get_earliest_stat_date(adv_setting)
        if earliest_date is None:
            return 1
        today = datetime.now().date()
        delta_days = (today - earliest_date).days + 1
        return max(1, (delta_days + page_size - 1) // page_size)

    @staticmethod
    def page_to_date_range(
        page: int,
        page_size: int = 14,
        earliest_date: date | None = None,
        today: date | None = None,
    ) -> tuple[date, date] | None:
        """Возвращает диапазон дат для страницы статистики.

        Page 1 соответствует последним `page_size` дням, page 2 — предыдущим
        `page_size` дням и так далее. Если окно целиком раньше `earliest_date`
        или после обрезки start > end, возвращает None.
        """
        today = today or datetime.now().date()
        shift_days = (max(page, 1) - 1) * page_size
        end_date = today - timedelta(days=shift_days)
        if earliest_date is not None and end_date < earliest_date:
            return None
        start_date = end_date - timedelta(days=page_size - 1)
        if earliest_date is not None and start_date < earliest_date:
            start_date = earliest_date
        if start_date > end_date:
            return None
        return start_date, end_date

    async def get_days_static_text_page(
        self,
        adv_setting: AdvSetting,
        page: int,
        options: DaysStatTextOptions | None = None,
        page_size: int = 14,
    ) -> tuple[str, int, int]:
        """Возвращает текст, текущую страницу и число страниц для UI."""
        options = options or DaysStatTextOptions()
        total_pages = await self.get_total_pages(adv_setting, page_size=page_size)
        current_page = min(max(page, 1), total_pages)
        earliest_date = await self.get_earliest_stat_date(adv_setting)
        page_range = self.page_to_date_range(
            current_page, page_size, earliest_date=earliest_date
        )
        if page_range is None:
            return "", current_page, total_pages
        start_date, end_date = page_range

        (
            concatenate_stat,
            common_card_stat,
            auto_views_by_day,
            keywords_views_by_day,
            auto_clicks_by_day,
            keywords_clicks_by_day,
            cluster_keyword_clicks_by_day,
        ) = await self._load_daily_stat_data(adv_setting, start_date, end_date)
        if not concatenate_stat or not common_card_stat:
            return "", current_page, total_pages

        concatenate_stat.sort(key=lambda x: x.date, reverse=True)

        text = "\n\nСтатистика по дням:\n"
        text += await self._get_days_static_text(
            adv_setting,
            concatenate_stat,
            common_card_stat,
            auto_views_by_day,
            keywords_views_by_day,
            auto_clicks_by_day,
            keywords_clicks_by_day,
            cluster_keyword_clicks_by_day,
            options=options,
        )
        return text, current_page, total_pages

    async def _load_daily_stat_data(
        self,
        adv_setting: AdvSetting,
        start_date: date,
        end_date: date,
    ) -> tuple[
        list[SmallFullAdvStatPerDay],
        list[CommonCardStat],
        dict[date, int],
        dict[date, int],
        dict[date, int],
        dict[date, int],
        dict[date, int],
    ]:
        """Загружает все дневные источники для одного диапазона дат."""
        if not adv_setting.nmids or adv_setting.adv_id is None:
            return ([], [], {}, {}, {}, {}, {})
        auto_adv_ids, auction_adv_ids = await self._collect_adv_ids_for_stats(
            adv_setting
        )
        concatenate_stat = await self.get_concatinated_stats_for_range(
            adv_setting, start_date, end_date
        )
        nmid = adv_setting.nmids[0]
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())
        common_card_stat = await common_stat_manager.get_stats_by_date_range(
            nmid, start_dt, end_dt
        )

        auto_views_by_day = await full_wb_adv_stat.get_daily_stats_by_last_days(
            auto_adv_ids, start_dt, end_dt
        )
        auto_views_by_day_map: dict[date, int] = {
            stat.date: stat.views for stat in auto_views_by_day
        }
        auto_clicks_by_day_map: dict[date, int] = {
            stat.date: stat.clicks for stat in auto_views_by_day
        }

        keywords_views_by_day = await full_wb_adv_stat.get_keywords_views_by_days(
            auto_adv_ids, start_dt, end_dt
        )
        keywords_clicks_by_day = await full_wb_adv_stat.get_keywords_clicks_by_days(
            auto_adv_ids, start_dt, end_dt
        )
        adv_ids_for_cluster_keywords = list(auto_adv_ids)
        adv_ids_for_cluster_keywords.extend(auction_adv_ids)
        cluster_keyword_clicks_by_day = await full_wb_adv_stat.get_keywords_clicks_by_days(
            adv_ids_for_cluster_keywords, start_dt, end_dt
        )

        return (
            concatenate_stat,
            common_card_stat,
            auto_views_by_day_map or {},
            keywords_views_by_day or {},
            auto_clicks_by_day_map or {},
            keywords_clicks_by_day or {},
            cluster_keyword_clicks_by_day or {},
        )

    async def _get_days_static_text(
        self,
        adv: AdvSetting,
        concatenated_adv_stat_result: list[SmallFullAdvStatPerDay],
        common_card_stats: list[CommonCardStat],
        auto_views_by_day: dict[date, int],
        keywords_views_by_day: dict[date, int],
        auto_clicks_by_day: dict[date, int],
        keywords_clicks_by_day: dict[date, int],
        cluster_keyword_clicks_by_day: dict[date, int],
        options: DaysStatTextOptions | None = None,
    ) -> str:
        """
        Получает текст статистики по дням.

        Args:
            adv: Настройки объявления.
            concatenated_adv_stat_result: Объединенный результат статистики по РК.
            common_card_stats: Статистика карточки по дням.
            auto_views_by_day: Показы авто-РК по дням.
            keywords_views_by_day: Показы по ключевым словам по дням.
            auto_clicks_by_day: Клики авто-РК по дням.
            keywords_clicks_by_day: Клики по ключам из кластеров авто по дням.
            cluster_keyword_clicks_by_day: Клики по ключам из кластеров авто+search.
            options: Флаги рендера дневной строки.

        Returns:
            Текст статистики по дням.
        """
        options = options or DaysStatTextOptions()
        date_to_common_stat: dict[date, CommonCardStat] = {
            cs.date: cs for cs in common_card_stats
        }

        text = ""
        today_date = datetime.now().date()
        shelves_operational = await is_rec_system_shelf_mode_operational(adv)
        for stat in concatenated_adv_stat_result:
            date_value = stat.date
            common_stat: CommonCardStat | None = date_to_common_stat.get(date_value)
            if not common_stat:
                continue
            text += self._format_day_row(
                date_value=date_value,
                common_stat=common_stat,
                adv_stat=stat,
                auto_views_by_day=auto_views_by_day,
                keywords_views_by_day=keywords_views_by_day,
                auto_clicks_by_day=auto_clicks_by_day,
                keywords_clicks_by_day=keywords_clicks_by_day,
                cluster_keyword_clicks_by_day=cluster_keyword_clicks_by_day,
                shelves_operational=shelves_operational,
                options=options,
                today_date=today_date,
            )
            text += "\n"

        target_sales = adv.plan_for_sales_for_day
        target_price = adv.target_price_for_order
        max_price_for_order = adv.max_price_for_order

        text += (
            f"План: продажи: {target_sales if target_sales else ' Не задано'}"
            f" Цель: {str(target_price) + 'р.' if target_sales else ' Не задано'}"
            f" Макс: {str(max_price_for_order) + 'р.' if max_price_for_order else ' Не задано'}\n"
        )

        return text

    def _format_day_row(
        self,
        *,
        date_value: date,
        common_stat: CommonCardStat,
        adv_stat: SmallFullAdvStatPerDay,
        auto_views_by_day: dict[date, int],
        keywords_views_by_day: dict[date, int],
        auto_clicks_by_day: dict[date, int],
        keywords_clicks_by_day: dict[date, int],
        cluster_keyword_clicks_by_day: dict[date, int],
        shelves_operational: bool,
        options: DaysStatTextOptions,
        today_date: date,
    ) -> str:
        """Формирует одну строку статистики по дню."""
        date_str = date_value.strftime("%d.%m.%Y")
        orders = common_stat.orders
        add_to_cart = common_stat.add_to_cart
        organic_cart = max(0, add_to_cart - adv_stat.added_to_cart)
        organic_orders = max(0, orders - adv_stat.orders)
        mean_pay_for_order = adv_stat.spend / (orders if orders else 1)

        text_row = f"{date_str}: Корз.:{add_to_cart}({organic_cart}"
        if options.show_organic_pct:
            text_row += f", {self._format_organic_pct(organic_cart, add_to_cart)}"
        text_row += f") Зак.:{orders}"

        if options.show_forecast and date_value == today_date:
            now = datetime.now()
            hours_passed = now.hour + now.minute / 60 + now.second / 3600
            fraction_of_day = hours_passed / 24
            mean_orders_for_fraction_day = int(round(orders / fraction_of_day, 0))
            if mean_orders_for_fraction_day:
                text_row += f"({mean_orders_for_fraction_day})"

        text_row += f"({organic_orders}"
        if options.show_organic_pct:
            text_row += f", {self._format_organic_pct(organic_orders, orders)}"
        text_row += f")шт."
        text_row += f"Себеc: {mean_pay_for_order:.2f}р."

        auto_views = auto_views_by_day.get(date_value, 0)
        keywords_views = keywords_views_by_day.get(date_value, 0)
        extra_views = auto_views - keywords_views
        if extra_views > 0:
            text_row += f" Доп.пок.: {extra_views}"

        auto_clicks = auto_clicks_by_day.get(date_value, 0)
        auto_keyword_clicks = keywords_clicks_by_day.get(date_value, 0)
        shelf_clicks = compute_shelf_clicks(auto_clicks, auto_keyword_clicks)
        organic_clicks = compute_organic_clicks(
            common_stat.open_card,
            adv_stat.clicks,
        )
        cluster_rek_clicks = cluster_keyword_clicks_by_day.get(date_value, 0)
        clicks_control_sum = cluster_rek_clicks + organic_clicks + shelf_clicks
        text_row += (
            f" Кл(рек.кл/орг/пол): {cluster_rek_clicks}/{organic_clicks}/"
            f"{shelf_clicks} ({clicks_control_sum})"
        )
        if options.show_clicks_warning and date_value == today_date:
            warn = should_show_clicks_warning(
                shelves_operational=shelves_operational,
                adv_clicks=cluster_rek_clicks,
                organic_clicks=organic_clicks,
                shelf_clicks=shelf_clicks,
            )
            text_row += warning_suffix(warn)

        return text_row

    @staticmethod
    def _format_organic_pct(organic_value: int, total_value: int) -> str:
        """Возвращает процент органики в кратком виде."""
        if total_value <= 0:
            return "0% орг."
        return f"{int(round(organic_value * 100 / total_value, 0))}% орг."

    async def _get_min_date(
        self, query: str, parameters: dict[str, object]
    ) -> date | None:
        """Получает минимальную дату по произвольному запросу ClickHouse."""
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result = await client.query(query, parameters=parameters)
        if not result or not result.first_row:
            return None
        return result.first_row[0]

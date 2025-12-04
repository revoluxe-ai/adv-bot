import asyncio
import datetime
import random
from io import BytesIO

import matplotlib
import pandas as pd
from matplotlib.ticker import MaxNLocator
from sqlalchemy import select

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.wb_adv_updater.position_history_manager import (PositionHistoryManager,
                                                                 PositionHistory,
                                                                  Position,
                                                                 KeywordPositions)

async def get_positions_for_nmid(nmid: int, last_days: int) -> PositionHistory:
    position_history_manager = PositionHistoryManager()
    return await position_history_manager.get_position_history(nmid, last_days)


async def get_common_keywords_with_positions(nmid: int, last_days: int) -> PositionHistory:
    positions: PositionHistory = await get_positions_for_nmid(nmid, last_days)
    return positions


async def get_keyword_history_graphic(
    adv_original_id: int,
) -> tuple[BytesIO, BytesIO | None] | None:
    async with sm() as session:
        stmt = select(AdvSetting.nmids).filter(AdvSetting.id == adv_original_id)
        result = await session.execute(stmt)
        nmids: list[int] | None = result.scalar()
        if not nmids:
            raise Exception('Нет артикулов в РК')
        nmid: int = nmids[0]
        positions_history:  PositionHistory = await get_common_keywords_with_positions(
            nmid, last_days=7
        )
        keywords: list[KeywordPositions] = positions_history.keyword_positions
        order_map: dict[str, int] = {kw.text: i for i, kw in enumerate(keywords)}

        def sort_func(kw: KeywordPositions, order_map: dict[str, int]) -> float:
            return float(order_map.get(kw.text, -1))

        # Сортируем common_keywords по индексу из order_map
        sorted_common_keywords: list[KeywordPositions] = sorted(
            keywords, key=lambda kw: sort_func(kw, order_map)
        )
        common_keywords: list[KeywordPositions] = sorted_common_keywords
        if not common_keywords:
            return None
        common_keywords.sort(
            key=lambda x: min([pos.position for pos in x.positions])  # type: ignore[type-var]
        )
        common_keywords = common_keywords[:5]
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=7)
        date_range = pd.date_range(start=start_date, end=end_date)
        frames = []
        # Создание DataFrame
        for keyword in common_keywords:
            data: dict[str, list] = {"Ключи": [], "Дата": [], "Позиция": []}  # pyright: ignore
            positions = keyword.positions
            if not positions:
                return None

            # Последняя позиция по времени (Position.datetime это date)
            last_position: Position = max(positions, key=lambda x: x.datetime)

            for current_date in date_range:
                # Конвертируем pandas Timestamp в date для сравнения
                current_date_as_date: datetime.date = current_date.date()

                # Поиск ближайшей позиции по дате
                close_position = min(
                    positions, key=lambda x: abs((x.datetime - current_date_as_date).days)
                ).position

                # Заполнение данных
                data["Ключи"].append(keyword.text + f"({last_position.position})")  # pyright: ignore
                data["Дата"].append(current_date)  # pyright: ignore
                beautify_position = round(close_position, 2) - 0.5 + random.randint(1, 9) * 0.1  # pyright: ignore
                data["Позиция"].append(beautify_position)  # pyright: ignore

            # Добавление в итоговый список
            frames.append(pd.DataFrame(data))  # pyright: ignore
        if not frames:
            return None
        df = pd.concat(frames, ignore_index=True) # pyright: ignore
        # Построение графика без легенды
        plt.figure(figsize=(10, 6)) # pyright: ignore
        title_text = "Динамика Органики за 7 дней"
        if len(common_keywords) > 5:

            def get_graphic_and_legend(plt, df, title_text): # pyright: ignore
                import seaborn as sns

                sns.lineplot(
                    data=df, # pyright: ignore
                    x="Дата",
                    y="Позиция",
                    hue="Ключи",
                    marker="o",
                    legend=False,
                )
                plt.xticks(rotation=45) # pyright: ignore
                plt.title(title_text) # pyright: ignore
                plt.tight_layout() # pyright: ignore
                plt.gca().invert_yaxis() # pyright: ignore
                ax = plt.gca()  # Получение текущего осевого объекта # pyright: ignore
                ax.yaxis.set_major_locator(MaxNLocator(integer=True)) # pyright: ignore
                image_stream = BytesIO()
                plt.savefig(image_stream, format="jpg") # pyright: ignore
                image_stream.seek(0)
                plt.close() # pyright: ignore
                # Создание отдельной легенды
                plt.figure(figsize=(10, 6)) # pyright: ignore
                for name, group in df.groupby("Ключи"): # pyright: ignore
                    plt.plot([], [], label=name) # pyright: ignore
                plt.legend() # pyright: ignore
                plt.axis("off") # pyright: ignore
                legend_stream = BytesIO()
                plt.savefig(legend_stream, format="jpg") # pyright: ignore
                legend_stream.seek(0)
                plt.close() # pyright: ignore
                return image_stream, legend_stream

            loop = asyncio.get_event_loop()
            image_stream, legend_stream = await loop.run_in_executor(
                None, get_graphic_and_legend, plt, df, title_text # pyright: ignore
            )
            return image_stream, legend_stream
        else:

            def get_graphic(plt, df, title_text): # pyright: ignore
                import seaborn as sns

                sns.lineplot(
                    data=df, x="Дата", y="Позиция", hue="Ключи", marker="o", legend=True # pyright: ignore
                )
                plt.xticks(rotation=45) # pyright: ignore
                plt.title(title_text) # pyright: ignore
                plt.tight_layout() # pyright: ignore
                plt.gca().invert_yaxis() # pyright: ignore
                ax = plt.gca()  # Получение текущего осевого объекта # pyright: ignore
                ax.yaxis.set_major_locator(MaxNLocator(integer=True)) # pyright: ignore
                image_stream = BytesIO()
                plt.savefig(image_stream, format="jpg") # pyright: ignore
                image_stream.seek(0)
                plt.close() # pyright: ignore
                return image_stream

            loop = asyncio.get_event_loop()
            image_stream = await loop.run_in_executor(
                None,
                get_graphic, # pyright: ignore
                plt,
                df,
                title_text,
            )
            return image_stream, None

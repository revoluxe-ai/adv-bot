import datetime
import random
from collections import defaultdict
from io import BytesIO
from typing import Optional
import asyncio
from sqlalchemy import select
import pandas as pd
import matplotlib
from matplotlib.ticker import MaxNLocator
import seaborn as sns
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from app.modules.common_slaves.wildberries.models import AdvSetting, WBItemPosition
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm
from app.utils.graphic_positions_creator.classes import CommonKeyword


async def get_common_keywords_with_positions(nmid)-> Optional[list[CommonKeyword]]:
        positions: list[WBItemPosition]\
            = await data_manager.get_keyword_positions_from_click_house(nmid)
        common_keywords = []
        if positions:
            text_to_positions = defaultdict(list)
            for position in positions:
                text_to_positions[position.keyword_text].append(position)

            for text, positions in text_to_positions.items():
                common_keyword = CommonKeyword(wb_item_positions=positions,
                                               text=text)
                common_keyword.wb_item_positions = positions
                common_keywords.append(common_keyword)

        return common_keywords


async def get_keyword_history_graphic(adv_original_id,
                                      keywords):
    async with sm() as session:
        stmt = select(AdvSetting.nmids)\
                .where(AdvSetting.id == adv_original_id)
        result = await session.execute(stmt)
        nmids = result.scalar()
        nmid = nmids[0]
        common_keywords: list[CommonKeyword] = await get_common_keywords_with_positions(nmid)
        def sort_func(kw: CommonKeyword, order_map):
            return order_map.get(kw.text,  -float('inf'))

        order_map = {kw.text: i for i, kw in enumerate(keywords)}
        # Сортируем common_keywords по индексу из order_map
        sorted_common_keywords = sorted(common_keywords,
                                        key=lambda kw: sort_func(kw, order_map))
        common_keywords = sorted_common_keywords
        if not common_keywords:
            return
        common_keywords.sort(key=lambda x: min([pos.promo_position for pos in  x.wb_item_positions]))
        common_keywords = common_keywords[:5]
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=7)
        date_range = pd.date_range(start=start_date, end=end_date)
        frames = []
        # Создание DataFrame
        for keyword in common_keywords:
            data = {
                "Ключи": [],
                "Дата": [],
                "Базовая Позиция": []
            }
            positions = keyword.wb_item_positions
            if not positions:
                return None

            # Убедимся, что все timestamps в positions tz-aware
            for position in positions:
                if position.timestamp.tzinfo is None:
                    position.timestamp = position.timestamp.replace(tzinfo=datetime.timezone.utc)

            # Последняя позиция по времени
            last_position: WBItemPosition = max(positions, key=lambda x: x.timestamp)

            # Приведение всех дат в date_range к UTC (tz-aware)
            for date in date_range:
                if date.tzinfo is None:
                    date = date.replace(tzinfo=datetime.timezone.utc)

                # Поиск ближайшей позиции
                close_position = min(positions, key=lambda x: abs(x.timestamp - date)).base_position

                # Заполнение данных
                data["Ключи"].append(keyword.text + f'({last_position.base_position})')
                data["Дата"].append(date)
                beautify_position = close_position - 0.5 + random.randint(1, 9) * 0.1
                data["Базовая Позиция"].append(beautify_position)

            # Добавление в итоговый список
            frames.append(pd.DataFrame(data))
        if not frames:
            return None
        df = pd.concat(frames, ignore_index=True)
        # Построение графика без легенды
        plt.figure(figsize=(10, 6))
        title_text = "Динамика Органики за 7 дней"
        if len(common_keywords) > 5:
            def get_graphic_and_legend(plt, df, title_text):
                sns.lineplot(data=df, x="Дата", y="Базовая Позиция", hue="Ключи", marker="o", legend=False)
                plt.xticks(rotation=45)
                plt.title(title_text)
                plt.tight_layout()
                plt.gca().invert_yaxis()
                ax = plt.gca()  # Получение текущего осевого объекта
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                image_stream = BytesIO()
                plt.savefig(image_stream, format='jpg')
                image_stream.seek(0)
                plt.close()
                # Создание отдельной легенды
                plt.figure(figsize=(10, 6))
                for name, group in df.groupby('Ключи'):
                    plt.plot([], [], label=name)
                plt.legend()
                plt.axis('off')
                legend_stream = BytesIO()
                plt.savefig(legend_stream, format='jpg')
                legend_stream.seek(0)
                plt.close()
                return image_stream, legend_stream
            loop = asyncio.get_event_loop()
            image_stream, legend_stream = await loop.run_in_executor(None,
                                                                     get_graphic_and_legend,
                                                                     plt,
                                                                     df,
                                                                     title_text)
            return image_stream, legend_stream
        else:
            def get_graphic(plt, df, title_text):
                sns.lineplot(data=df, x="Дата", y="Базовая Позиция", hue="Ключи", marker="o", legend=True)
                plt.xticks(rotation=45)
                plt.title(title_text)
                plt.tight_layout()
                plt.gca().invert_yaxis()
                ax = plt.gca()  # Получение текущего осевого объекта
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
                image_stream = BytesIO()
                plt.savefig(image_stream, format='jpg')
                image_stream.seek(0)
                plt.close()
                return image_stream
            loop = asyncio.get_event_loop()
            image_stream = await loop.run_in_executor(None,
                                                      get_graphic,
                                                      plt,
                                                      df,
                                                      title_text,
                                                      )
            return image_stream, None
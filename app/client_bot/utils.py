import csv
from io import StringIO
from typing import Union
import pandas as pd
from sqlalchemy import and_, select, func, desc
from sqlalchemy.orm import joinedload

from app.client_bot.const import BLACK_LIST, TURN_OFF, WHITE_LIST, AUTO_MODE
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.models import AdvKeyword, CommonKeyword, \
    WBItemPosition
from app.modules.wb_adv_updater import data_manager

from app.my_types import AdvSetting
from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models import  KeywordSetting
from app.utils.db.models import RefLink, User

from app.utils.db.session_maker import get_async_session_maker
import logging

logger = logging.getLogger(__name__)


_sm = get_async_session_maker

@dataclass
class KeywordForKeyboard:
    text: str
    good: bool
    statistic: CalculatedKeyword
    keyword_settings: KeywordSetting
    adv_setting: AdvSetting
    turn_on: bool
    bad_reason: Union[str, None] = None


async def get_keywords_for_keyboard( adv_setting: AdvSetting)-> list[CalculatedKeyword]:
    all_phrases: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv_setting)
    return all_phrases



async def get_csv_file(adv_setting: AdvSetting):
    keywords: list[CalculatedKeyword] = await get_keywords_for_keyboard(adv_setting)
    csv_output = StringIO()
    csv_writer = csv.writer(csv_output,
                            delimiter=';',
                            quotechar='"',
                            quoting=csv.QUOTE_MINIMAL,
                            lineterminator='\n')
    rows = []
    # Заголовки столбцов
    rows.append([
        'Запрос(вхождение)',
        'Запрос(точное соответствие)',
        'Клики',
        'Просмотры',
        "Количество запросов",
        'CTR',
        'Прогнозируемый CTR',
        'Включен-Выключен',
        "Статус",
        'Начальная позиция',
        'Текущая позиция',
        'Дополнительные клики'
    ])

    for keyword in keywords:
        clicks = keyword.clicks
        views = keyword.views
        ctr = round(keyword.ctr * 100, 2)
        if keyword.reason == 'max_position':
            hard_status = 'ЦП'
        elif keyword.reason == KeywordStatus.VIEWS_IS_NOT_ENOUGH:
            hard_status = 'МП'
        elif keyword.hard_status == BLACK_LIST:
            hard_status = 'НРФ'
        elif keyword.reason == 'max_cpc':
            hard_status = 'МС'
        elif keyword.hard_status == TURN_OFF:
            hard_status = 'О'
        elif keyword.hard_status == WHITE_LIST:
            hard_status = 'БС'
        elif keyword.hard_status == AUTO_MODE:
            hard_status = 'А'
        else:
            raise ValueError(f'Unknown hard_status: {keyword.hard_status}')

        turn_on = '✅Включен' if keyword.status == KeywordStatus.GOOD else '❌Выключен'

        # Определение позиций
        first_position = ''
        second_position = ''
        if adv_setting.parsing_active:
            if keyword.cpm:
                first_position = keyword.base_position
                second_position = keyword.promo_position
            elif keyword.real_position:
                first_position = keyword.real_position
            elif keyword.real_position == 0:
                first_position = ">i"
            else:
                first_position = '?'

        rows.append([
        keyword.text,
        '"' + keyword.text + '"',
        clicks,
        views,
        keyword.query,
        ctr,
        round(keyword.predict_ctr * 100, 2),
        turn_on,
        hard_status,
        first_position,
        second_position,
        keyword.keyword_setting.added_clicks or 0
        ])

    for row in rows:
        logger.debug(row)
        csv_writer.writerow(row)
    csv_string = csv_output.getvalue()
    csv_output.close()

    return csv_string

async def create_ref_link(ref_link_name, user_telegram_id):
    stmt = select(RefLink).where(and_(RefLink.name == ref_link_name, RefLink.referrer_id == user_telegram_id))
    async with _sm() as session:
        result = await session.execute(stmt)
        ref_link = result.scalar_one_or_none()
        if ref_link:
            return False
        stmt = select(User.id).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user_id = result.scalar_one()
        ref_link = RefLink(name=ref_link_name, referrer_id=user_id)
        session.add(ref_link)
        await session.commit()
        return ref_link

#
# async def get_keyword_history_graphic(adv_original_id):
#     import matplotlib
#     from matplotlib.ticker import MaxNLocator
#     matplotlib.use('Agg')
#     from matplotlib import pyplot as plt
#     async with _sm() as session:
#         stmt = select(AdvKeyword.text, func.sum(AdvKeyword.views).label('views')) \
#             .where(AdvKeyword.adv_setting_id == adv_original_id) \
#             .group_by(AdvKeyword.text) \
#             .order_by(desc('views')).limit(5)
#         result = await session.execute(stmt)
#         texts = result.scalars().all()
#         stmt = select(AdvSetting).where(AdvSetting.id == adv_original_id)
#         adv = await session.execute(stmt)
#         adv = adv.scalar()
#         limit = int(7*24/8) + 1
#         nmid = adv.nmids[0]
#         stmt = select(CommonKeyword) \
#             .join(CommonKeyword.wb_item_positions) \
#             .options(joinedload(CommonKeyword.wb_item_positions)) \
#             .where(and_(
#             WBItemPosition.nmid == nmid,
#                         CommonKeyword.text.in_(texts)
#                         )).limit(limit)
#         result = await session.execute(stmt)
#         common_keywords: list[CommonKeyword] = result.unique().scalars().all()
#
#         # Подготовка дат за последние 7 дней
#         end_date = datetime.datetime.now()
#         start_date = end_date - datetime.timedelta(days=7)
#         date_range = pd.date_range(start=start_date, end=end_date)
#         frames = []
#         # Создание DataFrame
#         for keyword in common_keywords:
#             data = {
#                 "Ключи": [],
#                 "Дата": [],
#                 "Позиция": []
#             }
#             positions = keyword.wb_item_positions
#             if not positions:
#                 return None
#             last_position: WBItemPosition = max(positions, key=lambda x: x.timestamp)
#             for date in date_range:
#                 close_position = min(positions, key=lambda x: abs(x.timestamp - date)).real_position
#                 data["Ключи"].append(keyword.text + f'({last_position.real_position})')
#                 data["Дата"].append(date)
#                 beutify_position = close_position - 0.5 +  random.randint(1, 9)*0.1
#                 data["Позиция"].append(beutify_position)
#             frames.append(pd.DataFrame(data))
#         if not frames:
#             return None
#         df = pd.concat(frames, ignore_index=True)
#         # Построение графика без легенды
#         plt.figure(figsize=(10, 6))
#         if len(common_keywords) > 5:
#             def get_graphic_and_legend():
#                 sns.lineplot(data=df, x="Дата", y="Позиция", hue="Ключи", marker="o", legend=False)
#                 plt.xticks(rotation=45)
#                 plt.title("Позиции за последние 7 дней")
#                 plt.tight_layout()
#                 plt.gca().invert_yaxis()
#                 ax = plt.gca()  # Получение текущего осевого объекта
#                 ax.yaxis.set_major_locator(MaxNLocator(integer=True))
#                 image_stream = BytesIO()
#                 plt.savefig(image_stream, format='jpg')
#                 image_stream.seek(0)
#                 plt.close()
#                 # Создание отдельной легенды
#                 plt.figure(figsize=(10, 6))
#                 for name, group in df.groupby('Ключи'):
#                     plt.plot([], [], label=name)
#                 plt.legend()
#                 plt.axis('off')
#                 legend_stream = BytesIO()
#                 plt.savefig(legend_stream, format='jpg')
#                 legend_stream.seek(0)
#                 plt.close()
#                 return image_stream, legend_stream
#             loop = asyncio.get_event_loop()
#             image_stream, legend_stream = await loop.run_in_executor(None, get_graphic_and_legend)
#             return image_stream, legend_stream
#         else:
#             def get_graphic():
#                 sns.lineplot(data=df, x="Дата", y="Позиция", hue="Ключи", marker="o", legend=True)
#                 plt.xticks(rotation=45)
#                 plt.title("Позиции за последние 7 дней")
#                 plt.tight_layout()
#                 plt.gca().invert_yaxis()
#                 ax = plt.gca()  # Получение текущего осевого объекта
#                 ax.yaxis.set_major_locator(MaxNLocator(integer=True))
#                 image_stream = BytesIO()
#                 plt.savefig(image_stream, format='jpg')
#                 image_stream.seek(0)
#                 plt.close()
#                 return image_stream
#             loop = asyncio.get_event_loop()
#             image_stream = await loop.run_in_executor(None, get_graphic)
#             return image_stream, None
import csv
import logging
from io import StringIO

from sqlalchemy import and_, select

from app.client_bot.const import AUTO_MODE, BLACK_LIST, TURN_OFF, WHITE_LIST

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from app.modules.wb_adv_updater.phrases_processor import get_good_bad_phrases
from app.utils.db.models import RefLink, User
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)


_sm = get_async_session_maker


# @dataclass
# class KeywordForKeyboard:
#     text: str
#     good: bool
#     statistic: CalculatedKeyword
#     keyword_settings: KeywordSetting
#     adv_setting: AdvSetting
#     turn_on: bool
#     bad_reason: str | None = None


async def get_keywords_for_keyboard(adv_setting: AdvSetting) -> list[CalculatedKeyword]:
    all_phrases: list[CalculatedKeyword] = await get_good_bad_phrases(adv_setting)
    return all_phrases


async def get_csv_file(adv_setting: AdvSetting) -> str:
    keywords: list[CalculatedKeyword] = await get_keywords_for_keyboard(adv_setting)
    csv_output = StringIO()
    csv_writer = csv.writer(
        csv_output,
        delimiter=";",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    header_row = [
        "Запрос(вхождение)",
        "Запрос(точное соответствие)",
        "Клики",
        "Просмотры",
        "Показов (история)",
        "CTR",
        "Прогнозируемый CTR",
        "Включен-Выключен",
        "Статус",
        "Позиция",
        "Рейтинг ключа",
        "Заказов",
    ]
    data_rows: list[list[str]] = []
    # Заголовки столбцов

    for keyword in keywords:
        clicks = keyword.clicks
        assert clicks is not None
        views = keyword.views
        assert views is not None
        predicted_ctr = keyword.predict_ctr or keyword.ctr
        ctr = round(keyword.ctr * 100, 2)
        try:
            keyword_reason = keyword.reason
        except Exception:
            keyword_reason = None
        if keyword_reason == "max_position":
            hard_status = "ЦП"
        elif keyword.hard_status == BLACK_LIST:
            hard_status = "НРФ"
        elif keyword_reason == "max_cpc":
            hard_status = "МС"
        elif keyword.hard_status == TURN_OFF:
            hard_status = "О"
        elif keyword.hard_status == WHITE_LIST:
            hard_status = "БС"
        elif keyword.hard_status == AUTO_MODE:
            hard_status = "А"
        else:
            raise ValueError(f"Unknown hard_status: {keyword.hard_status}")

        turn_on = "✅Включен" if keyword.status == KeywordStatus.GOOD else "❌Выключен"
        # TODO: Привести выгрузку к текущему формату, по уму - полностью переделать, убрать не а
        # Определение позиции (единое поле)
        first_position: str | float = ""
        position_value = keyword.position
        if position_value > 0:
            first_position = int(position_value + 0.5)
        elif position_value == 0:
            first_position = ">"
        else:
            first_position = "?"  # TODO: Кажется тут ошибка, потому что если позиция не может быть None
        data_rows.append(
            [
                keyword.text,
                '"' + keyword.text + '"',
                str(clicks),
                str(views),
                str(keyword.total_views if keyword.total_views else 0),
                str(ctr).replace(".", ","),
                str(round(predicted_ctr * 100, 2)).replace(".", ","),
                turn_on,
                hard_status,
                str(first_position),
                str(round(keyword.rating_by_orders * 100, 4)).replace(".", ","),
                str(keyword.total_orders if keyword.total_orders else 0),
            ]
        )

    data_rows.sort(key=lambda loc_row: int(loc_row[-1]), reverse=True)
    rows = [header_row] + data_rows

    for row in rows:
        logger.debug(row)
        csv_writer.writerow(row)
    csv_string = csv_output.getvalue()
    csv_output.close()

    return csv_string


async def create_ref_link(ref_link_name: str, user_telegram_id: int) -> RefLink | None:
    stmt = select(RefLink).where(
        and_(RefLink.name == ref_link_name, RefLink.referrer_id == user_telegram_id)
    )
    async with _sm(read_only=False) as session:
        result_ref_link = await session.execute(stmt)
        ref_link = result_ref_link.scalar_one_or_none()
        if ref_link:
            return None
        stmt_for_user_id = select(User.id).where(
            User.user_telegram_id == user_telegram_id
        )
        result = await session.execute(stmt_for_user_id)
        user_id: int = result.scalar_one()
        ref_link = RefLink(name=ref_link_name, referrer_id=user_id)
        session.add(ref_link)
        await session.commit()
        return ref_link


# TODO: Выпилить из кода парсер позиций
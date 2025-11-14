

from typing import List
from faker import Faker
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.models import KeywordSetting

fake = Faker("ru_RU")


def generate_calculated_keywords(keyword_settings: list[KeywordSetting]) -> list[CalculatedKeyword]:
    """Создаёт CalculatedKeyword DTO, связанные по keyword_setting_original_id."""
    result = []
    for ks in keyword_settings:
        predict_ctr = round(fake.pyfloat(min_value=0.1, max_value=3.0), 3)
        status = (
            KeywordStatus.GOOD
            if ks.hard_status in (1, 2) and predict_ctr >= 1.0
            else KeywordStatus.BAD
        )


        result.append(
            CalculatedKeyword(
                keyword_setting_original_id=ks.id,
                text=ks.text,
                clicks=fake.random_int(10, 1000),
                views=fake.random_int(100, 10000),
                spend=round(fake.pyfloat(min_value=1, max_value=500), 2),
                predict_ctr=predict_ctr,
                baes_ctr=predict_ctr * 0.8,
                hard_status=ks.hard_status,
                status=status,
                position=fake.random_int(-1, 6000),
                relevant=ks.relevant,
            )
        )
    return result
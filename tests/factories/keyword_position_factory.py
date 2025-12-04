import factory
from factory.fuzzy import FuzzyDateTime, FuzzyText, FuzzyInteger, FuzzyFloat
from datetime import datetime, timedelta, timezone

from app.core.mp.wb.dto import KeywordPosition

class KeywordStatFromJamFactory(factory.Factory):
    class Meta: # pyright: ignore
        model = KeywordPosition

    nmid = FuzzyInteger(100000, 9999999)
    text = FuzzyText(length=10)
    date = factory.LazyFunction(
        lambda: FuzzyDateTime( # pyright: ignore
            datetime.now(timezone.utc) - timedelta(days=30),
            datetime.now(timezone.utc)
        ).fuzz().date()
    )
    average_position = FuzzyFloat(1.0, 100.0, precision=2)
    orders = FuzzyInteger(0, 1000)
    total_views_avr_for_day = FuzzyInteger(100, 10000)



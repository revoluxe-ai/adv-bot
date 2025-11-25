import factory
from factory.fuzzy import FuzzyDateTime, FuzzyText, FuzzyInteger, FuzzyFloat
from datetime import datetime, timedelta, timezone

from app.core.mp.wb.dto import KeywordPosition

class KeywordPositionFactory(factory.Factory):
    class Meta:
        model = KeywordPosition

    nmid = FuzzyInteger(100000, 9999999)
    text = FuzzyText(length=10)
    date = factory.LazyAttribute(lambda o: FuzzyDateTime(datetime.now(timezone.utc) - timedelta(days=30), datetime.now(timezone.utc)).evaluate(2, None, {}).date())
    average_position = FuzzyFloat(1.0, 100.0, precision=2)
    orders = FuzzyInteger(0, 1000)
    total_views_avr_for_day = FuzzyInteger(100, 10000)



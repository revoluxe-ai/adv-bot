import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting, WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User

fake = Faker("ru_RU")


class WBCabinetFactory(SQLAlchemyModelFactory):
    class Meta:
        model = WBCabinet
        sqlalchemy_session = None

    id = factory.Sequence(lambda n: n + 1_000_000)
    shop_id = factory.LazyFunction(lambda: fake.uuid4())
    active = True
    expiration_time = factory.LazyFunction(lambda: fake.date_time_between(start_date="now", end_date="+30d"))
    balance = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0, max_value=1000), 2))
    bonus = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0, max_value=100), 2))
    demo = False
    expiration_alarm_days_pass = None


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None

    id = factory.Sequence(lambda n: n + 1_000)


class WBUserCabinetFactory(SQLAlchemyModelFactory):
    class Meta:
        model = WBUserCabinet
        sqlalchemy_session = None

    id = factory.Sequence(lambda n: n + 1_000)
    name = factory.LazyFunction(lambda: fake.company())
    wb_cabinet = factory.SubFactory(WBCabinetFactory)
    user = factory.SubFactory(UserFactory)

class AdvSettingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = AdvSetting
        sqlalchemy_session = None

    adv_id = factory.Sequence(lambda n: 1_000_000 + n)
    _search_adv_id = factory.LazyAttribute(lambda o: o.adv_id)

    max_place = factory.LazyFunction(lambda: fake.random_int(5, 100))
    name = factory.LazyFunction(lambda: fake.sentence(nb_words=3))
    max_cpm = factory.LazyFunction(lambda: fake.random_int(50, 3000))
    plan_for_sales_for_day = factory.LazyFunction(lambda: fake.random_int(10, 50))
    wb_cabinet = factory.SubFactory(WBCabinetFactory)
    target_price_for_order = factory.LazyFunction(
        lambda: round(fake.pyfloat(min_value=50, max_value=500), 2)
    )

    max_price_for_order = factory.LazyAttribute(
        lambda o: round(
            fake.pyfloat(
                min_value=o.target_price_for_order + 10,
                max_value=o.target_price_for_order + 400,
            ),
            2,
        )
    )

    active_status = "started"
    wb_cabinet_id = None

    auto_update_white_list = True
    auto_update_minus_phrases = True
    auto_update_target_place = True
    auto_update_exponent = True
    bot_active = False
    aggressiveness = 3
    exponent_predict_ctr = factory.LazyFunction(
        lambda: round(fake.pyfloat(min_value=0.5, max_value=2.0), 3)
    )
    auto_add_only_relevant_phrase = factory.LazyFunction(lambda: fake.boolean())


class KeywordSettingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = KeywordSetting
        sqlalchemy_session = None

    adv_setting_id = None
    text = factory.LazyFunction(lambda: fake.unique.word())
    hard_status = factory.LazyFunction(lambda: fake.random_element([0, 1, 2, 3]))
    relevant = factory.LazyAttribute(
        lambda o: o.hard_status in (1, 2, 3) and fake.boolean(chance_of_getting_true=80)
    )

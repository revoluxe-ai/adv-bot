from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, joinedload, contains_eager

from app.utils.db.models import User, WBCabinet, WBUserCabinet, RefLink
from app.modules.wb_adv_updater.models import ItemFeature, KeywordFeature, GlobalCategorySetting
from app.modules.common_slaves.wildberries.models import (WBUserCabinet,
                                                          WBToken,
                                                          AdvSetting,
                                                          AdvKeyword,
                                                          KeywordSetting,
                                                          WBCard)
from app.utils.db.session_maker import get_session_maker


recipient_db_session = get_session_maker()


def get_donor_sm():
    db_connector = f'postgresql://advupdater:uioyoh&.rdklh56b@147.45.239.215:5432/default_db'
    engine = create_engine(db_connector)
    return sessionmaker(bind=engine)


donor_sm = get_donor_sm()


if __name__ == '__main__':
    with recipient_db_session() as session:
        subquery = (
            select(User)
            .join(User.wb_user_cabinets)
            .join(WBUserCabinet.wb_cabinet)
            .join(WBCabinet.adv_settings)
            .join(AdvSetting.adv_keywords)
            .join(AdvKeyword.keyword_setting)
            .join(User.wb_tokens)
            .options(
                contains_eager(User.wb_user_cabinets)
                .contains_eager(WBUserCabinet.wb_cabinet)
                .contains_eager(WBCabinet.adv_settings)
                .contains_eager(AdvSetting.adv_keywords)
                .contains_eager(AdvKeyword.keyword_setting)
            )
            .where(User.username == 'MARIYA_Zommer', WBUserCabinet.name == "СТМ")
        ).alias('subquery')

        stmt = select(User).join(subquery, User.id == subquery.c.id)
        user = session.execute(stmt).scalars().first()
        wb_user_cabinets = user.wb_user_cabinets
    wb_user_cabinets = [wb_user_cabinet for wb_user_cabinet in wb_user_cabinets if wb_user_cabinet.name == 'СТМ']
    wb_user_cabinet = wb_user_cabinets[0]
    wb_cabinet = wb_user_cabinet.wb_cabinet
    adv_settings = wb_cabinet.adv_settings
    adv_setting = adv_settings[0]
    adv_keywords = adv_setting.adv_keywords
    adv_keyword = adv_keywords[0]
    keyword_setting = adv_keyword.keyword_setting
    wb_tokens = user.wb_tokens
    wb_token = wb_tokens[0]
    pass



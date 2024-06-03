from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, joinedload, selectinload

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
    db_connector = f'postgresql://gen_user:SV%7De%23CUTIX1KrW@147.45.239.215:5432/default_db'
    engine = create_engine(db_connector)
    return sessionmaker(bind=engine)


donor_sm = get_donor_sm()


if __name__ == '__main__':
    with recipient_db_session() as session:
        stmt = select(User).where(User.username == 'MARIYA_Zommer')
        user = session.query(stmt)
        print(user)

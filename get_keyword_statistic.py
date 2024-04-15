from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater.data_managers import get_keywords_statistic
from app.utils.db.session_maker import get_async_session_maker

sm = get_async_session_maker()


if __name__ == '__main__':

    with sm() as session:
        stmt = select(AdvSetting).filter(AdvSetting.adv_id ==  15010746)
        result = session.execute(stmt)
        adv_setting = result.scalar()

        pass_days = None



    keywords_stats = get_keywords_statistic(adv_setting, pass_days)

    for keywords_stat in keywords_stats:
        print(keywords_stat.text, keywords_stat.ctr, keywords_stat.clicks, keywords_stat.viess)

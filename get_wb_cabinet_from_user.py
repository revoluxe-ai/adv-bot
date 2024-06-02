from app.utils.db.models import User, WBCabinet, WBUserCabinet
from app.utils.db.session_maker import get_session_maker

sm = get_session_maker()


if __name__ == '__main__':
    with sm() as session:
        wb_cabinets = session.query(WBCabinet)\
            .join(WBCabinet.wb_user_cabinets)\
            .join(WBUserCabinet.user)\
            .filter(User.username == 'IrinaShackaya').all()
        pass





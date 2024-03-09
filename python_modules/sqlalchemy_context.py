from image_master.database.model import get_session_maker
from contextlib import contextmanager
from sqlalchemy.orm import Session

@contextmanager
def session_auto_commit()->Session:
    sm = get_session_maker()
    s = sm()
    try:
        yield s
        s.commit()
    except:
        s.rollback()
        raise
    finally:
        s.close()
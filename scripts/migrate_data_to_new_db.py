from app.utils.db.session_maker import get_session_maker


recipient_db_session = get_session_maker()



def get_donor_sm():
    db_connector = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:5432/{postgres_dbname}'
    return db_connector
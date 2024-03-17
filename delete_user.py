from select import select

from app.session_maker import  get_session_maker
from app.telegram_bot.models import User

sm = get_session_maker()




if __name__ == '__main__':
    with sm() as session:
        # Находим объекты, которые хотим удалить
        stmt = select(User).where(User.user_telegram_id == 5378020690)
        results = session.execute(stmt)
        users_to_delete = results.scalars().all()
        # Удаляем найденные объекты
        for user in users_to_delete:
            session.delete(user)
        session.commit()
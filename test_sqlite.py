from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Создание базы данных и модели
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)

# Создаем тестовую базу данных
engine = create_engine('sqlite:///test.db')
Base.metadata.create_all(engine)

# Создаем сессию
Session = sessionmaker(bind=engine)
session = Session()

# Добавляем тестового пользователя
user = User(name='Test User')
session.add(user)
session.commit()

# Получаем пользователя и выводим результат
result = session.query(User).first()
print(f"Имя пользователя: {result.name}")

# Закрываем сессию
session.close()
print("Тест SQLAlchemy с SQLite прошел успешно!") 
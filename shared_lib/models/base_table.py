from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from sqlalchemy import Integer


class BaseTable(DeclarativeBase):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    @declared_attr
    def __tablename__(self):
        return self.__name__.lower()


    def __repr__(self) -> str:
        return f"<BaseTable id={self.id}>"

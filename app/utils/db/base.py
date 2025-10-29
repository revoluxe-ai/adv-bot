from sqlalchemy import Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, declared_attr
from sqlalchemy.orm import DeclarativeBase, mapped_column
from typing import Any


class Base(DeclarativeBase):
    pass


class BaseTable(Base):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    @declared_attr
    def __tablename__(self) -> Any:
        return self.__name__.lower()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.id}>"

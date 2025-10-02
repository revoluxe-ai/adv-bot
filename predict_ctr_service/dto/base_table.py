from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, declared_attr


class BaseTable(DeclarativeBase):
    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    @declared_attr.directive
    def __tablename__(self) -> str:
        return self.__name__.lower()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.id}>"

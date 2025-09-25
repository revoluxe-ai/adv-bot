from sqlalchemy.exc import SQLAlchemyError
from typing import Any, cast

from . import model


class DataBase:
    def __init__(self) -> None:
        self.Session = model.get_session()

    def get_count_images(self) -> int:
        s = self.Session()
        try:
            result = s.query(model.Image).count()
        except SQLAlchemyError:
            raise SQLAlchemyError
        finally:
            s.close()
        return cast(int, result)

    def get_count_background_images(self) -> int:
        s = self.Session()
        try:
            result = s.query(model.Image).where(model.Image.is_background is True).count()
        except SQLAlchemyError:
            raise SQLAlchemyError
        finally:
            s.close()
        return cast(int, result)

    def get_image_by_id(self, image_id: int) -> model.Image:
        s = self.Session()
        image: model.Image = s.query(model.Image).get(image_id)
        return image

    def get_all_images(self) -> tuple[Any, Any]:
        session = self.Session()
        images = session.query(model.Image).order_by(model.Image.id).yield_per(50)
        return images, session

    def get_background_images(self) -> tuple[Any, Any]:
        session = self.Session()
        images = session.query(model.Image).where(model.Image.is_background is True).order_by(model.Image.id).yield_per(50)
        return images, session

from sqlalchemy.exc import SQLAlchemyError

from . import model
from .model import Image


class DataBase:
    def __init__(self):
        self.Session = model.get_session()

    def get_count_images(self):
        s = self.Session()
        try:
            result = s.query(Image).count()
        except SQLAlchemyError:
            raise SQLAlchemyError
        finally:
            s.close()
        return result


    def get_count_background_images(self):
        s = self.Session()
        try:
            result = s.query(Image).where(Image.is_background==True).count()
        except SQLAlchemyError:
            raise SQLAlchemyError
        finally:
            s.close()
        return result


    def get_image_by_id(self, image_id:int):
       s = self.Session()
       image:Image = s.query(Image).get(image_id)
       return image

    def get_all_images(self):
        session = self.Session()
        images = session.query(Image).order_by(Image.id).yield_per(50)
        return images, session



    def get_background_images(self):
        session = self.Session()
        images = session.query(Image).where(Image.is_background == True).order_by(Image.id).yield_per(50)
        return images, session









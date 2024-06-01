import logging
import os

from PIL import Image as PilImage
from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from auto_adv_master.utils.image_master import image_tools
from python_modules import path_setting_funcs

logger  = logging.getLogger(__name__)


Base = declarative_base()









def create_new_tables():
    db_connector = path_setting_funcs.get_alchemy_row()
    engine = create_engine(
        db_connector)
    Base.metadata.create_all(engine)



def get_Image(name:str, vector, keyword:str, width, height, is_background = False, good_for_poster = None):
    Img = Image(name=name,
                vector=vector,
                keyword=keyword,
                is_background=is_background,
                width = width,
                height = height,
                good_for_poster = good_for_poster)
    return Img



images_folder = 'card_media_creator/source'

# image_keyword_association = Table('image_keyword_association', Base.metadata,
#     Column('image_id', Integer, ForeignKey('images.id')),
#     Column('keyword_id', Integer, ForeignKey('keywords.id'))
# )

image_keyword_association = Table('image_keyword_association', Base.metadata,
    Column('image_id', Integer, ForeignKey('images.id')),
    Column('keyword_id', Integer, ForeignKey('keywords.id'))
)





class Keyword(Base):
    __tablename__ = 'keywords'
    id = Column(Integer, primary_key=True)
    text = Column(String, unique=True)
    images = relationship("Image", secondary=image_keyword_association, back_populates="keywords")
    word2vec = Column('word2vec', ARRAY(Float), nullable=True)



WB_CARD_MEDIA_FOLDER = 'wb_cards_media'

class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    offer_id = Column(String, unique=True)
    dhash = Column(String, ForeignKey('images.dhash'))
    image = relationship("Image", back_populates="items")
    barcode = Column(String(), unique=True)
    size_int = Column(Integer(), nullable=True)
    width = Column(Integer(), nullable=True)
    height = Column(Integer(), nullable=True)
    material = Column(String())
    wb_category_name = Column(String(),)
    __table_args__  = (UniqueConstraint('dhash', 'material',
                                        'wb_category_name', name='dont_item_copy'),
                       UniqueConstraint('offer_id', name='unique_offer_id'),
                       UniqueConstraint('barcode', name='unique_barcode'),)

    """
    Это временный метод, основной - переписать по
    анализу из Neo4j
    """
    @property
    def main_keyword(self):
        return self.image.keywords[0].text


    @property
    def default_price(self):
        price = 1500
        return price


    @hybrid_property
    def size(self):
        assert isinstance(self.size_int, int)
        size_int_str = str(self.size_int)
        assert len(size_int_str) == 4
        half_1 = size_int_str[:2]
        half_2 = size_int_str[2:]
        return half_1 + 'x' + half_2
    @property
    def X(self) -> float:
        return self._X

    @X.setter
    def X(self, value):
        assert isinstance(value, float)
        self._X = value

    def get_wb_json_characteristics(self, brand: str):
       generator = WbJsonGenerator()
       return generator.get_wb_json_characteristics(self, brand)


    @property
    def media(self):
        brand_folder = os.path.join(WB_CARD_MEDIA_FOLDER, self.brand)
        card_folder = os.path.join(brand_folder, self.offer_id)
        media = []
        for file in os.listdir(card_folder):
            file_path = os.path.join(card_folder, file)
            image = PilImage.open(file_path)
            media.append(image)
        return media

    @media.setter
    def media(self, medias: list[PilImage]):
        brand = self.brand
        brand_folder = os.path.join(WB_CARD_MEDIA_FOLDER, brand)
        if not os.path.exists(brand_folder):
            os.mkdir(brand_folder)
        card_folder = os.path.join(brand_folder, self.offer_id)
        if not os.path.exists(card_folder):
            os.mkdir(card_folder)
        for n, media in enumerate(medias, 1):
            file_path = os.path.join(card_folder, str(n) + '.png')
            media.save(file_path)







class Image(Base):
    __tablename__ = 'images'
    id = Column(Integer, primary_key=True)
    vector = Column("vector", ARRAY(Float))
    nouns = Column(ARRAY(String()), nullable=True)
    is_background = Column(Boolean, default=False)
    width = Column(Integer)
    height = Column(Integer)
    gpt_describe= Column(String())
    good_for_poster = Column(Boolean, default=None)
    owner = Column(String())
    dhash = Column(String(), unique=True)
    items = relationship("Item", back_populates="image", uselist=True)
    old_keywords =  Column(ARRAY(String))
    # keywords = relationship("Keyword",
    #                         secondary=image_keyword_association,
    #                         back_populates="images",
    #                         primaryjoin="Image.id==image_keyword_association.c.image_id")
    keywords = relationship("Keyword",
                                   secondary=image_keyword_association,
                                   back_populates="images")
    __table_args__ = (UniqueConstraint('dhash'),)





    def show(self):
        it = image_tools
        img = it.resize_image_proportionally(self.pil_image, 200)
        img.show()

    @hybrid_property
    def local_path(self):
        folder = 'card_media_creator/source'
        return os.path.join(folder, self.dhash + '.png')


    @property
    def pil_image(self):
        image = PilImage.open(self.local_path)
        return image







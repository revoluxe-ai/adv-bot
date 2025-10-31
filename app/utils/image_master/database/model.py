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
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.utils.image_master import image_tools

logger = logging.getLogger(__name__)


Base = declarative_base()


def get_Image(
    name: str,
    vector,
    keyword: str,
    width,
    height,
    is_background=False,
    good_for_poster=None,
):
    Img = Image(
        name=name,
        vector=vector,
        keyword=keyword,
        is_background=is_background,
        width=width,
        height=height,
        good_for_poster=good_for_poster,
    )
    return Img


images_folder = "card_media_creator/source"

# image_keyword_association = Table('image_keyword_association', Base.metadata,
#     Column('image_id', Integer, ForeignKey('images.id')),
#     Column('keyword_id', Integer, ForeignKey('keywords.id'))
# )

image_keyword_association = Table(
    "image_keyword_association",
    Base.metadata,
    Column("image_id", Integer, ForeignKey("images.id")),
    Column("keyword_id", Integer, ForeignKey("keywords.id")),
)


class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True)
    text = Column(String, unique=True)
    images = relationship(
        "Image", secondary=image_keyword_association, back_populates="keywords"
    )
    word2vec = Column("word2vec", ARRAY(Float), nullable=True)


WB_CARD_MEDIA_FOLDER = "wb_cards_media"


class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True)
    vector = Column("vector", ARRAY(Float))
    nouns = Column(ARRAY(String()), nullable=True)
    is_background = Column(Boolean, default=False)
    width = Column(Integer)
    height = Column(Integer)
    gpt_describe = Column(String())
    good_for_poster = Column(Boolean, default=None)
    owner = Column(String())
    dhash = Column(String(), unique=True)
    old_keywords = Column(ARRAY(String))
    # keywords = relationship("Keyword",
    #                         secondary=image_keyword_association,
    #                         back_populates="images",
    #                         primaryjoin="Image.id==image_keyword_association.c.image_id")
    keywords = relationship(
        "Keyword", secondary=image_keyword_association, back_populates="images"
    )
    __table_args__ = (UniqueConstraint("dhash"),)

    def show(self):
        it = image_tools
        img = it.resize_image_proportionally(self.pil_image, 200)
        img.show()

    @hybrid_property
    def local_path(self):
        folder = "card_media_creator/source"
        return os.path.join(folder, self.dhash + ".png")

    @property
    def pil_image(self):
        image = PilImage.open(self.local_path)
        return image

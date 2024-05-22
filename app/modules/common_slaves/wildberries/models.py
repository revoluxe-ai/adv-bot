import datetime
import json
from typing import TYPE_CHECKING

import jwt
from sqlalchemy import (
    BIGINT,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import UniqueConstraint

from app.utils.db.base import BaseTable

from . import exceptions

if TYPE_CHECKING:
    from app.utils.db.models import User

from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker()


class WBUserCabinet(BaseTable):
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    wb_cabinet = relationship("WBCabinet", back_populates="wb_user_cabinets")
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user: Mapped['User']  = relationship("User", back_populates="wb_user_cabinets",
                                       )
    name = Column(String(255), nullable=False)
    __table_args__ = (UniqueConstraint('wb_cabinet_id', 'user_id',  name='_wb_cabinet_id_user_id_uc'),)





class WBCabinet(BaseTable):
    shop_id = Column(String, nullable=False, unique=True)
    wb_cards = relationship('WBCard', back_populates='wb_cabinet', uselist=True)
    wb_categories = relationship('WBCategory', uselist=True)
    adv_settings = relationship('AdvSetting', back_populates='wb_cabinet', uselist=True)
    wb_user_cabinets: Mapped[list[WBUserCabinet]] = relationship("WBUserCabinet",
                                                           back_populates="wb_cabinet",
                                                                 )
    active = Column(Boolean, default=True)

    expiration_time = Column(DateTime, nullable=False, server_default=text('now() + interval \'7 day\''))
    expiration_alarm_days_pass = Column(Integer, default=None)
    demo: Mapped[bool] = Column(Boolean, default=True)



class WBToken(BaseTable):
    def __repr__(self):
        return f'user_id: {self.user_id}, shop_id: {self.shop_id}'
    api_key = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='wb_tokens',
                        lazy='joined')
    active = Column(Boolean, default=True)
    __table_args__ = (UniqueConstraint('api_key', 'user_id', name='_api_key_user_id_uc'),)



    @property
    def __payload(self):
        try:
            return jwt.decode(self.api_key, options={"verify_signature": False})
        except:
            raise exceptions.NotValidTokenError
    def get_payload(self, key, default=0):
        payload = self.__payload
        expire = payload.get('exp', default)
        if expire < datetime.datetime.now().timestamp():
            raise exceptions.TokenExpiredError('Token expired')
        return payload.get(key)


    @property
    def __expires(self):
        return datetime.datetime.utcfromtimestamp(self.__payload.get('exp'))

    @property
    def expires(self):
        return self.__expires


    @hybrid_property
    def shop_id(self):
        return self.get_payload('sid')

    @property
    def read_only(self) -> bool:
        # Проверяем, содержится ли категория "Токен только на чтение" в категориях
        return "Токен только на чтение" in self.categories

    @hybrid_property
    def categories(self) -> set[str]:
        categories_map = {
            1: "Контент",
            2: "Аналитика",
            3: "Цены и скидки",
            4: "Маркетплейс",
            5: "Статистика",
            6: "Продвижение",
            7: "Вопросы и отзывы",
            8: "Рекомендации",
            30: "Токен только на чтение",
        }
        s = self.get_payload('s', 0)
        categories = set()
        for bit_position, category_name in categories_map.items():
            if s & (1 << bit_position):
                categories.add(category_name)
        return categories




class AdvKeyword(BaseTable):
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'), nullable=False)
    adv_setting = relationship('AdvSetting', back_populates='adv_keywords')
    text = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    positive = Column(Boolean)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(Float, default=0)
    add_to_db = Column(Boolean, default=False)
    keyword_setting_id = Column(Integer, ForeignKey('keywordsetting.id'), nullable=False)
    keyword_setting = relationship('KeywordSetting', back_populates='adv_keywords')
    __table_args__ = (UniqueConstraint('text', 'date', 'adv_setting_id', name='_text_date_adv_setting_id_uc'),)





class WBCategory(BaseTable):
    cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)  # Добавляем внешний ключ, ссылающийся на кабинет
    wb_cabinet = relationship('WBCabinet', back_populates='wb_categories')  # Добавляем связь обратно к WbCabinet
    wb_category_name = Column(String, nullable=False)
    wb_cards = relationship('WBCard',
                            back_populates='wb_category',
                            uselist=True)


class WBCard(BaseTable): # Изменено название таблицы
    nmid = Column(Integer, unique=True, nullable=False)
    offer_id = Column(String)
    name = Column(String)
    wb_category_id = Column(Integer, ForeignKey('wbcategory.id'))
    wb_category = relationship('WBCategory', back_populates='wb_cards',
                               lazy='joined')
    json = Column(JSONB)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'))  # Добавляем внешний ключ к WbCabinet
    wb_cabinet = relationship('WBCabinet', back_populates='wb_cards')
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'))  # Добавлен внешний ключ
    adv_setting = relationship('AdvSetting', back_populates='wb_cards')
    updated = Column(Boolean, default=False)
    add_to_db = Column(Boolean, default=False)


    @hybrid_property
    def card_json(self):
        return json.loads(self.json)

    @property
    def brand(self):
        return self.card_json['brand']

    @property
    def photos(self):
        photos = self.card_json['photos']
        urls = []
        for photo in photos:
            url = photo['big']
            urls.append(url)
        return urls

class AdvSetting(BaseTable):
    def __repr__(self):
        return f'name: {self.name}, adverdId: {self.adv_id}, bot_active: {self.bot_active}, active_status: {self.active_status}'


    adv_id = Column(BIGINT(), unique=True)
    name = Column(String, nullable=False)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    wb_cabinet: Mapped[WBCabinet] = relationship('WBCabinet', back_populates='adv_settings',
                              lazy='joined')
    wb_cards = relationship('WBCard', back_populates='adv_setting', uselist=True)  # Изменено на множественное число
    active_status = Column(String, default=False)
    adv_keywords = relationship('AdvKeyword', back_populates='adv_setting',
                                uselist=True)
    bot_active = Column(Boolean, default=False)
    nmids = Column(JSONB, default=[])
    keyword_settings: Mapped[list['KeywordSetting']] = relationship('KeywordSetting', back_populates='adv_setting',
                                    uselist=True)
    pass_days = Column(Integer, default=30)
    boost = Column(Float, server_default=text('1'))
    type: Mapped[int] = Column(Integer, nullable=True)





class KeywordSetting(BaseTable):

    """
    hard_status
    0 - black listA
    1 - in test
    2 - white list

    """

    text = Column(String, nullable=False)
    adv_setting_id: Mapped[int] = mapped_column(ForeignKey('advsetting.id'))
    adv_setting: Mapped[AdvSetting] = relationship('AdvSetting', back_populates='keyword_settings', uselist=False)
    predict_ctr = Column(Float, nullable=True)
    adv_keywords = relationship('AdvKeyword', back_populates='keyword_setting', uselist=True)
    hard_status = Column(Integer, default=1)
    added_clicks = Column(Integer)
    added_views = Column(Integer)
    auto_block = Column(Boolean)
    __table_args__ = (UniqueConstraint('text', 'adv_setting_id'),
                      Index('ix_text_adv_setting_id', 'text', 'adv_setting_id'))



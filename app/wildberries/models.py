import json
import datetime
import typing

from sqlalchemy import (Column, Integer, String, ForeignKey,
                        BIGINT, Boolean, select, Float, DateTime, Table, text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, sessionmaker, Mapped, mapped_column
import jwt
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from . import exceptions
from app.db.base import BaseTable
from sqlalchemy.schema import UniqueConstraint








class WBCabinet(BaseTable):
    shop_id = Column(String, nullable=False, unique=True)
    wb_cards = relationship('WBCard', back_populates='wb_cabinet', uselist=True)
    wb_categories = relationship('WBCategory', uselist=True)
    adv_settings = relationship('AdvSetting', back_populates='wb_cabinet', uselist=True)
    wb_user_cabinets = relationship("WBUserCabinet", back_populates="wb_cabinet", uselist=True,
                                    lazy='joined')


class WBToken(BaseTable):
    api_key = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='wb_tokens',
                        lazy='joined')


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
            raise exceptions.TokenExpiredError
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
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'))
    adv_setting = relationship('AdvSetting', back_populates='adv_keywords')
    text = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    positive = Column(Boolean)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(Float, default=0)
    add_to_db = Column(Boolean, default=False)
    update_timestamp = Column(DateTime, nullable=False)
    keyword_setting_id = Column(Integer, ForeignKey('keywordsetting.id'))
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
    adv_id = Column(BIGINT(), unique=True)
    name = Column(String, nullable=False)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'))
    wb_cabinet = relationship('WBCabinet', back_populates='adv_settings',
                              lazy='joined')
    min_ctr = Column(Integer)
    wb_cards = relationship('WBCard', back_populates='adv_setting', uselist=True)  # Изменено на множественное число
    active_status = Column(String, default=False)
    adv_keywords = relationship('AdvKeyword', back_populates='adv_setting',
                                uselist=True)
    bot_active = Column(Boolean, default=False)
    nmids = Column(JSONB, default=[])
    keyword_settings = relationship('KeywordSetting', back_populates='adv_setting',
                                    uselist=True)





    @hybrid_property
    def wb_category_name(self):
        if self.wb_cards:
            return self.wb_cards[0].wb_category_name
        return None

    @wb_category_name.expression
    def wb_category_name(cls):
        return select([WBCard.wb_category_name]).where(WBCard.adv_setting_id == cls.id).limit(1).label(
            "wb_category_name")





class KeywordSetting(BaseTable):
    text = Column(String, nullable=False)
    adv_setting_id: Mapped[int] = mapped_column(ForeignKey('advsetting.id'))
    adv_setting: Mapped[AdvSetting] = relationship('AdvSetting', back_populates='keyword_settings', uselist=False)
    predict_ctr = Column(Float, nullable=True)
    pass_days = Column(Integer, nullable=False, default=30)
    adv_keywords = relationship('AdvKeyword', back_populates='keyword_setting', uselist=True)
    __table_args__ = (UniqueConstraint('text', 'adv_setting_id'),)



    @hybrid_property
    def clicks(self):
        clicks = 0
        adv_setting = self.adv_setting
        now = datetime.datetime.now()
        adv_keywords = filter(lambda x: x.keyword == self.text and x.date > now - datetime.timedelta(days=self.pass_days),
                              adv_setting.adv_keywords)
        for keyword in adv_keywords:
            clicks += keyword.clicks
        return clicks


    @clicks.expression
    def clicks(cls):
        # Использование text для задания интервала времени для PostgreSQL
        return (select([func.sum(AdvKeyword.clicks)])
                .where(AdvKeyword.keyword == cls.text,
                       AdvKeyword.date > func.now() - text(f"'{cls.pass_days} days'::interval"))
                .label('clicks'))


    @hybrid_property
    def views(self):
        views = 0
        adv_setting = self.adv_setting
        now = datetime.datetime.now()
        adv_keywords = filter(lambda x: x.keyword == self.text and x.date > now - datetime.timedelta(days=self.pass_days),
                              adv_setting.adv_keywords)
        for keyword in adv_keywords:
            views += keyword.views
        return views


    @views.expression
    def views(cls):
        # Использование text для задания интервала времени для PostgreSQL
        return (select([func.sum(AdvKeyword.views)])
                .where(AdvKeyword.keyword == cls.text,
                       AdvKeyword.date > func.now() - text(f"'{cls.pass_days} days'::interval"))
                .label('views'))

    @hybrid_property
    def spend(self):
        spend = 0
        adv_setting = self.adv_setting
        now = datetime.datetime.now()
        adv_keywords = filter(lambda x: x.keyword == self.text and x.date > now - datetime.timedelta(days=self.pass_days),
                              adv_setting.adv_keywords)
        for keyword in adv_keywords:
            spend += keyword.spend
        return spend


    @spend.expression
    def spend(cls):
        # Использование text для задания интервала времени для PostgreSQL
        return (select([func.sum(AdvKeyword.spend)])
                .where(AdvKeyword.keyword == cls.text,
                       AdvKeyword.date > func.now() - text(f"'{cls.pass_days} days'::interval"))
                .label('spend'))


    # @hybrid_property
    # def timestamp(self):
    #     return (select([func.max(AdvKeyword.date)])

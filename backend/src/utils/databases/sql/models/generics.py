# pylint:disable=missing-module-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods

from sqlalchemy import Column, String, Integer
#from sqlalchemy.orm import relationship

from . import Base


class Ticker(Base):
    __tablename__ = "tickers"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    base = Column(String)
    quote = Column(String)

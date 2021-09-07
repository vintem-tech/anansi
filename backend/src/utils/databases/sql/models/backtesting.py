# pylint:disable=missing-module-docstring
# pylint:disable=missing-class-docstring
# pylint:disable=too-few-public-methods

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import relationship

from . import Base

backtesting_ticker = Table(
    "backtesting_ticker",
    Base.metadata,
    Column(
        "klines_id",
        Integer,
        ForeignKey("backtesting_klines_controllers.id"),
        primary_key=True,
    ),
    Column("ticker_id", Integer, ForeignKey("tickers.id")),
    primary_key=True,
)


class BacktestingKlinesController(Base):
    __tablename__ = "backtesting_klines_controllers"

    id = Column(Integer, primary_key=True, index=True)
    broker = relationship("BacktestingBroker", back_populates="klines")
    keywords = relationship("Keyword", secondary="keyword_author")
    ticker = relationship("Ticker", secondary="backtesting_ticker")
    is_updating = Column(Boolean, default=False)
    oldest_timestamp = Column(TIMESTAMP)
    newest_timestamp = Column(TIMESTAMP)


class BacktestingBroker(Base):
    __tablename__ = "backtesting_brokers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    klines = relationship(
        "BacktestingKlinesController", back_populates="broker"
    )

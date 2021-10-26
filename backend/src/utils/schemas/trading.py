# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
# pylint: disable=unsubscriptable-object

"""Traders pydantic model classes."""

from os import error
from typing import Dict, Optional, Union, List

from pydantic import BaseModel, EmailStr

from src.lib.marketdata.klines.operators.classifiers import didi_v1

class Ticker(BaseModel):
    """Market ticker attributes"""

    symbol: str
    base: str = str()
    quote: str = str()

class OperationalModes(BaseModel):
    """Stores the possible operation modes"""

    real: str = "real"
    test: str = "test"
    backtesting: str = "backtesting"

class BacktestingStatus(BaseModel):
    starting:str = "starting"
    collecting_data:str = "collecting_data"
    running:str = "running"
    finish:str = "finish"
    error:str = "error"
    


# Shared properties
class TraderBase(BaseModel):
    broker: str = "binance"
    tickers: List[Ticker] = [
        Ticker(
            symbol="BTCUSDT",
            base="BTC",
            quote="USDT"
        ),
        Ticker(
            symbol="ETHUSDT",
            base="ETH",
            quote="USDT"
        ),
        Ticker(
            symbol="NEOUSDT",
            base="NEO",
            quote="USDT"
        ),
        Ticker(
            symbol="LINKUSDT",
            base="LINK",
            quote="USDT"
        )
        ]
    mode: str = OperationalModes().backtesting
    classifier: str = "didi_v1"
    classifier_setup: BaseModel = didi_v1.Setup()
    # stoploss:


# Properties to receive on trader creation
class TraderCreate(TraderBase):
    pass


# Properties to receive on Trader update
class TraderUpdate(TraderBase):
    pass


# Properties shared by models stored in DB
class TraderInDBBase(TraderBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True


# Properties to return to client
class Trader(TraderInDBBase):
    pass


# Properties properties stored in DB
class TraderInDB(TraderInDBBase):
    pass
# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument

from pydantic import BaseModel  # , validator

# from typing import Sequence
from ..marketdata.schemas import Market, DidiIndexDefault


class DefaultOperation(BaseModel):
    classifier_name: str = "DidiIndex"
    classifier_setup: BaseModel = DidiIndexDefault()
    market: Market = Market(broker_name="Binance", quote_symbol="BTC", base_symbol = "USDT")
    time_frame: str = "2h"
    backtesting: bool = True
    initial_base_amount:float = 1000.00

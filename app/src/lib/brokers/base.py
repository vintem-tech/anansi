"""Collection of libraries, modules or classes important for the
brokers' implementation"""

# pylint: disable=unused-import
# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods


from typing import Union

import pandas as pd
import requests
from pydantic import BaseModel

from ..utils.schemas import Order, Quantity
from ..utils.tools.documentation import DocInherit
from ..utils.tools.formatting import FormatKlines

DF = pd.core.frame.DataFrame


def get_response(endpoint: str) -> Union[requests.models.Response, None]:
    """A try/cath to handler with request/response."""
    try:
        response = requests.get(endpoint)
        if response.status_code == 200:
            return response

        return None

    except ConnectionError as error:
        raise Exception from error


class Broker:
    """Broker low level functions"""

    def __init__(self, settings=None):
        self.settings = settings

    def server_time(self) -> int:
        """Date time of broker server.

        Returns (int): Seconds timestamp
        """

        raise NotImplementedError

    def max_requests_limit_hit(self) -> bool:
        """Boolean test to verify if the limit of broker requests,
        on current minute (for a given IP), was hit.

        Returns (bool): Hit the limit?
        """

        raise NotImplementedError

    def get_klines(self, ticker_symbol: str, time_frame: str, **kwargs) -> DF:
        """Historical market data (candlesticks, OHLCV).

        Args:
            time_frame (str): '1m', '2h', '1d'...

        **kwargs:
            number_of_candles (int): Number or desired candelesticks for
            request; must to respect the broker limits.

            since (int): Open_time of the first kline
            until (int): Open_time of the last kline

        Returns (DataFrame):
            N lines DataFrame, where 'N' is the number of candlesticks
            returned by broker, which must be less than or equal to the
            'LIMIT_PER_REQUEST' parameter, defined in the broker's
            settings (settings module). The dataframe columns represents
            the information provided by the broker, declared by the
            parameter 'kline_information' (settings, on the broker
            settings class).
        """

        raise NotImplementedError

    def oldest_kline(self, ticker_symbol: str, time_frame: str) -> DF:
        """Oldest avaliable kline of this time frame"""

        return self.get_klines(
            ticker_symbol, time_frame, since=1, number_samples=1
        )[:1]

    def get_price(self, ticker_symbol: str, **kwargs) -> float:
        """Instant average trading price"""
        raise NotImplementedError

    def ticker_info(self, ticker_symbol: str) -> dict:
        """Pertinent information about a 'ticker_symbol' """

        raise NotImplementedError

    def free_quantity_asset(self, asset_symbol: str) -> float:
        """Avaliable amount of a certain asset_symbol."""

        raise NotImplementedError

    def min_notional(self, ticker_symbol: str) -> float:
        """Minimum quantity (base) admitted in an order for
        the market identified by the 'ticker_symbol'."""

        raise NotImplementedError

    def minimal_order_quantity(self, ticker_symbol) -> float:
        """Minimal possible trading amount (quote)."""
        raise NotImplementedError

    def execute_order(self, order: Order):
        """Proceed real trading orders """
        raise NotImplementedError

    def execute_test_order(self, order: Order):
        """Proceed test trading orders """
        raise NotImplementedError


class BrokerSettings(BaseModel):
    """Broker parent class """

    datetime_format: str = "timestamp"
    datetime_unit: str = "seconds"
    base_endpoint: str = str()
    ping_endpoint: str = str()
    time_endpoint: str = str()
    klines_endpoint: str = str()
    request_weight_per_minute: int = None
    records_per_request: int = None
    possible_time_frames: list = [
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    ]
    kline_information: list = [
        "Open_time",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Close_time",
    ]
    klines_desired_informations: list = kline_information[:-1]
    ignore_opened_candle: bool = True
    show_only_desired_info: bool = True
    fee_rate_decimal: float = 0.001

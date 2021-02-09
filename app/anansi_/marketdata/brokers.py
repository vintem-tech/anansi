# pylint: disable=E1136
# pylint: disable=no-name-in-module

"""All the brokers low level communications goes here."""
import sys
from typing import Union

import pandas as pd
import pendulum
import requests
from pydantic import BaseModel

from ..notifiers.notifiers import get_notifier
from ..sql_app.schemas import Market
from ..tools import documentation, formatting
from .settings import BinanceSettings

thismodule = sys.modules[__name__]

DocInherit = documentation.DocInherit
notifier = get_notifier(broadcasters=["TelegramNotifier"])

def get_response(endpoint: str) -> Union[requests.models.Response, None]:
    """A try/cath to handler with request/response."""
    try:
        with requests.get(endpoint) as response:
            if response.status_code == 200:
                return response
    except Exception as connect_exception:
        notifier.error(connect_exception)
    return None


def remove_last_candle_if_unclosed(klines: pd.DataFrame) -> pd.DataFrame:
    """If the last candle are not yet closed, it'll be elimated.

    Args:
        klines (pd.DataFrame): Candlesticks of the desired period Dataframe.

    Returns:
        pd.DataFrame: Adjusted Dataframe.
    """
    last_open_time = klines[-1:].Open_time.item()
    delta_time = (pendulum.now(tz="UTC")).int_timestamp - last_open_time
    unclosed = bool(delta_time < klines.attrs["SecondsTimeFrame"])

    if unclosed:
        return klines[:-1]
    return klines


class Broker:
    """Parent class that should be a model to group broker functions """

    def __init__(self, market: Market, settings: BaseModel):
        self.market = market
        self.settings = settings

    def server_time(self) -> int:
        """Date time of broker server.

        Returns (int): Seconds timestamp
        """
        raise NotImplementedError

    def was_request_limit_reached(self) -> bool:
        """Boolean test to verify if the request limit, in the current
        minute (for a given IP), has been reached.

        Returns (bool): Hit the limit?
        """
        raise NotImplementedError

    def get_klines(self, time_frame: str, **kwargs) -> pd.DataFrame:
        """Historical market data (candlesticks, OHLCV).

        Returns (pd.DataFrame): N lines DataFrame, where 'N' is the number of
        candlesticks returned by broker, which must be less than or equal to
        the 'LIMIT_PER_REQUEST' parameter, defined in the broker's settings
        (settings module). The dataframe columns represents the information
        provided by the broker, declared by the parameter 'kline_information'
        (settings, on the broker settings class).

        Args:
            time_frame (str): '1m', '2h', '1d'...

        **kwargs:
            number_of_candles (int): Number or desired candelesticks
            for request; must to respect the broker limits.

            It's possible to pass timestamps (seconds):
            since (int): Open_time of the first candlestick on desired series
            until (int): Open_time of the last candlestick on desired series
        """

        raise NotImplementedError


class Binance(Broker):
    """All needed functions, wrapping the communication with binance"""

    @DocInherit
    def __init__(self, market: Market, settings=BinanceSettings()):
        super().__init__(market, settings)

    @DocInherit
    def server_time(self) -> int:
        endpoint = self.settings.time_endpoint
        time_str = ((get_response(endpoint)).json()["serverTime"]) / 1000
        return int(float(time_str))

    @DocInherit
    def was_request_limit_reached(self) -> bool:
        ping_endpoint = self.settings.ping_endpoint
        request_weight_per_minute = self.settings.request_weight_per_minute
        requests_on_current_minute = int(
            (get_response(ping_endpoint)).headers["x-mbx-used-weight-1m"]
        )
        if requests_on_current_minute >= request_weight_per_minute:
            return True
        return False

    @DocInherit
    def get_klines(self, time_frame: str, **kwargs) -> pd.DataFrame:
        since: int = kwargs.get("since")
        until: int = kwargs.get("until")
        number_of_candles: int = kwargs.get("number_of_candles")

        endpoint = self.settings.klines_endpoint.format(self.market.ticker_symbol, time_frame)
        if since:
            endpoint += "&startTime={}".format(str(since * 1000))
        if until:
            endpoint += "&endTime={}".format(str(until * 1000))
        if number_of_candles:
            endpoint += "&limit={}".format(str(number_of_candles))
        raw_klines = (get_response(endpoint)).json()

        klines = formatting.FormatKlines(
            time_frame,
            raw_klines,
            datetime_format=self.settings.datetime_format,
            datetime_unit=self.settings.datetime_unit,
            columns=self.settings.kline_information,
        ).to_dataframe()

        if self.settings.ignore_opened_candle:
            klines = remove_last_candle_if_unclosed(klines)

        if self.settings.show_only_desired_info:
            return klines[self.settings.klines_desired_informations]
        return klines

def get_broker(market: Market) -> Broker:
    """Given a market, returns an instantiated broker"""
    return getattr(thismodule, market.broker_name.capitalize())(market)

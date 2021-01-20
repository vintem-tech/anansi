# pylint: disable=E1136
# pylint: disable=no-name-in-module

"""All the brokers low level communications goes here."""
import sys
from decimal import Decimal
from typing import Optional, Union

import pandas as pd
import pendulum
import requests
from binance.client import Client as BinanceClient
from pydantic import BaseModel

from ..notifiers.notifiers import get_notifier
from ..sql_app.schemas import BaseModel, Market, Order, Portfolio
from ..tools import doc, formatting
from .settings import BinanceSettings

thismodule = sys.modules[__name__]

DocInherit = doc.DocInherit
notifier = get_notifier(broadcasters=["TelegramNotifier"])

def get_response(endpoint: str) -> Union[requests.models.Response, None]:
    """A try/cath to handler with request/response."""
    try:
        with requests.get(endpoint) as response:
            if response.status_code == 200:
                return response
    except Exception as connect_exception:
        #raise ConnectionError(
        #    "Could not establish a broker connection."
        #) from connect_exception
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


class Quant:
    """Auxiliary class to store the amount quantity information, useful
    for the trade order flow"""

    is_enough: Optional[bool]
    value: Optional[str]


class Broker:
    """Parent class that should be a model to group broker functions """

    def __init__(self, market: Market, settings: BaseModel):
        self.market = market
        self.settings = settings
        self.ticker_symbol=(market.quote_symbol + market.base_symbol).upper()

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

    def get_price(self) -> float:
        """Intant trading average price"""
        raise NotImplementedError

    def get_portfolio(self) -> Portfolio:
        """The portfolio composition, given a market"""
        raise NotImplementedError

    def get_min_lot_size(self) -> float:
        """Minimal possible trading amount, by quote."""
        raise NotImplementedError

    def execute_order(self, order: Order):
        """Proceed trade orders """
        raise NotImplementedError

    def test_order(self, order: Order):
        """Proceed test orders """
        raise NotImplementedError


class Binance(Broker):
    """All needed functions, wrapping the communication with binance"""

    @DocInherit
    def __init__(self, market: Market, settings=BinanceSettings()):
        super().__init__(market, settings)
        self.client = BinanceClient(
            api_key=self.settings.api_key, api_secret=self.settings.api_secret
        )

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

        endpoint = self.settings.klines_endpoint.format(self.ticker_symbol, time_frame)
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

    @DocInherit
    def get_price(self) -> float:
        return float(self.client.get_avg_price(symbol=self.ticker_symbol)["price"])

    @DocInherit
    def get_portfolio(self) -> float:
        portfolio = Portfolio()
        portfolio.quote, portfolio.base = (
            float(self.client.get_asset_balance(asset=symbol)["free"])
            for symbol in [self.market.quote_symbol, self.market.base_symbol]
        )
        return portfolio

    @DocInherit
    def get_min_lot_size(self) -> float:
        min_notional = float(
            self.client.get_symbol_info(symbol=self.ticker_symbol)[
                "filters"
            ][3]["minNotional"]
        )  # Measured by base asset

        return 1.03*min_notional/self.get_price()

    def _sanitize_quantity(self, quantity: float) -> Quant:
        quant = Quant()
        quant.is_enough = False

        info = self.client.get_symbol_info(symbol=self.ticker_symbol)
        minimum = float(info["filters"][2]["minQty"])
        quant_ = Decimal.from_float(quantity).quantize(Decimal(str(minimum)))

        if float(quant_) > self.get_min_lot_size():
            quant.is_enough = True
            quant.value = str(quant_)

        return quant

    def _sanitize_price(self, price: float) -> str:
        info = self.client.get_symbol_info(symbol=self.ticker_symbol)
        price_filter = float(info["filters"][0]["tickSize"])

        return str(
            Decimal.from_float(price).quantize(Decimal(str(price_filter)))
        )

    def _order_market(self, order: Order) -> dict:
        order_report = dict()

        executor = "order_market_{}".format(order.side)
        quant = self._sanitize_quantity(order.quantity)

        if quant.is_enough:
            order_report = getattr(self.client, executor)(
                symbol=self.ticker_symbol, quantity=quant.value
            )
        return order_report

    def _order_limit(self, order: Order) -> dict:
        order_report = dict()

        executor = "order_limit_{}".format(order.side)
        quant = self._sanitize_quantity(order.quantity)
        price = self._sanitize_price(order.price)

        if quant.is_enough:
            order_report = getattr(self.client, executor)(
                symbol=self.ticker_symbol,
                quantity=quant.value,
                price=price,
            )
        return order_report

    @DocInherit
    def execute_order(self, order: Order) -> dict:
        executor = "_order_{}".format(order.order_type)
        order_report = getattr(self, executor)(order)

        if order.notify:
            notifier.trade(str(order_report))
        return order_report

    @DocInherit
    def test_order(self, order: Order):
        pass

def get_broker(market: Market) -> Broker:
    """Given a market, returns an instantiated broker"""
    return getattr(thismodule, market.broker_name.capitalize())(market)

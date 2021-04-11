# pylint: disable=E1136
# pylint: disable=no-name-in-module

"""All the brokers low level communications goes here."""
import sys
from decimal import Decimal
from typing import Union

import pandas as pd
import requests
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceOrderException
from pydantic import BaseModel

from ...config.settings import BinanceSettings
from ..tools import documentation, formatting
from ..utils.databases.sql.schemas import Market, Order, Portfolio, Quant

thismodule = sys.modules[__name__]
DocInherit = documentation.DocInherit


def get_response(endpoint: str) -> Union[requests.models.Response, None]:
    """A try/cath to handler with request/response."""
    try:
        response = requests.get(endpoint)
        if response.status_code == 200:
            return response
    except ConnectionError as error:
        raise Exception.with_traceback(error) from ConnectionError
    return None


class Broker:
    """Must be a model that groups broker needed low level functions"""

    def __init__(self, market: Market, settings: BaseModel):
        self.market = market
        self.settings = settings
        self.market = market
        self.order = Order()

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

    def get_klines(self, time_frame: str, **kwargs) -> pd.core.frame.DataFrame:
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

    def oldest_kline(self, time_frame: str) -> pd.core.frame.DataFrame:
        """Oldest avaliable kline of this time frame"""

        return self.get_klines(
            time_frame=time_frame, since=1, number_samples=1
        ).iloc[0]

    def get_price(self, **kwargs) -> float:
        """Instant average trading price"""
        raise NotImplementedError

    def get_portfolio(self) -> Portfolio:
        """The portfolio composition, given a market"""
        raise NotImplementedError

    def get_min_lot_size(self) -> float:
        """Minimal possible trading amount, by quote."""
        raise NotImplementedError

    def execute(self, order: Order):
        """Proceed real trading orders """
        raise NotImplementedError

    def execute_test(self, order: Order):
        """Proceed test trading orders """
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
        time_str = (get_response(endpoint)).json()["serverTime"]
        return int(float(time_str) / 1000)

    @DocInherit
    def max_requests_limit_hit(self) -> bool:
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

        endpoint = self.settings.klines_endpoint.format(
            self.market.ticker_symbol, time_frame
        )
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

        if self.settings.show_only_desired_info:
            return klines[self.settings.klines_desired_informations]
        return klines

    @DocInherit
    def get_price(self, **kwargs) -> float:
        return float(
            self.client.get_avg_price(symbol=self.market.ticker_symbol)[
                "price"
            ]
        )

    @DocInherit
    def get_portfolio(self) -> float:
        portfolio = Portfolio()
        portfolio.quote, portfolio.base = (
            float(self.client.get_asset_balance(asset=symbol)["free"])
            for symbol in [self.market.quote_symbol, self.market.base_symbol]
        )
        return portfolio

    @DocInherit
    def get_min_lot_size(self) -> float:  # Measured by quote asset
        min_notional = float(  # Measured by base asset
            self.client.get_symbol_info(symbol=self.market.ticker_symbol)[
                "filters"
            ][3]["minNotional"]
        )
        return 1.03 * min_notional / self.get_price()

    def _sanitize_quantity(self, quantity: float) -> Quant:
        quant = Quant()
        quant.is_enough = False

        info = self.client.get_symbol_info(symbol=self.market.ticker_symbol)
        minimum = float(info["filters"][2]["minQty"])
        quant_ = Decimal.from_float(quantity).quantize(Decimal(str(minimum)))

        if float(quant_) > self.get_min_lot_size():
            quant.is_enough = True
            quant.value = str(quant_)
        return quant

    def _sanitize_price(self, price: float) -> str:
        info = self.client.get_symbol_info(symbol=self.market.ticker_symbol)
        price_filter = float(info["filters"][0]["tickSize"])
        return str(
            Decimal.from_float(price).quantize(Decimal(str(price_filter)))
        )

    def _order_market(self) -> dict:
        executor = "order_market_{}".format(self.order.signal)
        quant = self._sanitize_quantity(self.order.suggested_quantity)

        if quant.is_enough:
            return getattr(self.client, executor)(
                symbol=self.market.ticker_symbol, quantity=quant.value
            )
        return dict()

    def _order_limit(self) -> dict:
        executor = "order_limit_{}".format(self.order.signal)
        quant = self._sanitize_quantity(self.order.suggested_quantity)

        if quant.is_enough:
            return getattr(self.client, executor)(
                symbol=self.market.ticker_symbol,
                quantity=quant.value,
                price=self._sanitize_price(self.order.price),
            )
        return dict()

    @DocInherit
    def _check_and_update_order(self) -> dict:
        order = self.client.get_order(
            symbol=self.market.ticker_symbol, orderId=self.order.id_by_broker
        )
        quote_amount = float(order["executedQty"])
        base_amount = float(order["cummulativeQuoteQty"])
        self.order.price = base_amount / quote_amount
        self.order.timestamp = int(float(order["time"]) / 1000)
        self.order.fulfilled = True
        self.order.proceeded_quantity = quote_amount
        self.order.fee = self.settings.fee_rate_decimal * base_amount

    @DocInherit
    def execute(self, order: Order) -> Order:
        self.order = order
        if self.order.generated_signal == "hold":
            self.order.warnings = "Ignored hold signal"
            return self.order

        order_executor = "_order_{}".format(order.order_type)
        try:
            fulfilled_order = getattr(self, order_executor)()
            if fulfilled_order:
                self.order.id_by_broker = fulfilled_order["orderId"]
                self._check_and_update_order()
            else:
                self.order.warnings = "Insufficient balance"
        except BinanceOrderException as broker_erro:
            self.order.warnings = str(broker_erro)
        return self.order

    @DocInherit
    def execute_test(self, order: Order):
        pass


def get_broker(market: Market) -> Broker:
    """Given a market, returns an instantiated broker"""
    return getattr(thismodule, market.broker_name.capitalize())(market)

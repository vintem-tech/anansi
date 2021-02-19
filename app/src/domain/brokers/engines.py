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
from environs import Env
from pydantic import BaseModel

from ...config.settings import BinanceSettings
from ...repositories.sql_app.schemas import Market, Order, Portfolio, Quant
from ...repositories.sql_app.schemas import Signals as sig
from ...tools import documentation, formatting
from ..marketdata.klines import PriceFromStorage
from ...repositories.sql_app.models import Operation

thismodule = sys.modules[__name__]

DocInherit = documentation.DocInherit


def get_response(endpoint: str) -> Union[requests.models.Response, None]:
    """A try/cath to handler with request/response."""
    try:
        with requests.get(endpoint) as response:
            if response.status_code == 200:
                return response
    except ConnectionError as error:
        raise Exception.with_traceback(error) from ConnectionError
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
        self.market = market
        self.order = Order()

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
        """Proceed trade orders """
        raise NotImplementedError

    def execute_test(self, order: Order):
        """Proceed test orders """
        raise NotImplementedError

class Binance(Broker):
    """All needed functions, wrapping the communication with binance"""

    @DocInherit
    def __init__(self, market: Market, settings=BinanceSettings()):
        super().__init__(market, settings)
        self.client = BinanceClient(
            api_key=self.settings.api_key,
            api_secret=self.settings.api_secret
            )
    
    @DocInherit
    def server_time(self) -> int:
        endpoint = self.settings.time_endpoint
        time_str = (get_response(endpoint)).json()["serverTime"]
        return int(float(time_str)/1000)

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
    def get_klines(
        self, time_frame: str, ignore_opened_candle=True, **kwargs
    ) -> pd.DataFrame:
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

        if ignore_opened_candle:
            klines = remove_last_candle_if_unclosed(klines)

        if self.settings.show_only_desired_info:
            return klines[self.settings.klines_desired_informations]
        return klines


class BackTestingBroker:
    def __init__(self, operation):
        self.operation = operation
        self.setup = operation.operational_setup()
        self.fee_rate_decimal = self.setup.backtesting.fee_rate_decimal
        self.order = Order()
        self.portfolio = Portfolio()
        self.order_id = 1

    def get_price(self, **kwargs) -> float:
        """Instant (past or present) artificial average trading price"""

        return PriceFromStorage(
            market=self.setup.market,
            price_metrics=self.setup.backtesting_price_metrics,
        ).get_price_at(desired_datetime=kwargs.get("at_time"))

    def get_portfolio(self) -> Portfolio:
        """The portfolio composition, given a market"""

        return Portfolio(
            quote=self.operation.position.porfolio.quote,
            base=self.operation.position.portfolio.base,
        )

    def get_min_lot_size(self) -> float:
        """Minimal possible trading amount, by quote."""

        return 10.3 / self.get_price()

    def _order_buy(self):
        order_amount = self.order.suggested_quantity
        fee_quote = self.fee_rate_decimal * order_amount
        spent_base_amount = order_amount * self.order.price
        bought_quote_amount = self.order.suggested_quantity - fee_quote

        new_base = self.portfolio.base - spent_base_amount
        new_quote = self.portfolio.quote + bought_quote_amount

        self.order.fee = fee_quote * self.order.price
        self.order.proceeded_quantity = bought_quote_amount
        self.operation.position.portolio.update(base=new_base, quote=new_quote)

    def _order_sell(self):
        order_amount = self.order.suggested_quantity
        fee_quote = self.fee_rate_decimal * order_amount
        bought_base_amount = self.order.price * (order_amount - fee_quote)

        new_base = self.portfolio.base + bought_base_amount
        new_quote = self.portfolio.quote - order_amount

        self.order.fee = fee_quote * self.order.price
        self.order.proceeded_quantity = order_amount - fee_quote
        self.operation.position.portolio.update(base=new_base, quote=new_quote)

    def _order_market(self) -> dict:
        executor = "_order_{}".format(self.order.signal)
        getattr(self, executor)()

    def _order_limit(self) -> dict:
        raise NotImplementedError

    def _append_order_to_storage(self) -> dict:
        columns=list(self.order.dict().keys())
        data=[list(self.order.dict().values())]
        _order = pd.DataFrame(columns, data)
        self.operation.save_result(database="order", result=_order)

    def execute(self, order: Order) -> Order:
        self.order = order
        self.order.order_id = self.order_id
        if self.order.signal == sig.hold:
            self.order.warnings = "Bypassed due to the 'hold' signal"
        else:
            self.portfolio = self.get_portfolio()
            if self.order.suggested_quantity > self.get_min_lot_size():
                order_executor = "_order_{}".format(order.order_type)
                getattr(self, order_executor)()
                self.order.fulfilled = True
            else:
                self.order.warnings = "Insufficient balance."
        self._append_order_to_storage()
        self.order_id += 1
        return self.order


class Binance(Broker):
    """All needed functions, wrapping the communication with binance"""

    def __init__(self, market: Market):
        super().__init__(market)


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
            symbol=self.market.ticker_symbol, orderId=self.order.order_id
        )
        quote_amount = float(order["executedQty"])
        base_amount = float(order["cummulativeQuoteQty"])
        self.order.price = base_amount / quote_amount
        self.order.timestamp = int(float(order["time"]) / 1000)
        self.order.fulfilled = True
        self.order.proceeded_quantity = quote_amount
        self.order.fee = self.fee_rate_decimal * base_amount

    @DocInherit
    def execute(self, order: Order) -> Order:
        self.order = order
        if self.order.generated_signal == sig.hold:
            self.order.warnings = "Ignored hold signal"
            return self.order

        order_executor = "_order_{}".format(order.order_type)
        try:
            fulfilled_order = getattr(self, order_executor)()
            if fulfilled_order:
                self.order.order_id = fulfilled_order["orderId"]
                self._check_and_update_order()
            else:
                self.order.warnings = "Insufficient balance"
        except Exception as broker_erro:
            self.order.warnings = str(broker_erro)
        return self.order

    @DocInherit
    def execute_test(self, order: Order):
        pass


def get_broker(market: Market) -> Broker:
    """Given a market, returns an instantiated broker"""
    return getattr(thismodule, market.broker_name.capitalize())(market)

def get_broker(operation: Operation) -> Union[Broker, BackTestingBroker]:
    """Returns an instance of 'Broker' class  which can perform real
    orders to the brokers using its secure APIs (real trading), or
    update useful operational control attributes (back testing).

    Args:
    operation (Operation): Entity containing the attributes related to
    the implementation of a single operation (1 market, 1 classifier
    setup and 1 stoploss setup), as well as convenient methods for
    manipulating these attributes.
    """

    setup = operation.operational_setup()
    if setup.backtesting.is_on:
        return BackTestingBroker(operation)

    market = setup.market
    return getattr(thismodule, market.broker_name.capitalize())(market)

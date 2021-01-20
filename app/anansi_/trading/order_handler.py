# pylint: disable=E1136
# pylint: disable=no-name-in-module

import sys
from typing import Optional, Union

from pydantic import BaseModel

from ..brokers.brokers import get_broker
from ..marketdata.klines import PriceFromStorage
from ..notifiers.notifiers import get_notifier
from ..sql_app.schemas import OpSetup, Order, Portfolio  # Market
from ..tools.serializers import Deserialize

thismodule = sys.modules[__name__]


class Parameters(BaseModel):
    quote_symbol: Optional[str]
    base_symbol: Optional[str]
    initial_equivalent_quote: Optional[float]
    min_lot_size: Optional[float]


"""
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)

        self.classifier = get_classifier(
            classifier_name=self.setup.classifier_name,
            market=self.setup.market,
            time_frame=self.setup.time_frame,
            setup=self.setup.classifier_setup)

"""


class OrderHandler:
    def __init__(self, operation: OpSetup):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)
        self.broker = get_broker(self.setup.market)
        self.notifier = get_notifier(broadcasters=self.setup.broadcasters)
        self.parameters = self._fill_in_parameters()

    def _fill_in_parameters(self):
        parameters = Parameters()

        parameters.quote_symbol = self.setup.market.quote_symbol
        parameters.base_symbol = self.setup.market.base_symbol
        parameters.initial_equivalent_quote: float = None
        parameters.min_lot_size = self.broker.get_min_lot_size()

        return parameters

    def current_price(self):
        raise NotImplementedError

    def update_result(self, portfolio: Portfolio, price) -> None:
        backtesting = bool(self.setup.backtesting)
        debbug = bool(self.setup.debbug)
        result = self.operation.current_result
        equivalent_base = portfolio.quote * price + portfolio.base

        result[self.parameters.quote_symbol] = portfolio.quote
        result[self.parameters.base_symbol] = portfolio.base

        result[
            "Equivalent_{}".format(self.parameters.base_symbol)
        ] = equivalent_base
        result["Price"] = price
        if backtesting:
            result["Hold"] = self.parameters.initial_equivalent_quote * price

        if debbug:
            current_opentime = result.Open_time.tail(1).item()
            side = result.Side.tail(1).item()
            leverage = result.Leverage.tail(1).item()

            msg = """\n{}
===================\n
Equivalent {} = {} 
Price = {} 
Quote amount = {} {}
Base amount = {} {}\n
Side = {}
Leverage = {}
""".format(
                current_opentime,
                self.parameters.base_symbol,
                equivalent_base,
                price,
                portfolio.quote,
                self.parameters.quote_symbol,
                portfolio.base,
                self.parameters.base_symbol,
                side,
                leverage,
            )
            self.notifier.debbug(msg)
        self.operation.save_current_result()

    def get_portfolio(self) -> Portfolio:
        raise NotImplementedError

    def sanitize_order_amount(self, order_amount: float) -> float:
        precision = self.parameters.order_amount_precision
        amount_str = "{:0.0{}f}".format(order_amount, precision)

        return float(amount_str)

    def proceed(self):
        raise NotImplementedError


class BacktestingOrderHandler(OrderHandler):
    def __init__(self, operation: OpSetup):
        super().__init__(operation)

    def current_price(self) -> float:
        price_getter = PriceFromStorage(self.setup.market, "ohlc4")
        current_time = self.operation.current_result.Open_time.tail(1).item()
        return price_getter.get_price_at(desired_datetime=current_time)

    def _reset_result(self):
        portfolio = Portfolio()
        initial_base_amount = self.setup.initial_base_amount
        price = self.current_price()

        self.parameters.initial_equivalent_quote = initial_base_amount / price

        portfolio.quote = 0.0
        portfolio.base = initial_base_amount

        self.update_result(portfolio, price=price)

    def _get_asset(self, asset_kind: str) -> float:
        asset_key = getattr(self.parameters, "{}_symbol".format(asset_kind))
        return (self.operation.current_result[asset_key]).item()

    def get_portfolio(self) -> Portfolio:
        portfolio = Portfolio()

        portfolio_does_not_exist = not bool(
            (self.parameters.quote_symbol and self.parameters.base_symbol)
            in self.operation.current_result.columns
        )
        if portfolio_does_not_exist:
            self._reset_result()

        portfolio.quote = self._get_asset("quote")
        portfolio.base = self._get_asset("base")

        return portfolio

    def proceed(self):
        price = self.current_price()
        portfolio = self.get_portfolio()
        side = self.operation.current_result.Side.item()

        fee_rate_decimal = self.broker.settings.fee_rate_decimal
        leverage = self.operation.current_result.Leverage.item()

        if not self.setup.allow_naked_sells and side == "Short":
            side = "Zeroed"

        if side == "Long":
            order_amount = leverage * (portfolio.base / price)

            if order_amount > self.parameters.min_lot_size:
                fee_quote = fee_rate_decimal * order_amount
                bought_quote_amount = order_amount - fee_quote

                portfolio.quote += bought_quote_amount
                portfolio.base -= order_amount * price

        if side == "Zeroed":
            order_amount = portfolio.quote

            if order_amount > self.parameters.min_lot_size:
                fee_quote = fee_rate_decimal * order_amount
                bought_base_amount = price * (order_amount - fee_quote)

                portfolio.quote -= order_amount
                portfolio.base += bought_base_amount

        self.update_result(portfolio, price)


class RealTradingOrderHandler(OrderHandler):
    def __init__(self, operation: OpSetup):
        super().__init__(operation)

    def current_price(self):
        return self.broker.get_price()

    def get_portfolio(self) -> Portfolio:
        return self.broker.get_portfolio()

    def proceed(self):
        price = self.current_price()
        portfolio = self.get_portfolio()
        side = self.operation.current_result.Side.item()
        fee_rate_decimal = self.broker.settings.fee_rate_decimal
        leverage = self.operation.current_result.Leverage.item()

        order = Order(
            test_order=self.setup.test_order,
            ticker_symbol=(
                self.setup.market.quote_symbol + self.setup.market.base_symbol
            ).upper(),
            side=str(),
            order_type=self.setup.order_type,
            quantity=0.0,
            price=price,
        )
        if not self.setup.allow_naked_sells and side == "Short":
            side = "Zeroed"

        if side == "Long":
            order_amount = 0.998 * (leverage * (portfolio.base / price))

            if order_amount > self.parameters.min_lot_size:
                fee_quote = fee_rate_decimal * order_amount
                bought_quote_amount = order_amount - fee_quote

                order.side = "buy"
                order.quantity = order_amount
                self.notifier.trade(order.json())
                self.broker.execute_order(order)

                portfolio.quote += bought_quote_amount
                portfolio.base -= order_amount * price

        if side == "Zeroed":
            order_amount = 0.998 * (portfolio.quote)

            if order_amount > self.parameters.min_lot_size:
                fee_quote = fee_rate_decimal * order_amount
                bought_base_amount = price * (order_amount - fee_quote)

                order.side = "sell"
                order.quantity = order_amount
                self.notifier.trade(order.json())
                self.broker.execute_order(order)

                portfolio.quote -= order_amount
                portfolio.base += bought_base_amount

        self.update_result(portfolio, price)


def get_order_handler(
    operation: OpSetup,
) -> Union[BacktestingOrderHandler, RealTradingOrderHandler]:

    backtesting = (Deserialize(name="setup").from_json(operation.setup)).backtesting

    if backtesting:
        return BacktestingOrderHandler(operation)
    return RealTradingOrderHandler(operation)

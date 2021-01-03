import sys
from typing import Union, Optional
from .schemas import Market, OpSetup, Order, Portfolio
from .brokers import get_broker
from ..marketdata.klines import PriceFromStorage
from ..share.notifiers import Notifier

thismodule = sys.modules[__name__]


class OrderHandler:
    def __init__(self, operation: OpSetup):
        self.operation = operation
        self._quote_symbol = operation.setup.market.quote_symbol
        self._base_symbol = operation.setup.market.base_symbol
        self.broker = get_broker(operation.setup.market)
        self.notifier = Notifier(broadcasters=operation.setup.broadcasters)
        self.notifier.show_header = False

        self.initial_equivalent_quote: float = None

    def current_price(self):
        raise NotImplementedError

    def reset_result(self):
        raise NotImplementedError

    def update_result(self, portfolio: Portfolio, price) -> None:
        backtesting = bool(self.operation.setup.backtesting)
        debbug = bool(self.operation.setup.debbug)
        result = self.operation.current_result
        equivalent_base = portfolio.quote * price + portfolio.base

        result[self._quote_symbol] = portfolio.quote
        result[self._base_symbol] = portfolio.base

        result["Equivalent_{}".format(self._base_symbol)] = equivalent_base
        result["Price"] = price
        if backtesting:
            result["Hold"] = self.initial_equivalent_quote * price

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
                self._base_symbol,
                equivalent_base,
                price,
                portfolio.quote,
                self._quote_symbol,
                portfolio.base,
                self._base_symbol,
                side,
                leverage,
            )
            self.notifier.debbug(msg)
        self.operation.save_current_result()

    def get_asset(self, asset_kind: str) -> float:
        raise NotImplementedError

    def portfolio(self) -> Portfolio:
        raise NotImplementedError

    def minimal_quote_amount(self):
        return self.broker.minimal_base_amount/self.current_price()
    
    def BKP_sanitize_order_amount(self, order_amount: float) -> float:
        factor = int(order_amount / self.minimal_quote_amount())
        precision = self.broker.precision
        amount = factor * self.minimal_quote_amount()
        amount_str = "{:0.0{}f}".format(amount, precision)        

        return float(amount_str)

    def sanitize_order_amount(self, order_amount: float) -> float:
        factor = int(order_amount / self.broker.minimal_amount)

        return factor * self.broker.minimal_amount

    def proceed(self):
        raise NotImplementedError


class BacktestingOrderHandler(OrderHandler):
    def __init__(self, operation: OpSetup):
        super(BacktestingOrderHandler, self).__init__(operation)
        self.debbug = True

    def current_price(self) -> float:
        price_getter = PriceFromStorage(self.operation.setup.market, "ohlc4")
        current_time = self.operation.current_result.Open_time.tail(1).item()
        return price_getter.get_price_at(desired_datetime=current_time)

    def reset_result(self):
        portfolio = Portfolio()
        initial_base_amount = self.operation.setup.initial_base_amount
        price = self.current_price()

        self.initial_equivalent_quote = initial_base_amount / price
        
        portfolio.quote = 0.0; portfolio.base = initial_base_amount
        
        self.update_result(portfolio, price=price)

    def get_asset(self, asset_kind: str) -> float:
        asset_key = getattr(self, "_{}_symbol".format(asset_kind))
        return (self.operation.current_result[asset_key]).item()

    def portfolio(self) -> Portfolio:
        portfolio = Portfolio()

        portfolio_does_not_exist = not bool(
            (self._quote_symbol and self._base_symbol)
            in self.operation.current_result.columns
        )
        if portfolio_does_not_exist:
            self.reset_result()

        portfolio.quote = self.get_asset("quote")
        portfolio.base = self.get_asset("base")

        return portfolio

    def proceed(self):
        price = self.current_price()
        portfolio = self.portfolio()
        side = self.operation.current_result.Side.item()
        minimal_amount = 0.0005 #self.broker.minimal_amount #self.minimal_quote_amount()
        fee_rate_decimal = self.broker.fee_rate_decimal
        leverage = self.operation.current_result.Leverage.item()

        if side == "Long":
            raw_order_amount = leverage * (portfolio.base / price)
            order_amount = self.sanitize_order_amount(raw_order_amount)

            if order_amount > minimal_amount:
                fee_quote = fee_rate_decimal * order_amount
                bought_quote_amount = order_amount - fee_quote

                portfolio.quote += bought_quote_amount
                portfolio.base -= order_amount * price

        if side == "Zeroed":
            raw_order_amount = portfolio.quote
            order_amount = self.sanitize_order_amount(raw_order_amount)

            if order_amount > minimal_amount:
                fee_quote = fee_rate_decimal * order_amount
                bought_base_amount = price * (order_amount - fee_quote)

                portfolio.quote -= order_amount
                portfolio.base += bought_base_amount

        self.update_result(portfolio, price)


class RealTradingOrderHandler(OrderHandler):
    def __init__(self, operation: OpSetup):
        super(RealTradingOrderHandler, self).__init__(operation)
        self.debbug = True

    def current_price(self):
        return self.broker.price()

    def proceed(self):
        price = self.current_price()
        portfolio = self.broker.portfolio()
        side = self.operation.current_result.Side.item()
        minimal_amount = 0.0005 #self.broker.minimal_amount #self.minimal_quote_amount()
        fee_rate_decimal = self.broker.fee_rate_decimal
        leverage = self.operation.current_result.Leverage.item()
        order = Order(
            test_order=self.operation.setup.test_order,
            ticker_symbol=self.operation.setup.market.ticker_symbol,
            side=str(),
            order_type=self.operation.setup.order_type,
            quantity=0.0,
            price=price,
        )

        if side == "Long":
            raw_order_amount = leverage * (portfolio.base / price)
            order_amount = self.sanitize_order_amount(raw_order_amount)

            if order_amount > minimal_amount:
                fee_quote = fee_rate_decimal * order_amount
                bought_quote_amount = order_amount - fee_quote

                order.side = "BUY"
                order.quantity = order_amount
                self.broker.execute(order)
                self.notifier.trade(order.json())

                portfolio.quote += bought_quote_amount
                portfolio.base -= order_amount * price

        if side == "Zeroed":
            raw_order_amount = portfolio.quote
            order_amount = self.sanitize_order_amount(raw_order_amount)

            if order_amount > minimal_amount:
                fee_quote = fee_rate_decimal * order_amount
                bought_base_amount = price * (order_amount - fee_quote)

                order.side = "SELL"
                order.quantity = order_amount
                self.broker.execute(order)
                self.notifier.trade(order.json())

                portfolio.quote -= order_amount
                portfolio.base += bought_base_amount

        self.update_result(portfolio, price)


def order_handler(
    operation: OpSetup,
) -> Union[BacktestingOrderHandler, RealTradingOrderHandler]:
    if operation.setup.backtesting:
        return BacktestingOrderHandler(operation)
    return RealTradingOrderHandler(operation)

# pylint: disable=E1136
# pylint: disable=no-name-in-module

"""All the brokers low level communications goes here."""
import sys
from decimal import Decimal
from typing import Optional, Union

from binance.client import Client as BinanceClient
from environs import Env
from pydantic import BaseModel

from ..marketdata.klines import PriceFromStorage
from ..notifiers.notifiers import get_notifier
from ..sql_app.schemas import Market, Order, Portfolio
from ..tools import doc
from ..tools.serializers import Deserialize
from .models import Operation

env = Env()

thismodule = sys.modules[__name__]

DocInherit = doc.DocInherit
notifier = get_notifier(broadcasters=["TelegramNotifier"])


class Quant(BaseModel):
    """Auxiliary class to store the amount quantity information, useful
    for the trade order flow"""

    is_enough: Optional[bool]
    value: Optional[str]


#! TODO: Are settings really needed here?
class Broker:
    """Parent class that should be a model to group broker functions"""

    def __init__(self, market: Market):  # , settings: BaseModel):
        self.market = market
        self.fee_rate_decimal: float = 0.001
        self.order = Order()
        # self.settings = settings

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


class BackTestingBroker:
    def __init__(self, operation):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)
        self.fee_rate_decimal = self.setup.backtesting.fee_rate_decimal

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

    def execute(self, order: Order):
        """Proceed trade orders """
        raise NotImplementedError


BINANCE_API_KEY = str()
BINANCE_API_SECRET = str()

#! TODO: change API key
BINANCE_API_KEY = (
    "rjp1jPSMK1XSvFAv8HzhnpOoWFmyH9XmPQ6Rj3r1RB29VuPWGWy5uRhL4XysHoVw"
)
BINANCE_API_SECRET = (
    "f5biQUiVqNhK33zPLkmJmn3bzVX7azrENNvWHPNuNyy2cX7XgwLCSq2ZTTc498Qj"
)


class Binance(Broker):
    """All needed functions, wrapping the communication with binance"""

    def __init__(self, market: Market):  # , settings=BinanceSettings()):
        super().__init__(market)  # , settings)
        self.client = BinanceClient(
            api_key=env.str("BINANCE_API_KEY", default=BINANCE_API_KEY),
            api_secret=env.str(
                "BINANCE_API_SECRET", default=BINANCE_API_SECRET
            ),
        )

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
    def get_min_lot_size(self) -> float:
        min_notional = float(
            self.client.get_symbol_info(symbol=self.market.ticker_symbol)[
                "filters"
            ][3]["minNotional"]
        )  # Measured by base asset
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
        self.order.at_time = int(float(order["time"]) / 1000)
        self.order.status = "fulfilled"
        self.order.portfolio_after = self.get_portfolio()
        self.order.proceeded_quantity = quote_amount
        self.order.fee = self.fee_rate_decimal * base_amount

    @DocInherit
    def execute(self, order: Order) -> Order:
        self.order = order
        order_executor = "_order_{}".format(order.order_type)
        fulfilled_order = getattr(self, order_executor)()
        if fulfilled_order:
            order.order_id = fulfilled_order["orderId"]
            self._check_and_update_order()
        else:
            self.order.status = "unfulfilled"
        return self.order

    @DocInherit
    def execute_test(self, order: Order):
        pass


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

    _setup = Deserialize(name="setup").from_json(operation.setup)
    backtesting = _setup.backtesting
    if backtesting:
        return BackTestingBroker(operation)

    market = _setup.market
    return getattr(thismodule, market.broker_name.capitalize())(market)

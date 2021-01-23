# pylint: disable=E1136
# pylint: disable=no-name-in-module

"""All the brokers low level communications goes here."""
import sys
import time
from decimal import Decimal
from typing import Optional, Union

from binance.client import Client as BinanceClient
from environs import Env
from pydantic import BaseModel

from ..notifiers.notifiers import get_notifier
from ..sql_app.schemas import Market, Order, Portfolio
from ..tools import doc

env = Env()

thismodule = sys.modules[__name__]

DocInherit = doc.DocInherit
notifier = get_notifier(broadcasters=["TelegramNotifier"])


class Quant:
    """Auxiliary class to store the amount quantity information, useful
    for the trade order flow"""

    is_enough: Optional[bool]
    value: Optional[str]


class Broker:
    """Parent class that should be a model to group broker functions """

    def __init__(self, market: Market):  # , settings: BaseModel):
        self.market = market
        self.fee_rate_decimal: float = 0.001
        # self.settings = settings

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

    def check_order(self, order_id):
        """Verify order status and return the relevant informations"""
        raise NotImplementedError


BINANCE_API_KEY = None
BINANCE_API_SECRET = None

BINANCE_API_KEY = (
    "rjp1jPSMK1XSvFAv8HzhnpOoWFmyH9XmPQ6Rj3r1RB29VuPWGWy5uRhL4XysHoVw"
)
BINANCE_API_SECRET = (
    "f5biQUiVqNhK33zPLkmJmn3bzVX7azrENNvWHPNuNyy2cX7XgwLCSq2ZTTc498Qj"
)


class Binance(Broker):
    """All needed functions, wrapping the communication with binance"""

    @DocInherit
    def __init__(self, market: Market):  # , settings=BinanceSettings()):
        super().__init__(market)  # , settings)
        self.client = BinanceClient(
            api_key=env.str("BINANCE_API_KEY", default=BINANCE_API_KEY),
            api_secret=env.str(
                "BINANCE_API_SECRET", default=BINANCE_API_SECRET
            ),
        )

    @DocInherit
    def get_price(self) -> float:
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

    def _order_market(self, order: Order) -> dict:
        order_report = dict()

        executor = "order_market_{}".format(order.side)
        quant = self._sanitize_quantity(order.quantity)

        if quant.is_enough:
            order_report = getattr(self.client, executor)(
                symbol=self.market.ticker_symbol, quantity=quant.value
            )
        return order_report

    def _order_limit(self, order: Order) -> dict:
        order_report = dict()

        executor = "order_limit_{}".format(order.side)
        quant = self._sanitize_quantity(order.quantity)
        price = self._sanitize_price(order.price)

        if quant.is_enough:
            order_report = getattr(self.client, executor)(
                symbol=self.market.ticker_symbol,
                quantity=quant.value,
                price=price,
            )
        return order_report

    @DocInherit
    def check_order(self, order_id) -> dict:
        order = self.client.get_order(
            symbol=self.market.ticker_symbol, orderId=order_id
        )
        quote_amount=float(order["executedQty"]),
        base_amount=float(order["cummulativeQuoteQty"]),
        price=base_amount / quote_amount,

        order_dict = dict(
            timestamp=int(float(order["time"]) / 1000),
            signal=order["side"],
            price=price,
            fee=self.fee_rate_decimal * base_amount,
            quote_amount=quote_amount,
        )
        return order_dict

    @DocInherit
    def execute_order(self, order: Order) -> dict:
        checked_order = dict()
        executor = "_order_{}".format(order.order_type)
        _order = getattr(self, executor)(order)

        if _order:
            while True:
                try:
                    checked_order = self.check_order(
                        order_id=_order["orderId"]
                    )
                    break
                except Exception as error:
                    notifier.error(error)
                    time.sleep(10)
        return checked_order

    @DocInherit
    def test_order(self, order: Order):
        pass


def get_broker(market: Market) -> Broker:
    """Given a market, returns an instantiated broker"""
    return getattr(thismodule, market.broker_name.capitalize())(market)

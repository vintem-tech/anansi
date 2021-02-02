# pylint: disable=E1136
# pylint: disable=no-name-in-module

import pandas as pd
import sys
from typing import Optional, Union

from pydantic import BaseModel

from .brokers import get_broker
from ..marketdata.klines import PriceFromStorage
from ..notifiers.notifiers import get_notifier
from ..sql_app.schemas import (
    # Order,
    Portfolio,
    PossibleSignals as sig,
)  # Market
from ..tools.serializers import Deserialize
from ..tools.time_handlers import ParseDateTime

from .models import Operation

thismodule = sys.modules[__name__]


class Order(BaseModel):
    """Order parameters collection"""

    test_order: bool = False
    notify: bool = True
    signal: Optional[str]
    order_type: Optional[str] = "market"
    quantity: Optional[float]
    leverage: Optional[float]
    price: Optional[float] = None
    at_time: Optional[int]
    portfolio: Optional[Portfolio]
    fee: Optional[float]


class Signal:
    def __init__(self, from_side: str, to_side: str, by_stop: bool):
        self.from_side = from_side.capitalize()
        self.to_side = to_side.capitalize()
        self.by_stop = by_stop

    def generate(self):
        if self.from_side == self.to_side:
            return sig.hold

        if self.from_side == "Zeroed":
            if self.to_side == "Long":
                return sig.buy
            if self.to_side == "Short":
                return sig.naked_sell

        if self.from_side == "Long":
            if self.to_side == "Zeroed":
                if self.by_stop:
                    return sig.long_stopped
                return sig.sell
            if self.to_side == "Short":
                return sig.double_naked_sell

        if self.from_side == "Short":
            if self.to_side == "Zeroed":
                if self.by_stop:
                    return sig.short_stopped
                return sig.buy
            if self.to_side == "Long":
                return sig.double_buy


class BackTestingBroker:
    def __init__(self, operation):
        self.operation = operation

    def get_price(self) -> float:
        """Instant average trading price"""
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


class OrderHandler:
    def __init__(self, operation: Operation):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)
        self.broker = (
            BackTestingBroker(operation)
            if self.setup.backtesting
            else get_broker(self.setup.market)
        )
        self.order = Order()

    def _buy(self):
        self.order.signal = sig.buy
        self.order.quantity = 0.998 * (
            self.order.leverage
            * (self.order.portfolio.base / self.order.price)
        )
        return self.broker.execute_order(self.order)

    def _sell(self):
        self.order.signal = sig.sell
        self.order.quantity = 0.998 * self.order.portfolio.quote
        return self.broker.execute_order(self.order)

    def _naked_sell(self):
        pass

    def _double_naked_sell(self):
        pass

    def _double_buy(self):
        pass

    def _long_stopped(self):
        pass

    def _short_stopped(self):
        pass

    def proceed(
        self,
        at_time: int,
        analysis_result: pd.core.frame.DataFrame,
        by_stop: bool = False,
    ):
        generated_signal = Signal(
            from_side=self.operation.position.side,
            to_side=analysis_result.Side.item(),
            by_stop=by_stop,
        ).generate()
        self.order.at_time = at_time
        self.order.leverage = analysis_result.Leverage.item()
        self.order.price = self.broker.get_price()
        self.order.portfolio = self.broker.get_portfolio()

        _order = getattr(self, "_{}".format(generated_signal))
        return _order  # Na verdade, fará atualizações nos registros...


def get_order_handler(operation: Operation) -> OrderHandler:
    return OrderHandler(operation)

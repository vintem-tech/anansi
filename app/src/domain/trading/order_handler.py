# pylint: disable=E1136
# pylint: disable=no-name-in-module

import sys
from typing import Optional, Union

import pandas as pd
from pydantic import BaseModel

from ..notifiers.notifiers import get_notifier
from ..sql_app.schemas import DateTimeType, Order, Portfolio
from ..sql_app.schemas import Signals as sig  # Order,; Market
from ..tools.serializers import Deserialize
from ..tools.time_handlers import ParseDateTime
from .brokers import get_broker
from .models import Operation

thismodule = sys.modules[__name__]


# Cuidar do objeto Order, bem como da atualização em banco de dados (TradeLog) em caso de movimento

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


class OrderHandler:
    def __init__(self, operation: Operation):
        self.operation = operation
        self.setup = Deserialize(name="setup").from_json(operation.setup)
        self.broker = get_broker(operation)
        self.order = self.setup.default_order # Cuidar deste instanciamento da ordem, a fim de que seja um objeto Pydantic

    def _hold(self):
        self.order.signal = sig.hold
        order = self.order
        self.order = self.broker.execute(order)

    def _buy(self):
        self.order.signal = sig.buy
        self.order.quantity = 0.998 * (
            self.order.leverage
            * (self.order.portfolio.base / self.order.price)
        )
        order = self.order
        self.order = self.broker.execute(order)

    def _sell(self):
        self.order.signal = sig.sell
        self.order.quantity = 0.998 * self.order.portfolio.quote
        order = self.order
        self.order = self.broker.execute(order)

    def _naked_sell(self):
        pass

    def _double_naked_sell(self):
        pass

    def _double_buy(self):
        pass

    def _long_stopped(self):
        self.order.order_type = "market"
        self._sell()

    def _short_stopped(self):
        pass

    def _process(self, signal: str) -> None:
        getattr(self, "_{}".format(signal))

    def _update_and_notifier(self):
        pass

    def proceed(
        self,
        at_time: int,
        analysis_result: pd.core.frame.DataFrame,
        by_stop: bool = False,
    ):
        self.order.order_type = self.setup.default_order_type
        self.order.from_side = self.operation.position.side
        self.order.to_side = analysis_result.Side.item()
        self.order = self.setup.default_order
        self.order.status = "unfulfilled"
        self.order.generated_signal = Signal(
            from_side=self.order.from_side,
            to_side=self.order.to_side,
            by_stop=by_stop,
        ).generate()
        self.order.at_time = at_time
        self.order.leverage = analysis_result.Leverage.item()
        self.order.price = self.broker.get_price(at_time=at_time)
        self.order.portfolio_before = self.broker.get_portfolio()

        self._process(self.order.generated_signal)
        self._update_and_notifier()

def get_order_handler(operation: Operation) -> OrderHandler:
    return OrderHandler(operation)

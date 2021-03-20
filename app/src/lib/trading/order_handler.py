# pylint: disable=E1136
# pylint: disable=no-name-in-module

import sys

import pandas as pd

from ...log import Notifier
from ..brokers.backtesting import BackTestingBroker
from ..brokers.engines import get_broker

# from ..tools.serializers import Deserialize
from ..tools.time_handlers import ParseDateTime
from ..utils.databases.sql.models import Monitor, Operation
from ..utils.databases.sql.schemas import DateTimeType, Order, Signals


from ..utils.databases.sql.schemas import OperationalModes

# from typing import Optional, Union

# from pydantic import BaseModel

thismodule = sys.modules[__name__]
sig = Signals()
modes = OperationalModes()


class Signal:
    def __init__(self, from_side: str, to_side: str, by_stop=False):
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


class OrderExecutor:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.setup = analyzer.monitor.operation.setup()
        mode = analyzer.monitor.operation.mode
        self.broker = (
            BackTestingBroker(analyzer.monitor)
            if mode == modes.backtesting
            else get_broker(market=analyzer.monitor.market())
        )

    def proceed(self):
        return True


class OrderHandler:
    def __init__(self, operation):
        self.operation = operation
        self.setup = operation.setup()
        self.buy_queue = list()

    def _buy_queue_execution(self):
        pass

    def process(self, analyzers: list):
        if analyzers:
            self.buy_queue = list()
            for analyzer in analyzers:
                signal = Signal(
                    from_side=analyzer.order.from_side,
                    to_side=analyzer.order.to_side,
                ).generate()
                analyzer.order.signal = signal
                executor = OrderExecutor(analyzer)

                if signal in [sig.sell, sig.hold]:
                    executor.proceed()

                elif signal == sig.buy:
                    self.buy_queue.append(executor)

            self._buy_queue_execution()

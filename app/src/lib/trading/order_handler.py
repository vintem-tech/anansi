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
    def __init__(self, bases: list):
        self.buy_queue = {base: list() for base in bases}
        self.imediate_signals = [sig.sell, sig.hold]

    @staticmethod
    def _populate_quantities(buy_list: list):
        weight_sum = 0
        avaliable_base_amount = (buy_list[0]).broker.get_portfolio.base

        for executor in buy_list:
            weight_sum += executor.analyzer.order.score

        for executor in buy_list:
            weight = executor.analyzer.order.score / weight_sum
            executor.analyzer.order.quantity = weight * avaliable_base_amount

        return buy_list

    @staticmethod
    def _proceed(buy_list: list):
        for executor in buy_list:
            executor.proceed()

    def _buy_pipeline(self, buy_queue):
        for executor in buy_queue:
            base = executor.analyzer.monitor.market.base
            buy_list = self.buy_queue[base]
            buy_list.append(executor)

            if executor.analyzer.monitor.is_master:
                executor.proceed()
                buy_list.pop(buy_list.index(executor))

        for buy_list in self.buy_queue.values():
            if buy_list:
                self._proceed(self._populate_quantities(buy_list))

    def process(self, analyzers: list):
        buy_queue = list()
        if analyzers:
            for analyzer in analyzers:
                signal = Signal(
                    from_side=analyzer.order.from_side,
                    to_side=analyzer.order.to_side,
                ).generate()
                analyzer.order.signal = signal
                executor = OrderExecutor(analyzer)

                if signal in self.imediate_signals:
                    executor.proceed()

                elif signal == sig.buy:
                    buy_queue.append(executor)
        if buy_queue:
            self._buy_pipeline(buy_queue)

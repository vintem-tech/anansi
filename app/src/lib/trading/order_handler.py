# pylint: disable=E1136
# pylint: disable=no-name-in-module

# from ..brokers.backtesting import BackTestingBroker
# from ..tools.serializers import Deserialize
# from ..tools.time_handlers import ParseDateTime
# from typing import Optional, Union
# from pydantic import BaseModel
# from ...log import Notifier

import sys

import pandas as pd

from ..brokers.engines import get_broker
from ..marketdata.klines import PriceFromStorage
from ..utils.databases.sql.models import Monitor, Operation
from ..utils.databases.sql.schemas import (
    OperationalModes,
    Order,
    Portfolio,
    Signals,
)

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


class BackTestingBroker:
    """Handle with orders, in case of backtesting"""

    def __init__(self, operation):
        self.operation = operation
        self.setup = operation.operational_setup()
        self.fee_rate_decimal = self.setup.backtesting.fee_rate_decimal
        self.order = Order()
        self.portfolio = Portfolio()
        self.order_id = 1

    def get_price(self, **kwargs) -> float:
        """Instant (past or present) artificial average trading price"""

        price_getter = PriceFromStorage(
            market=self.setup.market,
            price_metrics=self.setup.backtesting_price_metrics,
        )

        return price_getter.get_price_at(
            desired_datetime=kwargs.get("at_time")
        )

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
        columns = list(self.order.dict().keys())
        data = [list(self.order.dict().values())]
        _order = pd.DataFrame(columns, data)
        self.operation.save_result(database="order", result=_order)

    def execute(self, order: Order) -> Order:
        """Proceeds order validation and some trading calculation,
        saving the order like a time series.

        Args:
            order (Order): [description]

        Returns:
            Order: [description]
        """
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

    def _validate_order(self, signal: str):
        order = self.analyzer.order
        if not order.price:
            order.price = self.broker.get_price(at_time=order.timestamp)

        if not order.quantity:
            portfolio = self.broker.get_portfolio()
            if signal in [sig.buy]:
                order.quantity = portfolio.base
            if signal in [sig.sell]:
                order.quantity = portfolio.quote

        return order

    def _hold(self):
        order = self.analyzer.order
        order.interpreted_signal = sig.hold
        self.analyzer.order = self.broker.execute(order)

    def _buy(self):
        signal = sig.buy
        order = self._validate_order(signal)
        order.interpreted_signal = signal

        order.quantity = 0.998 * (order.quantity / order.price)

        self.analyzer.order = self.broker.execute(order)
        self.analyzer.notify_trade()

    def _sell(self):
        signal = sig.sell
        order = self._validate_order(signal)
        order.interpreted_signal = signal

        order.quantity = 0.998 * order.quantity

        self.analyzer.order = self.broker.execute(order)
        self.analyzer.notify_trade()

    def _naked_sell(self):
        pass

    def _double_naked_sell(self):
        pass

    def _double_buy(self):
        pass

    def _long_stopped(self):
        self.analyzer.order.order_type = "market"
        self._sell()

    def _short_stopped(self):
        pass

    def _update_and_notifier(self):
        pass

    def proceed(self):
        signal = self.analyzer.order.generated_signal
        signal_handler = getattr(self, "_{}".format(signal))

        signal_handler()


class OrderHandler:
    def __init__(self, bases_symbols: list):
        self.bases_symbols = bases_symbols
        self.buy_queues = {
            base_symbol: list() for base_symbol in self.bases_symbols
        }
        self.high_priority_signals = [
            sig.sell,
            sig.hold,
            sig.short_stopped,
            sig.long_stopped,
            sig.naked_sell,
            sig.double_buy,
        ]

    @staticmethod
    def _populate_orders_quantities(buy_queue: list):
        _executor = buy_queue[0]
        portfolio = _executor.broker.get_portfolio()
        avaliable_base_amount = portfolio.base

        score_sum = sum(
            [abs(executor.analyzer.order.score) for executor in buy_queue]
        )

        for executor in buy_queue:
            weight = abs(executor.analyzer.order.score) / score_sum
            executor.analyzer.order.quantity = weight * avaliable_base_amount

        return buy_queue

    @staticmethod
    def _proceed(buy_queue: list):
        for executor in buy_queue:
            executor.proceed()
            buy_queue.pop(buy_queue.index(executor))

    def _handle_with(self, buy_queue):
        # Split executors in buy_queues by base_symbol
        for executor in buy_queue:
            base_symbol = executor.analyzer.monitor.market.base_symbol
            buy_queue = self.buy_queues[base_symbol]
            buy_queue.append(executor)

            if executor.analyzer.monitor.is_master:
                executor.proceed()
                buy_queue.pop(buy_queue.index(executor))

        queues = self.buy_queues.values()
        for queue in queues:

            not_an_empty_queue = bool(queue)
            if not_an_empty_queue:
                _queue = self._populate_orders_quantities(queue)
                self._proceed(buy_queue=_queue)

    def process(self, analyzers: list):
        buy_queue = list()
        if analyzers:
            for analyzer in analyzers:
                signal = Signal(
                    from_side=analyzer.order.from_side,
                    to_side=analyzer.order.to_side,
                ).generate()
                analyzer.order.generated_signal = signal
                executor = OrderExecutor(analyzer)

                if signal in self.high_priority_signals:
                    executor.proceed()

                elif signal == sig.buy:
                    buy_queue.append(executor)
                # TODO: treat 'double_buy' scenario
        if buy_queue:
            self._handle_with(buy_queue)

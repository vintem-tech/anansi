# pylint: disable=no-name-in-module

import json
import sys

from pydantic import BaseModel

from ..brokers import get_broker
from ..marketdata.klines import PriceFromStorage
from ..utils.databases.sql.models import Monitor
from ..utils.schemas import (
    MarketPartition,
    OperationalModes,
    Order,
    Sides,
    Signals,
)

thismodule = sys.modules[__name__]
sig = Signals()
modes = OperationalModes()
sides = Sides()


class SignalGenerator(BaseModel):
    order: Order

    @staticmethod
    def _from_zeroed_to_zeroed():
        return sig.sell

    @staticmethod
    def _from_zeroed_to_long():
        return sig.buy

    @staticmethod
    def _from_long_to_zeroed():
        return sig.sell

    @staticmethod
    def _from_zeroed_to_short():
        return sig.naked_sell

    @staticmethod
    def _from_short_to_long():
        return sig.double_buy

    @staticmethod
    def _from_long_to_short():
        return sig.double_naked_sell

    def _has_score_increased(self):
        return bool(abs(self.order.to.score) > abs(self.order.from_.score))

    def _from_long_to_long(self):
        if self._has_score_increased():
            return sig.buy
        return sig.hold

    def _from_short_to_short(self):
        if self._has_score_increased():
            return sig.sell
        return sig.hold

    def generate(self):
        from_side = self.order.from_.side
        to_side = self.order.to.side

        signal = getattr(self, "_from_{}_to_{}".format(from_side, to_side))
        return signal()


class BackTestingBroker:
    """Handle with orders, in case of backtesting"""

    def __init__(self, monitor: Monitor):
        self.monitor = monitor
        self.ticker = monitor.ticker()
        self.setup = monitor.operation.setup()
        self.order = Order()

    def get_price(self, **kwargs) -> float:
        """Instant (past or present) artificial average trading price"""

        price_getter = PriceFromStorage(
            ticker=self.ticker,
            price_metrics=self.setup.backtesting.price_metrics,
        )

        return price_getter.get_price_at(
            desired_datetime=kwargs.get("at_time")
        )

    def get_portfolio(self) -> MarketPartition:
        """The portfolio composition, given a ticker"""

        wallet = json.loads(self.monitor.operation.wallet)
        # print("wallet", wallet)
        return MarketPartition(
            quote=wallet.get(self.ticker.quote_symbol, 0.0),
            base=wallet.get(self.ticker.base_symbol, 0.0),
        )

    def get_min_lot_size(self) -> float:  # TODO: rever isto
        """Minimal possible trading amount, by quote."""

        return 10.3 / self.get_price(at_time=self.order.timestamp)

    def _update_wallet(self, delta_quote, delta_base):
        wallet_ = json.loads(self.monitor.operation.wallet)

        quote_symbol = self.ticker.quote_symbol
        base_symbol = self.ticker.base_symbol

        quote = wallet_.get(quote_symbol, 0.0)
        base = wallet_.get(base_symbol, 0.0)

        wallet_.update(
            **{
                quote_symbol: quote + delta_quote,
                base_symbol: base + delta_base,
            }
        )
        self.monitor.operation.update(wallet=json.dumps(wallet_))

    def _process_fee(self) -> float:
        fee = self.setup.backtesting.fee_rate_decimal * self.order.quantity
        self.order.fee = fee * self.order.price  # base equivalent
        return fee  # quote equivalent

    def _market_buy_order(self):
        fee = self._process_fee()
        spent_base_amount = self.order.quantity * self.order.price
        bought_quote_amount = self.order.quantity - fee
        self._update_wallet(
            delta_quote=bought_quote_amount, delta_base=-spent_base_amount
        )
        return True

    def _market_sell_order(self):
        fee = self._process_fee()
        bought_base_amount = self.order.price * (self.order.quantity - fee)
        self._update_wallet(
            delta_quote=-self.order.quantity, delta_base=bought_base_amount
        )
        return True

    def _limit_buy_order(self):
        raise NotImplementedError

    def _limit_sell_order(self):
        raise NotImplementedError

    def execute(self, order: Order) -> Order:
        """Proceeds order validation and some trading calculation,
        saving the order like a time series.

        Args:
            order (Order): Order parameters collection

        Returns:
            Order: Order parameters collection
        """

        self.order = order
        # signal = order.interpreted_signal

        if order.signal == sig.hold:
            self.order.warnings = "Bypassed due to the 'hold' signal"
            return self.order

        if order.quantity > self.get_min_lot_size():
            processor = "_{}_{}_order".format(order.order_type, order.signal)
            self.order.fulfilled = getattr(self, processor)()
            return self.order

        # Se o sinal for de venda e o montante insuficiente, então a posição deve ser desarmada.

        self.order.warnings = "Insufficient balance."
        return self.order


class OrderExecutor:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.setup = analyzer.monitor.operation.setup()
        self.backtesting = bool(
            analyzer.monitor.operation.mode == modes.backtesting
        )
        self.broker = (
            BackTestingBroker(analyzer.monitor)
            if self.backtesting
            else get_broker(ticker=analyzer.monitor.ticker())
        )

    def _validate_order(self):
        order = self.analyzer.order
        if not order.price:
            order.price = self.broker.get_price(at_time=order.timestamp)

        if not order.quantity:
            portfolio = self.broker.get_portfolio()
            # signal = order.interpreted_signal
            order.quantity = order.leverage * portfolio.base

            if order.signal == sig.sell:
                order.quantity = portfolio.quote

        return order

    def _hold(self):
        order = self.analyzer.order
        # order.interpreted_signal = sig.hold
        self.analyzer.order = self.broker.execute(order)

    def _buy(self):
        # self.analyzer.order.interpreted_signal = sig.buy
        order = self._validate_order()

        order.quantity = (
            0.998 * order.to.score * (order.quantity / order.price)
        )
        self.analyzer.order = self.broker.execute(order)

    def _sell(self):
        # self.analyzer.order.interpreted_signal = sig.sell
        order = self._validate_order()

        order.quantity = 0.998 * order.quantity
        self.analyzer.order = self.broker.execute(order)

    def _naked_sell(self):
        if self.setup.trading.allow_naked_sells:
            raise NotImplementedError

    def _double_naked_sell(self):
        self._sell()
        self._naked_sell()

    def _double_buy(self):
        raise NotImplementedError

    def _long_stopped(self):
        self.analyzer.order.order_type = "market"
        self._sell()
        self.analyzer.order.order_type = self.setup.default_order_type

    def _short_stopped(self):
        pass

    def proceed(self):
        signal_run = getattr(self, "_{}".format(self.analyzer.order.signal))
        signal_run()


class OrderHandler:
    def __init__(self, bases_symbols: list):
        self.bases_symbols = bases_symbols

    @staticmethod
    def _fill_the_order_quantities_in_the(buy_queue: list):
        _executor = buy_queue[0]
        # print(_executor.analyzer.monitor.ticker().dict())

        portfolio = _executor.broker.get_portfolio()
        # print(portfolio.dict())
        avaliable_base_amount = portfolio.base
        # print("avaliable_base_amount", avaliable_base_amount)

        score_sum = sum(
            [executor.analyzer.order.to.score for executor in buy_queue]
        )
        # print("score_sum", score_sum)

        for executor in buy_queue:
            weight = executor.analyzer.order.to.score / score_sum
            # print("weight", weight)

            leverage = executor.analyzer.order.leverage
            # print("leverage", leverage)

            quantity = leverage * weight * avaliable_base_amount
            executor.analyzer.order.quantity = quantity

        return buy_queue

    @staticmethod
    def _proceed_each_buy_in_the(buy_queue: list):
        for executor in buy_queue:
            executor.proceed()
            buy_queue.pop(buy_queue.index(executor))

    def _buy_queue_handler(self, buy_queue):
        # Splits executors into separate queues, indexed by base symbol
        base_indexed_queues = {
            base_symbol: list() for base_symbol in self.bases_symbols
        }

        for executor in buy_queue:
            ticker = executor.analyzer.monitor.ticker()
            buy_queue = base_indexed_queues.get(ticker.base_symbol)
            buy_queue.append(executor)

            if executor.analyzer.monitor.is_master:
                executor.proceed()

                ## Comment below in order proceed master monitor buy twice.
                # buy_queue.pop(buy_queue.index(executor))

        queues = base_indexed_queues.values()
        for non_empty_queue in (queue for queue in queues if queue):
            queue_ = self._fill_the_order_quantities_in_the(non_empty_queue)
            self._proceed_each_buy_in_the(buy_queue=queue_)

    def process(self, analyzers: list):
        buy_queue = list()

        for analyzer in analyzers:
            signal = SignalGenerator(order=analyzer.order).generate()

            analyzer.order.signal = signal
            executor = OrderExecutor(analyzer)

            if signal not in [sig.buy, sig.double_buy]:
                executor.proceed()

            elif signal == sig.buy:
                buy_queue.append(executor)
        if buy_queue:
            self._buy_queue_handler(buy_queue)

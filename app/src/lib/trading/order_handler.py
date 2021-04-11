import json
import sys

from ..brokers.engines import get_broker
from ..marketdata.klines import PriceFromStorage
from ..utils.databases.sql.models import Monitor
from ..utils.databases.sql.schemas import (
    OperationalModes,
    Order,
    Portfolio,
    Sides,
    Signals,
)

thismodule = sys.modules[__name__]
sig = Signals()
modes = OperationalModes()
sides = Sides()


class Signal:
    def __init__(self, from_side: str, to_side: str, by_stop=False):
        self.from_side = from_side.lower()
        self.to_side = to_side.lower()
        self.by_stop = by_stop

    def generate(self):
        if self.from_side == self.to_side:
            return sig.hold

        if self.from_side == sides.zeroed:
            if self.to_side == sides.long:
                return sig.buy
            if self.to_side == sides.short:
                return sig.naked_sell

        if self.from_side == sides.long:
            if self.to_side == sides.zeroed:
                if self.by_stop:
                    return sig.long_stopped
                return sig.sell
            if self.to_side == sides.short:
                return sig.double_naked_sell

        if self.from_side == sides.short:
            if self.to_side == sides.zeroed:
                if self.by_stop:
                    return sig.short_stopped
                return sig.buy
            if self.to_side == sides.long:
                return sig.double_buy


class BackTestingBroker:
    """Handle with orders, in case of backtesting"""

    def __init__(self, monitor: Monitor):
        self.monitor = monitor
        self.market = monitor.market()
        self.setup = monitor.operation.setup()
        self.order = Order()

    def get_price(self, **kwargs) -> float:
        """Instant (past or present) artificial average trading price"""

        price_getter = PriceFromStorage(
            market=self.market,
            price_metrics=self.setup.backtesting.price_metrics,
        )

        return price_getter.get_price_at(
            desired_datetime=kwargs.get("at_time")
        )

    def get_portfolio(self) -> Portfolio:
        """The portfolio composition, given a market"""

        wallet = json.loads(self.monitor.operation.wallet)
        return Portfolio(
            quote=wallet.get(self.market.quote_symbol),
            base=wallet.get(self.market.base_symbol),
        )

    def get_min_lot_size(self) -> float:
        """Minimal possible trading amount, by quote."""

        return 10.3 / self.get_price()

    def _update_wallet(self, delta_quote, delta_base):
        _wallet = json.loads(self.monitor.operation.wallet)

        quote_symbol = self.market.quote_symbol
        base_symbol = self.market.base_symbol

        quote = _wallet.get(quote_symbol)
        base = _wallet.get(base_symbol)

        _wallet.update(
            **{
                quote_symbol: quote + delta_quote,
                base_symbol: base + delta_base,
            }
        )
        self.monitor.operation.update(wallet=json.dumps(_wallet))

    def _process_fee(self) -> float:
        fee = self.setup.backtesting.fee_rate_decimal * self.order.quantity
        self.order.fee = fee * self.order.price # base equivalent
        return fee # quote equivalent

    def _market_buy_order(self):
        fee = self._process_fee()
        spent_base_amount = self.order.quantity * self.order.price
        bought_quote_amount = self.order.quantity - fee
        self._update_wallet(
            delta_quote=bought_quote_amount, delta_base=-spent_base_amount
        )

    def _market_sell_order(self):
        fee = self._process_fee()
        bought_base_amount = self.order.price * (self.order.quantity - fee)
        self._update_wallet(
            delta_quote=-self.order.quantity, delta_base=bought_base_amount
        )

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
        if self.order.interpreted_signal == sig.hold:
            self.order.warnings = "Bypassed due to the 'hold' signal"

        else:
            if self.order.quantity > self.get_min_lot_size():
                order_processor = getattr(
                    self,
                    "_{}_{}_order".format(
                        order.order_type, order.interpreted_signal
                    ),
                )
                order_processor()
                self.order.fulfilled = True

            else:
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
            else get_broker(market=analyzer.monitor.market())
        )

    def _validate_order(self):
        order = self.analyzer.order
        if not order.price:
            order.price = self.broker.get_price(at_time=order.timestamp)

        return order

    def _save_and_report_trade(self):
        self.analyzer.monitor.report_trade(payload=self.analyzer.order)

    def _hold(self):
        order = self.analyzer.order
        order.interpreted_signal = sig.hold
        self.analyzer.order = self.broker.execute(order)

        if self.backtesting:
            self._save_and_report_trade()

    def _buy(self):
        order = self._validate_order()
        order.interpreted_signal = sig.buy
        order.quantity = 0.998 * (order.quantity / order.price)

        self.analyzer.order = self.broker.execute(order)
        self._save_and_report_trade()

    def _sell(self):
        order = self._validate_order()
        order.interpreted_signal = sig.sell
        order.quantity = 0.998 * (self.broker.get_portfolio().quote)

        self.analyzer.order = self.broker.execute(order)
        self._save_and_report_trade()

    def _naked_sell(self):
        pass

    def _double_naked_sell(self):
        pass

    def _double_buy(self):
        pass

    def _long_stopped(self):
        self.analyzer.order.order_type = "market"
        self._sell()
        self.analyzer.order.order_type = self.setup.default_order_type

    def _short_stopped(self):
        pass

    def proceed(self):
        signal = self.analyzer.order.generated_signal
        signal_handler = getattr(self, "_{}".format(signal))

        signal_handler()


class OrderHandler:
    def __init__(self, bases_symbols: list):
        self.bases_symbols = bases_symbols
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
            [executor.analyzer.order.score for executor in buy_queue]
        )

        for executor in buy_queue:
            weight = executor.analyzer.order.score / score_sum
            leverage = executor.analyzer.order.leverage

            executor.analyzer.order.quantity = (
                leverage * weight * avaliable_base_amount
            )

        return buy_queue

    @staticmethod
    def _proceed_each_buy_on(buy_queue: list):
        for executor in buy_queue:
            executor.proceed()
            buy_queue.pop(buy_queue.index(executor))

    def _buy_queue_handler(self, buy_queue):
        # Splits executors into separate queues, indexed by base symbol
        base_indexed_queues = {
            base_symbol: list() for base_symbol in self.bases_symbols
        }

        for executor in buy_queue:
            market = executor.analyzer.monitor.market()
            buy_queue = base_indexed_queues.get(market.base_symbol)
            buy_queue.append(executor)

            if executor.analyzer.monitor.is_master:
                executor.proceed()
                buy_queue.pop(buy_queue.index(executor))

        queues = base_indexed_queues.values()
        for queue in queues:
            if queue:
                _queue = self._populate_orders_quantities(queue)
                self._proceed_each_buy_on(buy_queue=_queue)

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
            self._buy_queue_handler(buy_queue)

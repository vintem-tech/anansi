"""Handle with orders, in case of backtesting"""

import pandas as pd

from ..marketdata.klines import PriceFromStorage
from ..utils.databases.sql.schemas import Order, MarketPartition, Signals

sig = Signals()

class BackTestingBroker:
    """Handle with orders, in case of backtesting"""

    def __init__(self, monitor):
        self.monitor = monitor
        self.setup = monitor.operation.backtesting()
        self.fee_rate_decimal = self.setup.fee_rate_decimal
        self.order = Order()
        self.portfolio = MarketPartition()
        self.order_id = 1

    def get_price_at(self, desired_datetime) -> float:
        """Instant (past or present) artificial average trading price"""

        return PriceFromStorage(
            market=self.monitor.market(),
            price_metrics=self.setup.price_metrics,
        ).get_price_at(desired_datetime)

    def get_portfolio(self) -> MarketPartition:
        """The portfolio composition, given a market"""

        return MarketPartition(
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

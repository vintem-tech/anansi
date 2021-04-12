import pandas as pd

from ..marketdata.operators.classifiers import get_classifier
from ..tools.time_handlers import time_frame_to_seconds
from ..utils.databases.sql.models import Monitor, Operation
from ..utils.databases.sql.schemas import (
    ClassifierPayLoad,
    DateTimeType,
    OperationalModes,
    Order,
    Sides,
)
from .orderflow import OrderHandler

modes = OperationalModes()
sides = Sides()


class Analyzer:
    def __init__(self, monitor: Monitor):
        self.monitor = monitor
        self.setup = monitor.operation.setup()
        self.classifier = get_classifier(
            payload=ClassifierPayLoad(
                market=monitor.market(),
                classifier=self.setup.classifier,
                backtesting=bool(monitor.operation.mode == modes.backtesting),
            )
        )
        self.was_updated = False
        self.has_a_trade_occurred = False
        self.current_timestamp: int = None
        self.order = Order()
        self.result = pd.DataFrame()

    def _is_a_new_analysis_needed(self) -> bool:
        last_check = self.monitor.last_check.by_classifier_at
        step = time_frame_to_seconds(self.setup.classifier.setup.time_frame)
        return bool(self.current_timestamp >= last_check + step)

    def _evaluate_side(self) -> str:
        score = self.result.score
        if score > self.setup.trading.score_that_triggers_long_side:
            return sides.long

        if score < self.setup.trading.score_that_triggers_short_side:
            return sides.short
        return sides.zeroed

    def _reset(self):
        self.was_updated = False
        self.has_a_trade_occurred = False

    def _refresh_result(self):
        self.result = self.classifier.get_restult_at(self.current_timestamp)
        self.monitor.save_result("classifier", self.result)

    def _populate_order(self):
        self.order.test_order = bool(
            self.monitor.operation.mode == modes.test_trading
        )
        self.order.timestamp = self.current_timestamp
        self.order.order_type = self.setup.trading.default_order_type
        self.order.leverage = self.setup.trading.leverage
        self.order.score = self.result.score
        self.order.from_side = self.monitor.position.side
        self.order.to_side = self._evaluate_side()

    def _update(self):
        self.was_updated = True
        self.monitor.last_check.update(by_classifier_at=self.current_timestamp)

    def check_at(self, desired_datetime: DateTimeType):
        self._reset()
        self.current_timestamp = desired_datetime

        if self._is_a_new_analysis_needed():
            self._refresh_result()
            self._populate_order()
            self._update()

    def save_trading_log(self):
        self.monitor.save_trading_log(payload=self.order.dict())


class Trader:
    def __init__(self, operation: Operation):
        monitors = operation.list_of_active_monitors()
        self.analyzers = [Analyzer(monitor) for monitor in monitors]
        self.order_handler = OrderHandler(
            bases_symbols=operation.bases_symbols()
        )
        # self.stop_loss = [StopLoss(monitor) for monitor in monitors]

    def check_at(self, desired_datetime: DateTimeType):
        # for stop in self.stop_loss:
        #    stop.check_at(desired_datetime)

        updated_analyzers = list()
        for analyzer in self.analyzers:
            analyzer.check_at(desired_datetime)
            if analyzer.was_updated:
                updated_analyzers.append(analyzer)

        if updated_analyzers:
            self.order_handler.process(analyzers=updated_analyzers)
